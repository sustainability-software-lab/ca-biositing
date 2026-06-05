"""
Load CARB food processing facilities into the database.

Provides two entry points:

* ``load(df)``          — Prefect ``@task``; used by the normal sheet ETL.
* ``load_seed_csv(df)`` — plain function; called by the flow *before* the
                          sheet ETL to restore previously geocoded rows from
                          the seed CSV without hitting the geocoder API.

Both functions share the same UPSERT logic and conflict key
``(name, address, city, zip)``.
"""

import logging
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from prefect import task, get_run_logger
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from ca_biositing.pipeline.utils.engine import get_engine

_module_logger = logging.getLogger(__name__)


def _upsert_records(df: pd.DataFrame, logger) -> int:
    """
    Core UPSERT logic shared by ``load()`` and ``load_seed_csv()``.

    Returns the number of records processed.  Raises on DB errors so the
    caller can decide how to handle them.
    """
    # Lazy import — never at module level (avoids Docker import hangs)
    from ca_biositing.datamodels.models import InfrastructureFoodProcessingFacilities

    now = datetime.now(timezone.utc)
    table_columns = {c.name for c in InfrastructureFoodProcessingFacilities.__table__.columns}
    # Replace both NaN *and* empty strings with None so the DB receives NULL
    # rather than "" for unpopulated text columns.
    records = df.replace({np.nan: None}).replace({"": None}).to_dict(orient="records")

    engine = get_engine()
    with Session(engine) as session:
        with session.begin():
            for i, record in enumerate(records):
                if i > 0 and i % 500 == 0:
                    logger.info(f"Processed {i} records...")

                clean_record = {k: v for k, v in record.items() if k in table_columns}

                clean_record["updated_at"] = now
                if clean_record.get("created_at") is None:
                    clean_record["created_at"] = now

                stmt = insert(InfrastructureFoodProcessingFacilities).values(clean_record)

                update_dict = {
                    c.name: stmt.excluded[c.name]
                    for c in InfrastructureFoodProcessingFacilities.__table__.columns
                    if c.name not in ["processing_facility_id", "created_at"]
                }

                upsert_stmt = stmt.on_conflict_do_update(
                    index_elements=["name", "address", "city", "zip"],
                    set_=update_dict,
                )

                session.execute(upsert_stmt)

    return len(records)


def load_seed_csv(df: pd.DataFrame) -> int:
    """Upsert seed CSV rows into ``infrastructure_food_processing_facilities``.

    This is a plain function (not a Prefect task) so it can be called from
    the flow before the Prefect task graph is fully wired.  It uses the same
    UPSERT conflict key ``(name, address, city, zip)`` as ``load()``, making
    repeated calls fully idempotent.

    Parameters
    ----------
    df:
        DataFrame returned by ``extract_seed_csv()``.  Must not be None or
        empty (the caller is responsible for that guard).

    Returns
    -------
    int
        Number of rows upserted.
    """
    logger = _module_logger

    if df is None or df.empty:
        logger.info("[seed] No seed rows to upsert.")
        return 0

    logger.info("[seed] Upserting %d rows from seed CSV into infrastructure_food_processing_facilities...", len(df))

    try:
        count = _upsert_records(df, logger)
        logger.info("[seed] Upserted %d rows into infrastructure_food_processing_facilities.", count)
        return count
    except Exception as exc:
        logger.error("[seed] Failed to upsert seed CSV rows: %s", exc)
        raise


@task
def load(df: pd.DataFrame) -> bool:
    """
    Upserts infrastructure_food_processing_facilities records.
    """
    logger = get_run_logger()

    if df is None or df.empty:
        logger.info("No data to load.")
        return True

    logger.info(f"[etl] Upserting {len(df)} records from sheet...")

    try:
        count = _upsert_records(df, logger)
        logger.info(f"[etl] Successfully upserted {count} records.")
        return True

    except Exception as exc:
        logger.error(f"Failed to load records: {exc}")
        return False
