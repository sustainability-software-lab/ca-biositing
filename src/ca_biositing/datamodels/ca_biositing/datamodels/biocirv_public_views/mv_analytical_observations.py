"""mv_analytical_observations.py

Primary Zenodo Stage 1 release table at the technical-replicate observation grain
(`biocirv_public.mv_analytical_observations`).

Includes strictly the 5 Stage 1 Aim 1 record types:
- `proximate` (`ProximateRecord`)
- `compositional` (`CompositionalRecord`)
- `xrf` (`XrfRecord`)
- `icp` (`IcpRecord`)
- `calorimetry` (`CalorimetryRecord`)

Excludes `UltimateRecord`, `XrdRecord`, `FtnirRecord`, and Aim 2 record types.

Governance & Privacy Rules (from `data_portal_views/common.py`):
1. `get_resource_filter(Resource)` — excludes problematic resources (`EXCLUDED_RESOURCES`).
2. `get_provider_filter(Provider)` — excludes restricted providers (`EXCLUDED_PROVIDERS`, e.g. `jaguar`).
3. `get_qc_status_filter(qc_pass)` — excludes records marked `fail` (`EXCLUDED_QC_STATUSES`) as well as
   unreviewed records where `qc_pass IS NULL` (matching `mv_biomass_composition` and `resource_analysis_map`).
4. `get_icp_filter(analysis_type, unit_name, value)` — enforces ICP unit (`ppm`) and physical cap (`ICP_MAX_PPM`).
5. `get_sum_constraints_subquery(...)` — enforces proximate (`[95, 105]`) and compositional (`[40, 105]`)
   sum checks using `(resource_id, coalesce(experiment_id, -1), analysis_type)` grouping for 100% parity
   with `data_portal.mv_biomass_composition`.
6. Privacy redaction — exposes only `Provider.codename` and county-level geography (`Place.county_name`,
   `Place.county_fips`, `Place.state_name`, `Place.geoid`); never exposes street address, city, ZIP,
   lat/lon, contact IDs, or freeform `.note` columns.

Required indexes:
    CREATE UNIQUE INDEX idx_mv_biocirv_obs_id ON biocirv_public.mv_analytical_observations (id)
    CREATE UNIQUE INDEX idx_mv_biocirv_obs_observation_id ON biocirv_public.mv_analytical_observations (observation_id)
"""

from __future__ import annotations

from sqlalchemy import and_, case, func, literal, or_, select
from sqlalchemy.orm import aliased

from ca_biositing.datamodels.data_portal_views.common import (
    COMPOSITIONAL_SUM_MAX,
    COMPOSITIONAL_SUM_MIN,
    PROXIMATE_SUM_MAX,
    PROXIMATE_SUM_MIN,
    get_icp_filter,
    get_provider_filter,
    get_qc_status_filter,
    get_resource_filter,
    get_sum_constraints_subquery,
)
from ca_biositing.datamodels.models.aim1_records import (
    CalorimetryRecord,
    CompositionalRecord,
    IcpRecord,
    ProximateRecord,
    XrfRecord,
)
from ca_biositing.datamodels.models.experiment_equipment.experiment import Experiment
from ca_biositing.datamodels.models.field_sampling.field_sample import FieldSample
from ca_biositing.datamodels.models.general_analysis.dimension_type import DimensionType
from ca_biositing.datamodels.models.general_analysis.observation import Observation
from ca_biositing.datamodels.models.methods_parameters_units.method import (
    Method,
    MethodAbbrev,
    MethodCategory,
    MethodStandard,
)
from ca_biositing.datamodels.models.methods_parameters_units.parameter import Parameter
from ca_biositing.datamodels.models.methods_parameters_units.unit import Unit
from ca_biositing.datamodels.models.people.provider import Provider
from ca_biositing.datamodels.models.places.location_address import LocationAddress
from ca_biositing.datamodels.models.places.place import Place
from ca_biositing.datamodels.models.resource_information.primary_ag_product import (
    PrimaryAgProduct,
)
from ca_biositing.datamodels.models.resource_information.resource import (
    Resource,
    ResourceClass,
    ResourceSubclass,
)
from ca_biositing.datamodels.models.sample_preparation.preparation_method import (
    PreparationMethod,
)
from ca_biositing.datamodels.models.sample_preparation.prepared_sample import (
    PreparedSample,
)

PROXIMATE_TYPES = ["proximate analysis", "proximate_record", "proximate"]
COMPOSITIONAL_TYPES = ["compositional analysis", "compositional_record", "compositional"]
XRF_TYPES = ["xrf analysis", "xrf_record", "xrf"]
ICP_TYPES = ["icp analysis", "icp_record", "icp"]
CALORIMETRY_TYPES = ["calorimetry analysis", "calorimetry_record", "calorimetry"]

