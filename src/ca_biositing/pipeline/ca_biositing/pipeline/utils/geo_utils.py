from __future__ import annotations

import functools
from functools import partial
import json
import logging
import math
import os
from pathlib import Path
import re
from typing import Any, Iterable, Mapping, Sequence

import addfips
from geopy.extra.rate_limiter import RateLimiter
from geopy.geocoders import GoogleV3
import numpy as np
import pandas as pd
from prefect import get_run_logger
from shapely.geometry import Point, shape
from shapely.prepared import prep
from sqlmodel import Session, select

# Initialize FIPS helper at module level (safe, no network/keys required)
af = addfips.AddFIPS()

_DATA_DIR = Path(__file__).resolve().parent / "data"
_CA_COUNTIES_GEOJSON_PATH = _DATA_DIR / "ca_counties.geojson"
_CA_LOOKUP_JSON_PATH = _DATA_DIR / "ca_zip_city_county.json"

# California bounding box (with slight coastal/border margin)
_CA_LAT_MIN = 32.4
_CA_LAT_MAX = 42.1
_CA_LON_MIN = -124.6
_CA_LON_MAX = -114.0
_COASTAL_BORDER_TOLERANCE_DEG = 0.05

_ZIP5_RE = re.compile(r"\b(\d{5})(?:-\d{4})?\b")
_TRAILING_ZIP5_RE = re.compile(r"(?:^|[,\s])(\d{5})(?:-\d{4})?\s*$")
_LATLON_SPLIT_RE = re.compile(r"[\s,;]+")

address_types = [
    "street_number",
    "route",
    "intersection",
    "natural_feature",
    "airport",
    "park",
    "point_of_interest",
    "post_box",
    "landmark",
]


def _get_logger() -> logging.Logger:
    """Return Prefect run logger if inside a flow/task context, else module logger."""
    try:
        return get_run_logger()
    except Exception:
        return logging.getLogger(__name__)


@functools.lru_cache(maxsize=1)
def _load_ca_reference_data() -> dict[str, dict[str, str]]:
    """Load and cache static California county, ZIP, and city reference tables."""
    with _CA_LOOKUP_JSON_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return {
        "geoid_to_county_name": dict(data.get("geoid_to_county_name", {})),
        "county_name_to_geoid": dict(data.get("county_name_to_geoid", {})),
        "zip_to_geoid": dict(data.get("zip_to_geoid", {})),
        "zip3_to_geoid": dict(data.get("zip3_to_geoid", {})),
        "city_to_geoid": dict(data.get("city_to_geoid", {})),
    }


@functools.lru_cache(maxsize=1)
def _load_ca_county_polygons() -> list[tuple[str, Any, Any]]:
    """Load and cache prepared Shapely geometries for all 58 California counties."""
    with _CA_COUNTIES_GEOJSON_PATH.open("r", encoding="utf-8") as f:
        fc = json.load(f)

    polygons: list[tuple[str, Any, Any]] = []
    for feat in fc.get("features", []):
        props = feat.get("properties") or {}
        geoid = str(props.get("GEOID") or props.get("geoid") or "").strip().zfill(5)
        geom_raw = feat.get("geometry")
        if not geoid or not geom_raw:
            continue
        geom = shape(geom_raw)
        polygons.append((geoid, geom, prep(geom)))

    polygons.sort(key=lambda item: item[0])
    return polygons


def get_canonical_ca_county_name(geoid: str | None) -> str | None:
    """Return the canonical California county name for a 5-digit FIPS ``geoid``.

    Examples:
        - ``"06000"`` -> ``"State of California"``
        - ``"06077"`` -> ``"San Joaquin"``
        - ``"06113"`` -> ``"Yolo"``
    """
    if geoid is None:
        return None
    try:
        if pd.isna(geoid):
            return None
    except Exception:
        pass
    norm = str(geoid).strip()
    if not norm:
        return None
    if len(norm) == 4 and norm.isdigit() and norm.startswith("6"):
        norm = f"0{norm}"
    ref = _load_ca_reference_data()
    return ref["geoid_to_county_name"].get(norm)


