"""
Load CARB food processing facilities into the database.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timezone
from prefect import task, get_run_logger
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from ca_biositing.pipeline.utils.engine import get_engine


@task
def load(df: pd.DataFrame) -> bool:
    """
    Upserts infrastructure_food_processing_facilities records.
    """
    logger = get_run_logger()

    if df is None or df.empty:
        logger.info("No data to load.")
        return True

    logger.info(f"Upserting {len(df)} records...")

    try:
        # Lazy import to avoid Docker import hangs
        from ca_biositing.datamodels.models import InfrastructureFoodProcessingFacilities

        now = datetime.now(timezone.utc)
        table_columns = {c.name for c in InfrastructureFoodProcessingFacilities.__table__.columns}
        # FIX: replace both NaN *and* empty strings with None so the DB
        # receives NULL rather than "" for unpopulated text columns.
        records = df.replace({np.nan: None}).replace({"": None}).to_dict(orient="records")

        engine = get_engine()
        with Session(engine) as session:
            with session.begin():
                for i, record in enumerate(records):
                    if i > 0 and i % 500 == 0:
                        logger.info(f"Processed {i} records...")

                    clean_record = {k: v for k, v in record.items() if k in table_columns}

                    clean_record["updated_at"] = now
                    if clean_record.get("created_at") is None:
                        clean_record["created_at"] = now

                    stmt = insert(InfrastructureFoodProcessingFacilities).values(clean_record)

                    update_dict = {
                        c.name: stmt.excluded[c.name]
                        for c in InfrastructureFoodProcessingFacilities.__table__.columns
                        if c.name not in ["processing_facility_id", "created_at"]
                    }

                    upsert_stmt = stmt.on_conflict_do_update(
                        index_elements=["name", "address", "city", "zip"],
                        set_=update_dict,
                    )

                    session.execute(upsert_stmt)

        logger.info("Successfully upserted records.")
        return True

    except Exception as exc:
        logger.error(f"Failed to load records: {exc}")
        return False