STAGE_1_RECORD_TYPES = (
    PROXIMATE_TYPES
    + COMPOSITIONAL_TYPES
    + XRF_TYPES
    + ICP_TYPES
    + CALORIMETRY_TYPES
)

_value_unit = aliased(Unit, name="value_unit")
_dimension_unit = aliased(Unit, name="dimension_unit")

_analysis_type_expr = case(
    (func.lower(Observation.record_type).in_(PROXIMATE_TYPES), literal("proximate")),
    (func.lower(Observation.record_type).in_(COMPOSITIONAL_TYPES), literal("compositional")),
    (func.lower(Observation.record_type).in_(XRF_TYPES), literal("xrf")),
    (func.lower(Observation.record_type).in_(ICP_TYPES), literal("icp")),
    (func.lower(Observation.record_type).in_(CALORIMETRY_TYPES), literal("calorimetry")),
    else_=func.lower(Observation.record_type),
)

_matched_record_pk = func.coalesce(
    ProximateRecord.id,
    CompositionalRecord.id,
    XrfRecord.id,
    IcpRecord.id,
    CalorimetryRecord.id,
)

_matched_prepared_sample_id = func.coalesce(
    ProximateRecord.prepared_sample_id,
    CompositionalRecord.prepared_sample_id,
    XrfRecord.prepared_sample_id,
    IcpRecord.prepared_sample_id,
    CalorimetryRecord.prepared_sample_id,
)

_matched_resource_id = func.coalesce(
    ProximateRecord.resource_id,
    CompositionalRecord.resource_id,
    XrfRecord.resource_id,
    IcpRecord.resource_id,
    CalorimetryRecord.resource_id,
    FieldSample.resource_id,
)

_matched_method_id = func.coalesce(
    ProximateRecord.method_id,
    CompositionalRecord.method_id,
    XrfRecord.method_id,
    IcpRecord.method_id,
    CalorimetryRecord.method_id,
)

_matched_experiment_id = func.coalesce(
    ProximateRecord.experiment_id,
    CompositionalRecord.experiment_id,
    XrfRecord.experiment_id,
    IcpRecord.experiment_id,
    CalorimetryRecord.experiment_id,
)

_matched_replicate_no = func.coalesce(
    ProximateRecord.technical_replicate_no,
    CompositionalRecord.technical_replicate_no,
    XrfRecord.technical_replicate_no,
    IcpRecord.technical_replicate_no,
    CalorimetryRecord.technical_replicate_no,
)

_matched_replicate_total = func.coalesce(
    ProximateRecord.technical_replicate_total,
    CompositionalRecord.technical_replicate_total,
    XrfRecord.technical_replicate_total,
    IcpRecord.technical_replicate_total,
    CalorimetryRecord.technical_replicate_total,
)

_matched_raw_data_id = func.coalesce(
    ProximateRecord.raw_data_id,
    CompositionalRecord.raw_data_id,
    XrfRecord.raw_data_id,
    IcpRecord.raw_data_id,
    CalorimetryRecord.raw_data_id,
)

# Do NOT fall back to literal("pass"): unreviewed records with qc_pass IS NULL
# must remain NULL so get_qc_status_filter(qc_pass) excludes them under 3-valued SQL logic.
_matched_qc_pass = func.coalesce(
    ProximateRecord.qc_pass,
    CompositionalRecord.qc_pass,
    XrfRecord.qc_pass,
    IcpRecord.qc_pass,
    CalorimetryRecord.qc_pass,
)