def _is_missing(val: object) -> bool:
    """Return True if ``val`` is None, NaN/NA, or an empty/whitespace string."""
    if val is None:
        return True
    if isinstance(val, (tuple, list, dict, set)):
        return len(val) == 0
    try:
        if pd.isna(val):
            return True
    except Exception:
        pass
    if isinstance(val, str):
        stripped = val.strip()
        if not stripped or stripped.lower() in {"nan", "none", "null", "n/a", "na", "-"}:
            return True
    return False


def parse_latlon(val: object) -> tuple[float, float] | None:
    """Parse California ``(lat, lon)`` coordinates from a string or sequence.

    Handles:
    - ``"lat, lon"`` strings (with optional parentheses/brackets and whitespace)
    - ``(lat, lon)`` tuples or 2-element lists
    - Swapped ``(lon, lat)`` values when the first value is in California
      longitude ``[-124.6, -114.0]`` and the second is in California latitude
      ``[32.4, 42.1]``.

    Returns ``None`` for missing, malformed, or out-of-California coordinates
    without ever logging the raw coordinate value.
    """
    if _is_missing(val):
        return None

    first: float
    second: float

    if isinstance(val, (tuple, list)):
        if len(val) != 2:
            return None
        try:
            first = float(val[0])
            second = float(val[1])
        except (TypeError, ValueError):
            return None
    elif isinstance(val, str):
        cleaned = val.strip().strip("()[]{}")
        if not cleaned:
            return None
        parts = [p for p in _LATLON_SPLIT_RE.split(cleaned) if p]
        if len(parts) != 2:
            return None
        try:
            first = float(parts[0])
            second = float(parts[1])
        except (TypeError, ValueError):
            return None
    else:
        return None

    if not (math.isfinite(first) and math.isfinite(second)):
        return None

    # Normal order: (lat, lon) inside California bounds
    if _CA_LAT_MIN <= first <= _CA_LAT_MAX and _CA_LON_MIN <= second <= _CA_LON_MAX:
        return (first, second)

    # Swapped order: (lon, lat) inside California bounds
    if _CA_LON_MIN <= first <= _CA_LON_MAX and _CA_LAT_MIN <= second <= _CA_LAT_MAX:
        return (second, first)

    return None


def _normalize_place_token(val: object) -> str:
    """Normalize a county or city string for dictionary lookup."""
    if _is_missing(val):
        return ""
    text = str(val).strip().lower()
    # Strip trailing ZIP codes if attached
    text = re.sub(r"\b\d{5}(?:-\d{4})?\s*$", "", text).strip()
    # Strip state suffixes such as ", ca", ", california", "(ca)"
    text = re.sub(r"(?:[,\s]+|\()(?:ca|calif\.?|california)\)?$", "", text).strip()
    # Replace punctuation (except hyphens between words) with spaces
    text = re.sub(r"[.,;:()/\\'\"]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _lookup_county_name(
    val: object,
    county_to_geoid: Mapping[str, str] | None = None,
) -> str | None:
    """Match an explicit county name or 5-digit CA county geoid."""
    if _is_missing(val):
        return None

    ref = _load_ca_reference_data()
    geoid_to_name = ref["geoid_to_county_name"]
    static_county_map = ref["county_name_to_geoid"]

    raw_str = str(val).strip()
    if len(raw_str) == 4 and raw_str.isdigit() and raw_str.startswith("6"):
        raw_str = f"0{raw_str}"
    if raw_str in geoid_to_name and raw_str != "06000":
        return raw_str

    norm = _normalize_place_token(val)
    if not norm:
        return None

    # Strip trailing "county" / "co"
    base = re.sub(r"\s+(?:county|co|cnty)$", "", norm).strip()
    candidates = [base, norm, f"{base} county"]

    if county_to_geoid:
        lower_custom = {str(k).strip().lower(): str(v).strip() for k, v in county_to_geoid.items() if k and v}
        for cand in candidates:
            if cand in lower_custom and lower_custom[cand] != "06000":
                return lower_custom[cand]

    for cand in candidates:
        if cand in static_county_map:
            return static_county_map[cand]

    return None


