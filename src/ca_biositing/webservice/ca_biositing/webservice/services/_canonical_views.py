"""Canonical view selectors for feedstock services.

PostgreSQL queries the materialized view objects in the ca_biositing schema.
SQLite tests fall back to the canonical SQLAlchemy view expressions.
"""

from __future__ import annotations

from sqlalchemy import Boolean, Date, DateTime, Float, Integer, String, column, table
from sqlalchemy.orm import Session

from ca_biositing.datamodels.biocirv_public_views import (
    BIOCIRV_PUBLIC_SCHEMA,
    mv_analytical_observations,
    mv_analytical_summary,
    mv_resources,
    mv_sample_summary,
    mv_samples,
    register_sqlite_udfs,
)
from ca_biositing.datamodels.views import (
    ANALYSIS_DATA_VIEW,
    USDA_CENSUS_VIEW,
    USDA_RESOURCE_COMMODITY_VIEW,
    USDA_SURVEY_VIEW,
    VIEW_SCHEMA,
)


def _uses_postgres(session: Session) -> bool:
    bind = session.get_bind()
    if bind is None:
        return False
    return bind.dialect.name == "postgresql"


def _postgres_view(name: str, *columns):
    return table(name, *columns, schema=VIEW_SCHEMA)


def _biocirv_public_view(name: str, *columns):
    return table(name, *columns, schema=BIOCIRV_PUBLIC_SCHEMA)


def get_analysis_data_view(session: Session):
    if _uses_postgres(session):
        return _postgres_view(
            "analysis_data_view",
            column("id", Integer),
            column("resource_id", Integer),
            column("resource", String),
            column("geoid", String),
            column("parameter", String),
            column("value", Float),
            column("unit", String),
            column("dimension", String),
            column("dimension_value", Float),
            column("dimension_unit", String),
        )
    return ANALYSIS_DATA_VIEW.subquery("analysis_data_view")


def get_usda_census_view(session: Session):
    if _uses_postgres(session):
        return _postgres_view(
            "usda_census_view",
            column("id", Integer),
            column("usda_crop", String),
            column("geoid", String),
            column("parameter", String),
            column("value", Float),
            column("unit", String),
            column("dimension", String),
            column("dimension_value", Float),
            column("dimension_unit", String),
            column("commodity_id", Integer),
            column("source_record_id", Integer),
            column("record_year", Integer),
        )
    return USDA_CENSUS_VIEW.subquery("usda_census_view")


def get_usda_resource_commodity_view(session: Session):
    if _uses_postgres(session):
        return _postgres_view(
            "usda_resource_commodity_view",
            column("resource", String),
            column("commodity_id", Integer),
        )
    return USDA_RESOURCE_COMMODITY_VIEW.subquery("usda_resource_commodity_view")


def get_usda_survey_view(session: Session):
    if _uses_postgres(session):
        return _postgres_view(
            "usda_survey_view",
            column("id", Integer),
            column("usda_crop", String),
            column("geoid", String),
            column("parameter", String),
            column("value", Float),
            column("unit", String),
            column("dimension", String),
            column("dimension_value", Float),
            column("dimension_unit", String),
            column("commodity_id", Integer),
            column("source_record_id", Integer),
            column("record_year", Integer),
            column("survey_program_id", Integer),
            column("survey_period", String),
            column("reference_month", String),
            column("seasonal_flag", Boolean),
        )
    return USDA_SURVEY_VIEW.subquery("usda_survey_view")


def get_biocirv_observations_view(session: Session):
    if _uses_postgres(session):
        return _biocirv_public_view(
            "mv_analytical_observations",
            column("record_id", String),
            column("analysis_type", String),
            column("resource_name", String),
            column("resource_code", String),
            column("resource_class", String),
            column("resource_subclass", String),
            column("primary_ag_product", String),
            column("prepared_sample_name", String),
            column("prep_method_name", String),
            column("drying_step", Boolean),
            column("field_sample_name", String),
            column("provider_codename", String),
            column("county_name", String),
            column("county_fips", String),
            column("state_name", String),
            column("geoid", String),
            column("parameter_name", String),
            column("value", Float),
            column("unit_name", String),
            column("dimension_name", String),
            column("dimension_value", Float),
            column("dimension_unit_name", String),
            column("technical_replicate_no", Integer),
            column("technical_replicate_total", Integer),
            column("method_name", String),
            column("method_abbrev", String),
            column("method_category", String),
            column("method_standard", String),
            column("experiment_name", String),
        )
    register_sqlite_udfs(session)
    return mv_analytical_observations.subquery("mv_analytical_observations")


