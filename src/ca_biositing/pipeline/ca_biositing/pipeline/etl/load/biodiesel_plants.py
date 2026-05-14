import pandas as pd
import numpy as np
from datetime import datetime, timezone
from prefect import task, get_run_logger
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import select
from sqlalchemy.orm import Session
from ca_biositing.pipeline.utils.engine import get_engine
from ca_biositing.pipeline.utils.geo_utils import get_geoid

@task
def load(df: pd.DataFrame) -> bool:
    """
    Upserts BiodieselPlant records into the database.
    Returns True on success, False on failure.
    """
    logger = get_run_logger()

    if df is None or df.empty:
        logger.info("No data to load.")
        return True

    logger.info(f"Upserting {len(df)} records...")

    try:
        # Lazy import to avoid Docker import hangs
        from ca_biositing.datamodels.models import InfrastructureBiodieselPlants
        from ca_biositing.datamodels.models import LocationAddress, Place

        now = datetime.now(timezone.utc)

        # Filter columns to match the table schema
        table_columns = {c.name for c in InfrastructureBiodieselPlants.__table__.columns}
        records = df.replace({np.nan: None}).to_dict(orient="records")

        engine = get_engine()
        with engine.connect() as conn:
            with Session(bind=conn) as session:

                for i, record in enumerate(records):
                    if i > 0 and i % 500 == 0:
                        logger.info(f"Processed {i} records...")

                    # Keep only columns that exist in the model
                    clean_record = {k: v for k, v in record.items() if k in table_columns}
                     # Handle timestamps
                    clean_record['updated_at'] = now
                    if clean_record.get('created_at') is None:
                        clean_record['created_at'] = now

                    # Build Upsert Statement (PostgreSQL specific)
                    stmt = insert(InfrastructureBiodieselPlants).values(clean_record)

                    # Define columns to update on conflict
                    # Exclude primary keys and creation timestamps
                    update_dict = {
                        c.name: stmt.excluded[c.name]
                        for c in InfrastructureBiodieselPlants.__table__.columns
                        if c.name not in ['biodiesel_plant_id', 'created_at', 'record_id']
                    }

                    upsert_stmt = stmt.on_conflict_do_update(
                        index_elements=['biodiesel_plant_id'], # Replace with your unique constraint column
                        set_=update_dict
                    )

                    session.execute(upsert_stmt)

                session.commit()
        logger.info("Successfully upserted records.")
        return True
    except Exception as e:
        logger.error(f"Failed to load records: {e}")
        return False
