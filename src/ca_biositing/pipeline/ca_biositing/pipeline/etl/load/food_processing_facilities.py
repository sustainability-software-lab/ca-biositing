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
from sqlalchemy import func
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
                    if c.name not in ["processing_facility_id", "created_at", "geocode_status"]
                }

                # geocode_status: use COALESCE so an incoming NULL never overwrites
                # an existing 'success' or 'failed' value.  This prevents the sheet
                # ETL from clobbering geocode_status on rows that were skipped by the
                # delta check (they have geocode_status=None in the DataFrame but
                # already have a resolved status in the DB from a previous run).
                tbl = InfrastructureFoodProcessingFacilities.__table__
                update_dict["geocode_status"] = func.coalesce(
                    stmt.excluded["geocode_status"],
                    tbl.c["geocode_status"],
                )

                upsert_stmt = stmt.on_conflict_do_update(
                    index_elements=["name", "address", "city", "zip"],
                    set_=update_dict,
                )

                session.execute(upsert_stmt)

    return len(records)


def _parse_datetime_or_none(value) -> "datetime | None":
    """Coerce a value to a datetime or return None.

    Handles proper datetimes, ISO strings, and silently discards anything
    that cannot be parsed (e.g. the malformed "29:13.8" artifact that appears
    in some seed CSVs exported from Google Sheets).
    """
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    if isinstance(value, datetime):
        return value
    try:
        return pd.to_datetime(value, utc=True).to_pydatetime()
    except Exception:
        return None


def _clean_seed_df(df: pd.DataFrame) -> pd.DataFrame:
    """Apply the same cleaning pipeline to seed CSV rows that the transform
    applies to incoming sheet rows, so the DB always stores clean values that
    will match the delta-check address keys.

    Cleaning steps (must mirror the transform pipeline):
    1. Drop ``processing_facility_id`` — the seed CSV exports the DB primary
       key, but re-inserting it causes a UniqueViolation when the row already
       exists (the PK constraint fires before the ON CONFLICT clause can
       redirect to an UPDATE).  The DB auto-generates the ID on INSERT and
       the ON CONFLICT key is ``(name, address, city, zip)``, so the PK
       column must be absent from the seed upsert payload.
    2. Collapse newlines/extra whitespace in address (``_clean_address``).
    3. Extract 5-digit ZIP (strip ZIP+4 and float artifacts like "93721.0").
    4. Hardcode state = "CA" (all facilities are in California).
    5. Normalize city to Title Case (CARB source data is ALL CAPS; mirrors
       the transform's city normalization so seed rows match incoming rows).
    6. Coerce created_at/updated_at to proper datetimes or None (guards
       against malformed values like "29:13.8" from Google Sheets exports).
    """
    df = df.copy()

    # 1. Drop processing_facility_id so the DB auto-generates it on INSERT.
    #    Re-inserting the exported PK causes a UniqueViolation when the row
    #    already exists because the PK constraint fires before ON CONFLICT.
    if "processing_facility_id" in df.columns:
        df = df.drop(columns=["processing_facility_id"])

    # 2. Normalize address whitespace (same as transform's _clean_address)
    if "address" in df.columns:
        df["address"] = df["address"].apply(
            lambda v: (
                " ".join(str(v).replace("\n", " ").replace("\r", " ").split()).strip()
                if v is not None and str(v).strip() not in ("", "nan", "None")
                else None
            )
        )

    # 3. Extract 5-digit ZIP (same regex as transform)
    if "zip" in df.columns:
        df["zip"] = df["zip"].astype(str).str.extract(r"(\d{5})")[0]

    # 4. Hardcode state so the delta-check key always uses "CA" on both sides
    df["state"] = "CA"

    # 5. Normalize city to Title Case — mirrors the transform pipeline so that
    #    seed rows loaded from the CSV always match the casing of incoming sheet
    #    rows (both go through Title Case normalization before hitting the DB).
    if "city" in df.columns:
        df["city"] = df["city"].astype("string").str.title()

    # 6. Sanitize datetime columns — unparseable values (e.g. "29:13.8") become
    #    None so _upsert_records() falls back to setting them to `now`.
    for col in ("created_at", "updated_at"):
        if col in df.columns:
            df[col] = df[col].apply(_parse_datetime_or_none)

    return df


def load_seed_csv(df: pd.DataFrame) -> int:
    """Upsert seed CSV rows into ``infrastructure_food_processing_facilities``.

    This is a plain function (not a Prefect task) so it can be called from
    the flow before the Prefect task graph is fully wired.  It uses the same
    UPSERT conflict key ``(name, address, city, zip)`` as ``load()``, making
    repeated calls fully idempotent.

    The seed rows are cleaned with ``_clean_seed_df`` before upserting so the
    DB always stores values in the same format that the transform produces for
    incoming sheet rows.  This ensures the delta-check address keys match on
    both sides and rows already geocoded in the seed are not re-queued.

    If the seed CSV does not have a ``geocode_status`` column (e.g. older seed
    files), it is added with ``None`` (pending) for all rows.  Seed rows that
    already have lat/lon will be skipped by the delta check anyway, so leaving
    their status as None is safe.

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

    logger.info(
        "[seed] Cleaning %d seed rows before upsert (address normalization, "
        "5-digit zip, state=CA)...",
        len(df),
    )
    df = _clean_seed_df(df)

    # Handle seed CSVs that predate the geocode_status column — set to None (pending)
    if "geocode_status" not in df.columns:
        logger.info(
            "[seed] Seed CSV has no 'geocode_status' column; defaulting to None (pending) "
            "for all seed rows."
        )
        df = df.copy()
        df["geocode_status"] = None

    logger.info(
        "[seed] Upserting %d rows from seed CSV into "
        "infrastructure_food_processing_facilities...",
        len(df),
    )

    try:
        count = _upsert_records(df, logger)
        logger.info(
            "[seed] Upserted %d rows into infrastructure_food_processing_facilities.",
            count,
        )
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
