import pandas as pd

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

# from prefect import task, get_run_logger

from geopy.geocoders import GoogleV3
import os
from prefect import task, get_run_logger

import numpy as np
import pandas as pd

API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")
geolocator = GoogleV3(api_key=API_KEY)


# for other python libraries like geocoder you can do time.sleep i think
# max rate is 50 requests per second
from geopy.extra.rate_limiter import RateLimiter
geocode = RateLimiter(geolocator.geocode, min_delay_seconds=0.1)



import addfips
af = addfips.AddFIPS()

 # warning: can be slow for VERY LONG dataframes, and returns "None" for misspelled names.
 # I've added warning handling for the latter problem

address_types = ['street_number', 'route', "intersection", "natural_feature", "airport", "park", "point_of_interest", 'post_box', 'landmark']




# scour the json for the appropriate address component
def get_component(name_length, comp_type, addy_components):
  return next((name[name_length] for name in addy_components if comp_type in name["types"]), None)


# main function; need to define names of columns where address and latlong are stored
def parse_addresses(df, address_column="address", merge_columns=[], lat="latitude", long="longitude"):

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

  address_df = pd.DataFrame(columns=["closest_address_line_1", "closest_address_line_2", "closest_city", "closest_county", "closest_state", "closest_postal_code", "closest_latitude", "closest_longitude"])
  geoid_df = pd.DataFrame(columns=["closest_geoid", "closest_state_name", "closest_state_fips", "closest_county_name", "closest_county_fips"])

  # put weird addresses in an array for displaying in a warning
  unparseable = []
  for index, row in df.iterrows():
    try:
      if row['is_na']:
        # categorize as unparseable
        raise Exception

      info = geocode(row[address_column]).raw
      addy_components = info['address_components']


      # idea for address:
      # - get component types
      # - iterate through component types and see if they match the following type
      # - add to address if it exists

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
      if isinstance(row[lat], float) and isinstance(row[long], float):
        latitude = row[lat]
        longitude = row[long]
      else:
        latitude = info['geometry']['location']['lat'] if isinstance(info['geometry']['location']['lat'], float) else None
        longitude = info['geometry']['location']['lng'] if isinstance(info['geometry']['location']['lng'], float) else None


      address_result = {"closest_address_line_1": address, "closest_address_line_2": None, "closest_city": city, "closest_county": county, "closest_state": state, "closest_postal_code": zip_code + "-" + zip_suffix if (isinstance(zip, str) and isinstance(zip_suffix, str)) else None, "closest_latitude": latitude, "closest_longitude": longitude}

      # get geoids
      geoid = af.get_county_fips(county, state) if (isinstance(county, str) and isinstance(state, str)) else None
      state_fips = geoid[:2] if isinstance(geoid, str) else None
      county_fips = geoid[2:] if isinstance(geoid, str) else None
      geoid_result = {'closest_geoid': geoid, "closest_state_name": state, "closest_state_fips": state_fips, "closest_county_name": county, "closest_county_fips": county_fips}

      if geoid is None:
        unparseable = unparseable + [str(index) + "\t" + str(row[address_column])]

    except:
      # handle weird addresses
      unparseable = unparseable + [str(index) + "\t" + str(row[address_column])]

      if isinstance(row[lat], float) and isinstance(row[long], float):
        latitude = row[lat]
        longitude = row[long]
      else:
        latitude = info['geometry']['location']['lat'] if isinstance(info['geometry']['location']['lat'], float) else None
        longitude = info['geometry']['location']['lng'] if isinstance(info['geometry']['location']['lng'], float) else None

      address_result = {"closest_address_line_1": None, "closest_address_line_2": None, "closest_city": None, "closest_county": None, "closest_state": None, "closest_postal_code": None, "closest_latitude": latitude, "closest_longitude": longitude}
      geoid_result = {'closest_geoid': "00000", "closest_state_name": None, "closest_state_fips": None, "closest_county_name": None, "closest_county_fips": None}

    address_df.loc[index] = address_result
    geoid_df.loc[index] = geoid_result

  # convert to geodataframe
  # projection is NAD83 / California Albers, which is what USGS uses: https://spatialreference.org/ref/epsg/3310/
  # address_gdf = gpd.GeoDataFrame(
  #   address_df, geometry=gpd.points_from_xy(address_df["longitude"], address_df['latitude']), crs="EPSG:3310"
  # )

  # print weird addresses
  if len(unparseable) > 0:
    logger.warn(f"Some addresses were unparseable: \n{"\n".join(unparseable)}")


  # returns a gdf and a df that need to be added to the database
  return address_df, geoid_df
