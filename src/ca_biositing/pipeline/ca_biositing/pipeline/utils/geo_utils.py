import pandas as pd
import numpy as np
import os
from functools import partial
from prefect import task, get_run_logger

address_types = ['street_number', 'route', "intersection", "natural_feature", "airport", "park", "point_of_interest", 'post_box', 'landmark']

# ---------------------------------------------------------------------------
# California bounding box — used to reject geocoder results outside the state.
# All facilities in this project are in California; any result outside these
# bounds is treated as a geocoding failure.
# Generous margins to include all CA territory (Channel Islands, etc.).
# ---------------------------------------------------------------------------
_CA_LAT_MIN = 32.5
_CA_LAT_MAX = 42.0
_CA_LON_MIN = -124.5
_CA_LON_MAX = -114.1


def _is_in_california(lat, lon) -> bool:
    """Return True if the coordinate falls within California's bounding box."""
    if lat is None or lon is None:
        return False
    try:
        return _CA_LAT_MIN <= float(lat) <= _CA_LAT_MAX and _CA_LON_MIN <= float(lon) <= _CA_LON_MAX
    except (TypeError, ValueError):
        return False


def _get_fips_helper():
    """Lazily initialize the AddFIPS helper to avoid import-time failures."""
    import addfips
    return addfips.AddFIPS()


def get_geocoder():
    """
    Lazily initialize the GoogleV3 geocoder and rate limiter.
    This avoids ConfigurationErrors at import time if the API key is missing.

    The geocoder is constrained to California (US) via the Google Maps
    ``components`` filter.  This is a hard API-level constraint that prevents
    ambiguous street names from being resolved to locations outside California
    (e.g. a short address like "5069 W CLAYTON" being geocoded to Asia).

    Both current callers of this function (food processing facilities and
    biodiesel plants) are California-only datasets, so this constraint is
    always correct.
    """
    from geopy.geocoders import GoogleV3
    from geopy.extra.rate_limiter import RateLimiter

    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        # During CI test collection, we want to allow import but fail only when used
        # However, to satisfy geopy's requirement without breaking collection:
        return None

    geolocator = GoogleV3(api_key=api_key)
    # Wrap geocode with a CA/US components filter so every call is constrained
    # to California regardless of what the address string contains.
    geocode_ca = partial(
        geolocator.geocode,
        components={"country": "US", "administrative_area": "CA"},
    )
    return RateLimiter(geocode_ca, min_delay_seconds=0.1)

def get_geoid(val, county_to_geoid):
    """
    Lookup GEIOD for a given county name or string.
    """
    if pd.isna(val) or not val:
        return "06000"
    val_clean = str(val).strip().lower()
    if val_clean in county_to_geoid:
        return county_to_geoid[val_clean]
    if f"{val_clean} county" in county_to_geoid:
        return county_to_geoid[f"{val_clean} county"]
    return "06000"

# scour the json for the appropriate address component
def get_component(name_length, comp_type, addy_components):
    return next((name[name_length] for name in addy_components if comp_type in name["types"]), None)

