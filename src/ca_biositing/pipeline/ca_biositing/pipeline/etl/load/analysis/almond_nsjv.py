"""
ETL Load for Almond NSJV county agricultural reports.

Loads transformed almond payloads into provenance tables, parameters,
resource records, and observations using idempotent upsert behavior.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
import logging
import re
from typing import Any, Optional

import numpy as np
import pandas as pd
from prefect import get_run_logger, task
from sqlmodel import Session, select

from ca_biositing.pipeline.utils.engine import get_engine


ALMOND_DATA_SOURCE_NAME = (
    "Market and End-Use Analysis for the Biomass Feedstock Landscape in the North San Joaquin Valley"
)
ALMOND_DATA_SOURCE_TITLE = ALMOND_DATA_SOURCE_NAME
ALMOND_METHOD_CATEGORY_NAME = "manual extraction of values from PDF report"
ALMOND_METHOD_NAME = ALMOND_METHOD_CATEGORY_NAME
ALMOND_PRICE_DATASET_NAME = "BEAM whitepaper county ag report almond prices"
ALMOND_PRODUCTION_DATASET_NAME = "BEAM whitepaper county ag report almond production"
ALMOND_PRICE_PARAMETER_NAME = "price received"
ALMOND_PRICE_PARAMETER_DESCRIPTION = "Price received"
ALMOND_WEIGHTED_AVERAGE_PARAMETER_NAME = "price production weighted average"
ALMOND_WEIGHTED_AVERAGE_PARAMETER_DESCRIPTION = "Price production weighted average"


def _get_logger():
    try:
        return get_run_logger()
    except Exception:
        return logging.getLogger(__name__)


def _normalize_text(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    text = str(value).strip().lower()
    text = re.sub(r"\s+", " ", text)
    return text


def _normalize_parameter_name(value: Any) -> str:
    """Normalize parameter name to lowercase with spaces (not snake_case)."""
    if value is None or pd.isna(value):
        return ""
    text = str(value).strip().lower().replace("'", "'")
    text = re.sub(r"[\s_-]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text


def _clean_value(value: Any) -> Any:
    if value is None or pd.isna(value):
        return None
    if isinstance(value, np.generic):
        return value.item()
    return value


def _to_date(value: Any) -> Optional[date]:
    if value is None or pd.isna(value):
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return None
    return parsed.date()


def _to_decimal(value: Any) -> Optional[Decimal]:
    if value is None or pd.isna(value):
        return None
    try:
        if isinstance(value, str):
            # Remove currency symbols, commas, and whitespace
            cleaned = re.sub(r"[$,\s]+", "", value)
            if cleaned == "":
                return None
            return Decimal(cleaned)
        return Decimal(str(value))
    except Exception:
        return None


def _get_first_present(row: dict[str, Any], candidates: tuple[str, ...]) -> Any:
    for candidate in candidates:
        if candidate in row:
            return row[candidate]
    return None


def _upsert_by_name(
    session: Session,
    model: Any,
    name: str,
    payload: dict[str, Any],
) -> tuple[Any, bool]:
    normalized_name = _normalize_text(name)
    for row in session.exec(select(model)).all():
        if _normalize_text(getattr(row, "name", None)) == normalized_name:
            for key, value in payload.items():
                if key != "id":
                    setattr(row, key, value)
            return row, False

    instance = model(**payload)
    session.add(instance)
    session.flush()
    return instance, True


def _ensure_data_source(session: Session) -> tuple[Any, bool]:
    from ca_biositing.datamodels.models import DataSource

    payload = {
        "name": ALMOND_DATA_SOURCE_NAME,
        "full_title": ALMOND_DATA_SOURCE_TITLE,
        "description": "Source metadata for almond county agricultural report ETL.",
        "updated_at": datetime.now(timezone.utc),
    }
    instance, created = _upsert_by_name(session, DataSource, ALMOND_DATA_SOURCE_NAME, payload)
    now = datetime.now(timezone.utc)
    if instance is not None:
        if hasattr(instance, "updated_at"):
            instance.updated_at = now
        if created and hasattr(instance, "created_at") and getattr(instance, "created_at", None) is None:
            instance.created_at = now
    return instance, created


def _ensure_method_category(session: Session) -> tuple[Any, bool]:
    """Ensure the method category exists for almond ETL."""
    from ca_biositing.datamodels.models import MethodCategory

    name = "research method"
    payload = {
        "name": name,
        "description": "Research method for manual data extraction",
    }
    return _upsert_by_name(session, MethodCategory, name, payload)


def _ensure_method(session: Session, data_source_id: int, method_category_id: int, etl_run_id: Any = None, lineage_group_id: Any = None) -> tuple[Any, bool]:
    from ca_biositing.datamodels.models import Method

    payload = {
        "name": ALMOND_METHOD_NAME,
        "description": "Manual extraction of almond county agricultural report values.",
        "method_category_id": method_category_id,
        "source_id": data_source_id,
        "updated_at": datetime.now(timezone.utc),
    }
    instance, created = _upsert_by_name(session, Method, ALMOND_METHOD_NAME, payload)
    now = datetime.now(timezone.utc)
    if instance is not None:
        if hasattr(instance, "updated_at"):
            instance.updated_at = now
        if created and hasattr(instance, "created_at") and getattr(instance, "created_at", None) is None:
            instance.created_at = now
        if etl_run_id is not None and hasattr(instance, "etl_run_id"):
            instance.etl_run_id = etl_run_id
        if lineage_group_id is not None and hasattr(instance, "lineage_group_id"):
            instance.lineage_group_id = lineage_group_id
    return instance, created


def _ensure_dataset(
    session: Session,
    *,
    name: str,
    record_type: str,
    data_source_id: int,
    description: str,
    etl_run_id: Any = None,
    lineage_group_id: Any = None,
) -> tuple[Any, bool]:
    from ca_biositing.datamodels.models import Dataset

    payload = {
        "name": name,
        "record_type": record_type,
        "source_id": data_source_id,
        "start_date": date(2017, 1, 1),
        "end_date": date(2024, 12, 31),
        "description": description,
        "updated_at": datetime.now(timezone.utc),
    }
    instance, created = _upsert_by_name(session, Dataset, name, payload)
    now = datetime.now(timezone.utc)
    if instance is not None:
        if hasattr(instance, "updated_at"):
            instance.updated_at = now
        if created and hasattr(instance, "created_at") and getattr(instance, "created_at", None) is None:
            instance.created_at = now
        if etl_run_id is not None and hasattr(instance, "etl_run_id"):
            instance.etl_run_id = etl_run_id
        if lineage_group_id is not None and hasattr(instance, "lineage_group_id"):
            instance.lineage_group_id = lineage_group_id
    return instance, created


def _resolve_resource_id(session: Session, resource_value: Any) -> Optional[int]:
     from ca_biositing.datamodels.models import Resource

     if isinstance(resource_value, (int, float)) and not pd.isna(resource_value):
         return int(resource_value)

     normalized_resource = _normalize_text(resource_value)
     if normalized_resource == "":
         return None

     for row in session.exec(select(Resource)).all():
         if _normalize_text(getattr(row, "name", None)) == normalized_resource:
             return getattr(row, "id", None)
     # If not found, create a new Resource record using the provided name.
     try:
         now = datetime.now(timezone.utc)
         new = Resource(name=str(resource_value).strip(), created_at=now, updated_at=now)
         session.add(new)
         session.flush()
         return getattr(new, "id", None)
     except Exception:
         return None


def _ensure_unit(session: Session, unit_value: Any) -> Optional[int]:
     """Resolve unit by name and create if missing (similar to _resolve_resource_id)."""
     from ca_biositing.datamodels.models import Unit

     if isinstance(unit_value, (int, float)) and not pd.isna(unit_value):
         return int(unit_value)

     normalized_unit = _normalize_text(unit_value)
     if normalized_unit == "":
         return None

     for row in session.exec(select(Unit)).all():
         if _normalize_text(getattr(row, "name", None)) == normalized_unit:
             return getattr(row, "id", None)
     # If not found, create a new Unit record using the provided name.
     try:
         new = Unit(name=str(unit_value).strip())
         session.add(new)
         session.flush()
         return getattr(new, "id", None)
     except Exception:
         return None


def _find_parameter(session: Session, name: str) -> Any:
    from ca_biositing.datamodels.models import Parameter

    normalized_name = _normalize_parameter_name(name)
    if normalized_name == "":
        return None

    for row in session.exec(select(Parameter)).all():
        if _normalize_parameter_name(getattr(row, "name", None)) == normalized_name:
            return row
    return None


def _resolve_parameter_by_name(session: Session, name: Any) -> Any:
    parameter = _find_parameter(session, name)
    if parameter is not None:
        return parameter

    normalized_name = _normalize_parameter_name(name)
    alias_map = {
        "weighted average price": "price production weighted average",
        "price production weighted average": "weighted average price",
        "price": "price received",
        "price_avg": "price received",
    }
    alias_name = alias_map.get(normalized_name)
    if alias_name is None:
        return None
    return _find_parameter(session, alias_name)


def _upsert_parameter(session: Session, row: dict[str, Any], etl_run_id: Any, lineage_group_id: Any) -> bool:
    from ca_biositing.datamodels.models import Parameter

    name = _normalize_parameter_name(_clean_value(row.get("name")))
    if name == "":
        return False

    now = datetime.now(timezone.utc)
    standard_unit_id = _clean_value(row.get("standard_unit_id"))
    calculated = row.get("calculated")
    description = _clean_value(row.get("description"))

    for existing in session.exec(select(Parameter)).all():
        if _normalize_parameter_name(getattr(existing, "name", None)) == name:
            existing.name = name
            existing.description = description
            existing.standard_unit_id = standard_unit_id
            existing.calculated = calculated
            existing.updated_at = now
            existing.etl_run_id = etl_run_id
            existing.lineage_group_id = lineage_group_id
            return False

    session.add(
        Parameter(
            name=name,
            description=description,
            standard_unit_id=standard_unit_id,
            calculated=calculated,
            created_at=now,
            updated_at=now,
            etl_run_id=etl_run_id,
            lineage_group_id=lineage_group_id,
        )
    )
    return True


def _ensure_weighted_average_parameter(
    session: Session,
    parameter_df: Optional[pd.DataFrame],
    etl_run_id: Any,
    lineage_group_id: Any,
) -> bool:
    from ca_biositing.datamodels.models import Parameter

    existing = _find_parameter(session, ALMOND_WEIGHTED_AVERAGE_PARAMETER_NAME)
    if existing is not None:
        return False

    unit_id = None
    if isinstance(parameter_df, pd.DataFrame) and not parameter_df.empty:
        price_rows = parameter_df[
            parameter_df["name"].astype(str).str.strip().str.lower() == ALMOND_PRICE_PARAMETER_NAME
        ]
        if not price_rows.empty:
            unit_id = _clean_value(price_rows.iloc[0].get("standard_unit_id"))

        if unit_id is None:
            for _, row in parameter_df.iterrows():
                candidate_unit_id = _clean_value(row.get("standard_unit_id"))
                if candidate_unit_id is not None:
                    unit_id = candidate_unit_id
                    break

    if unit_id is None:
        existing_price_received = _find_parameter(session, ALMOND_PRICE_PARAMETER_NAME)
        if existing_price_received is not None:
            unit_id = getattr(existing_price_received, "standard_unit_id", None)

    now = datetime.now(timezone.utc)
    session.add(
        Parameter(
            name=ALMOND_WEIGHTED_AVERAGE_PARAMETER_NAME,
            description=ALMOND_WEIGHTED_AVERAGE_PARAMETER_DESCRIPTION,
            standard_unit_id=unit_id,
            calculated=True,
            created_at=now,
            updated_at=now,
            etl_run_id=etl_run_id,
            lineage_group_id=lineage_group_id,
        )
    )
    return True


def _ensure_price_received_parameter(
    session: Session,
    parameter_df: Optional[pd.DataFrame],
    etl_run_id: Any,
    lineage_group_id: Any,
) -> bool:
    from ca_biositing.datamodels.models import Parameter

    existing = _find_parameter(session, ALMOND_PRICE_PARAMETER_NAME)
    if existing is not None:
        return False

    unit_id = None
    if isinstance(parameter_df, pd.DataFrame) and not parameter_df.empty:
        price_rows = parameter_df[
            parameter_df["name"].astype(str).str.strip().str.lower() == ALMOND_PRICE_PARAMETER_NAME
        ]
        if not price_rows.empty:
            unit_id = _clean_value(price_rows.iloc[0].get("standard_unit_id"))

        if unit_id is None:
            weighted_rows = parameter_df[
                parameter_df["name"].astype(str).str.strip().str.lower() == ALMOND_WEIGHTED_AVERAGE_PARAMETER_NAME
            ]
            if not weighted_rows.empty:
                unit_id = _clean_value(weighted_rows.iloc[0].get("standard_unit_id"))

        if unit_id is None:
            for _, row in parameter_df.iterrows():
                candidate_unit_id = _clean_value(row.get("standard_unit_id"))
                if candidate_unit_id is not None:
                    unit_id = candidate_unit_id
                    break

    now = datetime.now(timezone.utc)
    session.add(
        Parameter(
            name=ALMOND_PRICE_PARAMETER_NAME,
            description=ALMOND_PRICE_PARAMETER_DESCRIPTION,
            standard_unit_id=unit_id,
            calculated=False,
            created_at=now,
            updated_at=now,
            etl_run_id=etl_run_id,
            lineage_group_id=lineage_group_id,
        )
    )
    return True


def _upsert_record_table(
    session: Session,
    logger: Any,
    *,
    model: Any,
    payload_row: dict[str, Any],
    dataset_id: int,
    source_id: Optional[int],
    method_id: Optional[int],
    etl_run_id: Any,
    lineage_group_id: Any,
) -> tuple[bool, Optional[int], Optional[int], Optional[date], Optional[int]]:
    now = datetime.now(timezone.utc)
    resource_id = _resolve_resource_id(session, _get_first_present(payload_row, ("resource_id", "resource")))
    if resource_id is None:
        logger.error("Skipping %s row with unresolved resource.", model.__tablename__)
        return False, None, None, None, None

    geoid = _clean_value(payload_row.get("geoid"))
    if geoid is None:
        logger.error("Skipping %s row with missing geoid.", model.__tablename__)
        return False, None, None, None, None

    primary_ag_product_id = _clean_value(payload_row.get("primary_ag_product_id"))
    note = _clean_value(payload_row.get("note"))

    if model.__tablename__ == "resource_price_record":
        report_start_date = _to_date(payload_row.get("report_start_date"))
        report_end_date = _to_date(payload_row.get("report_end_date"))
        freight_terms = _clean_value(payload_row.get("freight_terms"))
        transport_mode = _clean_value(payload_row.get("transport_mode"))
        for existing in session.exec(select(model)).all():
            if (
                getattr(existing, "dataset_id", None) == dataset_id
                and getattr(existing, "source_id", None) == source_id
                and getattr(existing, "geoid", None) == geoid
                and getattr(existing, "resource_id", None) == resource_id
                and getattr(existing, "report_start_date", None) == report_start_date
                and getattr(existing, "report_end_date", None) == report_end_date
                and getattr(existing, "primary_ag_product_id", None) == primary_ag_product_id
                and getattr(existing, "freight_terms", None) == freight_terms
                and getattr(existing, "transport_mode", None) == transport_mode
            ):
                existing.method_id = method_id
                existing.note = note
                existing.updated_at = now
                existing.etl_run_id = etl_run_id
                existing.lineage_group_id = lineage_group_id
                return False, resource_id, dataset_id, report_start_date, getattr(existing, "id", None)

        instance = model(
            dataset_id=dataset_id,
            method_id=method_id,
            geoid=geoid,
            resource_id=resource_id,
            primary_ag_product_id=primary_ag_product_id,
            source_id=source_id,
            report_start_date=report_start_date,
            report_end_date=report_end_date,
            freight_terms=freight_terms,
            transport_mode=transport_mode,
            note=note,
            created_at=now,
            updated_at=now,
            etl_run_id=etl_run_id,
            lineage_group_id=lineage_group_id,
        )
        session.add(instance)
        session.flush()
        return True, resource_id, dataset_id, report_start_date, getattr(instance, "id", None)

    report_date = _to_date(payload_row.get("report_date"))
    scenario = _clean_value(payload_row.get("scenario"))
    for existing in session.exec(select(model)).all():
        if (
            getattr(existing, "dataset_id", None) == dataset_id
            and getattr(existing, "geoid", None) == geoid
            and getattr(existing, "resource_id", None) == resource_id
            and getattr(existing, "report_date", None) == report_date
            and getattr(existing, "primary_ag_product_id", None) == primary_ag_product_id
            and getattr(existing, "scenario", None) == scenario
        ):
            existing.method_id = method_id
            existing.note = note
            existing.updated_at = now
            existing.etl_run_id = etl_run_id
            existing.lineage_group_id = lineage_group_id
            return False, resource_id, dataset_id, report_date, getattr(existing, "id", None)

    instance = model(
        dataset_id=dataset_id,
        method_id=method_id,
        geoid=geoid,
        primary_ag_product_id=primary_ag_product_id,
        resource_id=resource_id,
        report_date=report_date,
        scenario=scenario,
        note=note,
        created_at=now,
        updated_at=now,
        etl_run_id=etl_run_id,
        lineage_group_id=lineage_group_id,
    )
    session.add(instance)
    session.flush()
    return True, resource_id, dataset_id, report_date, getattr(instance, "id", None)


def _upsert_observation(
    session: Session,
    row: dict[str, Any],
    *,
    dataset_id: int,
    record_id: int,
    etl_run_id: Any,
    lineage_group_id: Any,
) -> bool:
    from ca_biositing.datamodels.models import Observation

    geoid = _clean_value(row.get("geoid"))
    parameter_id = _clean_value(row.get("parameter_id"))
    unit_id = _clean_value(row.get("unit_id"))
    if geoid is None or parameter_id is None or unit_id is None:
        return False

    resource_id = _resolve_resource_id(session, _get_first_present(row, ("resource_id", "resource")))
    if resource_id is None:
        return False

    record_type = _clean_value(row.get("record_type"))
    value = _to_decimal(row.get("value"))
    note = _clean_value(row.get("note"))
    now = datetime.now(timezone.utc)

    for existing in session.exec(select(Observation)).all():
        if (
            str(getattr(existing, "record_id", None)) == str(record_id)
            and getattr(existing, "record_type", None) == record_type
            and getattr(existing, "parameter_id", None) == parameter_id
            and getattr(existing, "unit_id", None) == unit_id
        ):
            existing.dataset_id = dataset_id
            existing.value = value
            existing.note = note
            existing.updated_at = now
            existing.etl_run_id = etl_run_id
            existing.lineage_group_id = lineage_group_id
            return False

    session.add(
        Observation(
            record_id=str(record_id),
            dataset_id=dataset_id,
            record_type=record_type,
            parameter_id=parameter_id,
            value=value,
            unit_id=unit_id,
            note=note,
            created_at=now,
            updated_at=now,
            etl_run_id=etl_run_id,
            lineage_group_id=lineage_group_id,
        )
    )
    return True


@task
def load_county_ag_reports(payloads: dict[str, Any]) -> dict[str, int]:
    """Load almond county agricultural report payloads into the database."""

    logger = _get_logger()
    if not payloads:
        logger.info("No almond payloads supplied.")
        return {}

    parameter_df = payloads.get("parameter")
    record_payloads = payloads.get("records") or {}
    observation_df = payloads.get("observation")

    engine = get_engine()
    from ca_biositing.datamodels.models import Observation, ResourcePriceRecord, ResourceProductionRecord

    counts = {
        "data_source": 0,
        "method_category": 0,
        "method": 0,
        "dataset": 0,
        "parameter": 0,
        "resource_price_record": 0,
        "resource_production_record": 0,
        "observation": 0,
    }

    with engine.connect() as conn:
        with Session(bind=conn) as session:
            try:
                data_source, created = _ensure_data_source(session)
                counts["data_source"] += int(created)
                # Determine provenance IDs from payloads (prefer parameter payload if present)
                provenance_etl_run_id = None
                provenance_lineage_group_id = None
                try:
                    if isinstance(parameter_df, pd.DataFrame) and not parameter_df.empty:
                        provenance_etl_run_id = _clean_value(parameter_df.iloc[0].get("etl_run_id"))
                        provenance_lineage_group_id = _clean_value(parameter_df.iloc[0].get("lineage_group_id"))
                    else:
                        # fallback to records payloads
                        if isinstance(record_payloads, dict):
                            for key in ("resource_price_record", "resource_production_record"):
                                df = record_payloads.get(key)
                                if isinstance(df, pd.DataFrame) and not df.empty:
                                    provenance_etl_run_id = provenance_etl_run_id or _clean_value(df.iloc[0].get("etl_run_id"))
                                    provenance_lineage_group_id = provenance_lineage_group_id or _clean_value(df.iloc[0].get("lineage_group_id"))
                                    if provenance_etl_run_id and provenance_lineage_group_id:
                                        break
                except Exception:
                    provenance_etl_run_id = provenance_etl_run_id

                method_category, created = _ensure_method_category(session)
                counts["method_category"] += int(created)

                method, created = _ensure_method(session, data_source.id, method_category.id, etl_run_id=provenance_etl_run_id, lineage_group_id=provenance_lineage_group_id)
                counts["method"] += int(created)

                price_dataset, created = _ensure_dataset(
                    session,
                    name=ALMOND_PRICE_DATASET_NAME,
                    record_type="resource_price_record",
                    data_source_id=data_source.id,
                    description="Almond resource prices manually extracted from NSJV county ag reports",
                    etl_run_id=provenance_etl_run_id,
                    lineage_group_id=provenance_lineage_group_id,
                )
                counts["dataset"] += int(created)
                production_dataset, created = _ensure_dataset(
                    session,
                    name=ALMOND_PRODUCTION_DATASET_NAME,
                    record_type="resource_production_record",
                    data_source_id=data_source.id,
                    description="Almond production manually extracted from NSJV county ag reports",
                    etl_run_id=provenance_etl_run_id,
                    lineage_group_id=provenance_lineage_group_id,
                )
                counts["dataset"] += int(created)

                if any(value is None for value in (data_source.id, method_category.id, method.id, price_dataset.id, production_dataset.id)):
                    raise ValueError("Almond load preconditions failed: required provenance ids were not resolved.")

                dataset_by_record_type = {
                    "resource_price_record": price_dataset.id,
                    "resource_production_record": production_dataset.id,
                }
                record_id_lookup: dict[tuple[str, str, int, int], int] = {}

                if isinstance(parameter_df, pd.DataFrame) and not parameter_df.empty:
                    for _, row in parameter_df.iterrows():
                        if _upsert_parameter(
                            session,
                            row.to_dict(),
                            _clean_value(row.get("etl_run_id")),
                            _clean_value(row.get("lineage_group_id")),
                        ):
                            counts["parameter"] += 1
                else:
                    logger.info("No parameter payload found for almond load.")

                if _ensure_price_received_parameter(
                    session,
                    parameter_df=parameter_df,
                    etl_run_id=(_clean_value(parameter_df.iloc[0]["etl_run_id"]) if isinstance(parameter_df, pd.DataFrame) and not parameter_df.empty and "etl_run_id" in parameter_df.columns else None),
                    lineage_group_id=(_clean_value(parameter_df.iloc[0]["lineage_group_id"]) if isinstance(parameter_df, pd.DataFrame) and not parameter_df.empty and "lineage_group_id" in parameter_df.columns else None),
                ):
                    counts["parameter"] += 1

                if _ensure_weighted_average_parameter(
                    session,
                    parameter_df=parameter_df,
                    etl_run_id=(_clean_value(parameter_df.iloc[0]["etl_run_id"]) if isinstance(parameter_df, pd.DataFrame) and not parameter_df.empty and "etl_run_id" in parameter_df.columns else None),
                    lineage_group_id=(_clean_value(parameter_df.iloc[0]["lineage_group_id"]) if isinstance(parameter_df, pd.DataFrame) and not parameter_df.empty and "lineage_group_id" in parameter_df.columns else None),
                ):
                    counts["parameter"] += 1

                if isinstance(record_payloads, dict):
                    price_records = record_payloads.get("resource_price_record")
                    production_records = record_payloads.get("resource_production_record")

                    if isinstance(price_records, pd.DataFrame) and not price_records.empty:
                        for _, row in price_records.iterrows():
                            inserted, resource_id, _, report_start_date, record_db_id = _upsert_record_table(
                                session,
                                logger,
                                model=ResourcePriceRecord,
                                payload_row=row.to_dict(),
                                dataset_id=price_dataset.id,
                                source_id=data_source.id,
                                method_id=method.id,
                                etl_run_id=_clean_value(row.get("etl_run_id")),
                                lineage_group_id=_clean_value(row.get("lineage_group_id")),
                            )
                            if record_db_id is not None and resource_id is not None and report_start_date is not None:
                                key = ("resource_price_record", str(_clean_value(row.get("geoid"))), int(resource_id), int(report_start_date.year))
                                logger.info("Adding record to lookup: key=%s, record_db_id=%s", key, record_db_id)
                                record_id_lookup[key] = int(record_db_id)
                            if inserted:
                                counts["resource_price_record"] += 1

                    if isinstance(production_records, pd.DataFrame) and not production_records.empty:
                        for _, row in production_records.iterrows():
                            inserted, resource_id, _, report_date, record_db_id = _upsert_record_table(
                                session,
                                logger,
                                model=ResourceProductionRecord,
                                payload_row=row.to_dict(),
                                dataset_id=production_dataset.id,
                                source_id=None,
                                method_id=method.id,
                                etl_run_id=_clean_value(row.get("etl_run_id")),
                                lineage_group_id=_clean_value(row.get("lineage_group_id")),
                            )
                            if record_db_id is not None and resource_id is not None and report_date is not None:
                                key = ("resource_production_record", str(_clean_value(row.get("geoid"))), int(resource_id), int(report_date.year))
                                logger.info("Adding record to lookup: key=%s, record_db_id=%s", key, record_db_id)
                                record_id_lookup[key] = int(record_db_id)
                            if inserted:
                                counts["resource_production_record"] += 1

                if isinstance(observation_df, pd.DataFrame) and not observation_df.empty:
                    # build unit lookup for fallbacks
                    from ca_biositing.datamodels.models import Unit

                    unit_lookup: dict[str, int] = {}
                    for u in session.exec(select(Unit)).all():
                        if getattr(u, "name", None):
                            unit_lookup[_normalize_text(getattr(u, "name"))] = getattr(u, "id")

                    for _, row in observation_df.iterrows():
                        record_type = _clean_value(row.get("record_type"))
                        dataset_id = dataset_by_record_type.get(record_type)
                        if dataset_id is None:
                            logger.error("Skipping observation with unsupported record_type=%s", record_type)
                            continue
                        if _clean_value(row.get("geoid")) is None:
                            logger.error("Skipping observation with missing geoid.")
                            continue

                        observation_resource_id = _resolve_resource_id(session, _get_first_present(row, ("resource_id", "resource")))
                        if observation_resource_id is None:
                            logger.error(
                                "Skipping observation with unresolved resource: resource_name=%s, geoid=%s, year=%s",
                                _get_first_present(row, ("resource_id", "resource")),
                                row.get("geoid"),
                                row.get("year"),
                            )
                            continue

                        observation_year = row.get("year")
                        if observation_year is None or pd.isna(observation_year):
                            logger.error(
                                "Skipping observation with missing year: geoid=%s, resource_id=%s",
                                row.get("geoid"),
                                observation_resource_id,
                            )
                            continue

                        lookup_key = (record_type, str(_clean_value(row.get("geoid"))), int(observation_resource_id), int(observation_year))
                        record_db_id = record_id_lookup.get(lookup_key)
                        if record_db_id is None:
                            logger.error(
                                "Skipping observation with unresolved source record id: lookup_key=%s, geoid=%s, resource_id=%s, year=%s",
                                lookup_key,
                                row.get("geoid"),
                                observation_resource_id,
                                observation_year,
                            )
                            continue

                        resolved_parameter = _clean_value(row.get("parameter_id"))
                        resolved_parameter_row = None

                        if resolved_parameter is None:
                            resolved_parameter_row = _resolve_parameter_by_name(session, row.get("parameter_name"))
                            if resolved_parameter_row is not None:
                                resolved_parameter = getattr(resolved_parameter_row, "id", None)

                        # Unit resolution fallback (runs if unit_id is missing, regardless of how parameter was resolved)
                        if resolved_parameter is not None and _clean_value(row.get("unit_id")) is None:
                            row = row.copy()
                            unit_id = None

                            # 1. Try to get standard unit from the parameter if we have the row
                            if resolved_parameter_row is None:
                                from ca_biositing.datamodels.models import Parameter
                                resolved_parameter_row = session.get(Parameter, resolved_parameter)

                            if resolved_parameter_row is not None:
                                unit_id = getattr(resolved_parameter_row, "standard_unit_id", None)

                            # 2. Fallback by record_type if unit still missing
                            if unit_id is None:
                                if record_type == "resource_production_record":
                                    unit_id = unit_lookup.get(_normalize_text("tons")) or unit_lookup.get(_normalize_text("ton"))
                                    if unit_id is None:
                                        unit_id = _ensure_unit(session, "tons")
                                elif record_type == "resource_price_record":
                                    unit_id = unit_lookup.get(_normalize_text("dollars per ton")) or unit_lookup.get(_normalize_text("dollars per ton delivered"))
                                    if unit_id is None:
                                        unit_id = _ensure_unit(session, "dollars per ton")

                            row["unit_id"] = unit_id
                        if resolved_parameter is None:
                            logger.error(
                                "Skipping observation with unresolved parameter: name=%s, geoid=%s, resource_id=%s, year=%s",
                                row.get("parameter_name") or row.get("parameter_id"),
                                row.get("geoid"),
                                _get_first_present(row, ("resource_id", "resource")),
                                row.get("year"),
                            )
                            continue

                        if _clean_value(row.get("unit_id")) is None:
                            logger.error(
                                "Skipping observation with missing unit_id after parameter resolution: parameter=%s, geoid=%s, resource=%s, year=%s",
                                row.get("parameter_name") or resolved_parameter,
                                row.get("geoid"),
                                row.get("resource") or observation_resource_id,
                                observation_year,
                            )
                            continue

                        if _clean_value(row.get("parameter_id")) is None:
                            row = row.copy()
                            row["parameter_id"] = resolved_parameter

                        # Use the actual record ID from the lookup instead of a composite string
                        row = row.copy()
                        row["record_id"] = record_db_id

                        if _upsert_observation(
                            session,
                            row.to_dict(),
                            dataset_id=dataset_id,
                            record_id=record_db_id,
                            etl_run_id=_clean_value(row.get("etl_run_id")),
                            lineage_group_id=_clean_value(row.get("lineage_group_id")),
                        ):
                            counts["observation"] += 1

                session.commit()

                if counts["observation"] > 0:
                    sample = session.exec(select(Observation).where(Observation.dataset_id.in_([price_dataset.id, production_dataset.id])).limit(1)).first()
                    if sample is not None:
                        logger.info(
                            "Spot check observation: record_id=%s, record_type=%s, value=%s",
                            sample.record_id,
                            sample.record_type,
                            sample.value,
                        )
            except Exception:
                session.rollback()
                raise

    logger.info("Almond NSJV load completed with counts: %s", counts)
    return counts