def _lookup_coordinates_pip(lat: float, lon: float) -> str | None:
    """Resolve ``(lat, lon)`` to a 5-digit California county FIPS via point-in-polygon."""
    point = Point(lon, lat)
    polygons = _load_ca_county_polygons()

    for geoid, geom, prep_geom in polygons:
        if prep_geom.covers(point) or geom.touches(point):
            return geoid

    # Coastal / border tolerance fallback (~5 km / 0.05 deg inside CA bounds)
    best_geoid: str | None = None
    best_dist = float("inf")
    for geoid, geom, _ in polygons:
        dist = float(geom.distance(point))
        if dist < best_dist:
            best_dist = dist
            best_geoid = geoid

    if best_geoid is not None and best_dist <= _COASTAL_BORDER_TOLERANCE_DEG:
        return best_geoid

    return None


def _extract_zip5(val: object, *, trailing_only: bool = False) -> str | None:
    """Extract a 5-digit ZIP string from ``val`` if present.

    When ``trailing_only=True``, only matches a 5-digit (or ZIP+4) token
    anchored at the end of ``val`` so leading street numbers (e.g.
    ``"91342 Foothill Blvd, Some Ranch, CA"``) are never misread as ZIP codes.
    """
    if _is_missing(val):
        return None
    if isinstance(val, (int, np.integer)):
        s = str(int(val)).strip()
        return s.zfill(5) if len(s) <= 5 else None
    if isinstance(val, (float, np.floating)):
        if not math.isfinite(float(val)):
            return None
        s = str(int(round(float(val)))).strip()
        return s.zfill(5) if len(s) <= 5 else None

    text = str(val).strip()
    if re.fullmatch(r"\d+\.0+", text):
        text = text.split(".", 1)[0]
    pattern = _TRAILING_ZIP5_RE if trailing_only else _ZIP5_RE
    match = pattern.search(text)
    if match:
        return match.group(1)
    return None


def _lookup_zip_geoid(val: object, *, trailing_only: bool = False) -> str | None:
    """Resolve a 5-digit or ZIP+4 California postal code to a 5-digit county FIPS."""
    zip5 = _extract_zip5(val, trailing_only=trailing_only)
    if not zip5:
        return None

    ref = _load_ca_reference_data()
    zip_map = ref["zip_to_geoid"]
    if zip5 in zip_map:
        return zip_map[zip5]

    try:
        zip_int = int(zip5)
    except ValueError:
        return None

    if 90001 <= zip_int <= 96162:
        zip3_map = ref["zip3_to_geoid"]
        prefix = zip5[:3]
        if prefix in zip3_map:
            return zip3_map[prefix]

    return None


def _lookup_city_or_place(
    val: object,
    county_to_geoid: Mapping[str, str] | None = None,
) -> str | None:
    """Resolve a California city, town, CDP, or place description to a county FIPS."""
    if _is_missing(val):
        return None

    ref = _load_ca_reference_data()
    city_map = ref["city_to_geoid"]

    norm = _normalize_place_token(val)
    if not norm:
        return None

    # Remove leading "city of " or "town of "
    cleaned = re.sub(r"^(?:city|town|village)\s+of\s+", "", norm).strip()
    for candidate in (cleaned, norm, cleaned.replace("st ", "saint "), cleaned.replace("mt ", "mount ")):
        if candidate in city_map:
            return city_map[candidate]
        county_hit = _lookup_county_name(candidate, county_to_geoid=county_to_geoid)
        if county_hit:
            return county_hit

    return None


