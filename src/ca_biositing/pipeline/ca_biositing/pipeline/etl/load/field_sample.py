import pandas as pd
import numpy as np
from datetime import datetime, timezone
from prefect import task, get_run_logger
from sqlalchemy import select
from sqlalchemy.orm import Session
from ca_biositing.pipeline.utils.engine import get_engine
from ca_biositing.pipeline.utils.geo_utils import get_geoid

@task
def load_field_sample(df: pd.DataFrame):
    """
    Upserts FieldSample records into the database.
    Links sampling_location_id based on preserved location metadata.
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
        logger.info("No FieldSample record data to load.")
        return

    logger.info(f"Upserting {len(df)} FieldSample records...")

    try:
        from ca_biositing.datamodels.models import FieldSample, LocationAddress, Place
        now = datetime.now(timezone.utc)
        table_columns = {c.name for c in FieldSample.__table__.columns}

        # Replace NaN with None for database compatibility
        records = df.replace({np.nan: None}).to_dict(orient='records')

        with Session(get_engine()) as session:
            # Prepare geography mapping and location mapping
            places = session.execute(select(Place.geoid, Place.county_name)).all()
            county_to_geoid = {p.county_name.lower(): p.geoid for p in places if p.county_name}

            # First pass: collect all geoids that will be referenced
            geoids_to_use = set()
            for record in records:
                geoid = get_geoid(record.get('sampling_location'), county_to_geoid)
                geoids_to_use.add(geoid)

            # Ensure all referenced Place records exist before inserting samples
            existing_geoids = {p.geoid for p in places}
            for geoid in geoids_to_use:
                if geoid not in existing_geoids:
                    # Create Place record with minimal metadata (geoid only)
                    place_data = {"geoid": geoid}
                    session.add(Place(**place_data))
                    logger.info(f"Created Place record for geoid={geoid}")
            session.flush()

            # Fetch all existing LocationAddress records into memory for bulk lookup
            # Including ZIP in the lookup key as per plan
            addresses = session.execute(
                select(
                    LocationAddress.id,
                    LocationAddress.geography_id,
                    LocationAddress.address_line1,
                    LocationAddress.city,
                    LocationAddress.zip
                )
            ).all()
            addr_map = {}
            for a in addresses:
                key = (a.geography_id, a.address_line1, a.city, a.zip)
                addr_map[key] = a.id

            # Fetch all existing FieldSample records to avoid N+1 queries
            # Use (name, resource_id) as the lookup key for better specificity
            existing_samples = session.execute(select(FieldSample)).scalars().all()
            samples_map = {(s.name, s.resource_id): s for s in existing_samples}

            for record in records:
                name = record.get('name')
                resource_id = record.get('resource_id')
                if not name:
                    logger.warning("Skipping record with missing 'name'.")
                    continue

                # Determine sampling_location_id
                geoid = get_geoid(record.get('sampling_location'), county_to_geoid)
                addr1 = record.get('sampling_street')
                city = record.get('sampling_city')
                zip_code = record.get('sampling_zip')

                # Standardize for lookup
                addr1 = str(addr1).strip() if addr1 else None
                city = str(city).strip() if city else None
                zip_code = str(zip_code).strip() if zip_code else None

                sampling_location_id = addr_map.get((geoid, addr1, city, zip_code))

                # Check for existing record by (name, resource_id) using in-memory map
                lookup_key = (name, resource_id)
                existing_record = samples_map.get(lookup_key)

                clean_record = {k: v for k, v in record.items() if k in table_columns}
                clean_record['sampling_location_id'] = sampling_location_id
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
                    new_fs = FieldSample(**clean_record)
                    session.add(new_fs)
                    # Update in-memory map to prevent duplicates within the same batch
                    samples_map[lookup_key] = new_fs

            session.commit()
        logger.info("Successfully upserted FieldSample records.")
    except Exception as e:
        logger.error(f"Failed to load FieldSample records: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise
