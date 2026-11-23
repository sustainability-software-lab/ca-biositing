import pandas as pd
import numpy as np
from datetime import datetime, timezone
from prefect import task, get_run_logger
from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session
from ca_biositing.pipeline.utils.engine import get_engine

@task(retries=3, retry_delay_seconds=10)(retries=3, retry_delay_seconds=10)
def load_observation(df: pd.DataFrame):
    """
    Upserts observations into the database.
    """
    logger = get_run_logger()
    if df is None or df.empty:
        logger.info("No observation data to load.")
        return

    logger.info(f"Upserting {len(df)} observations...")

    try:
        now = datetime.now(timezone.utc)
        records = df.replace({np.nan: None}).to_dict(orient='records')

        from ca_biositing.datamodels.models import Observation
        engine = get_engine()
        with engine.connect() as conn:
            with Session(bind=conn) as session:
                for i, record in enumerate(records):
                    record['updated_at'] = now
                    if record.get('created_at') is None:
                        record['created_at'] = now

                    # Supersede any observation for this (record_id, record_type, parameter_id)
                    # recorded under a different unit (e.g. a corrected ppm value replacing a
                    # stale %), since unit_id is part of the upsert conflict key below and a
                    # unit change would otherwise insert alongside the old row instead of
                    # replacing it.
                    session.execute(
                        delete(Observation).where(
                            Observation.record_id == record['record_id'],
                            Observation.record_type == record['record_type'],
                            Observation.parameter_id == record['parameter_id'],
                            Observation.unit_id.is_distinct_from(record['unit_id']),
                        )
                    )

                    stmt = insert(Observation).values(record)
                    update_dict = {
                        c.name: stmt.excluded[c.name]
                        for c in Observation.__table__.columns
                        if c.name not in ['id', 'created_at', 'record_id']
                    }
                    upsert_stmt = stmt.on_conflict_do_update(
                        index_elements=['record_id', 'record_type', 'parameter_id', 'unit_id'],
                        set_=update_dict
                    )
                    session.execute(upsert_stmt)
                session.commit()
        logger.info("Successfully upserted observations.")
    except Exception as e:
        logger.error(f"Failed to load observations: {e}")
        raise
