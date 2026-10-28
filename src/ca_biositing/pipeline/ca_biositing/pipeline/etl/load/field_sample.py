from __future__ import annotations

from datetime import datetime, timezone
import logging
import sys
import traceback

import numpy as np
import pandas as pd
from prefect import get_run_logger, task
from sqlmodel import Session, select

from ca_biositing.pipeline.utils.engine import get_engine
from ca_biositing.pipeline.utils.geo_utils import (
    ensure_anonymous_county_addresses,
    resolve_county_geoid,
)

_LEGACY_RAW_LOCATION_KEYS = (
    "geography_id",
    "sampling_county",
    "Sampling_County",
    "sampling_latlong",
    "Sampling_LatLong",
    "sampling_zip",
    "Sampling_Zip",
    "sampling_city",
    "Sampling_City",
    "sampling_street",
    "Sampling_Street",
    "sampling_location",
    "Sampling_Location",
)

_LOCATION_FK_COLUMNS = (
    "sampling_location_id",
    "field_storage_location_id",
    "field_sample_storage_location_id",
)


def _is_non_empty(val: object) -> bool:
    """Return True if ``val`` is not None/NaN/blank."""
    if val is None:
        return False
    try:
        if pd.isna(val):
            return False
    except Exception:
        pass
    if isinstance(val, str) and not val.strip():
        return False
    return True


def _coerce_optional_int(val: object) -> int | None:
    """Coerce an optional FK value to ``int`` or ``None``."""
    if not _is_non_empty(val):
        return None
    try:
        return int(float(val))
    except (TypeError, ValueError):
        return None


@task
def load_field_sample(df: pd.DataFrame) -> None:
    """Upsert ``FieldSample`` records into the database.

    Preserves ``sampling_location_id``, ``field_storage_location_id``, and
    ``field_sample_storage_location_id`` resolved during transform. If
    ``sampling_location_id`` is ``None`` and legacy raw location columns are
    present on a record, resolves the county FIPS via ``resolve_county_geoid``
    and links to its canonical anonymous ``LocationAddress`` row via
    ``ensure_anonymous_county_addresses``.
    """
    try:
        logger = get_run_logger()
    except Exception:
        logger = logging.getLogger("prefect.task_runs")
        if not logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)

    if df is None or df.empty:
        logger.info("No FieldSample record data to load.")
        return

    logger.info(f"Upserting {len(df)} FieldSample records...")

    try:
        from ca_biositing.datamodels.models import FieldSample, Place

        now = datetime.now(timezone.utc)
        table_columns = {c.name for c in FieldSample.__table__.columns}

        records = df.replace({np.nan: None}).to_dict(orient="records")

        etl_run_id = None
        lineage_group_id = None
        for rec in records:
            if etl_run_id is None and rec.get("etl_run_id") is not None:
                etl_run_id = rec.get("etl_run_id")
            if lineage_group_id is None and rec.get("lineage_group_id") is not None:
                lineage_group_id = rec.get("lineage_group_id")

        with Session(get_engine()) as session:
            places = session.exec(select(Place.geoid, Place.county_name)).all()
            county_to_geoid = {
                str(p.county_name).strip().lower(): str(p.geoid).strip()
                for p in places
                if getattr(p, "county_name", None) and getattr(p, "geoid", None)
            }

            # Resolve fallback county geoids only for records missing sampling_location_id
            # that carry legacy raw location columns
            fallback_geoid_by_idx: dict[int, str] = {}
            for idx, record in enumerate(records):
                if _coerce_optional_int(record.get("sampling_location_id")) is not None:
                    continue
                if any(_is_non_empty(record.get(k)) for k in _LEGACY_RAW_LOCATION_KEYS):
                    raw_geoid = record.get("geography_id")
                    explicit_county = (
                        raw_geoid
                        if _is_non_empty(raw_geoid) and str(raw_geoid).strip() != "06000"
                        else (
                            record.get("sampling_county")
                            or record.get("Sampling_County")
                            or record.get("sampling_location")
                            or record.get("Sampling_Location")
                        )
                    )
                    fallback_geoid_by_idx[idx] = resolve_county_geoid(
                        county=explicit_county,
                        latlong=record.get("sampling_latlong") or record.get("Sampling_LatLong"),
                        zip_code=record.get("sampling_zip") or record.get("Sampling_Zip"),
                        city=record.get("sampling_city") or record.get("Sampling_City"),
                        street=record.get("sampling_street") or record.get("Sampling_Street"),
                        location_desc=record.get("sampling_location") or record.get("Sampling_Location"),
                        county_to_geoid=county_to_geoid,
                    )

            fallback_addr_map: dict[str, int] = {}
            if fallback_geoid_by_idx:
                fallback_addr_map = ensure_anonymous_county_addresses(
                    session,
                    set(fallback_geoid_by_idx.values()),
                    etl_run_id=etl_run_id,
                    lineage_group_id=lineage_group_id,
                )

            existing_samples = session.exec(select(FieldSample)).all()
            samples_map = {(s.name, s.resource_id): s for s in existing_samples}

            for idx, record in enumerate(records):
                name = record.get("name")
                resource_id = _coerce_optional_int(record.get("resource_id"))
                if not name:
                    logger.warning("Skipping record with missing 'name'.")
                    continue

                clean_record = {k: v for k, v in record.items() if k in table_columns}
                for fk_col in _LOCATION_FK_COLUMNS:
                    if fk_col in clean_record:
                        clean_record[fk_col] = _coerce_optional_int(clean_record[fk_col])

                if clean_record.get("sampling_location_id") is None and idx in fallback_geoid_by_idx:
                    clean_record["sampling_location_id"] = fallback_addr_map.get(
                        fallback_geoid_by_idx[idx]
                    )

                clean_record["updated_at"] = now

                lookup_key = (name, resource_id)
                existing_record = samples_map.get(lookup_key)

                if existing_record:
                    for key, value in clean_record.items():
                        if key not in ["id", "created_at"]:
                            setattr(existing_record, key, value)
                else:
                    if clean_record.get("created_at") is None:
                        clean_record["created_at"] = now
                    new_fs = FieldSample(**clean_record)
                    session.add(new_fs)
                    samples_map[lookup_key] = new_fs

            session.commit()
        logger.info("Successfully upserted FieldSample records.")
    except Exception as e:
        logger.error(f"Failed to load FieldSample records: {type(e).__name__}")
        logger.error("".join(traceback.format_tb(e.__traceback__)))
        raise