def get_biocirv_samples_view(session: Session):
    if _uses_postgres(session):
        return _biocirv_public_view(
            "mv_samples",
            column("prepared_sample_name", String),
            column("prep_date", Date),
            column("prep_method_name", String),
            column("prep_method_abbrev", String),
            column("prep_temp_c", Float),
            column("drying_step", Boolean),
            column("field_sample_name", String),
            column("resource_name", String),
            column("resource_code", String),
            column("resource_class", String),
            column("resource_subclass", String),
            column("primary_ag_product", String),
            column("provider_codename", String),
            column("county_name", String),
            column("county_fips", String),
            column("state_name", String),
            column("geoid", String),
            column("sample_collection_source", String),
            column("collection_timestamp", DateTime),
            column("harvest_date", Date),
            column("harvest_method_name", String),
            column("collection_method_name", String),
            column("ag_treatment_name", String),
            column("processing_method_name", String),
            column("field_storage_method_name", String),
            column("field_storage_duration_value", Float),
            column("field_storage_duration_unit", String),
            column("replicate_record_count", Integer),
            column("observation_count", Integer),
        )
    register_sqlite_udfs(session)
    return mv_samples.subquery("mv_samples")


def get_biocirv_resources_view(session: Session):
    if _uses_postgres(session):
        return _biocirv_public_view(
            "mv_resources",
            column("resource_name", String),
            column("resource_code", String),
            column("description", String),
            column("resource_class", String),
            column("resource_subclass", String),
            column("primary_ag_product", String),
            column("field_sample_count", Integer),
            column("prepared_sample_count", Integer),
            column("provider_count", Integer),
            column("county_count", Integer),
            column("replicate_record_count", Integer),
            column("observation_count", Integer),
            column("has_proximate", Boolean),
            column("has_compositional", Boolean),
            column("has_xrf", Boolean),
            column("has_icp", Boolean),
            column("has_calorimetry", Boolean),
        )
    register_sqlite_udfs(session)
    return mv_resources.subquery("mv_resources")


def get_biocirv_sample_summary_view(session: Session):
    if _uses_postgres(session):
        return _biocirv_public_view(
            "mv_sample_summary",
            column("prepared_sample_name", String),
            column("field_sample_name", String),
            column("resource_name", String),
            column("resource_code", String),
            column("provider_codename", String),
            column("county_name", String),
            column("county_fips", String),
            column("geoid", String),
            column("analysis_type", String),
            column("parameter_name", String),
            column("unit_name", String),
            column("mean_value", Float),
            column("std_dev", Float),
            column("min_value", Float),
            column("max_value", Float),
            column("replicate_count", Integer),
            column("method_name", String),
            column("drying_step", Boolean),
        )
    register_sqlite_udfs(session)
    return mv_sample_summary.subquery("mv_sample_summary")


def get_biocirv_analytical_summary_view(session: Session):
    if _uses_postgres(session):
        return _biocirv_public_view(
            "mv_analytical_summary",
            column("resource_name", String),
            column("resource_code", String),
            column("resource_class", String),
            column("resource_subclass", String),
            column("county_name", String),
            column("county_fips", String),
            column("state_name", String),
            column("geoid", String),
            column("analysis_type", String),
            column("parameter_name", String),
            column("unit_name", String),
            column("mean_value", Float),
            column("std_dev", Float),
            column("min_value", Float),
            column("max_value", Float),
            column("observation_count", Integer),
            column("prepared_sample_count", Integer),
            column("field_sample_count", Integer),
            column("provider_count", Integer),
        )
    register_sqlite_udfs(session)
    return mv_analytical_summary.subquery("mv_analytical_summary")
