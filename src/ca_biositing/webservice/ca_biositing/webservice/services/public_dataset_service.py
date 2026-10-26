"""Service layer for the BioCirV Open Public Dataset (`/v1/public`) endpoints.

Queries the 5 read-only materialized views in the `biocirv_public` schema
(with transparent SQLite fallback via `_canonical_views.py` for unit tests).
"""

from __future__ import annotations

import time
from typing import Any, Optional

from fastapi import HTTPException, status
from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session

from ca_biositing.webservice.exceptions import ResourceNotFoundException
from ca_biositing.webservice.services._canonical_views import (
    get_biocirv_analytical_summary_view,
    get_biocirv_observations_view,
    get_biocirv_resources_view,
    get_biocirv_sample_summary_view,
    get_biocirv_samples_view,
)
from ca_biositing.webservice.services._usda_lookup_common import (
    normalize_crop_name,
    normalized_sql_text,
)

MAX_PAGE_LIMIT = 100
MAX_PAGE_SKIP = 10_000
RELEASE_STAGE = "stage_1"
SCHEMA_VERSION = "1.0.0"

_DISCOVERY_CACHE_TTL_SECONDS = 300.0
_discovery_cache: dict[tuple[int, str], tuple[float, Any]] = {}


def clear_discovery_cache() -> None:
    """Clear the in-memory discovery endpoint cache (used after refresh or in tests)."""
    _discovery_cache.clear()


def _clamp_pagination(skip: int, limit: int) -> tuple[int, int]:
    clamped_skip = min(max(0, int(skip)), MAX_PAGE_SKIP)
    clamped_limit = max(1, min(int(limit), MAX_PAGE_LIMIT))
    return clamped_skip, clamped_limit


def _normalize_analysis_type(analysis_type: str) -> str:
    norm = analysis_type.strip().lower()
    for suffix in ("_record", " analysis"):
        if norm.endswith(suffix):
            norm = norm[: -len(suffix)].strip()
    return norm


def _apply_resource_filter(stmt, view, resource: str):
    cleaned = resource.strip()
    norm = normalize_crop_name(cleaned)
    if cleaned.isdigit():
        return stmt.where(
            or_(
                view.c.resource_id == int(cleaned),
                normalized_sql_text(view.c.resource_name) == norm,
                normalized_sql_text(view.c.resource_code) == norm,
            )
        )
    return stmt.where(
        or_(
            normalized_sql_text(view.c.resource_name) == norm,
            normalized_sql_text(view.c.resource_code) == norm,
        )
    )


def _row_to_dict(row: Any, float_fields: tuple[str, ...] = ()) -> dict[str, Any]:
    data = dict(row._mapping)
    for field in float_fields:
        if field in data and data[field] is not None:
            data[field] = float(data[field])
    return data


def _paginate_and_execute(
    session: Session,
    stmt,
    *,
    skip: int,
    limit: int,
    order_by_col,
    float_fields: tuple[str, ...] = (),
) -> dict[str, Any]:
    clamped_skip, clamped_limit = _clamp_pagination(skip, limit)
    count_subq = stmt.subquery("filtered_count_sq")
    total = session.execute(select(func.count()).select_from(count_subq)).scalar() or 0
    rows = session.execute(
        stmt.order_by(order_by_col).offset(clamped_skip).limit(clamped_limit)
    ).all()
    return {
        "release_stage": RELEASE_STAGE,
        "schema_version": SCHEMA_VERSION,
        "total": int(total),
        "skip": clamped_skip,
        "limit": clamped_limit,
        "data": [_row_to_dict(r, float_fields=float_fields) for r in rows],
    }


