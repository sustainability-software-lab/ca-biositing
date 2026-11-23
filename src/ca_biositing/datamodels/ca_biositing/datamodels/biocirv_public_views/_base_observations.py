"""_base_observations.py

Internal, non-materialized SQLAlchemy `select()` helper at the technical-replicate
observation grain, shared by `biocirv_public.mv_analytical_summary` and
`biocirv_public.mv_resources`.

Not materialized in PostgreSQL (`BIOCIRV_PUBLIC_VIEW_NAMES` contains only
`mv_analytical_summary` and `mv_resources`).

Includes strictly the Stage 1 Aim 1 record types configured in
`BIOCIRV_PUBLIC_ALLOWED_ANALYSIS_TYPES` (`proximate`, `compositional`, `icp`).

Excludes `XrfRecord`, `CalorimetryRecord`, `UltimateRecord`, `XrdRecord`, `FtnirRecord`,
and Aim 2 record types.

Governance & Privacy Rules (from `data_portal_views/common.py`):
1. `get_resource_filter(Resource)` — excludes problematic, null, and blank resources (`EXCLUDED_RESOURCES`).
2. `BIOCIRV_PUBLIC_ALLOWED_RESOURCES` — optional Stage 1 resource allowlist.
3. `BIOCIRV_PUBLIC_ALLOWED_ANALYSIS_TYPES` — Stage 1 analysis-type allowlist.
4. `get_provider_filter(Provider)` — excludes restricted providers (`EXCLUDED_PROVIDERS`, e.g. `jaguar`).
5. `get_qc_status_filter(qc_pass)` — excludes records marked `fail` (`EXCLUDED_QC_STATUSES`) as well as
   unreviewed records where `qc_pass IS NULL`.
6. `get_etl_load_date_filter(created_at)` — excludes records with ETL load `created_at` after `MAX_ETL_LOAD_DATE`.
7. `get_icp_filter(analysis_type, unit_name, value)` — enforces ICP unit (`ppm`) and physical cap (`ICP_MAX_PPM`).
8. `get_sum_constraints_subquery(...)` — enforces proximate (`[95, 105]`) and compositional (`[40, 105]`)
   sum checks using `(resource_id, coalesce(experiment_id, -1), analysis_type)` grouping.
9. Privacy redaction — downstream views aggregate away `record_id`, `prepared_sample_name`,
   `field_sample_name`, and `provider_codename`; street address, city, ZIP, lat/lon,
   contact IDs, and `.note` columns are never joined or projected.
"""

from __future__ import annotations

from sqlalchemy import and_, case, func, literal, or_, select
from sqlalchemy.orm import aliased

from ca_biositing.datamodels.data_portal_views.common import (
    COMPOSITIONAL_SUM_MAX,
    COMPOSITIONAL_SUM_MIN,
    PROXIMATE_SUM_MAX,
    PROXIMATE_SUM_MIN,
    get_etl_load_date_filter,
    get_icp_filter,
    get_provider_filter,
    get_qc_status_filter,
    get_resource_filter,
    get_sum_constraints_subquery,
)
from ca_biositing.datamodels.models.aim1_records import (
    CompositionalRecord,
    IcpRecord,
    ProximateRecord,
)
from ca_biositing.datamodels.models.field_sampling.field_sample import FieldSample
from ca_biositing.datamodels.models.general_analysis.observation import Observation
from ca_biositing.datamodels.models.methods_parameters_units.method import Method
from ca_biositing.datamodels.models.methods_parameters_units.parameter import Parameter
from ca_biositing.datamodels.models.methods_parameters_units.unit import Unit
from ca_biositing.datamodels.models.people.provider import Provider
from ca_biositing.datamodels.models.resource_information.primary_ag_product import (
    PrimaryAgProduct,
)
from ca_biositing.datamodels.models.resource_information.resource import Resource
from ca_biositing.datamodels.models.sample_preparation.preparation_method import (
    PreparationMethod,
)
from ca_biositing.datamodels.models.sample_preparation.prepared_sample import (
    PreparedSample,
)

