from __future__ import annotations

from unittest.mock import patch

import pandas as pd
from sqlalchemy import func
from sqlmodel import select

from ca_biositing.datamodels.models import LocationAddress, Place
from ca_biositing.pipeline.etl.load.location_address import load_location_address


@patch("ca_biositing.pipeline.etl.load.location_address.get_engine")
def test_load_location_address_unconditional_anonymization(mock_get_engine, session, engine):
    """Verify load_location_address unconditionally redacts sub-county fields and backfills Place."""
    mock_get_engine.return_value = engine

    # Note: Place rows are intentionally NOT pre-inserted to verify automatic creation/backfill
    df = pd.DataFrame(
        {
            "sampling_location": ["San Joaquin", "Fresno"],
            "address_line1": ["123 Main St", "456 Orchard Ave"],
            "address_line2": ["Suite 4", "Bldg B"],
            "city": ["Stockton", "Fresno"],
            "zip": ["95202", "93701"],
            "lat": [37.9577, 36.7378],
            "lon": [-121.2908, -119.7871],
            "is_anonymous": [False, False],
        }
    )

    load_location_address.fn(df)

    results = session.exec(select(LocationAddress).order_by(LocationAddress.geography_id)).all()
    assert len(results) == 2

    by_geoid = {r.geography_id: r for r in results}
    assert set(by_geoid.keys()) == {"06019", "06077"}

    for geoid in ("06077", "06019"):
        row = by_geoid[geoid]
        assert row.is_anonymous is True
        assert row.address_line1 is None
        assert row.address_line2 is None
        assert row.city is None
        assert row.zip is None
        assert row.lat is None
        assert row.lon is None

    place_06077 = session.get(Place, "06077")
    assert place_06077 is not None
    assert place_06077.county_name == "San Joaquin"
    assert place_06077.state_name is not None
    assert place_06077.state_name.upper() == "CALIFORNIA"
    assert place_06077.state_fips == "06"
    assert place_06077.county_fips == "077"

    place_06019 = session.get(Place, "06019")
    assert place_06019 is not None
    assert place_06019.county_name == "Fresno"


@patch("ca_biositing.pipeline.etl.load.location_address.get_engine")
def test_load_location_address_idempotent(mock_get_engine, session, engine):
    """Verify repeated calls and multiple rows for the same county produce 1 row per county."""
    mock_get_engine.return_value = engine

    df = pd.DataFrame(
        {
            "sampling_location": ["San Joaquin", "San Joaquin", "Fresno"],
            "address_line1": ["123 Old St", "789 Another Rd", "100 Fresno St"],
            "city": ["Stockton", "Lodi", "Fresno"],
            "zip": ["95202", "95240", "93701"],
            "is_anonymous": [False, False, True],
        }
    )

    load_location_address.fn(df)
    first_rows = session.exec(select(LocationAddress).order_by(LocationAddress.geography_id)).all()
    assert len(first_rows) == 2
    first_ids = {r.geography_id: r.id for r in first_rows}
    assert set(first_ids.keys()) == {"06019", "06077"}

    # Calling a second time with identical input must not create duplicate rows
    load_location_address.fn(df)
    second_rows = session.exec(select(LocationAddress).order_by(LocationAddress.geography_id)).all()
    assert len(second_rows) == 2
    second_ids = {r.geography_id: r.id for r in second_rows}
    assert second_ids == first_ids
    assert session.exec(select(func.count(LocationAddress.id))).one() == 2


@patch("ca_biositing.pipeline.etl.load.location_address.get_engine")
def test_load_location_address_preserves_non_anonymous_infrastructure_row(
    mock_get_engine, session, engine
):
    """Verify existing non-anonymous infrastructure LocationAddress rows remain untouched."""
    mock_get_engine.return_value = engine

    place1 = Place(geoid="06077", county_name="San Joaquin")
    session.add(place1)
    session.commit()

    facility_addr = LocationAddress(
        geography_id="06077",
        address_line1="500 Facility Rd",
        city="Stockton",
        zip="95202",
        is_anonymous=False,
    )
    session.add(facility_addr)
    session.commit()
    facility_id = facility_addr.id

    df = pd.DataFrame(
        {
            "geography_id": ["06077"],
            "city": ["Stockton"],
            "address_line1": ["500 Facility Rd"],
            "is_anonymous": [False],
        }
    )

    load_location_address.fn(df)

    all_rows = session.exec(select(LocationAddress).order_by(LocationAddress.id)).all()
    assert len(all_rows) == 2

    preserved = session.get(LocationAddress, facility_id)
    assert preserved is not None
    assert preserved.geography_id == "06077"
    assert preserved.address_line1 == "500 Facility Rd"
    assert preserved.city == "Stockton"
    assert preserved.zip == "95202"
    assert preserved.is_anonymous is False

    anon_rows = [r for r in all_rows if r.id != facility_id]
    assert len(anon_rows) == 1
    anon_row = anon_rows[0]
    assert anon_row.geography_id == "06077"
    assert anon_row.is_anonymous is True
    assert anon_row.address_line1 is None
    assert anon_row.address_line2 is None
    assert anon_row.city is None
    assert anon_row.zip is None
    assert anon_row.lat is None
    assert anon_row.lon is None
