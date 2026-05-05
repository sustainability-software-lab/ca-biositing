from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import re
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd
from prefect import get_run_logger, task
from sqlalchemy.dialects.postgresql import insert
from sqlmodel import Session, select

from ca_biositing.pipeline.utils.engine import get_engine


def _get_logger():
    try:
        return get_run_logger()
    except Exception:
        import logging

        return logging.getLogger(__name__)


def _normalize_name(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip().lower().replace("’", "'")
    text = text.replace("_", " ").replace("-", " ")
    text = re.sub(r"\s+", " ", text)
    return text


def _normalize_parameter_name(value: Any) -> str:
    """Normalize parameter name to lowercase with spaces (matching database parameters 1-10)."""
    if value is None:
        return ""
    text = str(value).strip().lower().replace("'", "'")
    text = text.replace("_", " ").replace("-", " ")
    text = re.sub(r"\s+", " ", text)
    return text


def _map_trend_to_numeric(value: Any) -> Optional[Decimal]:
    if value is None:
        return None
    text = str(value).strip().lower()
    if text in {"up", "increase", "increasing", "rising"}:
        return Decimal("1")
    if text in {"down", "decrease", "decreasing", "falling"}:
        return Decimal("-1")
    if text in {"steady", "stable", "flat", "no change"}:
        return Decimal("0")
    return None


def _to_python_value(value: Any) -> Any:
    if value is None:
        return None
    if value is pd.NA:
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, np.generic):
        value = value.item()
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    return value


def _row_to_dict(row: pd.Series) -> Dict[str, Any]:
    return {k: _to_python_value(v) for k, v in row.to_dict().items()}


def _first_by_normalized_name(session: Session, model: Any, name: Any) -> Any:
    target = _normalize_name(name)
    if target == "":
        return None
    rows = session.exec(select(model)).all()
    for row in rows:
        if _normalize_name(getattr(row, "name", None)) == target:
            return row
    return None


def _first_parameter_by_normalized_name(session: Session, name: Any) -> Any:
    from ca_biositing.datamodels.models import Parameter

    target = _normalize_parameter_name(name)
    if target == "":
        return None
    rows = session.exec(select(Parameter)).all()
    for row in rows:
        if _normalize_parameter_name(getattr(row, "name", None)) == target:
            return row
    return None


def _upsert_lookup_like(
    session: Session,
    model: Any,
    name: Any,
    description: Any = None,
    uri: Any = None,
):
    now = datetime.now(timezone.utc)
    existing = _first_by_normalized_name(session, model, name)
    if existing:
        if hasattr(existing, "name"):
            existing.name = _normalize_name(name)
        if hasattr(existing, "description"):
            existing.description = description if description is not None else existing.description
        if hasattr(existing, "uri"):
            existing.uri = uri if uri is not None else existing.uri
        if hasattr(existing, "updated_at"):
            existing.updated_at = now
        session.add(existing)
        session.flush()
        return existing

    payload: Dict[str, Any] = {"name": name, "description": description, "uri": uri}
    if hasattr(model, "created_at"):
        payload["created_at"] = now
        payload["updated_at"] = now

    new_row = model(**payload)
    session.add(new_row)
    session.flush()
    return new_row