# main function; need to define names of columns where address and latlong are stored
def parse_addresses(df, address_column="address", merge_columns=[], lat="latitude", long="longitude"):
    """Geocode addresses in a DataFrame using the Google Maps API.

    For each row the function attempts to geocode the address string.  The
    result is stored in two output DataFrames:

    * ``address_df`` — closest address components + lat/lon.
    * ``geoid_df``   — FIPS geoid components.

    A row is considered a **geocoding failure** (``closest_latitude=None``) when:
      - The row's address column is null/empty (``is_na`` flag).
      - The geocoder is not configured (``GOOGLE_MAPS_API_KEY`` not set).
      - The geocoder API returns ``None`` (address not found).
      - The geocoder API raises any exception (network error, quota, etc.).
      - The API response is missing expected fields (``address_components``,
        ``geometry``, etc.).

    In all failure cases ``closest_latitude`` and ``closest_longitude`` are
    set to ``None`` so the caller (the transform's ``_apply_geocoding()``) can
    unambiguously detect failure via ``lat is None`` and set
    ``geocode_status='failed'``.

    The geoid lookup failure (``geoid is None``) is logged as a warning but
    does NOT cause the row to be treated as a geocoding failure — lat/lon may
    still be valid even when the county FIPS lookup fails.
    """
    try:
        logger = get_run_logger()
    except Exception:
        import logging
        logger = logging.getLogger(__name__)

    # if address info is distributed among several columns, merge them together
    if len(merge_columns) > 0:
        df['is_na'] = df[merge_columns].isnull().sum(axis=1) >= 3 # if there are three or more columns with NaN values it's invalid
        df[address_column] = df[merge_columns].apply(lambda row: ', '.join(row.fillna('').values.astype(str)), axis=1)
    else:
        df['is_na'] = df[address_column].isnull()

    # Lazily initialize geocoder inside the function
    geocode = get_geocoder()

    address_df = pd.DataFrame(columns=["closest_address_line_1", "closest_address_line_2", "closest_city", "closest_county", "closest_state", "closest_postal_code", "closest_latitude", "closest_longitude"])
    geoid_df = pd.DataFrame(columns=["closest_geoid", "closest_state_name", "closest_state_fips", "closest_county_name", "closest_county_fips"])

    # put weird addresses in an array for displaying in a warning
    unparsable = []
    for index, row in df.iterrows():
        # Default failure result — overwritten on success below.
        # Setting these here (not inside the except block) ensures they are
        # always defined even if an unexpected exception escapes the try block.
        address_result = {
            "closest_address_line_1": None,
            "closest_address_line_2": None,
            "closest_city": None,
            "closest_county": None,
            "closest_state": None,
            "closest_postal_code": None,
            "closest_latitude": None,
            "closest_longitude": None,
        }
        geoid_result = {
            "closest_geoid": "00000",
            "closest_state_name": None,
            "closest_state_fips": None,
            "closest_county_name": None,
            "closest_county_fips": None,
        }

        try:
            if row['is_na'] or geocode is None:
                # Address is null or geocoder not configured — treat as failure.
                raise ValueError("Address is null or geocoder not configured")

            # Call the geocoder.  Returns None when the address is not found.
            geocode_result = geocode(row[address_column])
            if geocode_result is None:
                # Address not found by the geocoder — treat as failure.
                raise ValueError(f"Geocoder returned no result for: {row[address_column]!r}")

            info = geocode_result.raw
            addy_components = info['address_components']

            # get address components
            address = ""
            row_types = np.concatenate([name["types"] for name in addy_components])
            for possible_type in address_types:
                if possible_type in row_types and get_component("long_name", possible_type, addy_components) != None:
                    address = address + get_component("long_name", possible_type, addy_components) + " "
                    if possible_type != "street_number" and possible_type != "route":
                        print(get_component("long_name", possible_type, addy_components), possible_type)

            county = get_component("long_name", "administrative_area_level_2", addy_components)
            city = get_component("short_name", "locality", addy_components)
            state = get_component("short_name", "administrative_area_level_1", addy_components)
            zip_code = get_component("short_name", "postal_code", addy_components)
            zip_suffix = get_component("short_name", "postal_code_suffix", addy_components)

            # get latitude and longitude
            # FIX: use .get() so that DataFrames without pre-existing lat/lon
            # columns (e.g. the geocoder test set) don't raise KeyError here,
            # which was previously caught by the bare except and silently
            # prevented every geocoding API call from succeeding.
            existing_lat = row.get(lat) if hasattr(row, "get") else row[lat] if lat in row.index else None
            existing_lon = row.get(long) if hasattr(row, "get") else row[long] if long in row.index else None
            if isinstance(existing_lat, (float, int)) and not np.isnan(existing_lat) and \
               isinstance(existing_lon, (float, int)) and not np.isnan(existing_lon):
                latitude = existing_lat
                longitude = existing_lon
            else:
                latitude = info['geometry']['location']['lat'] if isinstance(info['geometry']['location']['lat'], float) else None
                longitude = info['geometry']['location']['lng'] if isinstance(info['geometry']['location']['lng'], float) else None

            # CA bounds validation — reject any geocoder result that falls
            # outside California's bounding box.  The components filter on
            # get_geocoder() is the primary constraint; this is a safety net
            # that catches any edge case where the API ignores the filter.
            # Treat out-of-CA results as a geocoding failure so the row gets
            # geocode_status='failed' and is not stored with wrong coordinates.
            if latitude is not None and longitude is not None and not _is_in_california(latitude, longitude):
                logger.warning(
                    "Geocoder returned out-of-CA coordinates (lat=%.4f, lon=%.4f) for %r "
                    "— rejecting result and treating as geocoding failure.",
                    latitude, longitude, row[address_column],
                )
                raise ValueError(
                    f"Out-of-CA geocoder result: lat={latitude}, lon={longitude} "
                    f"for address {row[address_column]!r}"
                )

            address_result = {
                "closest_address_line_1": address,
                "closest_address_line_2": None,
                "closest_city": city,
                "closest_county": county,
                "closest_state": state,
                "closest_postal_code": zip_code + "-" + zip_suffix if (isinstance(zip_code, str) and isinstance(zip_suffix, str)) else zip_code,
                "closest_latitude": latitude,
                "closest_longitude": longitude,
            }

            # get geoids — failure here does NOT invalidate lat/lon
            try:
                af = _get_fips_helper()
                geoid = af.get_county_fips(county, state) if (isinstance(county, str) and isinstance(state, str)) else None
                state_fips = geoid[:2] if isinstance(geoid, str) else None
                county_fips = geoid[2:] if isinstance(geoid, str) else None
                geoid_result = {
                    "closest_geoid": geoid,
                    "closest_state_name": state,
                    "closest_state_fips": state_fips,
                    "closest_county_name": county,
                    "closest_county_fips": county_fips,
                }
                if geoid is None:
                    unparsable = unparsable + [str(index) + "\t" + str(row[address_column])]
            except Exception as geoid_exc:
                logger.warning(
                    "FIPS geoid lookup failed for index %s (%r): %s — lat/lon still valid.",
                    index, row[address_column], geoid_exc,
                )
                # geoid_result stays as the default failure dict; lat/lon is still valid.

        except Exception as exc:
            # Geocoding failed — log and mark as unparsable.
            unparsable = unparsable + [str(index) + "\t" + str(row[address_column])]
            logger.debug("Geocoding failed for index %s (%r): %s", index, row[address_column], exc)

            # If the row already has valid lat/lon (e.g. pre-geocoded rows passed
            # through parse_addresses for address-component enrichment only),
            # preserve those coordinates even though the geocoder call failed.
            # This is safe: the transform's geocode_status logic only sets
            # geocode_status='failed' for rows that were actually attempted
            # (in to_geocode), not for rows that already had coordinates and
            # were skipped by the delta check.
            existing_lat = row.get(lat) if hasattr(row, "get") else row[lat] if lat in row.index else None
            existing_lon = row.get(long) if hasattr(row, "get") else row[long] if long in row.index else None
            if isinstance(existing_lat, (float, int)) and not pd.isna(existing_lat) and \
               isinstance(existing_lon, (float, int)) and not pd.isna(existing_lon):
                address_result["closest_latitude"] = existing_lat
                address_result["closest_longitude"] = existing_lon
            # Otherwise closest_latitude stays None (failure default set above),
            # which signals failure to the transform's geocode_status logic.

        address_df.loc[index] = address_result
        geoid_df.loc[index] = geoid_result

    # print weird addresses
    if len(unparsable) > 0:
        unparsable_msg = "\n".join(unparsable)
        logger.warning(f"Some addresses were unparsable: \n{unparsable_msg}")

    # returns a gdf and a df that need to be added to the database
    return address_df, geoid_df
