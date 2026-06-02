import pandas as pd
import numpy as np
from prefect import task, get_run_logger
from sqlalchemy.orm import Session
from ca_biositing.pipeline.utils.engine import get_engine

@task(name="load_places")
def load_places(df: pd.DataFrame):
    """
    Upserts place records into the database.
    """
    try:
        logger = get_run_logger()
    except Exception:
        import logging
        logger = logging.getLogger(__name__)

    if df is None or df.empty:
        logger.info("No data to load.")
        return

    logger.info(f"Upserting {len(df)} place records...")

    try:
        # CRITICAL: Lazy import models inside the task to avoid Docker import hangs
        from ca_biositing.datamodels.models import Place

        # Filter columns to match the table schema
        table_columns = {c.name for c in Place.__table__.columns}
        records = df.replace({np.nan: None}).to_dict(orient='records')

        engine = get_engine()
        with engine.connect() as conn:
            with Session(bind=conn) as session:
                for i, record in enumerate(records):
                    if i > 0 and i % 100 == 0:
                        logger.info(f"Processed {i} records...")

                    # Clean record to only include valid table columns
                    clean_record = {k: v for k, v in record.items() if k in table_columns}

                    # Use geoid as the unique identifier for upsert
                    geoid = clean_record.get('geoid')
                    if not geoid:
                        logger.warning(f"Skipping record without geoid: {clean_record}")
                        continue

                    existing_record = session.query(Place).filter(Place.geoid == geoid).first()

                    if existing_record:
                        # Update existing record
                        for key, value in clean_record.items():
                            setattr(existing_record, key, value)
                    else:
                        # Insert new record
                        new_place = Place(**clean_record)
                        session.add(new_place)

                session.commit()
        logger.info("Successfully upserted place records.")
    except Exception as e:
        logger.error(f"Failed to load place records: {e}")
        raise
