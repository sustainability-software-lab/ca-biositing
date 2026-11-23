"""mv_analytical_summary.py

Resource-level analytical summary (`biocirv_public.mv_analytical_summary`).

Grain:
    One row per `(resource_name, analysis_type, parameter_name, unit_name)`
    derived from `mv_analytical_observations`.

Required index:
    CREATE UNIQUE INDEX idx_mv_biocirv_summary_key
    ON biocirv_public.mv_analytical_summary (resource_name, analysis_type, parameter_name, unit_name)
"""

from __future__ import annotations

from sqlalchemy import func, select

from ._base_observations import mv_analytical_observations

_obs = mv_analytical_observations.subquery("obs_for_analytical_summary")

mv_analytical_summary = (
    select(
        _obs.c.resource_name,
        _obs.c.analysis_type,
        _obs.c.parameter_name,
        _obs.c.unit_name,
        func.avg(_obs.c.value).label("mean_value"),
        func.stddev(_obs.c.value).label("std_dev"),
        func.min(_obs.c.value).label("min_value"),
        func.max(_obs.c.value).label("max_value"),
        func.count().label("observation_count"),
        func.count(func.distinct(_obs.c.prepared_sample_name)).label(
            "prepared_sample_count"
        ),
        func.count(func.distinct(_obs.c.field_sample_name)).label("field_sample_count"),
        func.count(func.distinct(_obs.c.provider_codename)).label("provider_count"),
    )
    .select_from(_obs)
    .group_by(
        _obs.c.resource_name,
        _obs.c.analysis_type,
        _obs.c.parameter_name,
        _obs.c.unit_name,
    )
)
