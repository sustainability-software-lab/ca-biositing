"""Unit tests for the offline-first California county resolution engine and privacy hygiene."""

from __future__ import annotations

import logging

import pandas as pd
import pytest
from sqlmodel import select

from ca_biositing.datamodels.models import LocationAddress, Place
from ca_biositing.pipeline.utils.geo_utils import (
    _load_ca_county_polygons,
    _load_ca_reference_data,
    ensure_anonymous_county_addresses,
    get_canonical_ca_county_name,
    get_geoid,
    parse_addresses,
    parse_latlon,
    resolve_county_geoid,
)


def test_static_reference_bundle_covers_all_58_ca_counties():
    """Verify static GeoJSON and JSON lookup cover all 58 California counties."""
    ref = _load_ca_reference_data()
    polygons = _load_ca_county_polygons()

    assert len(polygons) == 58
    polygon_geoids = {geoid for geoid, _, _ in polygons}
    assert len(polygon_geoids) == 58

    geoid_to_name = ref["geoid_to_county_name"]
    assert geoid_to_name["06000"] == "State of California"
    assert geoid_to_name["06077"] == "San Joaquin"
    assert geoid_to_name["06113"] == "Yolo"
    assert polygon_geoids == {k for k in geoid_to_name if k != "06000"}

    assert get_canonical_ca_county_name("06000") == "State of California"
    assert get_canonical_ca_county_name("06077") == "San Joaquin"
    assert get_canonical_ca_county_name("6077") == "San Joaquin"
    assert get_canonical_ca_county_name("99999") is None
    assert get_canonical_ca_county_name(None) is None


@pytest.mark.parametrize(
    ("raw_county", "expected_geoid"),
    [
        ("San Joaquin", "06077"),
        ("San Joaquin County", "06077"),
        ("san joaquin co.", "06077"),
        ("yolo", "06113"),
        ("Yolo County, CA", "06113"),
        ("San Luis Obispo", "06079"),
        ("Contra Costa County", "06013"),
        ("06019", "06019"),
    ],
)
def test_resolve_county_geoid_priority_1_explicit_county(raw_county, expected_geoid):
    """Priority 1 resolves explicit California county names and variations."""
    assert resolve_county_geoid(county=raw_county) == expected_geoid


def test_parse_latlon_and_priority_2_point_in_polygon():
    """Priority 2 resolves synthetic coordinates inside California counties via PIP."""
    # Standard (lat, lon) string -> UC Davis (Yolo County)
    assert parse_latlon("38.5382, -121.7617") == pytest.approx((38.5382, -121.7617))
    assert resolve_county_geoid(latlong="38.5382, -121.7617") == "06113"

    # Parenthesized coordinates -> Fresno County
    assert resolve_county_geoid(latlong="(36.7378, -119.7871)") == "06019"

    # Separate lat/lon keyword args -> Stockton (San Joaquin County)
    assert resolve_county_geoid(lat=37.9577, lon=-121.2908) == "06077"

    # Swapped (lon, lat) coordinates -> automatically corrected to (lat, lon) in Yolo County
    assert parse_latlon("-121.7617, 38.5382") == pytest.approx((38.5382, -121.7617))
    assert resolve_county_geoid(latlong="-121.7617, 38.5382") == "06113"

    # Coastal point slightly offshore near Santa Cruz pier (within 0.05 deg tolerance) -> 06087
    assert resolve_county_geoid(latlong="36.9600, -122.0200") == "06087"

    # Out-of-state coordinates (New York City and Reno NV) -> None / fallback "06000"
    assert parse_latlon("40.7128, -74.0060") is None
    assert resolve_county_geoid(latlong="40.7128, -74.0060") == "06000"
    assert resolve_county_geoid(latlong="39.5296, -119.8138") == "06000"

    # Malformed / empty coordinates
    assert parse_latlon(None) is None
    assert parse_latlon("") is None
    assert parse_latlon("invalid, coords") is None


@pytest.mark.parametrize(
    ("raw_zip", "expected_geoid"),
    [
        ("95202", "06077"),
        ("93721-1234", "06019"),
        ("95616", "06113"),
        ("95695", "06113"),
        (95354, "06099"),
        (95340.0, "06047"),
        ("90099", "06037"),  # 3-digit prefix fallback for unenumerated LA ZIP
    ],
)
def test_resolve_county_geoid_priority_3_zip_codes(raw_zip, expected_geoid):
    """Priority 3 resolves California 5-digit and ZIP+4 codes offline."""
    assert resolve_county_geoid(zip_code=raw_zip) == expected_geoid


def test_straddling_zip_95391_precedence_regression():
    """Regression test for multi-county straddling ZIP 95391 (San Joaquin / Alameda).

    1. When explicit county 'Alameda' is supplied alongside ZIP '95391', Priority 1 wins ('06001').
    2. When Alameda coordinates are supplied alongside ZIP '95391', Priority 2 wins ('06001').
    3. When only ZIP '95391' is supplied, Priority 3 deterministically resolves to '06077'.
    """
    # Priority 1 beats Priority 3
    assert resolve_county_geoid(county="Alameda", zip_code="95391") == "06001"

    # Priority 2 (point inside eastern Alameda County near Altamont Pass) beats Priority 3
    assert resolve_county_geoid(latlong="37.7250, -121.6500", zip_code="95391") == "06001"

    # Priority 3 alone resolves 95391 to primary county San Joaquin (06077)
    assert resolve_county_geoid(zip_code="95391") == "06077"


