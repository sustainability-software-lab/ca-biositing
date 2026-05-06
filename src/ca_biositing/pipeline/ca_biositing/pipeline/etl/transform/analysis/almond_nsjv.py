"""
ETL Transform for Almond NSJV county ag reports.

Transforms the almond county ag report sheets into hourglass-style payloads
for parameters, resource records, and observations.
"""

from __future__ import annotations

from datetime import date
import re
from typing import Any, Dict, Optional

import pandas as pd
from prefect import get_run_logger, task
from sqlmodel import Session, select

from ca_biositing.pipeline.utils.cleaning_functions import cleaning as cleaning_mod
from ca_biositing.pipeline.utils.engine import get_engine
from ca_biositing.pipeline.utils.name_id_swap import normalize_dataframes

EXTRACT_SOURCES = ["parameters", "price_freight_terms", "price_production_county_ag_reports"]

_COUNTY_TO_GEOID = {
    "merced": "06047",
    "san joaquin": "06077",
    "nsjv": "NSJV",
    "stanislaus": "06099",
}

_ALLOWED_COUNTIES = {"merced", "san joaquin", "nsjv", "stanislaus"}

_COUNTY_PREFIXES = [
    ("san_joaquin_", "san joaquin"),
    ("stanislaus_", "stanislaus"),
    ("merced_", "merced"),
    ("nsjv_", "nsjv"),
]

_PRICE_TOKEN = "price"
_PRODUCTION_TOKEN = "production"


def _get_logger():
    try:
        return get_run_logger()
    except Exception:
        import logging

        return logging.getLogger(__name__)


