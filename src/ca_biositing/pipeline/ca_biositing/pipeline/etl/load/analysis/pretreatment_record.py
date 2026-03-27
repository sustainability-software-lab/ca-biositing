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

    try:
        from ca_biositing.datamodels.models import PretreatmentRecord
        now = datetime.now(timezone.utc)
        table_columns = {c.name for c in PretreatmentRecord.__table__.columns}
        records = df.replace({np.nan: None}).to_dict(orient='records')

        clean_records = []
        for record in records:
            clean_record = {k: v for k, v in record.items() if k in table_columns}
            clean_record['updated_at'] = now
            if clean_record.get('created_at') is None:
                clean_record['created_at'] = now
            clean_records.append(clean_record)

        if clean_records:
            from ca_biositing.pipeline.utils.engine import engine
            with Session(engine) as session:
                stmt = insert(PretreatmentRecord).values(clean_records)
                update_dict = {
                    c.name: stmt.excluded[c.name]
                    for c in PretreatmentRecord.__table__.columns
                    if c.name not in ['id', 'created_at', 'record_id']
                }
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
