"""Open, unauthenticated router for the BioCirV Living Dataset (`/v1/public`).

Protected by an in-memory fixed-window per-IP rate limiter (`public_rate_limit`)
and bounded pagination (`PublicPaginationDep`, `skip <= 10000`, `limit <= 100`).
"""

from __future__ import annotations

import threading
import time
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from ca_biositing.webservice.config import config
from ca_biositing.webservice.dependencies import SessionDep
from ca_biositing.webservice.services.public_dataset_service import (
    MAX_PAGE_LIMIT,
    MAX_PAGE_SKIP,
    PublicDatasetService,
)

from .schemas import (
    DiscoveryAnalysisTypeItem,
    DiscoveryCountyItem,
    DiscoveryParameterItem,
    PaginatedPublicResponse,
    PublicAnalyticalSummaryItem,
    PublicObservationItem,
    PublicResourceItem,
    PublicSampleItem,
    PublicSampleSummaryItem,
)

_RATE_LIMIT_WINDOW_SECONDS = 60.0
_MAX_RATE_LIMIT_BUCKETS = 10_000
_rate_limit_lock = threading.Lock()
_ip_rate_buckets: dict[str, tuple[float, int]] = {}


def get_public_pagination_params(
    skip: int = Query(0, ge=0, le=MAX_PAGE_SKIP, description="Number of records to skip"),
    limit: int = Query(
        100,
        ge=1,
        le=MAX_PAGE_LIMIT,
        description="Maximum number of records to return (1-100)",
    ),
) -> dict[str, int]:
    """Bounded pagination parameters (`0 <= skip <= 10000`, `1 <= limit <= 100`) for `/v1/public`."""
    return {"skip": skip, "limit": limit}


PublicPaginationDep = Annotated[dict[str, int], Depends(get_public_pagination_params)]


def reset_public_rate_limiter() -> None:
    """Reset the in-memory IP rate limit buckets (used in tests)."""
    with _rate_limit_lock:
        _ip_rate_buckets.clear()


def _resolve_client_ip(request: Request) -> str:
    """Resolve the client IP key for rate limiting.

    `X-Forwarded-For` is ignored unless `config.public_rate_limit_trust_x_forwarded_for`
    is explicitly enabled (e.g. behind Cloud Run / GFE). When trusted, the rightmost
    hop appended by the proxy is used rather than the client-controllable leftmost hop.
    """
    if config.public_rate_limit_trust_x_forwarded_for:
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            rightmost_hop = forwarded_for.split(",")[-1].strip()[:64]
            if rightmost_hop:
                return rightmost_hop
    if request.client and request.client.host:
        return request.client.host[:64]
    return "unknown"


def public_rate_limit(request: Request) -> None:
    """Enforce thread-safe, bounded per-IP fixed-window rate limiting on `/v1/public`."""
    client_ip = _resolve_client_ip(request)
    now = time.monotonic()
    max_requests = config.public_rate_limit_per_minute

    with _rate_limit_lock:
        if (
            client_ip not in _ip_rate_buckets
            and len(_ip_rate_buckets) >= _MAX_RATE_LIMIT_BUCKETS
        ):
            expired_ips = [
                ip
                for ip, (w_start, _) in _ip_rate_buckets.items()
                if (now - w_start) >= _RATE_LIMIT_WINDOW_SECONDS
            ]
            for ip in expired_ips:
                del _ip_rate_buckets[ip]
            while len(_ip_rate_buckets) >= _MAX_RATE_LIMIT_BUCKETS:
                oldest_ip = next(iter(_ip_rate_buckets))
                del _ip_rate_buckets[oldest_ip]

        window_start, count = _ip_rate_buckets.get(client_ip, (now, 0))
        if (now - window_start) >= _RATE_LIMIT_WINDOW_SECONDS:
            window_start = now
            count = 0

        count += 1
        _ip_rate_buckets[client_ip] = (window_start, count)

    if count > max_requests:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Public API rate limit exceeded. Please retry after 60 seconds.",
            headers={"Retry-After": "60"},
        )


router = APIRouter(
    prefix="/public",
    tags=["public-dataset"],
    dependencies=[Depends(public_rate_limit)],
)