from . import (
    BIOCIRV_PUBLIC_ALLOWED_ANALYSIS_TYPES,
    BIOCIRV_PUBLIC_ALLOWED_RESOURCES,
)

PROXIMATE_TYPES = ["proximate analysis", "proximate_record", "proximate"]
COMPOSITIONAL_TYPES = ["compositional analysis", "compositional_record", "compositional"]
ICP_TYPES = ["icp analysis", "icp_record", "icp"]

STAGE_1_RECORD_TYPES = PROXIMATE_TYPES + COMPOSITIONAL_TYPES + ICP_TYPES

_value_unit = aliased(Unit, name="value_unit")

_analysis_type_expr = case(
    (func.lower(Observation.record_type).in_(PROXIMATE_TYPES), literal("proximate")),
    (func.lower(Observation.record_type).in_(COMPOSITIONAL_TYPES), literal("compositional")),
    (func.lower(Observation.record_type).in_(ICP_TYPES), literal("icp")),
    else_=func.lower(Observation.record_type),
)

_matched_record_pk = func.coalesce(
    ProximateRecord.id,
    CompositionalRecord.id,
    IcpRecord.id,
)

_matched_prepared_sample_id = func.coalesce(
    ProximateRecord.prepared_sample_id,
    CompositionalRecord.prepared_sample_id,
    IcpRecord.prepared_sample_id,
)

_matched_resource_id = func.coalesce(
    ProximateRecord.resource_id,
    CompositionalRecord.resource_id,
    IcpRecord.resource_id,
    FieldSample.resource_id,
)

_matched_method_id = func.coalesce(
    ProximateRecord.method_id,
    CompositionalRecord.method_id,
    IcpRecord.method_id,
)

_matched_experiment_id = func.coalesce(
    ProximateRecord.experiment_id,
    CompositionalRecord.experiment_id,
    IcpRecord.experiment_id,
)

_matched_replicate_no = func.coalesce(
    ProximateRecord.technical_replicate_no,
    CompositionalRecord.technical_replicate_no,
    IcpRecord.technical_replicate_no,
)

# Do NOT fall back to literal("pass"): unreviewed records with qc_pass IS NULL
# must remain NULL so get_qc_status_filter(qc_pass) excludes them under 3-valued SQL logic.
_matched_qc_pass = func.coalesce(
    ProximateRecord.qc_pass,
    CompositionalRecord.qc_pass,
    IcpRecord.qc_pass,
)

_matched_created_at = func.coalesce(
    ProximateRecord.created_at,
    CompositionalRecord.created_at,
    IcpRecord.created_at,
)

_where_clauses = [
    func.lower(Observation.record_type).in_(STAGE_1_RECORD_TYPES),
    _analysis_type_expr.in_(BIOCIRV_PUBLIC_ALLOWED_ANALYSIS_TYPES),
    _matched_record_pk.is_not(None),
    get_resource_filter(Resource),
    get_provider_filter(Provider),
    get_qc_status_filter(_matched_qc_pass),
    get_etl_load_date_filter(_matched_created_at),
    get_icp_filter(_analysis_type_expr, _value_unit.name, Observation.value),
]

if BIOCIRV_PUBLIC_ALLOWED_RESOURCES:
    _where_clauses.append(
        func.lower(func.trim(Resource.name)).in_(
            [r.lower().strip() for r in BIOCIRV_PUBLIC_ALLOWED_RESOURCES]
        )
    )