@task
def load_qualitative_payloads(
    transformed_payloads: Dict[str, Any],
) -> Dict[str, int]:
    """
    Load Stage 2 qualitative transformed payloads in dependency-safe order.

    Expected payload keys:
      - data_source: DataFrame
      - parameter: DataFrame
      - use_case: DataFrame
      - provenance: {dataset, method_category, method, place}
      - records: {resource_storage_record, resource_transport_record, resource_end_use_record}
      - observation: DataFrame
    """
    logger = _get_logger()
    counts = {
        "data_source": 0,
        "parameter": 0,
        "use_case": 0,
        "dataset": 0,
        "method_category": 0,
        "method": 0,
        "place": 0,
        "resource_storage_record": 0,
        "resource_transport_record": 0,
        "resource_end_use_record": 0,
        "observation": 0,
    }
    observation_skips = {
        "missing_end_use_record": 0,
        "missing_parameter_id": 0,
        "missing_value_and_note": 0,
    }

    if not transformed_payloads:
        logger.info("No transformed payloads provided for qualitative load.")
        return counts

    from ca_biositing.datamodels.models import (
        DataSource,
        Dataset,
        Method,
        MethodCategory,
        Observation,
        Parameter,
        Place,
        ResourceEndUseRecord,
        ResourceStorageRecord,
        ResourceTransportRecord,
        UseCase,
    )
    data_source_columns = {c.name for c in DataSource.__table__.columns}
    now = datetime.now(timezone.utc)

    data_source_df = transformed_payloads.get("data_source")
    parameter_df = transformed_payloads.get("parameter")
    use_case_df = transformed_payloads.get("use_case")
    provenance = transformed_payloads.get("provenance") or {}
    records_payload = transformed_payloads.get("records") or {}
    observation_df = transformed_payloads.get("observation")

    engine = get_engine()
    with Session(engine) as session:
        # 1) DataSource
        source_payload: Dict[str, Any] = {}
        if isinstance(data_source_df, pd.DataFrame) and not data_source_df.empty:
            source_payload = _row_to_dict(data_source_df.iloc[0])
        source_name = _normalize_name(source_payload.get("name")) or _normalize_name(source_payload.get("full_title"))
        if source_name == "":
            source_name = "qualitative data"

        data_source_record = _first_by_normalized_name(session, DataSource, source_name)
        if data_source_record is None:
            payload = {k: v for k, v in source_payload.items() if k in data_source_columns}
            payload["name"] = source_payload.get("name") or source_name
            payload["created_at"] = payload.get("created_at") or now
            payload["updated_at"] = now
            data_source_record = DataSource(**payload)
            session.add(data_source_record)
            session.flush()
            counts["data_source"] += 1
        else:
            if source_payload:
                for key, value in source_payload.items():
                    if key in data_source_columns and key != "id":
                        setattr(data_source_record, key, value)
                if hasattr(data_source_record, "updated_at"):
                    data_source_record.updated_at = now
                session.add(data_source_record)

        source_id = data_source_record.id

        # 2) Parameter (idempotent by name)
        if isinstance(parameter_df, pd.DataFrame) and not parameter_df.empty:
            for _, row in parameter_df.iterrows():
                payload = _row_to_dict(row)
                name = payload.get("name")
                if _normalize_name(name) == "":
                    continue

                existing = _first_parameter_by_normalized_name(session, name)
                if existing:
                    existing.name = _normalize_parameter_name(name)
                    existing.description = payload.get("description")
                    existing.calculated = payload.get("calculated")
                    existing.standard_unit_id = payload.get("standard_unit_id")
                    if hasattr(existing, "etl_run_id"):
                        existing.etl_run_id = payload.get("etl_run_id")
                    if hasattr(existing, "lineage_group_id"):
                        existing.lineage_group_id = payload.get("lineage_group_id")
                    if getattr(existing, "created_at", None) is None:
                        existing.created_at = now
                    existing.updated_at = now
                    session.add(existing)
                else:
                    new_row = Parameter(
                        name=_normalize_parameter_name(name),
                        description=payload.get("description"),
                        calculated=payload.get("calculated"),
                        standard_unit_id=payload.get("standard_unit_id"),
                        created_at=now,
                        updated_at=now,
                        etl_run_id=payload.get("etl_run_id"),
                        lineage_group_id=payload.get("lineage_group_id"),
                    )
                    session.add(new_row)
                    counts["parameter"] += 1

        # 3) UseCase (idempotent by name)
        if isinstance(use_case_df, pd.DataFrame) and not use_case_df.empty:
            for _, row in use_case_df.iterrows():
                payload = _row_to_dict(row)
                name = payload.get("name")
                if _normalize_name(name) == "":
                    continue
                existing = _first_by_normalized_name(session, UseCase, name)
                if existing:
                    existing.name = _normalize_name(name)
                    if hasattr(existing, "description"):
                        existing.description = payload.get("description")
                    if hasattr(existing, "uri"):
                        existing.uri = payload.get("uri")
                    if hasattr(existing, "updated_at"):
                        existing.updated_at = now
                    session.add(existing)
                else:
                    use_case_payload = {"name": name}
                    if hasattr(UseCase, "description"):
                        use_case_payload["description"] = payload.get("description")
                    if hasattr(UseCase, "uri"):
                        use_case_payload["uri"] = payload.get("uri")
                    if hasattr(UseCase, "created_at"):
                        use_case_payload["created_at"] = now
                    if hasattr(UseCase, "updated_at"):
                        use_case_payload["updated_at"] = now
                    new_row = UseCase(**use_case_payload)
                    session.add(new_row)
                    counts["use_case"] += 1

        # 4) Provenance foundations
        method_category_df = provenance.get("method_category")
        method_df = provenance.get("method")
        dataset_df = provenance.get("dataset")
        place_df = provenance.get("place")

        method_category_record = None
        if isinstance(method_category_df, pd.DataFrame) and not method_category_df.empty:
            row = _row_to_dict(method_category_df.iloc[0])
            existing_method_category = _first_by_normalized_name(session, MethodCategory, row.get("name"))
            method_category_record = _upsert_lookup_like(
                session=session,
                model=MethodCategory,
                name=row.get("name"),
                description=row.get("description"),
                uri=row.get("uri"),
            )
            if existing_method_category is None and method_category_record is not None:
                counts["method_category"] += 1

        dataset_record = None
        if isinstance(dataset_df, pd.DataFrame) and not dataset_df.empty:
            row = _row_to_dict(dataset_df.iloc[0])
            name = row.get("name")
            record_type = row.get("record_type")
            existing = session.exec(
                select(Dataset).where(Dataset.name == name, Dataset.record_type == record_type)
            ).first()
            if existing:
                existing.source_id = source_id
                existing.start_date = row.get("start_date")
                existing.end_date = row.get("end_date")
                existing.description = row.get("description")
                existing.etl_run_id = row.get("etl_run_id")
                existing.lineage_group_id = row.get("lineage_group_id")
                existing.updated_at = now
                session.add(existing)
                dataset_record = existing
            else:
                dataset_record = Dataset(
                    name=name,
                    record_type=record_type,
                    source_id=source_id,
                    start_date=row.get("start_date"),
                    end_date=row.get("end_date"),
                    description=row.get("description"),
                    created_at=now,
                    updated_at=now,
                    etl_run_id=row.get("etl_run_id"),
                    lineage_group_id=row.get("lineage_group_id"),
                )
                session.add(dataset_record)
                counts["dataset"] += 1
            session.flush()

        method_record = None
        if isinstance(method_df, pd.DataFrame) and not method_df.empty:
            row = _row_to_dict(method_df.iloc[0])
            method_name = row.get("name")
            existing_method = _first_by_normalized_name(session, Method, method_name)
            method_category_id = getattr(method_category_record, "id", None)
            if existing_method:
                existing_method.method_category_id = method_category_id
                existing_method.source_id = source_id
                existing_method.etl_run_id = row.get("etl_run_id")
                existing_method.lineage_group_id = row.get("lineage_group_id")
                existing_method.updated_at = now
                session.add(existing_method)
                method_record = existing_method
            else:
                method_record = Method(
                    name=method_name,
                    method_category_id=method_category_id,
                    method_abbrev_id=row.get("method_abbrev_id"),
                    source_id=source_id,
                    created_at=now,
                    updated_at=now,
                    etl_run_id=row.get("etl_run_id"),
                    lineage_group_id=row.get("lineage_group_id"),
                )
                session.add(method_record)
                counts["method"] += 1
            session.flush()

        place_record = None
        if isinstance(place_df, pd.DataFrame) and not place_df.empty:
            row = _row_to_dict(place_df.iloc[0])
            geoid = row.get("geoid")
            place_record = session.exec(select(Place).where(Place.geoid == geoid)).first()
            if place_record:
                place_record.state_name = row.get("state_name")
                place_record.state_fips = row.get("state_fips")
                place_record.county_name = row.get("county_name")
                place_record.county_fips = row.get("county_fips")
                place_record.agg_level_desc = row.get("agg_level_desc")
                if hasattr(place_record, "etl_run_id"):
                    place_record.etl_run_id = row.get("etl_run_id")
                if hasattr(place_record, "lineage_group_id"):
                    place_record.lineage_group_id = row.get("lineage_group_id")
                session.add(place_record)
            else:
                place_record = Place(**row)
                session.add(place_record)
                counts["place"] += 1
            session.flush()

        dataset_id = getattr(dataset_record, "id", None)
        method_id = getattr(method_record, "id", None)
        geoid = getattr(place_record, "geoid", None)

        # 5) Profile record tables
        end_use_id_by_key: dict[str, int] = {}
        end_use_sample_keys: list[str] = []

        storage_df = records_payload.get("resource_storage_record")
        if isinstance(storage_df, pd.DataFrame) and not storage_df.empty:
            for _, row in storage_df.iterrows():
                payload = _row_to_dict(row)
                desc = payload.get("storage_description")
                if desc is None:
                    continue
                resource_id = payload.get("resource_id")
                existing = session.exec(
                    select(ResourceStorageRecord).where(
                        ResourceStorageRecord.resource_id == resource_id,
                        ResourceStorageRecord.storage_description == desc,
                        ResourceStorageRecord.dataset_id == dataset_id,
                        ResourceStorageRecord.method_id == method_id,
                        ResourceStorageRecord.geoid == geoid,
                    )
                ).first()
                if existing:
                    existing.note = payload.get("note")
                    existing.updated_at = now
                    existing.etl_run_id = payload.get("etl_run_id")
                    existing.lineage_group_id = payload.get("lineage_group_id")
                    session.add(existing)
                else:
                    record = ResourceStorageRecord(
                        dataset_id=dataset_id,
                        method_id=method_id,
                        geoid=geoid,
                        resource_id=resource_id,
                        storage_description=desc,
                        note=payload.get("note"),
                        created_at=now,
                        updated_at=now,
                        etl_run_id=payload.get("etl_run_id"),
                        lineage_group_id=payload.get("lineage_group_id"),
                    )
                    session.add(record)
                    counts["resource_storage_record"] += 1

        transport_df = records_payload.get("resource_transport_record")
        if isinstance(transport_df, pd.DataFrame) and not transport_df.empty:
            for _, row in transport_df.iterrows():
                payload = _row_to_dict(row)
                desc = payload.get("transport_description")
                if desc is None:
                    continue
                resource_id = payload.get("resource_id")
                existing = session.exec(
                    select(ResourceTransportRecord).where(
                        ResourceTransportRecord.resource_id == resource_id,
                        ResourceTransportRecord.transport_description == desc,
                        ResourceTransportRecord.dataset_id == dataset_id,
                        ResourceTransportRecord.method_id == method_id,
                        ResourceTransportRecord.geoid == geoid,
                    )
                ).first()
                if existing:
                    existing.note = payload.get("note")
                    existing.updated_at = now
                    existing.etl_run_id = payload.get("etl_run_id")
                    existing.lineage_group_id = payload.get("lineage_group_id")
                    session.add(existing)
                else:
                    record = ResourceTransportRecord(
                        dataset_id=dataset_id,
                        method_id=method_id,
                        geoid=geoid,
                        resource_id=resource_id,
                        transport_description=desc,
                        note=payload.get("note"),
                        created_at=now,
                        updated_at=now,
                        etl_run_id=payload.get("etl_run_id"),
                        lineage_group_id=payload.get("lineage_group_id"),
                    )
                    session.add(record)
                    counts["resource_transport_record"] += 1

        end_use_df = records_payload.get("resource_end_use_record")
        if isinstance(end_use_df, pd.DataFrame) and not end_use_df.empty:
            for _, row in end_use_df.iterrows():
                payload = _row_to_dict(row)
                resource_id = payload.get("resource_id")
                use_case_id = payload.get("use_case_id")
                record_key = payload.get("end_use_record_key")

                existing = session.exec(
                    select(ResourceEndUseRecord).where(
                        ResourceEndUseRecord.resource_id == resource_id,
                        ResourceEndUseRecord.use_case_id == use_case_id,
                        ResourceEndUseRecord.dataset_id == dataset_id,
                        ResourceEndUseRecord.method_id == method_id,
                        ResourceEndUseRecord.geoid == geoid,
                    )
                ).first()
                if existing:
                    existing.note = payload.get("note")
                    existing.updated_at = now
                    existing.etl_run_id = payload.get("etl_run_id")
                    existing.lineage_group_id = payload.get("lineage_group_id")
                    session.add(existing)
                    session.flush()
                    if isinstance(record_key, str) and record_key.strip():
                        end_use_id_by_key[record_key] = existing.id
                        if len(end_use_sample_keys) < 5:
                            end_use_sample_keys.append(record_key)
                else:
                    record = ResourceEndUseRecord(
                        dataset_id=dataset_id,
                        method_id=method_id,
                        geoid=geoid,
                        resource_id=resource_id,
                        use_case_id=use_case_id,
                        note=payload.get("note"),
                        created_at=now,
                        updated_at=now,
                        etl_run_id=payload.get("etl_run_id"),
                        lineage_group_id=payload.get("lineage_group_id"),
                    )
                    session.add(record)
                    session.flush()
                    counts["resource_end_use_record"] += 1
                    if isinstance(record_key, str) and record_key.strip():
                        end_use_id_by_key[record_key] = record.id
                        if len(end_use_sample_keys) < 5:
                            end_use_sample_keys.append(record_key)

        # 6) Observation
        if isinstance(observation_df, pd.DataFrame) and not observation_df.empty:
            table_columns = {c.name for c in Observation.__table__.columns}
            logger.info(
                f"Qualitative key map size: {len(end_use_id_by_key)}; sample record keys: {end_use_sample_keys}"
            )
            observation_sample_keys: list[str] = []
            for _, row in observation_df.iterrows():
                payload = _row_to_dict(row)
                key = payload.get("end_use_record_key")
                if isinstance(key, str) and len(observation_sample_keys) < 5:
                    observation_sample_keys.append(key)
                resolved_record_id = end_use_id_by_key.get(str(key)) if key is not None else None
                if resolved_record_id is None:
                    observation_skips["missing_end_use_record"] += 1
                    continue

                if payload.get("parameter_id") is None and payload.get("parameter_name") is not None:
                    parameter_row = _first_parameter_by_normalized_name(session, payload.get("parameter_name"))
                    if parameter_row is not None:
                        payload["parameter_id"] = getattr(parameter_row, "id", None) or getattr(
                            parameter_row, "parameter_id", None
                        )
                        if payload.get("unit_id") is None:
                            payload["unit_id"] = getattr(parameter_row, "standard_unit_id", None) or getattr(
                                parameter_row, "unit_id", None
                            )

                normalized_param_name = _normalize_parameter_name(payload.get("parameter_name"))
                if normalized_param_name == "resource_use_trend" and payload.get("value") is None:
                    mapped = _map_trend_to_numeric(payload.get("note"))
                    if mapped is not None:
                        payload["value"] = mapped

                payload["record_id"] = str(resolved_record_id)
                payload["dataset_id"] = dataset_id
                payload["record_type"] = "resource_end_use_record"
                payload["created_at"] = payload.get("created_at") or now
                payload["updated_at"] = now

                clean_payload = {
                    k: v
                    for k, v in payload.items()
                    if k in table_columns and k != "end_use_record_key"
                }

                if clean_payload.get("parameter_id") is None:
                    observation_skips["missing_parameter_id"] += 1
                    continue
                if clean_payload.get("value") is None and not clean_payload.get("note"):
                    observation_skips["missing_value_and_note"] += 1
                    continue

                stmt = insert(Observation.__table__).values(**clean_payload)
                update_cols = {
                    c: stmt.excluded[c]
                    for c in clean_payload.keys()
                    if c not in {"id", "created_at", "record_id", "record_type", "parameter_id", "unit_id"}
                }
                upsert_stmt = stmt.on_conflict_do_update(
                    index_elements=["record_id", "record_type", "parameter_id", "unit_id"],
                    set_=update_cols,
                )
                session.execute(upsert_stmt)
                counts["observation"] += 1

            logger.info(f"Qualitative observation sample keys: {observation_sample_keys}")

        session.commit()

    logger.info(f"Qualitative observation skip stats: {observation_skips}")
    logger.info(f"Qualitative load completed with counts: {counts}")
    return counts
