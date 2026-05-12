"""
ETL Load: County Ag Report Records

Loads transformed county ag report data into the CountyAgReportRecord table.
Uses upsert pattern with unique constraint on record_id.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timezone
from prefect import task, get_run_logger
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session
from ca_biositing.pipeline.utils.engine import get_engine


@task
def load_county_ag_report_records(df: pd.DataFrame):
    """
    Upserts county ag report records into the database.

    Ensures record_id is NOT NULL before loading.
    Uses upsert pattern to handle duplicates based on record_id.
    """
    try:
        logger = get_run_logger()
    except Exception:
        import logging
        logger = logging.getLogger(__name__)

    if df is None or df.empty:
        logger.info("No county ag report records to load.")
        return

    logger.info(f"Upserting {len(df)} county ag report records...")

    try:
        # CRITICAL: Lazy import models inside the task to avoid Docker import hangs
        from ca_biositing.datamodels.models.external_data import CountyAgReportRecord
        from ca_biositing.datamodels.models.places.place import Place

        now = datetime.now(timezone.utc)

        # Validate record_id is not null
        if 'record_id' not in df.columns:
            logger.error("DataFrame missing required 'record_id' column.")
            return

        if df['record_id'].isna().any():
            null_count = df['record_id'].isna().sum()
            logger.warning(f"Skipping {null_count} records with NULL record_id")
            df = df.dropna(subset=['record_id'])

        if df.empty:
            logger.warning("No valid records to load after filtering NULL record_id.")
            return

        # Filter columns to match the table schema
        table_columns = {c.name for c in CountyAgReportRecord.__table__.columns}
        records = df.replace({np.nan: None}).to_dict(orient='records')

        engine = get_engine()
        with engine.connect() as conn:
            with Session(bind=conn) as session:
                # 1. Ensure referenced Place records exist before inserting records.
                # Place is a reference table; we ensure the FK constraint is satisfied.
                geoids = {r['geoid'] for r in records if r.get('geoid')}
                if geoids:
                    from sqlalchemy import select
                    existing_geoids = {
                        g[0] for g in session.execute(select(Place.geoid).where(Place.geoid.in_(geoids))).all()
                    }
                    missing_geoids = geoids - existing_geoids

                    if missing_geoids:
                        logger.info(f"Creating {len(missing_geoids)} missing Place records...")
                        for geoid in missing_geoids:
                            # Fallback: parse GEOID into state/county FIPS
                            place_data = {
                                "geoid": geoid,
                                "state_fips": geoid[:2] if len(geoid) >= 2 else None,
                                "county_fips": geoid[2:] if len(geoid) >= 5 else None,
                                "state_name": "CALIFORNIA" if geoid.startswith("06") else None,
                            }
                            session.add(Place(**place_data))
                        session.flush()

                success_count = 0
                for i, record in enumerate(records):
                    if i > 0 and i % 500 == 0:
                        logger.info(f"Processed {i} records...")

                    # Clean record to only include valid table columns
                    clean_record = {k: v for k, v in record.items() if k in table_columns}

                    # Handle timestamps
                    clean_record['updated_at'] = now
                    if clean_record.get('created_at') is None:
                        clean_record['created_at'] = now

                    # Use upsert pattern (ON CONFLICT DO UPDATE)
                    # Unique constraint is on record_id
                    stmt = insert(CountyAgReportRecord.__table__).values(**clean_record)

                    # Columns to update if conflict occurs
                    update_cols = {
                        c: stmt.excluded[c]
                        for c in clean_record.keys()
                        if c not in ['id', 'record_id', 'created_at']
                    }

                    if update_cols:
                        stmt = stmt.on_conflict_do_update(
                            index_elements=['record_id'],
                            set_=update_cols
                        )
                    else:
                        stmt = stmt.on_conflict_do_nothing(
                            index_elements=['record_id']
                        )

                    session.execute(stmt)
                    success_count += 1

                session.commit()
                logger.info(f"Successfully upserted {success_count} county ag report records.")

    except Exception as e:
        logger.error(f"Failed to load county ag report records: {e}")
        raise
