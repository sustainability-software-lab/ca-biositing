"""mv_samples.py

De-identified sample provenance and preparation catalog (`biocirv_public.mv_samples`).

Grain:
    One row per unique `(prepared_sample_id, field_sample_id)` pair that has at least
    one QC-passing Stage 1 observation in `mv_analytical_observations`.

Count Definitions:
    - `replicate_record_count`: `COUNT(DISTINCT record_id)` — number of distinct
      analytical replicate records (from `ProximateRecord`, `CompositionalRecord`,
      `XrfRecord`, `IcpRecord`, `CalorimetryRecord`) associated with this sample.
    - `observation_count`: `COUNT(DISTINCT observation_id)` — number of distinct
      parameter-level `Observation` rows associated with this sample. Because a single
      analytical replicate record typically yields multiple parameter observations,
      `observation_count >= replicate_record_count`.

Fan-Out Prevention:
    `FieldSampleCondition` has a 1-to-many relationship with `FieldSample`. Both
    `ag_treatment_name` and `processing_method_name` are pre-aggregated in deduplicated
    subqueries grouped by `field_sample_id` (`string_agg(..., '; ')`) prior to joining,
    guaranteeing one row per `(prepared_sample_id, field_sample_id)`.

Required indexes:
    CREATE UNIQUE INDEX idx_mv_biocirv_samples_id ON biocirv_public.mv_samples (id)
    CREATE UNIQUE INDEX idx_mv_biocirv_samples_pair ON biocirv_public.mv_samples (prepared_sample_id, field_sample_id)
"""

from __future__ import annotations

from sqlalchemy import func, literal, select
from sqlalchemy.orm import aliased

from ca_biositing.datamodels.models.field_sampling import (
    AgTreatment,
    CollectionMethod,
    FieldSample,
    FieldSampleCondition,
    FieldStorageMethod,
    HarvestMethod,
    ProcessingMethod,
)
from ca_biositing.datamodels.models.methods_parameters_units.unit import Unit
from ca_biositing.datamodels.models.sample_preparation.preparation_method import (
    PreparationMethod,
    PreparationMethodAbbreviation,
)
from ca_biositing.datamodels.models.sample_preparation.prepared_sample import (
    PreparedSample,
)

from . import ordered_string_agg
from .mv_analytical_observations import mv_analytical_observations

_obs = mv_analytical_observations.subquery("obs_for_samples")

# Pre-aggregate FieldSampleCondition -> AgTreatment by field_sample_id to prevent row fan-out
_distinct_ag = (
    select(
        FieldSampleCondition.field_sample_id.label("field_sample_id"),
        AgTreatment.name.label("ag_treatment_name"),
    )
    .select_from(FieldSampleCondition)
    .join(AgTreatment, FieldSampleCondition.ag_treatment_id == AgTreatment.id)
    .where(
        FieldSampleCondition.field_sample_id.is_not(None),
        AgTreatment.name.is_not(None),
    )
    .distinct()
    .subquery("distinct_ag_treatments")
)

_ag_agg = (
    select(
        _distinct_ag.c.field_sample_id.label("field_sample_id"),
        ordered_string_agg(_distinct_ag.c.ag_treatment_name, literal("; ")).label(
            "ag_treatment_name"
        ),
    )
    .group_by(_distinct_ag.c.field_sample_id)
    .subquery("field_sample_ag_treatments")
)

# Pre-aggregate FieldSampleCondition -> ProcessingMethod by field_sample_id to prevent row fan-out
_distinct_pm = (
    select(
        FieldSampleCondition.field_sample_id.label("field_sample_id"),
        ProcessingMethod.name.label("processing_method_name"),
    )
    .select_from(FieldSampleCondition)
    .join(
        ProcessingMethod,
        FieldSampleCondition.processing_method_id == ProcessingMethod.id,
    )
    .where(
        FieldSampleCondition.field_sample_id.is_not(None),
        ProcessingMethod.name.is_not(None),
    )
    .distinct()
    .subquery("distinct_processing_methods")
)

_pm_agg = (
    select(
        _distinct_pm.c.field_sample_id.label("field_sample_id"),
        ordered_string_agg(_distinct_pm.c.processing_method_name, literal("; ")).label(
            "processing_method_name"
        ),
    )
    .group_by(_distinct_pm.c.field_sample_id)
    .subquery("field_sample_processing_methods")
)