_obs_base = (
    select(
        Observation.id.label("observation_id"),
        Observation.record_id.label("record_id"),
        _analysis_type_expr.label("analysis_type"),
        Resource.id.label("resource_id"),
        Resource.name.label("resource_name"),
        Resource.resource_code.label("resource_code"),
        ResourceClass.name.label("resource_class"),
        ResourceSubclass.name.label("resource_subclass"),
        PrimaryAgProduct.name.label("primary_ag_product"),
        PreparedSample.id.label("prepared_sample_id"),
        PreparedSample.name.label("prepared_sample_name"),
        PreparationMethod.name.label("prep_method_name"),
        PreparationMethod.drying_step.label("drying_step"),
        FieldSample.id.label("field_sample_id"),
        FieldSample.name.label("field_sample_name"),
        Provider.codename.label("provider_codename"),
        Place.county_name.label("county_name"),
        Place.county_fips.label("county_fips"),
        Place.state_name.label("state_name"),
        Place.geoid.label("geoid"),
        Parameter.name.label("parameter_name"),
        Observation.value.label("value"),
        _value_unit.name.label("unit_name"),
        DimensionType.name.label("dimension_name"),
        Observation.dimension_value.label("dimension_value"),
        _dimension_unit.name.label("dimension_unit_name"),
        _matched_replicate_no.label("technical_replicate_no"),
        _matched_replicate_total.label("technical_replicate_total"),
        Method.name.label("method_name"),
        MethodAbbrev.name.label("method_abbrev"),
        MethodCategory.name.label("method_category"),
        MethodStandard.name.label("method_standard"),
        _matched_experiment_id.label("experiment_id"),
        Experiment.name.label("experiment_name"),
        _matched_raw_data_id.label("raw_data_id"),
    )
    .select_from(Observation)
    .outerjoin(Parameter, Observation.parameter_id == Parameter.id)
    .outerjoin(_value_unit, Observation.unit_id == _value_unit.id)
    .outerjoin(DimensionType, Observation.dimension_type_id == DimensionType.id)
    .outerjoin(_dimension_unit, Observation.dimension_unit_id == _dimension_unit.id)
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
        XrfRecord,
        and_(
            func.lower(Observation.record_id) == func.lower(XrfRecord.record_id),
            func.lower(Observation.record_type).in_(XRF_TYPES),
        ),
    )
    .outerjoin(
        IcpRecord,
        and_(
            func.lower(Observation.record_id) == func.lower(IcpRecord.record_id),
            func.lower(Observation.record_type).in_(ICP_TYPES),
        ),
    )
    .outerjoin(
        CalorimetryRecord,
        and_(
            func.lower(Observation.record_id) == func.lower(CalorimetryRecord.record_id),
            func.lower(Observation.record_type).in_(CALORIMETRY_TYPES),
        ),
    )
    .outerjoin(PreparedSample, PreparedSample.id == _matched_prepared_sample_id)
    .outerjoin(PreparationMethod, PreparationMethod.id == PreparedSample.prep_method_id)
    .outerjoin(FieldSample, FieldSample.id == PreparedSample.field_sample_id)
    .outerjoin(Provider, Provider.id == FieldSample.provider_id)
    .outerjoin(LocationAddress, LocationAddress.id == FieldSample.sampling_location_id)
    .outerjoin(Place, Place.geoid == LocationAddress.geography_id)
    .outerjoin(Resource, Resource.id == _matched_resource_id)
    .outerjoin(ResourceClass, ResourceClass.id == Resource.resource_class_id)
    .outerjoin(ResourceSubclass, ResourceSubclass.id == Resource.resource_subclass_id)
    .outerjoin(PrimaryAgProduct, PrimaryAgProduct.id == Resource.primary_ag_product_id)
    .outerjoin(Method, Method.id == _matched_method_id)
    .outerjoin(MethodAbbrev, MethodAbbrev.id == Method.method_abbrev_id)
    .outerjoin(MethodCategory, MethodCategory.id == Method.method_category_id)
    .outerjoin(MethodStandard, MethodStandard.id == Method.method_standard_id)
    .outerjoin(Experiment, Experiment.id == _matched_experiment_id)
    .where(
        and_(
            func.lower(Observation.record_type).in_(STAGE_1_RECORD_TYPES),
            _matched_record_pk.is_not(None),
            get_resource_filter(Resource),
            get_provider_filter(Provider),
            get_qc_status_filter(_matched_qc_pass),
            get_icp_filter(_analysis_type_expr, _value_unit.name, Observation.value),
        )
    )
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
        func.row_number().over(order_by=_obs_base.c.observation_id).label("id"),
        _obs_base.c.observation_id,
        _obs_base.c.record_id,
        _obs_base.c.analysis_type,
        _obs_base.c.resource_id,
        _obs_base.c.resource_name,
        _obs_base.c.resource_code,
        _obs_base.c.resource_class,
        _obs_base.c.resource_subclass,
        _obs_base.c.primary_ag_product,
        _obs_base.c.prepared_sample_id,
        _obs_base.c.prepared_sample_name,
        _obs_base.c.prep_method_name,
        _obs_base.c.drying_step,
        _obs_base.c.field_sample_id,
        _obs_base.c.field_sample_name,
        _obs_base.c.provider_codename,
        _obs_base.c.county_name,
        _obs_base.c.county_fips,
        _obs_base.c.state_name,
        _obs_base.c.geoid,
        _obs_base.c.parameter_name,
        _obs_base.c.value,
        _obs_base.c.unit_name,
        _obs_base.c.dimension_name,
        _obs_base.c.dimension_value,
        _obs_base.c.dimension_unit_name,
        _obs_base.c.technical_replicate_no,
        _obs_base.c.technical_replicate_total,
        _obs_base.c.method_name,
        _obs_base.c.method_abbrev,
        _obs_base.c.method_category,
        _obs_base.c.method_standard,
        _obs_base.c.experiment_id,
        _obs_base.c.experiment_name,
        _obs_base.c.raw_data_id,
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
