"""
ETL Load: Resource Images

Loads transformed resource image data into the ResourceImage table.
Uses upsert pattern with unique constraint on (resource_name, image_url, sort_order).
"""

import pandas as pd
import numpy as np
from datetime import datetime, timezone
from prefect import task, get_run_logger
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session
from ca_biositing.pipeline.utils.engine import get_engine


@task
def load_resource_images(df: pd.DataFrame):
    """
    Upserts resource image records into the database.

    Uses upsert pattern to handle duplicates (same resource_name, image_url, sort_order).
    """
    try:
        logger = get_run_logger()
    except Exception:
        import logging
        logger = logging.getLogger(__name__)

    if df is None or df.empty:
        logger.info("No data to load.")
        return

    logger.info(f"Upserting {len(df)} resource image records...")

    try:
        # CRITICAL: Lazy import models inside the task to avoid Docker import hangs
        from ca_biositing.datamodels.models import ResourceImage

        now = datetime.now(timezone.utc)

        # Filter columns to match the table schema
        table_columns = {c.name for c in ResourceImage.__table__.columns}
        records = df.replace({np.nan: None}).to_dict(orient='records')

        engine = get_engine()
        with engine.connect() as conn:
            with Session(bind=conn) as session:
                success_count = 0
                for i, record in enumerate(records):
                    if i > 0 and i % 500 == 0:
                        logger.info(f"Processed {i} records...")

                    # Clean record to only include valid table columns
                    clean_record = {k: v for k, v in record.items() if k in table_columns}

                    # Handle timestamps
                    clean_record['updated_at'] = now
                    if clean_record.get('created_at') is None:
                        clean_record['created_at'] = now

                    # Use upsert pattern (ON CONFLICT DO UPDATE)
                    # Unique constraint is on (resource_name, image_url, sort_order)
                    stmt = insert(ResourceImage.__table__).values(**clean_record)
                    stmt = stmt.on_conflict_do_update(
                        index_elements=['resource_name', 'image_url', 'sort_order'],
                        set_={
                            'resource_id': stmt.excluded.resource_id,
                            'etl_run_id': stmt.excluded.etl_run_id,
                            'lineage_group_id': stmt.excluded.lineage_group_id,
                            'updated_at': stmt.excluded.updated_at,
                        }
                    )
                    session.execute(stmt)
                    success_count += 1

                session.commit()
        logger.info(f"Successfully upserted {success_count} resource image records.")
    except Exception as e:
        logger.error(f"Failed to load resource image records: {e}")
        raise