_sample_obs_agg = (
    select(
        _obs.c.prepared_sample_id.label("prepared_sample_id"),
        _obs.c.field_sample_id.label("field_sample_id"),
        func.max(_obs.c.resource_id).label("resource_id"),
        func.max(_obs.c.resource_name).label("resource_name"),
        func.max(_obs.c.resource_code).label("resource_code"),
        func.max(_obs.c.resource_class).label("resource_class"),
        func.max(_obs.c.resource_subclass).label("resource_subclass"),
        func.max(_obs.c.primary_ag_product).label("primary_ag_product"),
        func.max(_obs.c.provider_codename).label("provider_codename"),
        func.max(_obs.c.county_name).label("county_name"),
        func.max(_obs.c.county_fips).label("county_fips"),
        func.max(_obs.c.state_name).label("state_name"),
        func.max(_obs.c.geoid).label("geoid"),
        func.count(func.distinct(_obs.c.record_id)).label("replicate_record_count"),
        func.count(func.distinct(_obs.c.observation_id)).label("observation_count"),
    )
    .group_by(_obs.c.prepared_sample_id, _obs.c.field_sample_id)
    .subquery("sample_obs_agg")
)

_storage_duration_unit = aliased(Unit, name="storage_duration_unit")

mv_samples = (
    select(
        func.row_number()
        .over(
            order_by=(
                _sample_obs_agg.c.prepared_sample_id,
                _sample_obs_agg.c.field_sample_id,
            )
        )
        .label("id"),
        _sample_obs_agg.c.prepared_sample_id,
        PreparedSample.name.label("prepared_sample_name"),
        PreparedSample.prep_date.label("prep_date"),
        PreparationMethod.name.label("prep_method_name"),
        PreparationMethodAbbreviation.name.label("prep_method_abbrev"),
        PreparationMethod.prep_temp_c.label("prep_temp_c"),
        PreparationMethod.drying_step.label("drying_step"),
        _sample_obs_agg.c.field_sample_id,
        FieldSample.name.label("field_sample_name"),
        _sample_obs_agg.c.resource_id,
        _sample_obs_agg.c.resource_name,
        _sample_obs_agg.c.resource_code,
        _sample_obs_agg.c.resource_class,
        _sample_obs_agg.c.resource_subclass,
        _sample_obs_agg.c.primary_ag_product,
        _sample_obs_agg.c.provider_codename,
        _sample_obs_agg.c.county_name,
        _sample_obs_agg.c.county_fips,
        _sample_obs_agg.c.state_name,
        _sample_obs_agg.c.geoid,
        FieldSample.sample_collection_source.label("sample_collection_source"),
        FieldSample.collection_timestamp.label("collection_timestamp"),
        FieldSample.harvest_date.label("harvest_date"),
        HarvestMethod.name.label("harvest_method_name"),
        CollectionMethod.name.label("collection_method_name"),
        _ag_agg.c.ag_treatment_name.label("ag_treatment_name"),
        _pm_agg.c.processing_method_name.label("processing_method_name"),
        FieldStorageMethod.name.label("field_storage_method_name"),
        FieldSample.field_storage_duration_value.label("field_storage_duration_value"),
        _storage_duration_unit.name.label("field_storage_duration_unit"),
        _sample_obs_agg.c.replicate_record_count,
        _sample_obs_agg.c.observation_count,
    )
    .select_from(_sample_obs_agg)
    .outerjoin(
        PreparedSample,
        PreparedSample.id == _sample_obs_agg.c.prepared_sample_id,
    )
    .outerjoin(
        PreparationMethod,
        PreparationMethod.id == PreparedSample.prep_method_id,
    )
    .outerjoin(
        PreparationMethodAbbreviation,
        PreparationMethodAbbreviation.id == PreparationMethod.prep_method_abbrev_id,
    )
    .outerjoin(
        FieldSample,
        FieldSample.id == _sample_obs_agg.c.field_sample_id,
    )
    .outerjoin(
        HarvestMethod,
        HarvestMethod.id == FieldSample.harvest_method_id,
    )
    .outerjoin(
        CollectionMethod,
        CollectionMethod.id == FieldSample.collection_method_id,
    )
    .outerjoin(
        FieldStorageMethod,
        FieldStorageMethod.id == FieldSample.field_storage_method_id,
    )
    .outerjoin(
        _storage_duration_unit,
        _storage_duration_unit.id == FieldSample.field_storage_duration_unit_id,
    )
    .outerjoin(
        _ag_agg,
        _ag_agg.c.field_sample_id == FieldSample.id,
    )
    .outerjoin(
        _pm_agg,
        _pm_agg.c.field_sample_id == FieldSample.id,
    )
)
