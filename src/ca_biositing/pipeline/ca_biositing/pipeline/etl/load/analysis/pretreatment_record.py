"""
PretreatmentRecord load module.
"""
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from prefect import task, get_run_logger
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

@task(retries=3, retry_delay_seconds=10)
def load_pretreatment_record(df: pd.DataFrame):
    """
    Loads transformed Pretreatment record data into the database.
    Performs an upsert based on record_id.
    """
    logger = get_run_logger()

    if df is None or df.empty:
        logger.warning("No data provided to PretreatmentRecord load")
        return

    logger.info(f"PretreatmentRecord load: received DataFrame with columns: {df.columns.tolist()}")
    logger.info(f"PretreatmentRecord load: DataFrame shape: {df.shape}")

    try:
        from ca_biositing.datamodels.models import PretreatmentRecord
        now = datetime.now(timezone.utc)
        table_columns = {c.name for c in PretreatmentRecord.__table__.columns}

        logger.info(f"PretreatmentRecord load: table columns are: {sorted(table_columns)}")

        records = df.replace({np.nan: None}).to_dict(orient='records')

        logger.info(f"PretreatmentRecord load: processing {len(records)} records")
        if records:
            logger.info(f"PretreatmentRecord load: first record keys: {records[0].keys()}")

        clean_records = []
        for record in records:
            clean_record = {k: v for k, v in record.items() if k in table_columns}
            clean_record['updated_at'] = now
            if clean_record.get('created_at') is None:
                clean_record['created_at'] = now
            clean_records.append(clean_record)

        if clean_records:
            logger.info(f"PretreatmentRecord load: first clean record keys: {clean_records[0].keys()}")
            logger.info(f"PretreatmentRecord load: sample record values: {clean_records[0]}")

            from ca_biositing.pipeline.utils.engine import engine
            from ca_biositing.pipeline.utils.qc_protected_records import (
                build_qc_aware_update_dict,
                get_unsynced_qc_protected_record_ids,
            )
            with Session(engine) as session:
                protected_record_ids = get_unsynced_qc_protected_record_ids(
                    session,
                    PretreatmentRecord.__tablename__,
                    [str(r["record_id"]) for r in clean_records if r.get("record_id") is not None],
                )
                stmt = insert(PretreatmentRecord).values(clean_records)
                update_dict = build_qc_aware_update_dict(
                    PretreatmentRecord,
                    stmt,
                    protected_record_ids,
                )
                upsert_stmt = stmt.on_conflict_do_update(
                    index_elements=['record_id'],
                    set_=update_dict
                )
                session.execute(upsert_stmt)
                session.commit()

        logger.info("Successfully upserted Pretreatment records.")
    except Exception as e:
        logger.exception(f"Error during PretreatmentRecord load: {e}")
        raise
