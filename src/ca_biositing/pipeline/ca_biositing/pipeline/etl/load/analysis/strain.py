import pandas as pd
import numpy as np
from datetime import datetime, timezone
from prefect import task, get_run_logger
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session
from sqlalchemy import delete as sa_delete

@task(retries=3, retry_delay_seconds=10)
def load_strain(df: pd.DataFrame):
    """
    Upserts strain records into the database.
    """
    logger = get_run_logger()
    if df is None or df.empty:
        logger.info("No Strain record data to load.")
        return

    logger.info(f"Upserting {len(df)} Strain records...")

    try:
        from ca_biositing.datamodels.models.aim2_records.strain import Strain
        now = datetime.now(timezone.utc)
        table_columns = {c.name for c in Strain.__table__.columns}
        records = df.replace({np.nan: None}).to_dict(orient='records')

        clean_records = []
        seen_names = set()

        for record in records:
            name = record.get('name')
            if name is None or name in seen_names:
                continue
            seen_names.add(name)

            clean_record = {k: v for k, v in record.items() if k in table_columns}
            if 'updated_at' in table_columns:
                clean_record['updated_at'] = now
            if 'created_at' in table_columns and clean_record.get('created_at') is None:
                clean_record['created_at'] = now
            clean_records.append(clean_record)

        if clean_records:
            from ca_biositing.pipeline.utils.engine import engine
            with engine.connect() as conn:
                with Session(bind=conn) as session:
                    stmt = insert(Strain).values(clean_records)
                    update_dict = {
                        c.name: stmt.excluded[c.name]
                        for c in Strain.__table__.columns
                        if c.name not in ['id', 'created_at', 'name']
                    }
                    upsert_stmt = stmt.on_conflict_do_update(
                        index_elements=['name'],
                        set_=update_dict
                    )
                    session.execute(upsert_stmt)
                    session.commit()

                    # Conservative cleanup: remove stale strain rows that have no taxonomy
                    # fields (genus, species, strain) and are NOT in the newly loaded set.
                    try:
                        loaded_names = [r.get('name') for r in clean_records if r.get('name')]
                        if loaded_names:
                            del_stmt = sa_delete(Strain).where(
                                Strain.genus.is_(None),
                                Strain.species.is_(None),
                                Strain.strain.is_(None),
                                ~Strain.name.in_(loaded_names)
                            )
                            res = session.execute(del_stmt)
                            session.commit()
                            logger.info(f"Deleted {res.rowcount} stale Strain rows with null taxonomy and not in loaded set")
                    except Exception:
                        logger.exception("Failed during Strain cleanup step")

        logger.info("Successfully upserted Strain records.")
    except Exception:
        logger.exception("Failed to load Strain records")
        raise
