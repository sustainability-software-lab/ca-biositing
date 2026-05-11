import pandas as pd
import numpy as np
from datetime import datetime, timezone
from prefect import task, get_run_logger
from sqlalchemy import select
from sqlalchemy.orm import Session
from ca_biositing.pipeline.utils.engine import get_engine
from ca_biositing.pipeline.utils.geo_utils import get_geoid

@task
def load_location_address(df: pd.DataFrame):
    """
    Upserts LocationAddress records into the database.
    Maps generic location names (like counties) to geography_ids during load.
    """
    import logging
    import sys
    try:
        logger = get_run_logger()
    except Exception:
        logger = logging.getLogger("prefect.task_runs")
        if not logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)

    if df is None or df.empty:
        logger.info("No LocationAddress record data to load.")
        return

    logger.info(f"Upserting {len(df)} LocationAddress records...")

    try:
        from ca_biositing.datamodels.models import LocationAddress, Place
        now = datetime.now(timezone.utc)
        table_columns = {c.name for c in LocationAddress.__table__.columns}

        # Replace NaN with None for database compatibility
        records = df.replace({np.nan: None}).to_dict(orient='records')

        with Session(get_engine()) as session:
            # Prepare geography mapping
            places = session.execute(select(Place.geoid, Place.county_name)).all()
            county_to_geoid = {p.county_name.lower(): p.geoid for p in places if p.county_name}

            # First pass: collect all geoids that will be referenced
            geoids_to_use = set()
            for record in records:
                raw_loc = record.get('sampling_location')
                geography_id = get_geoid(raw_loc, county_to_geoid)
                geoids_to_use.add(geography_id)

            # Ensure all referenced Place records exist before inserting addresses
            existing_geoids = {p.geoid for p in places}
            for geoid in geoids_to_use:
                if geoid not in existing_geoids:
                    # Create Place record with minimal metadata (geoid only)
                    place_data = {"geoid": geoid}
                    session.add(Place(**place_data))
                    logger.info(f"Created Place record for geoid={geoid}")
            session.flush()

            # Fetch all existing LocationAddress records for bulk lookup
            existing_addresses = session.execute(select(LocationAddress)).scalars().all()
            addr_map = {}
            for a in existing_addresses:
                # Key includes ZIP as per plan
                # Standardize existing record keys for lookup to ensure matching works
                addr1_std = str(a.address_line1).strip().lower() if a.address_line1 else None
                city_std = str(a.city).strip().lower() if a.city else None
                zip_std = str(a.zip).strip() if a.zip else None
                key = (a.geography_id, addr1_std, city_std, zip_std)
                addr_map[key] = a

            for record in records:
                # Map raw sampling_location to geoid
                raw_loc = record.get('sampling_location')
                geography_id = get_geoid(raw_loc, county_to_geoid)

                address_line1 = record.get('address_line1')
                city = record.get('city')
                zip_code = record.get('zip')

                # Standardize for lookup
                addr1_std = str(address_line1).strip().lower() if address_line1 else None
                city_std = str(city).strip().lower() if city else None
                zip_std = str(zip_code).strip() if zip_code else None

                # Check for existing record using in-memory map
                lookup_key = (geography_id, addr1_std, city_std, zip_std)
                existing_record = addr_map.get(lookup_key)

                clean_record = {k: v for k, v in record.items() if k in table_columns}
                clean_record['geography_id'] = geography_id
                clean_record['updated_at'] = now

                if existing_record:
                    # Update existing record
                    for key, value in clean_record.items():
                        if key not in ['id', 'created_at']:
                            setattr(existing_record, key, value)
                else:
                    # Create new record
                    if clean_record.get('created_at') is None:
                        clean_record['created_at'] = now
                    new_la = LocationAddress(**clean_record)
                    session.add(new_la)

            session.commit()
        logger.info("Successfully upserted LocationAddress records.")
    except Exception as e:
        logger.error(f"Failed to load LocationAddress records: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise
