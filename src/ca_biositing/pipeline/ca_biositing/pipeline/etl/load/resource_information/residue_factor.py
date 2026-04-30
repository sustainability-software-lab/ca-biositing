"""
ETL Load: Residue Factors

Loads transformed residue factor data into the database using UPSERT pattern.
Uses composite unique key (resource_id, factor_type) for conflict resolution.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timezone
from typing import Dict
from prefect import task, get_run_logger
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from ca_biositing.pipeline.utils.engine import get_engine


@task
def load_residue_factors(df: pd.DataFrame) -> Dict[str, int]:
    """
    Upserts residue factor records into the database.

    Uses composite key (resource_id, factor_type) for conflict resolution.
    Insert new records, update existing records if resource_id + factor_type matches.

    Args:
        df: Transformed DataFrame from transform task

    Returns:
        Dictionary with counts: {'inserted': N, 'updated': M, 'failed': K}
    """
    try:
        logger = get_run_logger()
    except Exception:
        import logging

        logger = logging.getLogger(__name__)

    # ========================================
    # Validate Input
    # ========================================
    if df is None or df.empty:
        logger.info("No data to load.")
        return {"inserted": 0, "updated": 0, "failed": 0}

    logger.info(f"Loading {len(df)} residue factor records...")

    # CRITICAL: Lazy import models inside the task to avoid Docker import hangs
    from ca_biositing.datamodels.models import ResidueFactor

    # Validate resource_id is not null (required foreign key)
    if df["resource_id"].isna().any():
        null_count = df["resource_id"].isna().sum()
        logger.warning(f"Skipping {null_count} records with NULL resource_id")
        df = df.dropna(subset=["resource_id"])

    if df.empty:
        logger.warning("No valid records to load after filtering NULL resource_id.")
        return {"inserted": 0, "updated": 0, "failed": 0}

    # ========================================
    # Load Records with UPSERT
    # ========================================
    now = datetime.now(timezone.utc)

    # Filter columns to match the table schema
    table_columns = {c.name for c in ResidueFactor.__table__.columns}
    records = df.replace({np.nan: None}).to_dict(orient="records")

    inserted_count = 0
    updated_count = 0
    failed_count = 0
    failed_records = []

    engine = get_engine()
    with engine.connect() as conn:
        with Session(bind=conn) as session:
            for i, record in enumerate(records):
                if i > 0 and i % 100 == 0:
                    logger.info(f"Processed {i}/{len(records)} records...")

                try:
                    # Clean record to only include valid table columns
                    clean_record = {k: v for k, v in record.items() if k in table_columns}

                    # Handle timestamps
                    clean_record["updated_at"] = now
                    if clean_record.get("created_at") is None:
                        clean_record["created_at"] = now

                    # Ensure resource_id is set (required field)
                    if clean_record.get("resource_id") is None:
                        logger.warning(f"Skipping record {i} with NULL resource_id")
                        failed_count += 1
                        failed_records.append((i, "NULL resource_id"))
                        continue

                    # Use UPSERT pattern (ON CONFLICT DO UPDATE)
                    # Composite key: (resource_id, factor_type)
                    stmt = insert(ResidueFactor.__table__).values(**clean_record)

                    try:
                        # ON CONFLICT DO UPDATE for composite key (resource_id, factor_type)
                        stmt = stmt.on_conflict_do_update(
                            index_elements=["resource_id", "factor_type"],
                            set_={
                                "resource_name": stmt.excluded.resource_name,
                                "data_source_id": stmt.excluded.data_source_id,
                                "factor_min": stmt.excluded.factor_min,
                                "factor_max": stmt.excluded.factor_max,
                                "factor_mid": stmt.excluded.factor_mid,
                                "prune_trim_yield": stmt.excluded.prune_trim_yield,
                                "prune_trim_yield_unit_id": stmt.excluded.prune_trim_yield_unit_id,
                                "notes": stmt.excluded.notes,
                                "etl_run_id": stmt.excluded.etl_run_id,
                                "lineage_group_id": stmt.excluded.lineage_group_id,
                                "updated_at": stmt.excluded.updated_at,
                            },
                        )

                        # Try to determine if this is insert or update by checking if key exists
                        # We'll do a simple check: try a select first
                        from sqlalchemy import select

                        existing = session.execute(
                            select(ResidueFactor).where(
                                (ResidueFactor.resource_id == clean_record.get("resource_id"))
                                & (ResidueFactor.factor_type == clean_record.get("factor_type"))
                            )
                        ).first()

                        is_update = existing is not None

                    except Exception as constraint_error:
                        logger.warning(
                            f"Constraint error on record {i} - trying without ON CONFLICT: {constraint_error}"
                        )
                        # Fall back to simple insert if constraint doesn't match
                        stmt = insert(ResidueFactor.__table__).values(**clean_record)
                        is_update = False

                    session.execute(stmt)

                    if is_update:
                        updated_count += 1
                    else:
                        inserted_count += 1

                except Exception as e:
                    logger.error(
                        f"Error loading record {i}: {e}. Record: {record}"
                    )
                    failed_count += 1
                    failed_records.append((i, str(e)))
                    continue

            # Commit the transaction
            try:
                session.commit()
                logger.info("Successfully committed all records")
            except Exception as e:
                logger.error(f"Failed to commit transaction: {e}")
                session.rollback()
                failed_count += len(records) - inserted_count - updated_count

    # ========================================
    # Log Summary
    # ========================================
    logger.info(f"Load summary:")
    logger.info(f"  Inserted: {inserted_count}")
    logger.info(f"  Updated: {updated_count}")
    logger.info(f"  Failed: {failed_count}")

    if failed_records:
        logger.warning(f"Failed record details: {failed_records[:10]}")  # Show first 10

    return {
        "inserted": inserted_count,
        "updated": updated_count,
        "failed": failed_count,
    }
