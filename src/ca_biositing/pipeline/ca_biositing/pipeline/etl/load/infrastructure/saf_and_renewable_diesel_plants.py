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
    Upserts InfrastructureSafAndRenewableDieselPlants records into the database.
    Returns True on success, False on failure.
    """
    try:
        logger = get_run_logger()
    except Exception:
        import logging
        logger = logging.getLogger(__name__)

    if df is None or df.empty:
        logger.info("No data to load.")
        return True

    logger.info(f"Upserting {len(df)} records...")

    try:
        from ca_biositing.datamodels.models import InfrastructureSafAndRenewableDieselPlants

        now = datetime.now(timezone.utc)
        table_columns = {c.name for c in InfrastructureSafAndRenewableDieselPlants.__table__.columns}
        records = df.replace({np.nan: None}).to_dict(orient="records")

        engine = get_engine()
        with engine.connect() as conn:
            with Session(bind=conn) as session:
                for i, record in enumerate(records):
                    if i > 0 and i % 500 == 0:
                        logger.info(f"Processed {i} records...")

                    clean_record = {k: v for k, v in record.items() if k in table_columns}

                    stmt = insert(InfrastructureSafAndRenewableDieselPlants).values(clean_record)
                    update_dict = {
                        c.name: stmt.excluded[c.name]
                        for c in InfrastructureSafAndRenewableDieselPlants.__table__.columns
                        if c.name not in ["ibcc_index"]
                    }
                    upsert_stmt = stmt.on_conflict_do_update(
                        index_elements=["ibcc_index"],
                        set_=update_dict,
                    )
                    session.execute(upsert_stmt)

                session.commit()

        logger.info("Successfully upserted records.")
        return True
    except Exception as e:
        logger.error(f"Failed to load records: {e}")
        return False
