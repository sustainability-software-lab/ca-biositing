"""Pydantic v2 response schemas for the BioCirV Open Public Dataset (`/v1/public`)."""

from __future__ import annotations

from typing import Generic, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginatedPublicResponse(BaseModel, Generic[T]):
    """Standard paginated envelope for BioCirV Living Dataset public endpoints."""

    release_stage: str = Field(
        default="stage_1",
        description="BioCirV Living Dataset release stage identifier",
    )
    schema_version: str = Field(
        default="1.0.0",
        description="Public schema contract version",
    )
    total: int = Field(..., ge=0, description="Total matching records before pagination")
    skip: int = Field(..., ge=0, le=10000, description="Number of records skipped")
    limit: int = Field(..., ge=1, le=100, description="Maximum records returned per page")
    data: list[T] = Field(..., description="Page of matching records")


class PublicResourceItem(BaseModel):
    """Resource taxonomy and Stage 1 analytical coverage (`biocirv_public.mv_resources`)."""

    resource_name: Optional[str] = None
    description: Optional[str] = None
    resource_class: Optional[str] = None
    primary_ag_product: Optional[str] = None
    field_sample_count: int = 0
    prepared_sample_count: int = 0
    provider_count: int = 0
    observation_count: int = 0
    has_proximate: bool = False
    has_compositional: bool = False
    has_icp: bool = False


class PublicAnalyticalSummaryItem(BaseModel):
    """Resource-level analytical summary (`biocirv_public.mv_analytical_summary`)."""

    resource_name: Optional[str] = None
    analysis_type: Optional[str] = None
    parameter_name: Optional[str] = None
    unit_name: Optional[str] = None
    mean_value: Optional[float] = None
    std_dev: Optional[float] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    observation_count: int = 0
    prepared_sample_count: int = 0
    field_sample_count: int = 0
    provider_count: int = 0


class DiscoveryAnalysisTypeItem(BaseModel):
    """Discovery summary for a Stage 1 analysis type."""

    analysis_type: str
    observation_count: int
    resource_count: int
    parameter_count: int


class DiscoveryParameterItem(BaseModel):
    """Discovery summary for an analytical parameter and unit."""

    parameter_name: str
    unit_name: Optional[str] = None
    analysis_type: Optional[str] = None
    observation_count: int