def get_geocoder():
    """Lazily initialize the GoogleV3 geocoder and rate limiter."""
    api_key = os.environ.get("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return None

    geolocator = GoogleV3(api_key=api_key)
    return RateLimiter(geolocator.geocode, min_delay_seconds=0.1)


def get_reverse_geocoder():
    """Lazily initialize the REVERSE GoogleV3 geocoder and rate limiter."""
    api_key = os.environ.get("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return None

    geolocator = GoogleV3(api_key=api_key)
    return RateLimiter(partial(geolocator.reverse, exactly_one=True), min_delay_seconds=0.1)


def get_component(name_length: str, comp_type: str, addy_components: Iterable[Mapping[str, Any]]) -> str | None:
    """Extract a specific address component from a GoogleV3 geocoder response."""
    return next((name[name_length] for name in addy_components if comp_type in name["types"]), None)


def resolve_county_geoid(
    county: object = None,
    latlong: object = None,
    zip_code: object = None,
    city: object = None,
    street: object = None,
    *,
    lat: object = None,
    lon: object = None,
    location_desc: object = None,
    county_to_geoid: Mapping[str, str] | None = None,
    row: Mapping[str, Any] | pd.Series | None = None,
    allow_external_geocode: bool = False,
) -> str:
    """Resolve a California 5-digit county FIPS ``geoid`` using the 6-tier offline-first cascade.

    Priority order:
      1. Explicit county name (``county`` / ``sampling_county`` / ``prod_county``)
      2. Coordinate point-in-polygon against the 58 CA county polygons
         (``latlong`` or ``(lat, lon)``)
      3. Offline California 5-digit / ZIP+4 postal code lookup (``zip_code``)
      4. Offline California city / place lookup (``city`` / ``location_desc``)
      5. Optional external geocoder fallback (only when ``allow_external_geocode=True``
         and ``GOOGLE_MAPS_API_KEY`` is configured; sub-county components are
         discarded immediately in memory)
      6. State fallback ``"06000"``

    Never logs or prints raw sub-county inputs.
    """
    if isinstance(county, (Mapping, pd.Series)) and row is None:
        row = county
        county = None

    if row is not None:
        def _first_present(keys: Sequence[str]) -> object:
            for k in keys:
                if k in row and not _is_missing(row[k]):
                    return row[k]
            return None

        if _is_missing(county):
            county = _first_present(
                ("county", "sampling_county", "Sampling_County", "prod_county", "Prod_County", "geography_id")
            )
        if _is_missing(latlong):
            latlong = _first_present(
                ("latlong", "sampling_latlong", "Sampling_LatLong", "prod_latlong", "Prod_LatLong")
            )
        if _is_missing(lat):
            lat = _first_present(("lat", "latitude"))
        if _is_missing(lon):
            lon = _first_present(("lon", "long", "longitude"))
        if _is_missing(zip_code):
            zip_code = _first_present(
                ("zip_code", "zip", "sampling_zip", "Sampling_Zip", "prod_zip", "Prod_Zip")
            )
        if _is_missing(city):
            city = _first_present(
                ("city", "sampling_city", "Sampling_City", "prod_city", "Prod_City")
            )
        if _is_missing(street):
            street = _first_present(
                ("street", "address_line1", "sampling_street", "Sampling_Street", "prod_street", "Prod_Street")
            )
        if _is_missing(location_desc):
            location_desc = _first_present(
                (
                    "location_desc",
                    "sampling_location",
                    "Sampling_Location",
                    "prod_location",
                    "Prod_Location",
                    "location_name",
                    "fieldstorage_location",
                    "field_storage_location",
                )
            )

    # Priority 1: Explicit county name
    county_geoid = _lookup_county_name(county, county_to_geoid=county_to_geoid)
    if county_geoid:
        return county_geoid

    # Priority 2: Offline Coordinate Point-in-Polygon
    coords = parse_latlon(latlong)
    if coords is None and not _is_missing(lat) and not _is_missing(lon):
        coords = parse_latlon((lat, lon))
    if coords is not None:
        pip_geoid = _lookup_coordinates_pip(coords[0], coords[1])
        if pip_geoid:
            return pip_geoid

    # Priority 3: Offline California ZIP Code Lookup
    zip_geoid = _lookup_zip_geoid(zip_code)
    if zip_geoid:
        return zip_geoid

    # Priority 4: Offline California City / Place Name Lookup
    city_geoid = _lookup_city_or_place(city, county_to_geoid=county_to_geoid)
    if city_geoid:
        return city_geoid

    if not _is_missing(location_desc):
        desc_geoid = _lookup_city_or_place(location_desc, county_to_geoid=county_to_geoid)
        if desc_geoid:
            return desc_geoid
        desc_zip_geoid = _lookup_zip_geoid(location_desc, trailing_only=True)
        if desc_zip_geoid:
            return desc_zip_geoid

    # Check if `county` or `city` contained a ZIP or coordinate string passed via a single-arg caller
    if not _is_missing(county):
        alt_coords = parse_latlon(county)
        if alt_coords is not None:
            pip_geoid = _lookup_coordinates_pip(alt_coords[0], alt_coords[1])
            if pip_geoid:
                return pip_geoid
        alt_zip = _lookup_zip_geoid(county, trailing_only=True)
        if alt_zip:
            return alt_zip
        alt_city = _lookup_city_or_place(county, county_to_geoid=county_to_geoid)
        if alt_city:
            return alt_city

    # Priority 5: Optional External Geocoder Fallback
    if allow_external_geocode and os.environ.get("GOOGLE_MAPS_API_KEY"):
        parts = [
            str(p).strip()
            for p in (street, city, zip_code)
            if not _is_missing(p)
        ]
        if parts:
            query = ", ".join([*parts, "CA"])
            try:
                geocode = get_geocoder()
                if geocode is not None:
                    info = geocode(query)
                    if info is not None and hasattr(info, "raw"):
                        addy_components = info.raw.get("address_components", [])
                        ext_county = get_component("long_name", "administrative_area_level_2", addy_components)
                        ext_state = get_component("short_name", "administrative_area_level_1", addy_components)
                        del info
                        if ext_county:
                            resolved = _lookup_county_name(ext_county, county_to_geoid=county_to_geoid)
                            if resolved:
                                return resolved
                            if ext_state:
                                fips = af.get_county_fips(ext_county, ext_state)
                                if isinstance(fips, str) and fips.startswith("06") and len(fips) == 5:
                                    return fips
            except Exception:
                # Never log the raw query or exception message containing an address
                pass

    # Priority 6: State Default
    return "06000"


def get_geoid(val: object, county_to_geoid: Mapping[str, str] | None = None) -> str:
    """Lookup 5-digit California county GEOID for a county, city, ZIP, or coordinate value.

    Never logs raw ``val`` strings.
    """
    if _is_missing(val):
        return "06000"
    return resolve_county_geoid(county=val, county_to_geoid=county_to_geoid)


def ensure_anonymous_county_addresses(
    session: Session,
    geoids: Iterable[str | None],
    etl_run_id: object = None,
    lineage_group_id: object = None,
) -> dict[str, int]:
    """Ensure ``Place`` and canonical anonymous ``LocationAddress`` rows exist for ``geoids``.

    For every ``geoid`` in ``geoids`` (normalizing empty/None values to ``"06000"``):
    1. Ensures a ``Place`` row exists with canonical ``county_name`` from
       ``get_canonical_ca_county_name(geoid)``, ``state_name="CALIFORNIA"``,
       and ``state_fips="06"`` (backfilling ``county_name``, ``state_name``,
       and ``state_fips`` on existing ``Place`` rows if ``None``).
    2. Queries existing canonical anonymous ``LocationAddress`` rows where
       ``geography_id == geoid``, ``is_anonymous IS TRUE``, and all sub-county
       columns (``address_line1``, ``address_line2``, ``city``, ``zip``,
       ``lat``, ``lon``) are ``NULL``, selecting ``min(id)`` deterministically.
    3. Inserts a single canonical anonymous ``LocationAddress`` row for any
       ``geoid`` that does not yet have one.

    Returns:
        Mapping ``{geoid: location_address.id}``.
    """
    from ca_biositing.datamodels.models import LocationAddress, Place

    normalized_set: set[str] = set()
    for raw_geoid in geoids:
        if _is_missing(raw_geoid):
            normalized_set.add("06000")
        else:
            norm = str(raw_geoid).strip()
            if len(norm) == 4 and norm.isdigit() and norm.startswith("6"):
                norm = f"0{norm}"
            normalized_set.add(norm or "06000")

    if not normalized_set:
        return {}

    sorted_geoids = sorted(normalized_set)

    # 1. Ensure Place rows exist and have canonical county_name / state metadata
    for geoid in sorted_geoids:
        canonical_county_name = get_canonical_ca_county_name(geoid)
        state_fips = geoid[:2] if len(geoid) >= 2 else "06"
        county_fips = geoid[2:] if len(geoid) == 5 else None

        place = session.get(Place, geoid)
        if place is None:
            place = Place(
                geoid=geoid,
                state_name="CALIFORNIA",
                state_fips=state_fips,
                county_name=canonical_county_name,
                county_fips=county_fips,
                agg_level_desc="STATE" if geoid == "06000" else "COUNTY",
            )
            session.add(place)
        else:
            modified = False
            if place.county_name is None and canonical_county_name is not None:
                place.county_name = canonical_county_name
                modified = True
            if place.state_name is None:
                place.state_name = "CALIFORNIA"
                modified = True
            if place.state_fips is None:
                place.state_fips = state_fips
                modified = True
            if place.county_fips is None and county_fips is not None:
                place.county_fips = county_fips
                modified = True
            if modified:
                session.add(place)

    session.flush()

    # 2. Query existing canonical anonymous LocationAddress rows (ordered by id ASC)
    stmt = (
        select(LocationAddress)
        .where(
            LocationAddress.geography_id.in_(sorted_geoids),
            LocationAddress.is_anonymous.is_(True),
            LocationAddress.address_line1.is_(None),
            LocationAddress.address_line2.is_(None),
            LocationAddress.city.is_(None),
            LocationAddress.zip.is_(None),
            LocationAddress.lat.is_(None),
            LocationAddress.lon.is_(None),
        )
        .order_by(LocationAddress.id.asc())
    )
    existing_rows = session.exec(stmt).all()

    geoid_to_address_id: dict[str, int] = {}
    for row in existing_rows:
        if (
            row.geography_id is not None
            and row.id is not None
            and row.geography_id not in geoid_to_address_id
        ):
            geoid_to_address_id[row.geography_id] = int(row.id)

    # 3. Insert missing canonical anonymous LocationAddress rows
    new_rows: list[tuple[str, LocationAddress]] = []
    for geoid in sorted_geoids:
        if geoid in geoid_to_address_id:
            continue
        addr_kwargs: dict[str, Any] = {
            "geography_id": geoid,
            "address_line1": None,
            "address_line2": None,
            "city": None,
            "zip": None,
            "lat": None,
            "lon": None,
            "is_anonymous": True,
        }
        if not _is_missing(etl_run_id):
            addr_kwargs["etl_run_id"] = etl_run_id
        if not _is_missing(lineage_group_id):
            addr_kwargs["lineage_group_id"] = lineage_group_id
        anon_addr = LocationAddress(**addr_kwargs)
        session.add(anon_addr)
        new_rows.append((geoid, anon_addr))

    if new_rows:
        session.flush()
        for geoid, anon_addr in new_rows:
            if anon_addr.id is not None:
                geoid_to_address_id[geoid] = int(anon_addr.id)

    return geoid_to_address_id


# main function; need to define names of columns where address and latlong are stored
def parse_addresses(df, address_column="merged_address", merge_columns=[], lat="latitude", long="longitude"):
    logger = _get_logger()

    # if address info is distributed among several columns, merge them together
    if len(merge_columns) > 0:
        df["is_na"] = (
            df[merge_columns].isnull().sum(axis=1) >= 3
        )  # if there are three or more columns with NaN values it's invalid
        df[address_column] = df[merge_columns].apply(
            lambda row: ", ".join(row.fillna("").values.astype(str)), axis=1
        )
    else:
        df["is_na"] = df[address_column].isnull()

    # Lazily initialize geocoder inside the function
    geocode = get_geocoder()
    reverse = get_reverse_geocoder()

    address_df = pd.DataFrame(
        columns=[
            "geocoded_status",
            "closest_address_line_1",
            "closest_address_line_2",
            "closest_city",
            "closest_county",
            "closest_state",
            "closest_postal_code",
            "closest_latitude",
            "closest_longitude",
        ]
    )
    geoid_df = pd.DataFrame(
        columns=[
            "closest_geoid",
            "closest_state_name",
            "closest_state_fips",
            "closest_county_name",
            "closest_county_fips",
        ]
    )

    # Record only row indices of unparsable addresses (never raw address values)
    unparsable: list[str] = []
    for index, row in df.iterrows():
        if row["geocoded_status"] != "pending":
            continue
        try:
            # Check if we have coordinates to fallback on if the address is missing
            has_coords = (
                lat is not None
                and long is not None
                and row[lat] is not None
                and isinstance(row[lat], (float, int))
                and row[long] is not None
                and isinstance(row[long], (float, int))
            )

            if row["is_na"] and not has_coords:
                raise Exception(
                    "Row does not contain enough information (address or coordinates) to validate."
                )

            if geocode is None:
                raise Exception("Could not set up the geocoder.")
            if reverse is None:
                raise Exception("Could not set up the reverse geocoder.")

            # use address information to geocode. if that isn't available, use the latitude and longitude
            info = geocode(row[address_column])
            if info is None:
                # if lat and long exist
                if (
                    lat is not None
                    and long is not None
                    and row[lat] is not None
                    and isinstance(row[lat], (float, int))
                    and row[long] is not None
                    and isinstance(row[long], (float, int))
                ):
                    # use reverse geocoder
                    info = reverse(f"{row[lat]}, {row[long]}")
                else:
                    raise Exception("Could not find the address via the geocoder.")
            info = info.raw
            addy_components = info["address_components"]

            # get address components
            address = ""
            row_types = np.concatenate([name["types"] for name in addy_components])
            for possible_type in address_types:
                if (
                    possible_type in row_types
                    and get_component("long_name", possible_type, addy_components) is not None
                ):
                    address = (
                        address
                        + get_component("long_name", possible_type, addy_components)
                        + " "
                    )

            county = get_component("long_name", "administrative_area_level_2", addy_components)
            city = get_component("short_name", "locality", addy_components)
            state = get_component("short_name", "administrative_area_level_1", addy_components)
            zip_code = get_component("short_name", "postal_code", addy_components)
            zip_suffix = get_component("short_name", "postal_code_suffix", addy_components)

            # get latitude and longitude
            if (
                lat is not None
                and long is not None
                and not row[lat] is not None
                and isinstance(row[lat], (float, int))
                and not row[long] is not None
                and isinstance(row[long], (float, int))
            ):
                latitude = row[lat]
                longitude = row[long]
            else:
                latitude = (
                    info["geometry"]["location"]["lat"]
                    if isinstance(info["geometry"]["location"]["lat"], float)
                    else None
                )
                longitude = (
                    info["geometry"]["location"]["lng"]
                    if isinstance(info["geometry"]["location"]["lng"], float)
                    else None
                )

            address_result = {
                "geocoded_status": "true",
                "closest_address_line_1": address,
                "closest_address_line_2": None,
                "closest_city": city,
                "closest_county": county,
                "closest_state": state,
                "closest_postal_code": (
                    zip_code + "-" + zip_suffix
                    if (isinstance(zip_code, str) and isinstance(zip_suffix, str))
                    else zip_code
                ),
                "closest_latitude": latitude,
                "closest_longitude": longitude,
            }

            # get geoids
            geoid = (
                af.get_county_fips(county, state)
                if (isinstance(county, str) and isinstance(state, str))
                else None
            )
            state_fips = geoid[:2] if isinstance(geoid, str) else None
            county_fips = geoid[2:] if isinstance(geoid, str) else None
            geoid_result = {
                "closest_geoid": geoid,
                "closest_state_name": state,
                "closest_state_fips": state_fips,
                "closest_county_name": county,
                "closest_county_fips": county_fips,
            }

            if geoid is None or geoid == "":
                unparsable = unparsable + [str(index)]
                geoid_result = {
                    "closest_geoid": "00000",
                    "closest_state_name": None,
                    "closest_state_fips": None,
                    "closest_county_name": None,
                    "closest_county_fips": None,
                }

        except Exception:
            # Record only row index (never raw address or exception message containing address)
            unparsable = unparsable + [str(index)]

            if (
                lat is not None
                and long is not None
                and not row[lat] is not None
                and isinstance(row[lat], (float, int))
                and not row[long] is not None
                and isinstance(row[long], (float, int))
            ):
                latitude = row[lat]
                longitude = row[long]
            else:
                latitude = 0
                longitude = 0

            address_result = {
                "geocoded_status": "false",
                "closest_address_line_1": None,
                "closest_address_line_2": None,
                "closest_city": None,
                "closest_county": None,
                "closest_state": None,
                "closest_postal_code": None,
                "closest_latitude": latitude,
                "closest_longitude": longitude,
            }
            geoid_result = {
                "closest_geoid": "00000",
                "closest_state_name": None,
                "closest_state_fips": None,
                "closest_county_name": None,
                "closest_county_fips": None,
            }

        address_df.loc[index] = address_result
        geoid_df.loc[index] = geoid_result

    if len(unparsable) > 0:
        unparsable_msg = ", ".join(unparsable)
        logger.warning(f"Some addresses were unparsable at row indices: {unparsable_msg}")

    # returns a gdf and a df that need to be added to the database
    return address_df, geoid_df
