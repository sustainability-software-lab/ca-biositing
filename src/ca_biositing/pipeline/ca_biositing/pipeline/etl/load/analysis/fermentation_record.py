import pandas as pd
import numpy as np
from datetime import datetime, timezone
from prefect import task, get_run_logger
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

@task(retries=3, retry_delay_seconds=10)
def load_fermentation_record(df: pd.DataFrame):
    """
    Upserts Fermentation records into the database.
    """
    logger = get_run_logger()
    if df is None or df.empty:
        logger.info("No Fermentation record data to load.")
        return

    logger.info(f"Upserting {len(df)} Fermentation records...")

    try:
        from ca_biositing.datamodels.models import FermentationRecord
        now = datetime.now(timezone.utc)
        table_columns = {c.name for c in FermentationRecord.__table__.columns}
        records = df.replace({np.nan: None}).to_dict(orient='records')

        # Deduplicate records by record_id to avoid CardinalityViolation in bulk upsert
        seen_ids = set()
        clean_records = []

        # Log duplicates for debugging
        all_ids = [r.get('record_id') for r in records if r.get('record_id') is not None]
        id_counts = pd.Series(all_ids).value_counts()
        duplicates = id_counts[id_counts > 1]
        if not duplicates.empty:
            logger.warning(f"Found duplicate record_ids in input data: {duplicates.to_dict()}")

        for record in records:
            rid = record.get('record_id')
            if rid is None or rid in seen_ids:
                if rid in seen_ids:
                    logger.debug(f"Skipping duplicate record_id: {rid}")
                continue
            seen_ids.add(rid)

            clean_record = {k: v for k, v in record.items() if k in table_columns}
            clean_record['updated_at'] = now
            if clean_record.get('created_at') is None:
                clean_record['created_at'] = now
            clean_records.append(clean_record)

        if clean_records:
            from ca_biositing.pipeline.utils.engine import engine
            from ca_biositing.pipeline.utils.qc_protected_records import (
                build_qc_aware_update_dict,
                get_unsynced_qc_protected_record_ids,
            )

            with engine.connect() as conn:
                with Session(bind=conn) as session:
                    protected_record_ids = get_unsynced_qc_protected_record_ids(
                        session,
                        FermentationRecord.__tablename__,
                        [str(r["record_id"]) for r in clean_records if r.get("record_id") is not None],
                    )
                    stmt = insert(FermentationRecord).values(clean_records)
                    update_dict = build_qc_aware_update_dict(
                        FermentationRecord,
                        stmt,
                        protected_record_ids,
                    )
                    upsert_stmt = stmt.on_conflict_do_update(
                        index_elements=['record_id'],
                        set_=update_dict
                    )
                    session.execute(upsert_stmt)
                    session.commit()

        logger.info("Successfully upserted Fermentation records.")
    except Exception:
        logger.exception("Failed to load Fermentation records")
        raise
