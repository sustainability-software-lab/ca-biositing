from datetime import datetime, timezone

import numpy as np
import pandas as pd
from prefect import get_run_logger, task
from sqlalchemy import or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from ca_biositing.pipeline.utils.engine import get_engine


@task
def load(df: pd.DataFrame) -> bool:
    """
    Upserts InfrastructureWastewaterTreatmentPlants records into the database.
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
        from ca_biositing.datamodels.models import InfrastructureWastewaterTreatmentPlants

        now = datetime.now(timezone.utc)
        table_columns = {
            c.name for c in InfrastructureWastewaterTreatmentPlants.__table__.columns
        }
        records = df.replace({np.nan: None}).to_dict(orient="records")

        engine = get_engine()
        with engine.connect() as conn:
            with Session(bind=conn) as session:
                batch_size = 1000
                for start in range(0, len(records), batch_size):
                    clean_chunk = []
                    for i, record in enumerate(records[start : start + batch_size], start=start):
                        if i > 0 and i % 500 == 0:
                            logger.info(f"Processed {i} records...")

                        clean_record = {}
                        for k, v in record.items():
                            if k not in table_columns or (k == "plant_id" and v is None):
                                continue
                            if k == "plant_id" and isinstance(v, float) and v.is_integer():
                                v = int(v)
                            clean_record[k] = v

                        clean_record["updated_at"] = now
                        if clean_record.get("created_at") is None:
                            clean_record["created_at"] = now
                        clean_chunk.append(clean_record)

                    names = {
                        r.get("name") for r in clean_chunk if r.get("name") is not None
                    }
                    conditions = []
                    if names:
                        conditions.append(
                            InfrastructureWastewaterTreatmentPlants.name.in_(names)
                        )
                    if any(r.get("name") is None for r in clean_chunk):
                        conditions.append(
                            InfrastructureWastewaterTreatmentPlants.name.is_(None)
                        )

                    existing_by_key = {}
                    if conditions:
                        stmt1 = select(InfrastructureWastewaterTreatmentPlants).where(
                            or_(*conditions)
                        )
                        for existing in session.scalars(stmt1):
                            existing_by_key.setdefault(
                                (existing.name, existing.address_id), existing
                            )

                    pending_by_key = {}
                    for clean_record in clean_chunk:
                        nat_key = (clean_record.get("name"), clean_record.get("address_id"))
                        existing_record = existing_by_key.get(nat_key)
                        if existing_record is not None:
                            for k, v in clean_record.items():
                                if k not in ("plant_id", "created_at"):
                                    setattr(existing_record, k, v)
                        elif nat_key in pending_by_key:
                            prev_created = pending_by_key[nat_key]["created_at"]
                            pending_by_key[nat_key] = {
                                **pending_by_key[nat_key],
                                **clean_record,
                                "created_at": prev_created,
                            }
                        else:
                            pending_by_key[nat_key] = clean_record

                    # Deduplicate PKs per statement (avoids PostgreSQL CardinalityViolation on
                    # ON CONFLICT DO UPDATE); rows without PK rely on the SERIAL sequence.
                    pk_batch_by_id = {}
                    no_pk_batch = []
                    for pending in pending_by_key.values():
                        if "plant_id" in pending:
                            pk_id = pending["plant_id"]
                            if pk_id in pk_batch_by_id:
                                prev_created = pk_batch_by_id[pk_id]["created_at"]
                                pk_batch_by_id[pk_id] = {
                                    **pk_batch_by_id[pk_id],
                                    **pending,
                                    "created_at": prev_created,
                                }
                            else:
                                pk_batch_by_id[pk_id] = pending
                        else:
                            no_pk_batch.append(pending)

                    if pk_batch_by_id:
                        pk_batch = list(pk_batch_by_id.values())
                        stmt = insert(InfrastructureWastewaterTreatmentPlants).values(
                            pk_batch
                        )
                        update_cols = set(pk_batch[0].keys()) - {"plant_id", "created_at"}
                        update_dict = {col: stmt.excluded[col] for col in update_cols}
                        upsert_stmt = stmt.on_conflict_do_update(
                            index_elements=["plant_id"],
                            set_=update_dict,
                        )
                        session.execute(upsert_stmt)

                    if no_pk_batch:
                        session.execute(
                            insert(InfrastructureWastewaterTreatmentPlants).values(
                                no_pk_batch
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
