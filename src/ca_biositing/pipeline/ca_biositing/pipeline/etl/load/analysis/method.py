import numpy as np
import pandas as pd
from datetime import datetime, timezone
from prefect import task, get_run_logger
from sqlmodel import select
from sqlalchemy.orm import Session


@task(retries=3, retry_delay_seconds=10)
def load_method(df: pd.DataFrame):
    """Insert missing Method rows keyed by canonical method name."""
    logger = get_run_logger()

    if df is None or df.empty:
        logger.info("No Method metadata to load.")
        return

    if "name" not in df.columns:
        logger.warning("Method metadata is missing required 'name' column.")
        return

    method_df = df.copy()
    method_df["name"] = method_df["name"].astype(str).str.strip()
    method_df = method_df.replace({"": np.nan, "nan": np.nan, "None": np.nan, "-": np.nan}).dropna(subset=["name"])

    if method_df.empty:
        logger.info("No valid Method names found after cleaning.")
        return

    if "description" in method_df.columns:
        method_df["description"] = method_df["description"].astype(str).replace({"nan": None, "None": None, "": None})

    if "duration" in method_df.columns:
        method_df["duration"] = pd.to_numeric(method_df["duration"], errors="coerce")

    method_df = method_df.drop_duplicates(subset=["name"], keep="first")
    method_names = method_df["name"].tolist()

    from ca_biositing.datamodels.models import Method
    from ca_biositing.pipeline.utils.engine import engine

    with engine.connect() as conn:
        with Session(bind=conn) as session:
            existing_methods = session.execute(
                select(Method).where(Method.name.in_(method_names))
            ).scalars().all()

            methods_by_name = {}
            for method in existing_methods:
                methods_by_name.setdefault(method.name, []).append(method)

            now = datetime.now(timezone.utc)
            inserted_count = 0
            updated_count = 0

            for _, row in method_df.iterrows():
                name = row["name"]
                description = row.get("description") if "description" in method_df.columns else None
                duration = row.get("duration") if "duration" in method_df.columns else None

                existing_for_name = methods_by_name.get(name, [])
                if existing_for_name:
                    for method in existing_for_name:
                        if description is not None:
                            method.description = description
                        if pd.notna(duration):
                            method.duration = float(duration)
                        method.updated_at = now
                        updated_count += 1
                    continue

                payload = Method(
                    name=name,
                    description=description,
                    duration=float(duration) if pd.notna(duration) else None,
                    created_at=now,
                    updated_at=now,
                )
                session.add(payload)
                inserted_count += 1

            if inserted_count == 0 and updated_count == 0:
                logger.info("No Method rows to insert or update.")
                return

            session.commit()
            logger.info(f"Method load complete: inserted={inserted_count}, updated={updated_count}.")