_obs_base = (
    select(
        Observation.record_id.label("record_id"),
        _analysis_type_expr.label("analysis_type"),
        Resource.id.label("resource_id"),
        func.lower(func.trim(Resource.name)).label("resource_name"),
        PrimaryAgProduct.name.label("primary_ag_product"),
        PreparedSample.name.label("prepared_sample_name"),
        PreparationMethod.name.label("prep_method_name"),
        FieldSample.name.label("field_sample_name"),
        Provider.codename.label("provider_codename"),
        Parameter.name.label("parameter_name"),
        Observation.value.label("value"),
        _value_unit.name.label("unit_name"),
        _matched_replicate_no.label("technical_replicate_no"),
        Method.name.label("method_name"),
        _matched_experiment_id.label("experiment_id"),
    )
    .select_from(Observation)
    .outerjoin(Parameter, Observation.parameter_id == Parameter.id)
    .outerjoin(_value_unit, Observation.unit_id == _value_unit.id)
    # Collision-safe polymorphic outerjoins predicated on both record_id and record_type
    .outerjoin(
        ProximateRecord,
        and_(
            func.lower(Observation.record_id) == func.lower(ProximateRecord.record_id),
            func.lower(Observation.record_type).in_(PROXIMATE_TYPES),
        ),
    )
    .outerjoin(
        CompositionalRecord,
        and_(
            func.lower(Observation.record_id) == func.lower(CompositionalRecord.record_id),
            func.lower(Observation.record_type).in_(COMPOSITIONAL_TYPES),
        ),
    )
    .outerjoin(
        IcpRecord,
        and_(
            func.lower(Observation.record_id) == func.lower(IcpRecord.record_id),
            func.lower(Observation.record_type).in_(ICP_TYPES),
        ),
    )
    .outerjoin(PreparedSample, PreparedSample.id == _matched_prepared_sample_id)
    .outerjoin(PreparationMethod, PreparationMethod.id == PreparedSample.prep_method_id)
    .outerjoin(FieldSample, FieldSample.id == PreparedSample.field_sample_id)
    .outerjoin(Provider, Provider.id == FieldSample.provider_id)
    .outerjoin(Resource, Resource.id == _matched_resource_id)
    .outerjoin(PrimaryAgProduct, PrimaryAgProduct.id == Resource.primary_ag_product_id)
    .outerjoin(Method, Method.id == _matched_method_id)
    .where(and_(*_where_clauses))
).subquery("biocirv_obs_base")

_qc_stats = get_sum_constraints_subquery(
    select(
        _obs_base.c.resource_id,
        _obs_base.c.experiment_id,
        _obs_base.c.analysis_type,
        case(
            (func.lower(_obs_base.c.parameter_name) == "ash", literal("ash solids")),
            else_=func.lower(_obs_base.c.parameter_name),
        ).label("parameter_name"),
        _obs_base.c.value,
    ).subquery("biocirv_obs_measurements")
)

mv_analytical_observations = (
    select(
        _obs_base.c.record_id,
        _obs_base.c.analysis_type,
        _obs_base.c.resource_name,
        _obs_base.c.primary_ag_product,
        _obs_base.c.prepared_sample_name,
        _obs_base.c.prep_method_name,
        _obs_base.c.field_sample_name,
        _obs_base.c.provider_codename,
        _obs_base.c.parameter_name,
        _obs_base.c.value,
        _obs_base.c.unit_name,
        _obs_base.c.technical_replicate_no,
        _obs_base.c.method_name,
    )
    .select_from(_obs_base)
    .outerjoin(
        _qc_stats,
        and_(
            _obs_base.c.resource_id == _qc_stats.c.resource_id,
            func.coalesce(_obs_base.c.experiment_id, -1)
            == func.coalesce(_qc_stats.c.experiment_id, -1),
            _obs_base.c.analysis_type == _qc_stats.c.analysis_type,
        ),
    )
    .where(
        or_(
            and_(
                _obs_base.c.analysis_type == "proximate",
                or_(
                    _qc_stats.c.proximate_sum == 0,
                    and_(
                        _qc_stats.c.proximate_sum >= PROXIMATE_SUM_MIN,
                        _qc_stats.c.proximate_sum <= PROXIMATE_SUM_MAX,
                    ),
                ),
            ),
            and_(
                _obs_base.c.analysis_type == "compositional",
                or_(
                    _qc_stats.c.compositional_sum == 0,
                    and_(
                        _qc_stats.c.compositional_sum >= COMPOSITIONAL_SUM_MIN,
                        _qc_stats.c.compositional_sum <= COMPOSITIONAL_SUM_MAX,
                    ),
                ),
            ),
            _obs_base.c.analysis_type.notin_(["proximate", "compositional"]),
        )
    )
)