@router.get(
    "/resources",
    response_model=PaginatedPublicResponse[PublicResourceItem],
    summary="List QC-passing biomass resources with Stage 1 analytical coverage",
)
def list_public_resources(
    session: SessionDep,
    pagination: PublicPaginationDep,
    resource_class: Optional[str] = Query(
        None, description="Filter by resource class (case/underscore-insensitive)"
    ),
    resource_subclass: Optional[str] = Query(
        None, description="Filter by resource subclass (case/underscore-insensitive)"
    ),
    has_proximate: Optional[bool] = Query(
        None, description="Filter by presence of Proximate analysis data"
    ),
    has_compositional: Optional[bool] = Query(
        None, description="Filter by presence of Compositional analysis data"
    ),
    has_xrf: Optional[bool] = Query(
        None, description="Filter by presence of XRF analysis data"
    ),
    has_icp: Optional[bool] = Query(
        None, description="Filter by presence of ICP analysis data"
    ),
    has_calorimetry: Optional[bool] = Query(
        None, description="Filter by presence of Calorimetry analysis data"
    ),
) -> dict:
    return PublicDatasetService.list_resources(
        session,
        resource_class=resource_class,
        resource_subclass=resource_subclass,
        has_proximate=has_proximate,
        has_compositional=has_compositional,
        has_xrf=has_xrf,
        has_icp=has_icp,
        has_calorimetry=has_calorimetry,
        skip=pagination["skip"],
        limit=pagination["limit"],
    )


@router.get(
    "/resources/{resource}",
    response_model=PublicResourceItem,
    summary="Get a single biomass resource by ID, name, or resource code",
)
def get_public_resource(
    resource: str,
    session: SessionDep,
) -> dict:
    return PublicDatasetService.get_resource(session, resource)


@router.get(
    "/samples",
    response_model=PaginatedPublicResponse[PublicSampleItem],
    summary="List de-identified field and prepared samples in the Stage 1 release",
)
def list_public_samples(
    session: SessionDep,
    pagination: PublicPaginationDep,
    resource: Optional[str] = Query(
        None, description="Filter by resource ID, name, or code"
    ),
    county_name: Optional[str] = Query(
        None, description="Filter by county name (e.g. 'San Joaquin')"
    ),
    geoid: Optional[str] = Query(
        None, description="Filter by 5-digit county FIPS GEOID (e.g. '06077')"
    ),
    provider_codename: Optional[str] = Query(
        None, description="Filter by anonymized provider codename"
    ),
    prep_method_name: Optional[str] = Query(
        None, description="Filter by sample preparation method name"
    ),
    drying_step: Optional[bool] = Query(
        None, description="Filter by whether preparation included a drying step"
    ),
) -> dict:
    return PublicDatasetService.list_samples(
        session,
        resource=resource,
        county_name=county_name,
        geoid=geoid,
        provider_codename=provider_codename,
        prep_method_name=prep_method_name,
        drying_step=drying_step,
        skip=pagination["skip"],
        limit=pagination["limit"],
    )


@router.get(
    "/samples/{prepared_sample_id}",
    response_model=PublicSampleItem,
    summary="Get a single de-identified sample by prepared_sample_id",
)
def get_public_sample(
    prepared_sample_id: int,
    session: SessionDep,
) -> dict:
    return PublicDatasetService.get_sample(session, prepared_sample_id)


@router.get(
    "/analysis/observations",
    response_model=PaginatedPublicResponse[PublicObservationItem],
    summary="Query technical-replicate analytical observations (Zenodo Stage 1 primary table)",
)
def list_public_observations(
    session: SessionDep,
    pagination: PublicPaginationDep,
    resource: Optional[str] = Query(
        None, description="Filter by resource ID, name, or code"
    ),
    analysis_type: Optional[str] = Query(
        None,
        description="Filter by Stage 1 analysis type (proximate, compositional, xrf, icp, calorimetry)",
    ),
    parameter_name: Optional[str] = Query(
        None, description="Filter by analytical parameter name (e.g. 'moisture', 'glucan')"
    ),
    prepared_sample_id: Optional[int] = Query(
        None, description="Filter by prepared_sample_id"
    ),
    field_sample_id: Optional[int] = Query(
        None, description="Filter by field_sample_id"
    ),
    county_name: Optional[str] = Query(
        None, description="Filter by county name"
    ),
    geoid: Optional[str] = Query(
        None, description="Filter by 5-digit county FIPS GEOID"
    ),
    provider_codename: Optional[str] = Query(
        None, description="Filter by anonymized provider codename"
    ),
    drying_step: Optional[bool] = Query(
        None, description="Filter by whether preparation included a drying step"
    ),
) -> dict:
    return PublicDatasetService.list_observations(
        session,
        resource=resource,
        analysis_type=analysis_type,
        parameter_name=parameter_name,
        prepared_sample_id=prepared_sample_id,
        field_sample_id=field_sample_id,
        county_name=county_name,
        geoid=geoid,
        provider_codename=provider_codename,
        drying_step=drying_step,
        skip=pagination["skip"],
        limit=pagination["limit"],
    )


