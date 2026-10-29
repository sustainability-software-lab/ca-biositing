"""mv_resources.py

Resource taxonomy and Stage 1 analytical coverage catalog (`biocirv_public.mv_resources`).

Grain:
    One row per QC-passing `resource_name` that has at least one Stage 1 analytical
    observation in `mv_analytical_observations`.

Aggregation Rules:
    Because `mv_analytical_observations` is at the observation grain (multiple
    parameters and replicates per sample), all entity counts use explicit
    `COUNT(DISTINCT ...)` (or row count for observations):
    - `field_sample_count`: `COUNT(DISTINCT field_sample_name)`
    - `prepared_sample_count`: `COUNT(DISTINCT prepared_sample_name)`
    - `provider_count`: `COUNT(DISTINCT provider_codename)`
    - `county_count`: `COUNT(DISTINCT county_name)`
    - `replicate_record_count`: `COUNT(DISTINCT record_id)`
    - `observation_count`: `COUNT(*)`

Required index:
    CREATE UNIQUE INDEX idx_mv_biocirv_resources_name ON biocirv_public.mv_resources (resource_name)
"""

from __future__ import annotations

from sqlalchemy import case, func, select

from ca_biositing.datamodels.data_portal_views.common import get_resource_filter
from ca_biositing.datamodels.models.resource_information.primary_ag_product import (
    PrimaryAgProduct,
)
from ca_biositing.datamodels.models.resource_information.resource import (
    Resource,
    ResourceClass,
    ResourceSubclass,
)

from .mv_analytical_observations import mv_analytical_observations

_obs = mv_analytical_observations.subquery("obs_for_resources")

_resource_obs_agg = (
    select(
        _obs.c.resource_name.label("resource_name"),
        func.count(func.distinct(_obs.c.field_sample_name)).label("field_sample_count"),
        func.count(func.distinct(_obs.c.prepared_sample_name)).label(
            "prepared_sample_count"
        ),
        func.count(func.distinct(_obs.c.provider_codename)).label("provider_count"),
        func.count(func.distinct(_obs.c.county_name)).label("county_count"),
        func.count(func.distinct(_obs.c.record_id)).label("replicate_record_count"),
        func.count().label("observation_count"),
        case(
            (
                func.max(case((_obs.c.analysis_type == "proximate", 1), else_=0)) == 1,
                True,
            ),
            else_=False,
        ).label("has_proximate"),
        case(
            (
                func.max(case((_obs.c.analysis_type == "compositional", 1), else_=0))
                == 1,
                True,
            ),
            else_=False,
        ).label("has_compositional"),
        case(
            (
                func.max(case((_obs.c.analysis_type == "xrf", 1), else_=0)) == 1,
                True,
            ),
            else_=False,
        ).label("has_xrf"),
        case(
            (
                func.max(case((_obs.c.analysis_type == "icp", 1), else_=0)) == 1,
                True,
            ),
            else_=False,
        ).label("has_icp"),
        case(
            (
                func.max(case((_obs.c.analysis_type == "calorimetry", 1), else_=0)) == 1,
                True,
            ),
            else_=False,
        ).label("has_calorimetry"),
    )
    .where(_obs.c.resource_name.is_not(None))
    .group_by(_obs.c.resource_name)
    .subquery("resource_obs_agg")
)

mv_resources = (
    select(
        Resource.name.label("resource_name"),
        Resource.resource_code.label("resource_code"),
        Resource.description.label("description"),
        ResourceClass.name.label("resource_class"),
        ResourceSubclass.name.label("resource_subclass"),
        PrimaryAgProduct.name.label("primary_ag_product"),
        _resource_obs_agg.c.field_sample_count,
        _resource_obs_agg.c.prepared_sample_count,
        _resource_obs_agg.c.provider_count,
        _resource_obs_agg.c.county_count,
        _resource_obs_agg.c.replicate_record_count,
        _resource_obs_agg.c.observation_count,
        _resource_obs_agg.c.has_proximate,
        _resource_obs_agg.c.has_compositional,
        _resource_obs_agg.c.has_xrf,
        _resource_obs_agg.c.has_icp,
        _resource_obs_agg.c.has_calorimetry,
    )
    .select_from(_resource_obs_agg)
    .join(Resource, Resource.name == _resource_obs_agg.c.resource_name)
    .outerjoin(ResourceClass, ResourceClass.id == Resource.resource_class_id)
    .outerjoin(ResourceSubclass, ResourceSubclass.id == Resource.resource_subclass_id)
    .outerjoin(PrimaryAgProduct, PrimaryAgProduct.id == Resource.primary_ag_product_id)
    .where(get_resource_filter(Resource))
)
