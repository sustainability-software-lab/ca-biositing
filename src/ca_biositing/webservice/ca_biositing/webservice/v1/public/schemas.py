"""Pydantic v2 response schemas for the BioCirV Open Public Dataset (`/v1/public`)."""

from __future__ import annotations

from datetime import date, datetime
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

    id: int
    resource_id: int
    resource_name: Optional[str] = None
    resource_code: Optional[str] = None
    description: Optional[str] = None
    resource_class: Optional[str] = None
    resource_subclass: Optional[str] = None
    primary_ag_product: Optional[str] = None
    field_sample_count: int = 0
    prepared_sample_count: int = 0
    provider_count: int = 0
    county_count: int = 0
    replicate_record_count: int = 0
    observation_count: int = 0
    has_proximate: bool = False
    has_compositional: bool = False
    has_xrf: bool = False
    has_icp: bool = False
    has_calorimetry: bool = False


class PublicSampleItem(BaseModel):
    """De-identified sample provenance and preparation metadata (`biocirv_public.mv_samples`)."""

    id: int
    prepared_sample_id: Optional[int] = None
    prepared_sample_name: Optional[str] = None
    prep_date: Optional[date] = None
    prep_method_name: Optional[str] = None
    prep_method_abbrev: Optional[str] = None
    prep_temp_c: Optional[float] = None
    drying_step: Optional[bool] = None
    field_sample_id: Optional[int] = None
    field_sample_name: Optional[str] = None
    resource_id: Optional[int] = None
    resource_name: Optional[str] = None
    resource_code: Optional[str] = None
    resource_class: Optional[str] = None
    resource_subclass: Optional[str] = None
    primary_ag_product: Optional[str] = None
    provider_codename: Optional[str] = None
    county_name: Optional[str] = None
    county_fips: Optional[str] = None
    state_name: Optional[str] = None
    geoid: Optional[str] = None
    sample_collection_source: Optional[str] = None
    collection_timestamp: Optional[datetime] = None
    harvest_date: Optional[date] = None
    harvest_method_name: Optional[str] = None
    collection_method_name: Optional[str] = None
    ag_treatment_name: Optional[str] = None
    processing_method_name: Optional[str] = None
    field_storage_method_name: Optional[str] = None
    field_storage_duration_value: Optional[float] = None
    field_storage_duration_unit: Optional[str] = None
    replicate_record_count: int = 0
    observation_count: int = 0


class PublicObservationItem(BaseModel):
    """Technical-replicate analytical observation (`biocirv_public.mv_analytical_observations`)."""

    id: int
    observation_id: int
    record_id: Optional[str] = None
    analysis_type: Optional[str] = None
    resource_id: Optional[int] = None
    resource_name: Optional[str] = None
    resource_code: Optional[str] = None
    resource_class: Optional[str] = None
    resource_subclass: Optional[str] = None
    primary_ag_product: Optional[str] = None
    prepared_sample_id: Optional[int] = None
    prepared_sample_name: Optional[str] = None
    prep_method_name: Optional[str] = None
    drying_step: Optional[bool] = None
    field_sample_id: Optional[int] = None
    field_sample_name: Optional[str] = None
    provider_codename: Optional[str] = None
    county_name: Optional[str] = None
    county_fips: Optional[str] = None
    state_name: Optional[str] = None
    geoid: Optional[str] = None
    parameter_name: Optional[str] = None
    value: Optional[float] = None
    unit_name: Optional[str] = None
    dimension_name: Optional[str] = None
    dimension_value: Optional[float] = None
    dimension_unit_name: Optional[str] = None
    technical_replicate_no: Optional[int] = None
    technical_replicate_total: Optional[int] = None
    method_name: Optional[str] = None
    method_abbrev: Optional[str] = None
    method_category: Optional[str] = None
    method_standard: Optional[str] = None
    experiment_id: Optional[int] = None
    experiment_name: Optional[str] = None
    raw_data_id: Optional[int] = None


class PublicSampleSummaryItem(BaseModel):
    """Sample-level analytical summary (`biocirv_public.mv_sample_summary`)."""

    id: int
    prepared_sample_id: Optional[int] = None
    prepared_sample_name: Optional[str] = None
    field_sample_id: Optional[int] = None
    field_sample_name: Optional[str] = None
    resource_id: Optional[int] = None
    resource_name: Optional[str] = None
    resource_code: Optional[str] = None
    provider_codename: Optional[str] = None
    county_name: Optional[str] = None
    county_fips: Optional[str] = None
    geoid: Optional[str] = None
    analysis_type: Optional[str] = None
    parameter_name: Optional[str] = None
    unit_name: Optional[str] = None
    mean_value: Optional[float] = None
    std_dev: Optional[float] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    replicate_count: int = 0
    method_name: Optional[str] = None
    drying_step: Optional[bool] = None


class PublicAnalyticalSummaryItem(BaseModel):
    """Resource- and county-level analytical summary (`biocirv_public.mv_analytical_summary`)."""

    id: int
    resource_id: Optional[int] = None
    resource_name: Optional[str] = None
    resource_code: Optional[str] = None
    resource_class: Optional[str] = None
    resource_subclass: Optional[str] = None
    county_name: Optional[str] = None
    county_fips: Optional[str] = None
    state_name: Optional[str] = None
    geoid: Optional[str] = None
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


class DiscoveryCountyItem(BaseModel):
    """Discovery summary for a county represented in the public dataset."""

    geoid: Optional[str] = None
    county_name: str
    county_fips: Optional[str] = None
    state_name: Optional[str] = None
    prepared_sample_count: int
    observation_count: int