@router.get(
    "/analysis/sample-summaries",
    response_model=PaginatedPublicResponse[PublicSampleSummaryItem],
    summary="Query sample-level analytical summaries averaged across technical replicates",
)
def list_public_sample_summaries(
    session: SessionDep,
    pagination: PublicPaginationDep,
    resource: Optional[str] = Query(
        None, description="Filter by resource ID, name, or code"
    ),
    prepared_sample_id: Optional[int] = Query(
        None, description="Filter by prepared_sample_id"
    ),
    analysis_type: Optional[str] = Query(
        None,
        description="Filter by Stage 1 analysis type (proximate, compositional, xrf, icp, calorimetry)",
    ),
    parameter_name: Optional[str] = Query(
        None, description="Filter by analytical parameter name"
    ),
    county_name: Optional[str] = Query(
        None, description="Filter by county name"
    ),
    geoid: Optional[str] = Query(
        None, description="Filter by 5-digit county FIPS GEOID"
    ),
    drying_step: Optional[bool] = Query(
        None, description="Filter by whether preparation included a drying step"
    ),
) -> dict:
    return PublicDatasetService.list_sample_summaries(
        session,
        resource=resource,
        prepared_sample_id=prepared_sample_id,
        analysis_type=analysis_type,
        parameter_name=parameter_name,
        county_name=county_name,
        geoid=geoid,
        drying_step=drying_step,
        skip=pagination["skip"],
        limit=pagination["limit"],
    )


@router.get(
    "/analysis/summaries",
    response_model=PaginatedPublicResponse[PublicAnalyticalSummaryItem],
    summary="Query resource- and county-level analytical summaries (mean, std_dev, min, max, n)",
)
def list_public_analytical_summaries(
    session: SessionDep,
    pagination: PublicPaginationDep,
    resource: Optional[str] = Query(
        None, description="Filter by resource ID, name, or code"
    ),
    analysis_type: Optional[str] = Query(
        None,
        description="Filter by Stage 1 analysis type (proximate, compositional, xrf, icp, calorimetry)",
    ),
    parameter_name: Optional[str] = Query(
        None, description="Filter by analytical parameter name"
    ),
    county_name: Optional[str] = Query(
        None, description="Filter by county name"
    ),
    geoid: Optional[str] = Query(
        None, description="Filter by 5-digit county FIPS GEOID"
    ),
) -> dict:
    return PublicDatasetService.list_analytical_summaries(
        session,
        resource=resource,
        analysis_type=analysis_type,
        parameter_name=parameter_name,
        county_name=county_name,
        geoid=geoid,
        skip=pagination["skip"],
        limit=pagination["limit"],
    )


@router.get(
    "/discovery/analysis-types",
    response_model=list[DiscoveryAnalysisTypeItem],
    summary="List Stage 1 analysis types and coverage counts",
)
def list_public_analysis_types(session: SessionDep) -> list[dict]:
    return PublicDatasetService.list_analysis_types(session)


@router.get(
    "/discovery/parameters",
    response_model=list[DiscoveryParameterItem],
    summary="List analytical parameters, units, and analysis types in the Stage 1 release",
)
def list_public_parameters(session: SessionDep) -> list[dict]:
    return PublicDatasetService.list_parameters(session)


@router.get(
    "/discovery/counties",
    response_model=list[DiscoveryCountyItem],
    summary="List counties and GEOIDs represented in the Stage 1 release",
)
def list_public_counties(session: SessionDep) -> list[dict]:
    return PublicDatasetService.list_counties(session)
