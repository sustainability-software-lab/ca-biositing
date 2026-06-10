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

    Uses ``normalize_facility_text_fields()`` from the transform module as the
    **single source of truth** for text normalization — this guarantees that
    seed rows and sheet rows are always normalized identically, preventing
    delta-check key mismatches that cause spurious geocoder API calls.

    Cleaning steps:
    1. Drop ``processing_facility_id`` — the seed CSV exports the DB primary
       key, but re-inserting it causes a UniqueViolation when the row already
       exists (the PK constraint fires before the ON CONFLICT clause can
       redirect to an UPDATE).  The DB auto-generates the ID on INSERT and
       the ON CONFLICT key is ``(name, address, city, zip)``, so the PK
       column must be absent from the seed upsert payload.
    2. Collapse newlines/extra whitespace in address (mirrors _clean_address).
    3. Extract 5-digit ZIP (strip ZIP+4 and float artifacts like "93721.0").
    4. Hardcode state = "CA" (all facilities are in California).
    5. ALL CAPS normalization for name, address, city, state — via the shared
       ``normalize_facility_text_fields()`` helper imported from the transform
       module.  This replaces the old Title Case city normalization and extends
       it to name and address as well.
    6. Drop rows where ALL FOUR conflict-key columns (name, address, city, zip)
       are blank/None — these are phantom rows (e.g. blank rows appended to the
       DB by a bad ETL run) that would be upserted as a single NULL-key row and
       pollute the table.
    7. Normalize geocode_status: convert empty string '' to None so the DB
       stores NULL (pending) rather than '' — the delta check queries for
       geocode_status == 'failed', so '' rows would be incorrectly re-queued
       for geocoding on every run.
    8. Coerce created_at/updated_at to proper datetimes or None (guards
       against malformed values like "29:13.8" from Google Sheets exports).
    """
    # Lazy import — avoids circular import at module level; the transform module
    # is only needed here at call time, not at import time.
    from ca_biositing.pipeline.etl.transform.infrastructure.food_processing_facilities import (
        normalize_facility_text_fields,
    )

    df = df.copy()

    # 1. Drop processing_facility_id so the DB auto-generates it on INSERT.
    if "processing_facility_id" in df.columns:
        df = df.drop(columns=["processing_facility_id"])

    # 2. Collapse newlines/extra whitespace in address (mirrors _clean_address).
    #    Casing is handled by normalize_facility_text_fields() in step 5.
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

    # 5. ALL CAPS normalization for name, address, city, state.
    #    Single source of truth — same function used by the transform pipeline.
    df = normalize_facility_text_fields(df)

    # 6. Drop rows where ALL FOUR conflict-key columns are blank/None.
    #    These are phantom rows (e.g. blank rows from a bad ETL run) that would
    #    be upserted as a single NULL-key row and pollute the table.
    conflict_key_cols = ["name", "address", "city", "zip"]
    present_key_cols = [c for c in conflict_key_cols if c in df.columns]
    if present_key_cols:
        all_blank_mask = df[present_key_cols].apply(
            lambda col: col.isna() | (col.astype(str).str.strip() == "")
        ).all(axis=1)
        n_dropped = all_blank_mask.sum()
        if n_dropped > 0:
            _module_logger.info(
                "[seed] Dropping %d blank-key rows (all of name/address/city/zip are empty) "
                "before upsert — these are phantom rows from a previous bad ETL run.",
                n_dropped,
            )
        df = df[~all_blank_mask].copy()

    # 7. Normalize geocode_status: '' (empty string) → None so the DB stores
    #    NULL (pending) rather than ''.  The delta check queries for
    #    geocode_status == 'failed'; '' rows would be incorrectly re-queued.
    if "geocode_status" in df.columns:
        df["geocode_status"] = df["geocode_status"].apply(
            lambda v: None if (v is None or str(v).strip() == "") else v
        )

    # 7b. Correct geocode_status='success' rows that have no latitude.
    #     These are rows where a previous ETL run wrote geocode_status='success'
    #     but failed to store lat/lon (e.g. due to the old FIPS-failure bug that
    #     cleared latitude in the except block).  The UPSERT COALESCE preserved
    #     'success' on subsequent runs even though lat/lon was null.
    #     Reset these to None (pending) so the delta check re-queues them for
    #     geocoding — a row cannot be 'success' without coordinates.
    if "geocode_status" in df.columns and "latitude" in df.columns:
        bad_success_mask = (
            (df["geocode_status"] == "success")
            & (df["latitude"].isna() | (df["latitude"].astype(str).str.strip() == ""))
        )
        n_corrected = int(bad_success_mask.sum())
        if n_corrected > 0:
            _module_logger.info(
                "[seed] Correcting %d rows with geocode_status='success' but null latitude "
                "→ resetting to None (pending) so they are re-queued for geocoding.",
                n_corrected,
            )
            df.loc[bad_success_mask, "geocode_status"] = None

    # 8. Sanitize datetime columns — unparsable values (e.g. "29:13.8") become
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
