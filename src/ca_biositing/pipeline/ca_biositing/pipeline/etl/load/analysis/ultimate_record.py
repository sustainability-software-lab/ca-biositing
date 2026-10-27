import pandas as pd
import numpy as np
from datetime import datetime, timezone
from prefect import task, get_run_logger
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session
from ca_biositing.pipeline.utils.engine import get_engine

@task(retries=3, retry_delay_seconds=10)
def load_ultimate_record(df: pd.DataFrame):
    """
    Upserts Ultimate records into the database.
    """
    logger = get_run_logger()
    if df is None or df.empty:
        logger.info("No Ultimate record data to load.")
        return

    logger.info(f"Upserting {len(df)} Ultimate records...")

    try:
        from ca_biositing.datamodels.models import UltimateRecord
        now = datetime.now(timezone.utc)
        table_columns = {c.name for c in UltimateRecord.__table__.columns}
        records = df.replace({np.nan: None}).to_dict(orient='records')

        from ca_biositing.pipeline.utils.qc_protected_records import (
            build_qc_aware_update_dict,
            get_unsynced_qc_protected_record_ids,
        )

        engine = get_engine()
        with engine.connect() as conn:
            with Session(bind=conn) as session:
                protected_record_ids = get_unsynced_qc_protected_record_ids(
                    session,
                    UltimateRecord.__tablename__,
                    [str(r["record_id"]) for r in records if r.get("record_id") is not None],
                )
                for record in records:
                    clean_record = {k: v for k, v in record.items() if k in table_columns}
                    clean_record['updated_at'] = now
                    if clean_record.get('created_at') is None:
                        clean_record['created_at'] = now

                    stmt = insert(UltimateRecord).values(clean_record)
                    update_dict = build_qc_aware_update_dict(
                        UltimateRecord,
                        stmt,
                        protected_record_ids,
                        record_id=str(clean_record.get("record_id") or ""),
                    )
                    upsert_stmt = stmt.on_conflict_do_update(
                        index_elements=['record_id'],
                        set_=update_dict
                    )
                    session.execute(upsert_stmt)
                session.commit()
        logger.info("Successfully upserted Ultimate records.")
    except Exception as e:
        logger.error(f"Failed to load Ultimate records: {e}")
        raise
