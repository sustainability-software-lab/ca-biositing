"""mv_sample_summary.py

Sample-level analytical summary averaged across technical replicates
(`biocirv_public.mv_sample_summary`).

Grain:
    One row per `(prepared_sample_id, analysis_type, parameter_name, unit_name, drying_step)`
    derived from `mv_analytical_observations`.

Required index:
    CREATE UNIQUE INDEX idx_mv_biocirv_sample_summary_id ON biocirv_public.mv_sample_summary (id)
"""

from __future__ import annotations

from sqlalchemy import func, select

from .mv_analytical_observations import mv_analytical_observations

_obs = mv_analytical_observations.subquery("obs_for_sample_summary")

mv_sample_summary = (
    select(
        func.row_number()
        .over(
            order_by=(
                _obs.c.prepared_sample_id,
                _obs.c.analysis_type,
                _obs.c.parameter_name,
                _obs.c.unit_name,
            )
        )
        .label("id"),
        _obs.c.prepared_sample_id,
        func.max(_obs.c.prepared_sample_name).label("prepared_sample_name"),
        func.max(_obs.c.field_sample_id).label("field_sample_id"),
        func.max(_obs.c.field_sample_name).label("field_sample_name"),
        func.max(_obs.c.resource_id).label("resource_id"),
        func.max(_obs.c.resource_name).label("resource_name"),
        func.max(_obs.c.resource_code).label("resource_code"),
        func.max(_obs.c.provider_codename).label("provider_codename"),
        func.max(_obs.c.county_name).label("county_name"),
        func.max(_obs.c.county_fips).label("county_fips"),
        func.max(_obs.c.geoid).label("geoid"),
        _obs.c.analysis_type,
        _obs.c.parameter_name,
        _obs.c.unit_name,
        func.avg(_obs.c.value).label("mean_value"),
        func.stddev(_obs.c.value).label("std_dev"),
        func.min(_obs.c.value).label("min_value"),
        func.max(_obs.c.value).label("max_value"),
        func.count(func.distinct(_obs.c.observation_id)).label("replicate_count"),
        func.max(_obs.c.method_name).label("method_name"),
        _obs.c.drying_step,
    )
    .select_from(_obs)
    .group_by(
        _obs.c.prepared_sample_id,
        _obs.c.analysis_type,
        _obs.c.parameter_name,
        _obs.c.unit_name,
        _obs.c.drying_step,
    )
)