def _normalize_text(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    text = str(value).strip().lower()
    text = re.sub(r"[\s_-]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text


def _normalize_parameter_name(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    text = str(value).strip().lower().replace("’", "'")
    # Keep an underscore-normalized form for internal parsing, but
    # callers that need human-friendly names should use `_normalize_text`.
    text = re.sub(r"[\s_-]+", "_", text)
    text = re.sub(r"_+", "_", text)
    return text


def _first_existing_column(df: pd.DataFrame, candidates: list[str]) -> Optional[str]:
    for candidate in candidates:
        if candidate in df.columns:
            return candidate
    return None


def _parse_county_header(header: Any) -> tuple[str, str]:
    text = _normalize_text(header)
    if text == "":
        return "", ""

    normalized = _normalize_parameter_name(text)
    for prefix, county_key in _COUNTY_PREFIXES:
        if normalized.startswith(prefix):
            suffix = normalized[len(prefix):].strip(" _-")
            return county_key, suffix

    parts = normalized.split("_", 1)
    if len(parts) == 2:
        return parts[0], parts[1]
    return text, ""


def _classify_metric(metric_name: str) -> Optional[str]:
    normalized = _normalize_text(metric_name)
    if normalized == "":
        return None
    if _PRICE_TOKEN in normalized:
        return "resource_price_record"
    if _PRODUCTION_TOKEN in normalized or "acreage" in normalized or "acre" in normalized:
        return "resource_production_record"
    return None


def _load_place_lookup() -> dict[str, str]:
    engine = get_engine()
    lookup: dict[str, str] = {}
    from ca_biositing.datamodels.models import Place

    with Session(engine) as session:
        rows = session.exec(select(Place)).all()
        for row in rows:
            county_name = _normalize_text(getattr(row, "county_name", None))
            geoid = getattr(row, "geoid", None)
            if county_name and geoid:
                lookup[county_name] = str(geoid)
                # Also add a variant without the trailing word 'county' if present
                if county_name.endswith(" county"):
                    short = county_name.replace(" county", "").strip()
                    if short:
                        lookup[short] = str(geoid)
                # Also add a variant without the word 'co' or similar abbreviations
                if county_name.endswith(" co"):
                    short = county_name.replace(" co", "").strip()
                    if short:
                        lookup[short] = str(geoid)
                # Also map common short keys from _COUNTY_TO_GEOID if available
                for k, v in _COUNTY_TO_GEOID.items():
                    if k in county_name and county_name not in lookup:
                        lookup[k] = str(v)
    return lookup


def _resolve_geoid(county_name: str, place_lookup: dict[str, str]) -> Optional[str]:
    county_key = _normalize_text(county_name)
    if county_key in place_lookup:
        return place_lookup[county_key]
    # Fallback: check canonical mapping
    if county_key in _COUNTY_TO_GEOID:
        return str(_COUNTY_TO_GEOID[county_key])
    # Also try removing trailing word 'county'
    if county_key.endswith(" county"):
        short = county_key.replace(" county", "").strip()
        if short in place_lookup:
            return place_lookup[short]
        if short in _COUNTY_TO_GEOID:
            return str(_COUNTY_TO_GEOID[short])
    return None


def _load_freight_terms_lookup(df: Optional[pd.DataFrame]) -> dict[str, str]:
    lookup: dict[str, str] = {}
    if df is None or df.empty:
        return lookup

    cleaned = _clean_sheet(df)
    if cleaned is None or cleaned.empty:
        return lookup

    county_col = _first_existing_column(cleaned, ["county", "county_name", "place", "name"])
    geoid_col = _first_existing_column(cleaned, ["geoid", "geo_id"])
    freight_terms_col = _first_existing_column(cleaned, ["freight_terms", "freight_term", "terms"])
    if freight_terms_col is None:
        return lookup

    for _, row in cleaned.iterrows():
        freight_terms = row.get(freight_terms_col)
        if freight_terms is None or (isinstance(freight_terms, str) and freight_terms.strip() == ""):
            continue

        freight_text = str(freight_terms).strip()
        if freight_text == "":
            continue

        county_name = _normalize_text(row.get(county_col)) if county_col else ""
        geoid = _normalize_text(row.get(geoid_col)) if geoid_col else ""

        if county_name:
            lookup[county_name] = freight_text
            if county_name.endswith(" county"):
                lookup[county_name.replace(" county", "").strip()] = freight_text
            if county_name.endswith(" co"):
                lookup[county_name.replace(" co", "").strip()] = freight_text
        if geoid:
            lookup[str(geoid)] = freight_text

    return lookup


def _clean_sheet(df: pd.DataFrame) -> Optional[pd.DataFrame]:
    cleaned = cleaning_mod.standard_clean(df)
    if cleaned is None:
        return None
    return cleaned.copy()


@task
def transform_county_ag_parameters(
    data_sources: Dict[str, pd.DataFrame],
    etl_run_id: str | None = None,
    lineage_group_id: str | None = None,
) -> Optional[pd.DataFrame]:
    logger = _get_logger()
    if "parameters" not in data_sources:
        logger.error("Required data source 'parameters' not found.")
        return None

    raw_df = data_sources["parameters"].copy()
    if raw_df.empty:
        return pd.DataFrame()

    cleaned = _clean_sheet(raw_df)
    if cleaned is None or cleaned.empty:
        return pd.DataFrame()

    marker_col = _first_existing_column(cleaned, ["marker", "group", "category", "type", "tag"])
    if marker_col is None:
        marker_col = cleaned.columns[0]

    cleaned = cleaned[cleaned[marker_col].astype(str).str.contains("price_production_county_ag_reports", case=False, na=False)].copy()
    if cleaned.empty:
        logger.warning("No almond parameter rows matched the expected marker.")
        return pd.DataFrame()

    name_col = _first_existing_column(cleaned, ["name", "parameter", "parameter_name"])
    if name_col and name_col != "name":
        cleaned = cleaned.rename(columns={name_col: "name"})

    description_col = _first_existing_column(cleaned, ["description", "desc", "notes", "note"])
    if description_col and description_col != "description":
        cleaned = cleaned.rename(columns={description_col: "description"})

    unit_col = _first_existing_column(cleaned, ["standard_unit", "unit", "unit_name"])
    if unit_col and unit_col != "standard_unit":
        cleaned = cleaned.rename(columns={unit_col: "standard_unit"})

    if "name" not in cleaned.columns:
        logger.warning("Expected parameter name column not found in parameters sheet.")
        return pd.DataFrame()

    cleaned["name"] = cleaned["name"].apply(_normalize_text)
    cleaned = cleaned[cleaned["name"].astype(str).str.strip() != ""].copy()
    cleaned["calculated"] = cleaned["name"].str.contains("calculated|estimate", case=False, na=False)
    cleaned["parameter_dedupe_key"] = cleaned["name"].astype(str).str.strip().str.lower()
    cleaned["etl_run_id"] = etl_run_id
    cleaned["lineage_group_id"] = lineage_group_id

    from ca_biositing.datamodels.models import Unit

    normalized = normalize_dataframes(cleaned, {"standard_unit": (Unit, "name")})[0]
    if "standard_unit_id" not in normalized.columns:
        normalized["standard_unit_id"] = pd.NA

    desired_columns = [
        "name",
        "description",
        "calculated",
        "standard_unit_id",
        "parameter_dedupe_key",
        "etl_run_id",
        "lineage_group_id",
    ]
    logger.info("Prepared %s almond parameters.", len(normalized))
    return normalized[desired_columns].copy()


@task
def transform_county_ag_records(
    data_sources: Dict[str, pd.DataFrame],
    etl_run_id: str | None = None,
    lineage_group_id: str | None = None,
) -> Optional[Dict[str, pd.DataFrame]]:
    logger = _get_logger()
    if "price_production_county_ag_reports" not in data_sources:
        logger.error("Required data source 'price_production_county_ag_reports' not found.")
        return None

    raw_df = data_sources["price_production_county_ag_reports"].copy()
    if raw_df.empty:
        return {
            "resource_price_record": pd.DataFrame(),
            "resource_production_record": pd.DataFrame(),
        }

    place_lookup = _load_place_lookup()
    freight_terms_lookup = _load_freight_terms_lookup(data_sources.get("price_freight_terms"))
    records: dict[str, list[dict[str, Any]]] = {
        "resource_price_record": [],
        "resource_production_record": [],
    }

    def build_rows(raw_df: pd.DataFrame) -> None:
        cleaned = _clean_sheet(raw_df)
        if cleaned is None or cleaned.empty:
            return

        if "resource" not in cleaned.columns:
            resource_col = _first_existing_column(cleaned, ["resource_name", "primary_ag_product", "primary_product"])
            if resource_col:
                cleaned = cleaned.rename(columns={resource_col: "resource"})

        if "resource" in cleaned.columns:
            cleaned = cleaned[cleaned["resource"].notna() & (cleaned["resource"].astype(str).str.strip() != "")].copy()
        if cleaned.empty:
            return

        year_col = _first_existing_column(cleaned, ["year", "data_year", "report_year"])
        resource_col = _first_existing_column(cleaned, ["resource", "resource_name"])
        primary_product_col = _first_existing_column(cleaned, ["primary_ag_product", "primary_product"])
        if year_col is None or resource_col is None:
            logger.warning("Could not identify year/resource columns in almond sheet: columns=%s", cleaned.columns.tolist())
            return

        metric_columns = [col for col in cleaned.columns if col not in {year_col, resource_col, primary_product_col, "note", "description"}]
        for _, row in cleaned.iterrows():
            resource_value = row.get(resource_col)
            if pd.isna(resource_value) or str(resource_value).strip() == "":
                # Keep the current filter: skip rows with no resource even if they only contain
                # primary agricultural product information. This can be expanded later if needed.
                continue

            report_year = row.get(year_col)
            if pd.isna(report_year) or str(report_year).strip() == "":
                continue

            county_name = None
            geoid = None

            base_payload = {
                "geoid": geoid,
                "resource": resource_value,
                "primary_ag_product": row.get(primary_product_col) if primary_product_col else None,
                "report_year": int(float(report_year)),
                "note": row.get("note") if "note" in row.index else row.get("description"),
                "etl_run_id": etl_run_id,
                "lineage_group_id": lineage_group_id,
            }

            for column in metric_columns:
                metric_value = row.get(column)
                if metric_value is None or (isinstance(metric_value, str) and metric_value.strip() == ""):
                    continue

                record_type = _classify_metric(column)
                if record_type is None:
                    continue

                county_name_normalized, metric_name = _parse_county_header(column)
                if county_name_normalized not in _ALLOWED_COUNTIES:
                    continue
                county_name = county_name_normalized or county_name
                geoid = _resolve_geoid(county_name, place_lookup)
                if not geoid:
                    logger.error("Skipping almond row with unresolved county/geoid: county=%s column=%s", county_name, column)
                    continue

                payload = base_payload.copy()
                freight_terms = None
                if record_type == "resource_price_record":
                    # We may want a join table later mapping county x commodity to reported freight term.
                    freight_terms = freight_terms_lookup.get(county_name_normalized) or freight_terms_lookup.get(str(geoid))
                payload.update(
                    {
                        "geoid": geoid,
                        # store human-friendly parameter names (spaces, no underscores)
                        "metric_name": metric_name or _normalize_text(_parse_county_header(column)[1] or column),
                        "county_name": county_name_normalized or _normalize_text(county_name),
                        "value": metric_value,
                        "record_type": record_type,
                        "source_sheet": "price_production_county_ag_reports",
                        "freight_terms": freight_terms,
                    }
                )
                records[record_type].append(payload)

    build_rows(raw_df)

    price_records = pd.DataFrame(records["resource_price_record"])
    production_records = pd.DataFrame(records["resource_production_record"])

    for df in [price_records, production_records]:
        if not df.empty:
            df["report_start_date"] = pd.to_datetime(df["report_year"].astype(int).astype(str) + "-01-01").dt.date
            df["report_end_date"] = pd.to_datetime(df["report_year"].astype(int).astype(str) + "-12-31").dt.date
            # production records use a single report_date (Jan 1 of the year)
            if df is production_records:
                df["report_date"] = pd.to_datetime(df["report_year"].astype(int).astype(str) + "-01-01").dt.date
            df["dataset_dedupe_key"] = df["record_type"].astype(str) + "|" + df["geoid"].astype(str) + "|" + df["report_year"].astype(str)

    logger.info(
        "Prepared almond records: %s price rows, %s production rows.",
        len(price_records),
        len(production_records),
    )
    return {
        "resource_price_record": price_records,
        "resource_production_record": production_records,
    }


@task
def transform_county_ag_observations(
    data_sources: Dict[str, pd.DataFrame],
    etl_run_id: str | None = None,
    lineage_group_id: str | None = None,
) -> Optional[pd.DataFrame]:
    logger = _get_logger()
    if "price_production_county_ag_reports" not in data_sources:
        logger.error("Required data source 'price_production_county_ag_reports' not found.")
        return None

    from ca_biositing.datamodels.models import Parameter

    place_lookup = _load_place_lookup()
    engine = get_engine()
    parameter_lookup: dict[str, int] = {}
    with Session(engine) as session:
        rows = session.exec(select(Parameter)).all()
        for row in rows:
            name = _normalize_text(getattr(row, "name", None))
            if name:
                parameter_lookup[name] = row.id

    observation_rows: list[dict[str, Any]] = []

    def collect_observations(raw_df: pd.DataFrame) -> None:
        cleaned = _clean_sheet(raw_df)
        if cleaned is None or cleaned.empty:
            return

        if "resource" not in cleaned.columns:
            resource_col = _first_existing_column(cleaned, ["resource_name", "primary_ag_product", "primary_product"])
            if resource_col:
                cleaned = cleaned.rename(columns={resource_col: "resource"})

        year_col = _first_existing_column(cleaned, ["year", "data_year", "report_year"])
        if year_col is None or "resource" not in cleaned.columns:
            return

        metric_columns = [col for col in cleaned.columns if col not in {year_col, "resource", "primary_ag_product", "note", "description"}]

        for _, row in cleaned.iterrows():
            resource_value = row.get("resource")
            if pd.isna(resource_value) or str(resource_value).strip() == "":
                continue

            report_year = row.get(year_col)
            if pd.isna(report_year) or str(report_year).strip() == "":
                continue

            for column in metric_columns:
                value = row.get(column)
                if value is None or (isinstance(value, str) and value.strip() == ""):
                    continue

                record_type = _classify_metric(column)
                if record_type is None:
                    continue

                parameter_name = _normalize_text(_parse_county_header(column)[1] or column)
                parameter_id = parameter_lookup.get(parameter_name)

                county_name_normalized, _ = _parse_county_header(column)
                if county_name_normalized not in _ALLOWED_COUNTIES:
                    continue
                geoid = _resolve_geoid(county_name_normalized, place_lookup)
                if not geoid:
                    logger.error("Skipping observation with unresolved county/geoid: county=%s column=%s", county_name_normalized, column)
                    continue

                observation_rows.append(
                    {
                        "geoid": geoid,
                        "resource": resource_value,
                        "record_type": record_type,
                        "parameter_id": parameter_id,
                        "parameter_name": parameter_name,
                        "value": value,
                        "year": int(float(report_year)),
                        "report_date": date(int(float(report_year)), 1, 1),
                        "etl_run_id": etl_run_id,
                        "lineage_group_id": lineage_group_id,
                    }
                )

    collect_observations(data_sources["price_production_county_ag_reports"])

    observations = pd.DataFrame(observation_rows)
    if not observations.empty:
        observations["observation_dedupe_key"] = (
            observations["record_type"].astype(str)
            + "|"
            + observations["geoid"].astype(str)
            + "|"
            + observations["parameter_id"].astype(str)
            + "|"
            + observations["year"].astype(str)
            + "|"
            + observations["resource"].astype(str)
        )

    logger.info("Prepared %s almond observations.", len(observations))
    return observations


@task
def transform_almond_nsjv_payloads(
    data_sources: Dict[str, pd.DataFrame],
    etl_run_id: str | None = None,
    lineage_group_id: str | None = None,
) -> Dict[str, Any]:
    """Convenience wrapper that returns all transformed almond payloads."""
    return {
        "parameter": transform_county_ag_parameters.fn(
            data_sources=data_sources,
            etl_run_id=etl_run_id,
            lineage_group_id=lineage_group_id,
        ),
        "records": transform_county_ag_records.fn(
            data_sources=data_sources,
            etl_run_id=etl_run_id,
            lineage_group_id=lineage_group_id,
        ),
        "observation": transform_county_ag_observations.fn(
            data_sources=data_sources,
            etl_run_id=etl_run_id,
            lineage_group_id=lineage_group_id,
        ),
    }


def _log_dataframe_preview(logger: Any, name: str, df: Any, max_rows: int = 5) -> None:
    if not isinstance(df, pd.DataFrame):
        logger.info("%s: %s", name, type(df).__name__)
        return

    logger.info("%s shape: %s", name, df.shape)
    logger.info("%s columns: %s", name, df.columns.tolist())
    if df.empty:
        logger.info("%s is empty.", name)
        return

    preview = df.head(max_rows)
    logger.info("%s head(%s):\n%s", name, max_rows, preview.to_string(index=False))


@task
def preview_almond_nsjv_payloads(
    data_sources: Dict[str, pd.DataFrame],
    etl_run_id: str | None = None,
    lineage_group_id: str | None = None,
) -> Dict[str, Any]:
    """Run the almond transforms and log compact previews for manual inspection."""
    logger = _get_logger()
    payloads = transform_almond_nsjv_payloads.fn(
        data_sources=data_sources,
        etl_run_id=etl_run_id,
        lineage_group_id=lineage_group_id,
    )

    _log_dataframe_preview(logger, "parameter", payloads.get("parameter"))
    records = payloads.get("records") or {}
    _log_dataframe_preview(logger, "resource_price_record", records.get("resource_price_record"))
    _log_dataframe_preview(logger, "resource_production_record", records.get("resource_production_record"))
    _log_dataframe_preview(logger, "observation", payloads.get("observation"))

    return payloads