@pytest.mark.parametrize(
    ("raw_city", "expected_geoid"),
    [
        ("Stockton", "06077"),
        ("Bakersfield, CA", "06029"),
        ("Winters", "06113"),
        ("Davis, California", "06113"),
        ("Modesto, CA 95354", "06099"),
        ("Salinas", "06053"),
        ("El Centro", "06025"),
    ],
)
def test_resolve_county_geoid_priority_4_city_names(raw_city, expected_geoid):
    """Priority 4 resolves California city and place names offline."""
    assert resolve_county_geoid(city=raw_city) == expected_geoid


def test_resolve_county_geoid_row_dict_and_fallback():
    """Verify dict/Series convenience input and state default fallback ('06000')."""
    row = pd.Series(
        {
            "Sampling_County": None,
            "Sampling_LatLong": "",
            "Sampling_Zip": "95695-0001",
            "Sampling_City": "Woodland",
        }
    )
    assert resolve_county_geoid(row) == "06113"
    assert resolve_county_geoid() == "06000"
    assert resolve_county_geoid(county="", latlong=None, zip_code=None, city="UnknownPlaceXYZ") == "06000"


def test_house_numbers_in_free_text_are_never_misread_as_zip_codes():
    """Regression test: 5-digit house numbers in street/location_desc must not match ZIPs."""
    assert get_geoid("91342 Foothill Blvd, Some Ranch, CA", {}) == "06000"
    assert resolve_county_geoid(county="91342 Foothill Blvd, Some Ranch, CA") == "06000"
    assert (
        resolve_county_geoid(location_desc="Walk-in cooler at 93710 Barn Ln, provider site")
        == "06000"
    )
    # Trailing ZIPs in free-text or standalone ZIPs via get_geoid still resolve properly
    assert get_geoid("95202", {}) == "06077"
    assert resolve_county_geoid(location_desc="Storage facility, Stockton, CA 95202") == "06077"


def test_ensure_anonymous_county_addresses_idempotency_and_place_backfill(session):
    """Verify ensure_anonymous_county_addresses creates/backfills Place and deduplicates anonymous rows."""
    # Seed a bare Place row with missing county_name, state_name, and state_fips
    session.add(Place(geoid="06077", county_name=None, state_name=None, state_fips=None))
    # Seed a non-anonymous infrastructure LocationAddress for 06077 that must not be reused
    infra_addr = LocationAddress(
        geography_id="06077",
        address_line1="500 Industrial Pkwy",
        city="Stockton",
        zip="95202",
        is_anonymous=False,
    )
    session.add(infra_addr)
    session.commit()

    first_map = ensure_anonymous_county_addresses(
        session,
        ["06077", "06113", None, ""],
        etl_run_id="run-1",
        lineage_group_id=42,
    )
    assert set(first_map.keys()) == {"06077", "06113", "06000"}
    assert first_map["06077"] != infra_addr.id

    # Verify bare Place 06077 was backfilled and 06113 / 06000 were created
    place_06077 = session.get(Place, "06077")
    assert place_06077 is not None
    assert place_06077.county_name == "San Joaquin"
    assert place_06077.state_name == "CALIFORNIA"
    assert place_06077.state_fips == "06"
    assert place_06077.county_fips == "077"

    place_06113 = session.get(Place, "06113")
    assert place_06113 is not None
    assert place_06113.county_name == "Yolo"

    place_06000 = session.get(Place, "06000")
    assert place_06000 is not None
    assert place_06000.county_name == "State of California"

    # Calling a second time is strictly idempotent
    second_map = ensure_anonymous_county_addresses(session, ["06077", "06113", "06000"])
    assert second_map == first_map

    # Verify all returned anonymous rows have NULL sub-county fields
    for geoid, addr_id in second_map.items():
        row = session.get(LocationAddress, addr_id)
        assert row is not None
        assert row.geography_id == geoid
        assert row.is_anonymous is True
        assert row.address_line1 is None
        assert row.address_line2 is None
        assert row.city is None
        assert row.zip is None
        assert row.lat is None
        assert row.lon is None


def test_no_raw_subcounty_values_logged_or_printed(caplog, capsys):
    """Assert raw street addresses, cities, ZIPs, and coordinates never appear in logs or stdout."""
    secret_street = "742 Secret Grower Orchard Rd"
    secret_city = "ConfidentialHollow"
    secret_zip = "95288-9999"
    secret_coords = "37.951234, -121.298765"

    df = pd.DataFrame(
        {
            "geocoded_status": ["pending"],
            "merged_address": [f"{secret_street}, {secret_city}, CA {secret_zip}"],
            "latitude": [None],
            "longitude": [None],
        }
    )

    with caplog.at_level(logging.DEBUG):
        resolve_county_geoid(
            county=secret_street,
            latlong=secret_coords,
            zip_code=secret_zip,
            city=secret_city,
            street=secret_street,
        )
        get_geoid(secret_street, {"san joaquin": "06077"})
        parse_latlon(secret_coords)
        parse_addresses(df)

    captured = capsys.readouterr()
    combined = "\n".join([caplog.text, captured.out, captured.err])

    assert secret_street not in combined
    assert secret_city not in combined
    assert secret_zip not in combined
    assert "37.951234" not in combined
    assert "-121.298765" not in combined
