from datetime import datetime, timezone

import numpy as np
import pandas as pd
from prefect import get_run_logger, task
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from ca_biositing.pipeline.utils.engine import get_engine


@task
def load(df: pd.DataFrame) -> bool:
    """
    Upserts InfrastructurePetroleumPipelines records into the database.

    The geom column must contain WKB hex strings (e.g. from GeoDataFrame.wkb_hex).
    PostGIS accepts these natively.

    Returns True on success, False on failure.
    """
    try:
        logger = get_run_logger()
    except Exception:
        import logging

        logger = logging.getLogger(__name__)

    if df is None or df.empty:
        logger.info("No data to load.")
        return True

    logger.info(f"Upserting {len(df)} records...")

    try:
        # Lazy import to avoid Docker import hangs
        from ca_biositing.datamodels.models import InfrastructurePetroleumPipelines

        now = datetime.now(timezone.utc)
        table_columns = {
            c.name for c in InfrastructurePetroleumPipelines.__table__.columns
        }
        records = df.replace({np.nan: None}).to_dict(orient="records")

        engine = get_engine()
        with engine.connect() as conn:
            with Session(bind=conn) as session:
                batch_size = 1000
                for start in range(0, len(records), batch_size):
                    # Deduplicate PKs per statement (avoids PostgreSQL CardinalityViolation on
                    # ON CONFLICT DO UPDATE); rows without object_id fall back to SERIAL.
                    pk_batch_by_id = {}
                    fallback_records = []

                    for i, record in enumerate(records[start : start + batch_size], start=start):
                        if i > 0 and i % 500 == 0:
                            logger.info(f"Processed {i} records...")

                        clean_record = {}
                        for k, v in record.items():
                            if k not in table_columns or (k == "object_id" and v is None):
                                continue
                            if k == "object_id" and isinstance(v, float) and v.is_integer():
                                v = int(v)
                            clean_record[k] = v

                        clean_record["updated_at"] = now
                        if clean_record.get("created_at") is None:
                            clean_record["created_at"] = now

                        if "object_id" in clean_record:
                            obj_id = clean_record["object_id"]
                            if obj_id in pk_batch_by_id:
                                prev_created = pk_batch_by_id[obj_id]["created_at"]
                                pk_batch_by_id[obj_id] = {
                                    **pk_batch_by_id[obj_id],
                                    **clean_record,
                                    "created_at": prev_created,
                                }
                            else:
                                pk_batch_by_id[obj_id] = clean_record
                        else:
                            fallback_records.append(clean_record)

                    if pk_batch_by_id:
                        pk_batch = list(pk_batch_by_id.values())
                        stmt = insert(InfrastructurePetroleumPipelines).values(pk_batch)
                        update_cols = set(pk_batch[0].keys()) - {"object_id", "created_at"}
                        update_dict = {col: stmt.excluded[col] for col in update_cols}
                        upsert_stmt = stmt.on_conflict_do_update(
                            index_elements=["object_id"],
                            set_=update_dict,
                        )
                        session.execute(upsert_stmt)

                    if fallback_records:
                        no_pk_by_key = {}
                        for clean_record in fallback_records:
                            nat_key = (
                                clean_record.get("pipeline_name"),
                                clean_record.get("operator_name"),
                                clean_record.get("master_oid"),
                            )
                            stmt1 = select(InfrastructurePetroleumPipelines).where(
                                InfrastructurePetroleumPipelines.pipeline_name
                                == clean_record.get("pipeline_name"),
                                InfrastructurePetroleumPipelines.operator_name
                                == clean_record.get("operator_name"),
                                InfrastructurePetroleumPipelines.master_oid
                                == clean_record.get("master_oid"),
                            )
                            existing_record = session.scalars(stmt1).first()
                            if existing_record is not None:
                                for k, v in clean_record.items():
                                    if k not in ("object_id", "created_at"):
                                        setattr(existing_record, k, v)
                            elif nat_key in no_pk_by_key:
                                prev_created = no_pk_by_key[nat_key]["created_at"]
                                no_pk_by_key[nat_key] = {
                                    **no_pk_by_key[nat_key],
                                    **clean_record,
                                    "created_at": prev_created,
                                }
                            else:
                                no_pk_by_key[nat_key] = clean_record

                        if no_pk_by_key:
                            session.execute(
                                insert(InfrastructurePetroleumPipelines).values(
                                    list(no_pk_by_key.values())
                                )
                            )

                    session.flush()
                    session.expunge_all()

                session.commit()

        logger.info("Successfully upserted records.")
        return True
    except Exception as e:
        logger.error(f"Failed to load records: {e}")
        return False
