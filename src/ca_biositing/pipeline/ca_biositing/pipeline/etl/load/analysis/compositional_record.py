import pandas as pd
import numpy as np
from datetime import datetime, timezone
from prefect import task, get_run_logger
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session
from ca_biositing.pipeline.utils.engine import get_engine

@task(retries=3, retry_delay_seconds=10)
def load_compositional_record(df: pd.DataFrame):
    """
    Upserts Compositional records into the database.
    """
    logger = get_run_logger()
    if df is None or df.empty:
        logger.info("No Compositional record data to load.")
        return

    logger.info(f"Upserting {len(df)} Compositional records...")

    try:
        from ca_biositing.datamodels.models import CompositionalRecord
        now = datetime.now(timezone.utc)
        table_columns = {c.name for c in CompositionalRecord.__table__.columns}
        records = df.replace({np.nan: None}).to_dict(orient='records')

        engine = get_engine()
        with engine.connect() as conn:
            with Session(bind=conn) as session:
                for record in records:
                    clean_record = {k: v for k, v in record.items() if k in table_columns}
                    clean_record['updated_at'] = now
                    if clean_record.get('created_at') is None:
                        clean_record['created_at'] = now

                    stmt = insert(CompositionalRecord).values(clean_record)
                    update_dict = {
                        c.name: stmt.excluded[c.name]
                        for c in CompositionalRecord.__table__.columns
                        if c.name not in ['id', 'created_at', 'record_id']
                    }
                    upsert_stmt = stmt.on_conflict_do_update(
                        index_elements=['record_id'],
                        set_=update_dict
                    )
                    session.execute(upsert_stmt)
                session.commit()
        logger.info("Successfully upserted Compositional records.")
    except Exception as e:
        logger.error(f"Failed to load Compositional records: {e}")
        raise