class PublicDatasetService:
    """Read-only query service for `biocirv_public` views."""

    @staticmethod
    def list_resources(
        session: Session,
        *,
        resource_class: Optional[str] = None,
        resource_subclass: Optional[str] = None,
        has_proximate: Optional[bool] = None,
        has_compositional: Optional[bool] = None,
        has_xrf: Optional[bool] = None,
        has_icp: Optional[bool] = None,
        has_calorimetry: Optional[bool] = None,
        skip: int = 0,
        limit: int = MAX_PAGE_LIMIT,
    ) -> dict[str, Any]:
        view = get_biocirv_resources_view(session)
        stmt = select(view)

        if resource_class:
            stmt = stmt.where(
                normalized_sql_text(view.c.resource_class)
                == normalize_crop_name(resource_class)
            )
        if resource_subclass:
            stmt = stmt.where(
                normalized_sql_text(view.c.resource_subclass)
                == normalize_crop_name(resource_subclass)
            )
        if has_proximate is not None:
            stmt = stmt.where(view.c.has_proximate.is_(has_proximate))
        if has_compositional is not None:
            stmt = stmt.where(view.c.has_compositional.is_(has_compositional))
        if has_xrf is not None:
            stmt = stmt.where(view.c.has_xrf.is_(has_xrf))
        if has_icp is not None:
            stmt = stmt.where(view.c.has_icp.is_(has_icp))
        if has_calorimetry is not None:
            stmt = stmt.where(view.c.has_calorimetry.is_(has_calorimetry))

        return _paginate_and_execute(
            session,
            stmt,
            skip=skip,
            limit=limit,
            order_by_col=view.c.id,
        )

    @staticmethod
    def get_resource(session: Session, resource: str) -> dict[str, Any]:
        view = get_biocirv_resources_view(session)
        cleaned = resource.strip()
        norm = normalize_crop_name(cleaned)
        order_clauses = []
        if cleaned.isdigit():
            order_clauses.append(
                case((view.c.resource_id == int(cleaned), 0), else_=1)
            )
        order_clauses.append(
            case((normalized_sql_text(view.c.resource_code) == norm, 0), else_=1)
        )
        order_clauses.append(view.c.id)
        stmt = _apply_resource_filter(select(view), view, resource).order_by(
            *order_clauses
        )
        row = session.execute(stmt).first()
        if row is None:
            raise ResourceNotFoundException(resource)
        return _row_to_dict(row)

    @staticmethod
    def list_samples(
        session: Session,
        *,
        resource: Optional[str] = None,
        county_name: Optional[str] = None,
        geoid: Optional[str] = None,
        provider_codename: Optional[str] = None,
        prep_method_name: Optional[str] = None,
        drying_step: Optional[bool] = None,
        skip: int = 0,
        limit: int = MAX_PAGE_LIMIT,
    ) -> dict[str, Any]:
        view = get_biocirv_samples_view(session)
        stmt = select(view)

        if resource:
            stmt = _apply_resource_filter(stmt, view, resource)
        if county_name:
            stmt = stmt.where(
                normalized_sql_text(view.c.county_name)
                == normalize_crop_name(county_name)
            )
        if geoid:
            stmt = stmt.where(view.c.geoid == geoid.strip())
        if provider_codename:
            stmt = stmt.where(
                func.lower(view.c.provider_codename) == provider_codename.strip().lower()
            )
        if prep_method_name:
            stmt = stmt.where(
                normalized_sql_text(view.c.prep_method_name)
                == normalize_crop_name(prep_method_name)
            )
        if drying_step is not None:
            stmt = stmt.where(view.c.drying_step.is_(drying_step))

        return _paginate_and_execute(
            session,
            stmt,
            skip=skip,
            limit=limit,
            order_by_col=view.c.id,
            float_fields=("prep_temp_c", "field_storage_duration_value"),
        )

    @staticmethod
    def get_sample(session: Session, prepared_sample_id: int) -> dict[str, Any]:
        view = get_biocirv_samples_view(session)
        stmt = (
            select(view)
            .where(view.c.prepared_sample_id == prepared_sample_id)
            .order_by(view.c.id)
        )
        row = session.execute(stmt).first()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Prepared sample {prepared_sample_id} not found in public dataset",
            )
        return _row_to_dict(
            row, float_fields=("prep_temp_c", "field_storage_duration_value")
        )

    @staticmethod
    def list_observations(
        session: Session,
        *,
        resource: Optional[str] = None,
        analysis_type: Optional[str] = None,
        parameter_name: Optional[str] = None,
        prepared_sample_id: Optional[int] = None,
        field_sample_id: Optional[int] = None,
        county_name: Optional[str] = None,
        geoid: Optional[str] = None,
        provider_codename: Optional[str] = None,
        drying_step: Optional[bool] = None,
        skip: int = 0,
        limit: int = MAX_PAGE_LIMIT,
    ) -> dict[str, Any]:
        view = get_biocirv_observations_view(session)
        stmt = select(view)

        if resource:
            stmt = _apply_resource_filter(stmt, view, resource)
        if analysis_type:
            stmt = stmt.where(
                func.lower(view.c.analysis_type)
                == _normalize_analysis_type(analysis_type)
            )
        if parameter_name:
            stmt = stmt.where(
                normalized_sql_text(view.c.parameter_name)
                == normalize_crop_name(parameter_name)
            )
        if prepared_sample_id is not None:
            stmt = stmt.where(view.c.prepared_sample_id == prepared_sample_id)
        if field_sample_id is not None:
            stmt = stmt.where(view.c.field_sample_id == field_sample_id)
        if county_name:
            stmt = stmt.where(
                normalized_sql_text(view.c.county_name)
                == normalize_crop_name(county_name)
            )
        if geoid:
            stmt = stmt.where(view.c.geoid == geoid.strip())
        if provider_codename:
            stmt = stmt.where(
                func.lower(view.c.provider_codename) == provider_codename.strip().lower()
            )
        if drying_step is not None:
            stmt = stmt.where(view.c.drying_step.is_(drying_step))

        return _paginate_and_execute(
            session,
            stmt,
            skip=skip,
            limit=limit,
            order_by_col=view.c.id,
            float_fields=("value", "dimension_value"),
        )

    @staticmethod
    def list_sample_summaries(
        session: Session,
        *,
        resource: Optional[str] = None,
        prepared_sample_id: Optional[int] = None,
        analysis_type: Optional[str] = None,
        parameter_name: Optional[str] = None,
        county_name: Optional[str] = None,
        geoid: Optional[str] = None,
        drying_step: Optional[bool] = None,
        skip: int = 0,
        limit: int = MAX_PAGE_LIMIT,
    ) -> dict[str, Any]:
        view = get_biocirv_sample_summary_view(session)
        stmt = select(view)

        if resource:
            stmt = _apply_resource_filter(stmt, view, resource)
        if prepared_sample_id is not None:
            stmt = stmt.where(view.c.prepared_sample_id == prepared_sample_id)
        if analysis_type:
            stmt = stmt.where(
                func.lower(view.c.analysis_type)
                == _normalize_analysis_type(analysis_type)
            )
        if parameter_name:
            stmt = stmt.where(
                normalized_sql_text(view.c.parameter_name)
                == normalize_crop_name(parameter_name)
            )
        if county_name:
            stmt = stmt.where(
                normalized_sql_text(view.c.county_name)
                == normalize_crop_name(county_name)
            )
        if geoid:
            stmt = stmt.where(view.c.geoid == geoid.strip())
        if drying_step is not None:
            stmt = stmt.where(view.c.drying_step.is_(drying_step))

        return _paginate_and_execute(
            session,
            stmt,
            skip=skip,
            limit=limit,
            order_by_col=view.c.id,
            float_fields=("mean_value", "std_dev", "min_value", "max_value"),
        )

    @staticmethod
    def list_analytical_summaries(
        session: Session,
        *,
        resource: Optional[str] = None,
        analysis_type: Optional[str] = None,
        parameter_name: Optional[str] = None,
        county_name: Optional[str] = None,
        geoid: Optional[str] = None,
        skip: int = 0,
        limit: int = MAX_PAGE_LIMIT,
    ) -> dict[str, Any]:
        view = get_biocirv_analytical_summary_view(session)
        stmt = select(view)

        if resource:
            stmt = _apply_resource_filter(stmt, view, resource)
        if analysis_type:
            stmt = stmt.where(
                func.lower(view.c.analysis_type)
                == _normalize_analysis_type(analysis_type)
            )
        if parameter_name:
            stmt = stmt.where(
                normalized_sql_text(view.c.parameter_name)
                == normalize_crop_name(parameter_name)
            )
        if county_name:
            stmt = stmt.where(
                normalized_sql_text(view.c.county_name)
                == normalize_crop_name(county_name)
            )
        if geoid:
            stmt = stmt.where(view.c.geoid == geoid.strip())

        return _paginate_and_execute(
            session,
            stmt,
            skip=skip,
            limit=limit,
            order_by_col=view.c.id,
            float_fields=("mean_value", "std_dev", "min_value", "max_value"),
        )

    @staticmethod
    def list_analysis_types(session: Session) -> list[dict[str, Any]]:
        bind_key = id(session.get_bind())
        cache_key = (bind_key, "analysis_types")
        now = time.monotonic()
        cached = _discovery_cache.get(cache_key)
        if cached is not None and (now - cached[0]) < _DISCOVERY_CACHE_TTL_SECONDS:
            return cached[1]

        view = get_biocirv_observations_view(session)
        stmt = (
            select(
                view.c.analysis_type,
                func.count(func.distinct(view.c.observation_id)).label(
                    "observation_count"
                ),
                func.count(func.distinct(view.c.resource_id)).label("resource_count"),
                func.count(func.distinct(view.c.parameter_name)).label("parameter_count"),
            )
            .where(view.c.analysis_type.is_not(None))
            .group_by(view.c.analysis_type)
            .order_by(view.c.analysis_type)
        )
        rows = session.execute(stmt).all()
        result = [
            {
                "analysis_type": r.analysis_type,
                "observation_count": int(r.observation_count or 0),
                "resource_count": int(r.resource_count or 0),
                "parameter_count": int(r.parameter_count or 0),
            }
            for r in rows
        ]
        _discovery_cache[cache_key] = (now, result)
        return result

    @staticmethod
    def list_parameters(session: Session) -> list[dict[str, Any]]:
        bind_key = id(session.get_bind())
        cache_key = (bind_key, "parameters")
        now = time.monotonic()
        cached = _discovery_cache.get(cache_key)
        if cached is not None and (now - cached[0]) < _DISCOVERY_CACHE_TTL_SECONDS:
            return cached[1]

        view = get_biocirv_observations_view(session)
        stmt = (
            select(
                view.c.parameter_name,
                view.c.unit_name,
                view.c.analysis_type,
                func.count(func.distinct(view.c.observation_id)).label(
                    "observation_count"
                ),
            )
            .where(view.c.parameter_name.is_not(None))
            .group_by(view.c.parameter_name, view.c.unit_name, view.c.analysis_type)
            .order_by(view.c.parameter_name, view.c.unit_name, view.c.analysis_type)
        )
        rows = session.execute(stmt).all()
        result = [
            {
                "parameter_name": r.parameter_name,
                "unit_name": r.unit_name,
                "analysis_type": r.analysis_type,
                "observation_count": int(r.observation_count or 0),
            }
            for r in rows
        ]
        _discovery_cache[cache_key] = (now, result)
        return result

    @staticmethod
    def list_counties(session: Session) -> list[dict[str, Any]]:
        bind_key = id(session.get_bind())
        cache_key = (bind_key, "counties")
        now = time.monotonic()
        cached = _discovery_cache.get(cache_key)
        if cached is not None and (now - cached[0]) < _DISCOVERY_CACHE_TTL_SECONDS:
            return cached[1]

        view = get_biocirv_observations_view(session)
        stmt = (
            select(
                view.c.geoid,
                view.c.county_name,
                view.c.county_fips,
                view.c.state_name,
                func.count(func.distinct(view.c.prepared_sample_id)).label(
                    "prepared_sample_count"
                ),
                func.count(func.distinct(view.c.observation_id)).label(
                    "observation_count"
                ),
            )
            .where(view.c.county_name.is_not(None))
            .group_by(
                view.c.geoid,
                view.c.county_name,
                view.c.county_fips,
                view.c.state_name,
            )
            .order_by(view.c.county_name, view.c.geoid)
        )
        rows = session.execute(stmt).all()
        result = [
            {
                "geoid": r.geoid,
                "county_name": r.county_name,
                "county_fips": r.county_fips,
                "state_name": r.state_name,
                "prepared_sample_count": int(r.prepared_sample_count or 0),
                "observation_count": int(r.observation_count or 0),
            }
            for r in rows
        ]
        _discovery_cache[cache_key] = (now, result)
        return result
