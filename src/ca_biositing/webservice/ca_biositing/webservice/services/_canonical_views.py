"""Canonical view selectors for feedstock services.

PostgreSQL queries the materialized view objects in the ca_biositing schema.
SQLite tests fall back to the canonical SQLAlchemy view expressions.
"""

from __future__ import annotations

from sqlalchemy import Boolean, Date, DateTime, Float, Integer, String, column, table
from sqlalchemy.orm import Session

from ca_biositing.datamodels.biocirv_public_views import (
    BIOCIRV_PUBLIC_SCHEMA,
    mv_analytical_summary,
    mv_resources,
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


def get_biocirv_resources_view(session: Session):
    if _uses_postgres(session):
        return _biocirv_public_view(
            "mv_resources",
            column("resource_name", String),
            column("description", String),
            column("resource_class", String),
            column("primary_ag_product", String),
            column("field_sample_count", Integer),
            column("prepared_sample_count", Integer),
            column("provider_count", Integer),
            column("observation_count", Integer),
            column("has_proximate", Boolean),
            column("has_compositional", Boolean),
            column("has_icp", Boolean),
        )
    register_sqlite_udfs(session)
    return mv_resources.subquery("mv_resources")


def get_biocirv_analytical_summary_view(session: Session):
    if _uses_postgres(session):
        return _biocirv_public_view(
            "mv_analytical_summary",
            column("resource_name", String),
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
