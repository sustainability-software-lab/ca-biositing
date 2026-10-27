import pandas as pd
import numpy as np
from datetime import datetime, timezone
from prefect import task, get_run_logger
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session
from ca_biositing.pipeline.utils.engine import engine

@task(retries=3, retry_delay_seconds=10)
def load_xrd_record(df: pd.DataFrame):
    """
    Upserts XRD records into the database.
    """
    logger = get_run_logger()
    if df is None or df.empty:
        logger.info("No XRD record data to load.")
        return

    logger.info(f"Upserting {len(df)} XRD records...")

    try:
        from ca_biositing.datamodels.models import XrdRecord
        now = datetime.now(timezone.utc)
        table_columns = {c.name for c in XrdRecord.__table__.columns}
        records = df.replace({np.nan: None}).to_dict(orient='records')

        clean_records = []
        for record in records:
            clean_record = {k: v for k, v in record.items() if k in table_columns}
            clean_record['updated_at'] = now
            if clean_record.get('created_at') is None:
                clean_record['created_at'] = now
            clean_records.append(clean_record)

        if clean_records:
            from ca_biositing.pipeline.utils.qc_protected_records import (
                build_qc_aware_update_dict,
                get_unsynced_qc_protected_record_ids,
            )

            with engine.connect() as conn:
                with Session(bind=conn) as session:
                    protected_record_ids = get_unsynced_qc_protected_record_ids(
                        session,
                        XrdRecord.__tablename__,
                        [str(r["record_id"]) for r in clean_records if r.get("record_id") is not None],
                    )
                    stmt = insert(XrdRecord).values(clean_records)
                    update_dict = build_qc_aware_update_dict(
                        XrdRecord,
                        stmt,
                        protected_record_ids,
                    )
                    upsert_stmt = stmt.on_conflict_do_update(
                        index_elements=['record_id'],
                        set_=update_dict
                    )
                    session.execute(upsert_stmt)
                    session.commit()

        logger.info("Successfully upserted XRD records.")
    except Exception:
        logger.exception("Failed to load XRD records")
        raise
