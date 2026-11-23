"""mv_resources.py

Resource taxonomy and Stage 1 analytical coverage catalog (`biocirv_public.mv_resources`).

Grain:
    One row per QC-passing normalized `resource_name` (`lower(trim(name))`) that has at
    least one Stage 1 analytical observation in `_base_observations`. Uses a canonical
    `MIN(Resource.id)` per normalized name so all metadata columns (`description`,
    `resource_class`, `primary_ag_product`) come from a single physical `Resource` row,
    matching `mv_analytical_summary`'s `resource_name` normalization and guaranteeing
    uniqueness for `idx_mv_biocirv_resources_name`.

Aggregation Rules:
    Because `_base_observations` is at the observation grain (multiple
    parameters and replicates per sample), all entity counts use explicit
    `COUNT(DISTINCT ...)` (or row count for observations):
    - `field_sample_count`: `COUNT(DISTINCT field_sample_name)`
    - `prepared_sample_count`: `COUNT(DISTINCT prepared_sample_name)`
    - `provider_count`: `COUNT(DISTINCT provider_codename)`
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
)

from ._base_observations import mv_analytical_observations

_obs = mv_analytical_observations.subquery("obs_for_resources")

_resource_obs_agg = (
    select(
        _obs.c.resource_name.label("resource_name"),
        func.count(func.distinct(_obs.c.field_sample_name)).label("field_sample_count"),
        func.count(func.distinct(_obs.c.prepared_sample_name)).label(
            "prepared_sample_count"
        ),
        func.count(func.distinct(_obs.c.provider_codename)).label("provider_count"),
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
                func.max(case((_obs.c.analysis_type == "icp", 1), else_=0)) == 1,
                True,
            ),
            else_=False,
        ).label("has_icp"),
    )
    .where(_obs.c.resource_name.is_not(None))
    .group_by(_obs.c.resource_name)
    .subquery("resource_obs_agg")
)

_canonical_resource_ids = (
    select(
        func.lower(func.trim(Resource.name)).label("norm_name"),
        func.min(Resource.id).label("resource_id"),
    )
    .where(get_resource_filter(Resource))
    .group_by(func.lower(func.trim(Resource.name)))
    .subquery("canonical_resource_ids")
)

mv_resources = (
    select(
        _canonical_resource_ids.c.norm_name.label("resource_name"),
        Resource.description.label("description"),
        ResourceClass.name.label("resource_class"),
        PrimaryAgProduct.name.label("primary_ag_product"),
        _resource_obs_agg.c.field_sample_count,
        _resource_obs_agg.c.prepared_sample_count,
        _resource_obs_agg.c.provider_count,
        _resource_obs_agg.c.observation_count,
        _resource_obs_agg.c.has_proximate,
        _resource_obs_agg.c.has_compositional,
        _resource_obs_agg.c.has_icp,
    )
    .select_from(_resource_obs_agg)
    .join(
        _canonical_resource_ids,
        _canonical_resource_ids.c.norm_name == _resource_obs_agg.c.resource_name,
    )
    .join(Resource, Resource.id == _canonical_resource_ids.c.resource_id)
    .outerjoin(ResourceClass, ResourceClass.id == Resource.resource_class_id)
    .outerjoin(PrimaryAgProduct, PrimaryAgProduct.id == Resource.primary_ag_product_id)
)
