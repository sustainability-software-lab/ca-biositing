"""Resource Availability data API endpoints.

This module provides RESTful API endpoints for querying resource availability
(seasonal from_month and to_month data).
Endpoints follow REST principles with resources in the URL path.
"""

from __future__ import annotations

from fastapi import APIRouter, Path

from ca_biositing.webservice.dependencies import SessionDep
from ca_biositing.webservice.services.availability_service import AvailabilityService
from ca_biositing.webservice.v1.feedstocks.schemas import (
    AvailabilityResponse,
    DiscoveryResponse,
)

router = APIRouter(prefix="/availability", tags=["Availability"])


@router.get("/resources", response_model=DiscoveryResponse)
def list_availability_resources(session: SessionDep) -> DiscoveryResponse:
    """List all distinct resource names that have availability data.

    Example:
        GET /v1/feedstocks/availability/resources

    Returns:
        DiscoveryResponse with list of resource name strings
    """
    return DiscoveryResponse(values=AvailabilityService.list_resources(session))


@router.get("/geoids", response_model=DiscoveryResponse)
def list_availability_geoids(session: SessionDep) -> DiscoveryResponse:
    """List all distinct geoids that have availability data.

    Example:
        GET /v1/feedstocks/availability/geoids

    Returns:
        DiscoveryResponse with list of geoid strings
    """
    return DiscoveryResponse(values=AvailabilityService.list_geoids(session))


@router.get(
    "/resources/{resource}/geoid/{geoid}",
    response_model=AvailabilityResponse,
)
def get_availability_by_resource(
    session: SessionDep,
    resource: str = Path(..., description="Resource name (e.g., almond hulls, corn stover whole). Use GET /v1/feedstocks/availability/resources to discover available values."),
    geoid: str = Path(..., description="Geographic identifier (e.g., 06001)"),
) -> AvailabilityResponse:
    """Get seasonal availability window for a specific resource and geographic area.

    Returns the months during which the resource is available for harvest/collection.

    Example:
        GET /v1/feedstocks/availability/resources/almond hulls/geoid/06001

    Args:
        session: Database session (injected)
        resource: Resource name
        geoid: Geographic identifier (county FIPS code)

    Returns:
        AvailabilityResponse with from_month and to_month values

    Raises:
        ResourceNotFoundException: If resource not found or no availability data
    """
    data = AvailabilityService.get_by_resource(session, resource, geoid)
    return AvailabilityResponse(**data)
