"""
Shared subqueries and helper expressions for data portal materialized views.

This module contains reusable SQLAlchemy expressions that are imported by
multiple view definitions.
"""

from sqlalchemy import select, func, case, literal, and_, or_, cast, String, Integer, ARRAY, text
from sqlalchemy.dialects.postgresql import array as pg_array
from sqlalchemy.sql import expression
from ca_biositing.datamodels.models.general_analysis.observation import Observation
from ca_biositing.datamodels.models.methods_parameters_units.parameter import Parameter
from ca_biositing.datamodels.models.methods_parameters_units.unit import Unit
from ca_biositing.datamodels.models.aim1_records.compositional_record import CompositionalRecord
from ca_biositing.datamodels.models.aim1_records.proximate_record import ProximateRecord
from ca_biositing.datamodels.models.aim1_records.ultimate_record import UltimateRecord
from ca_biositing.datamodels.models.aim1_records.xrf_record import XrfRecord
from ca_biositing.datamodels.models.aim1_records.icp_record import IcpRecord
from ca_biositing.datamodels.models.aim1_records.calorimetry_record import CalorimetryRecord
from ca_biositing.datamodels.models.aim1_records.xrd_record import XrdRecord
from ca_biositing.datamodels.models.aim1_records.ftnir_record import FtnirRecord
from ca_biositing.datamodels.models.aim2_records.fermentation_record import FermentationRecord
from ca_biositing.datamodels.models.aim2_records.gasification_record import GasificationRecord
from ca_biositing.datamodels.models.aim2_records.pretreatment_record import PretreatmentRecord

# =============================================================================
# RESOURCE-LEVEL FILTERS
# =============================================================================
# Resources excluded from all data portal / analysis views. Each entry is
# annotated with when and why it was added, pulled from git history where
# available (see issues #396, #409, #422, PR #431).
EXCLUDED_RESOURCES = [
    "sargassum",  # excluded 2026-05: original placeholder exclusion, rationale undocumented
    "#n/a",  # excluded 2026-05: original placeholder exclusion, rationale undocumented
    "lab media",  # excluded 2026-05: original placeholder exclusion, rationale undocumented
    "alfalfa",  # excluded 2026-06: see issue #409, removed for testing purposes pending Y3 blends review
    "almond hulls and shells mix",  # excluded 2026-06: see issue #409
    "almond shells and hulls mix",  # excluded 2026-06: see issue #409 (added as a follow-up naming variant, PR #422)
    "almond woodchips",  # excluded 2026-06: see issue #409
]

# =============================================================================
# PRIMARY PRODUCT / PRIMARY AG PRODUCT FILTERS
# =============================================================================
# No primary ag products are excluded today. Placeholder so a future
# exclusion at this dimension has an obvious, pre-established place to go.
EXCLUDED_PRIMARY_AG_PRODUCTS = []

# =============================================================================
# EXPERIMENT-LEVEL FILTERS
# =============================================================================
# No experiments are excluded today. Placeholder for the same reason as
# EXCLUDED_PRIMARY_AG_PRODUCTS above.
EXCLUDED_EXPERIMENTS = []

# =============================================================================
# REPLICATE-LEVEL FILTERS
# =============================================================================
# technical_replicate_no / technical_replicate_total are not currently used
# for filtering anywhere in the codebase. Placeholder only, documenting that
# this dimension exists and is available if a future issue needs it.
EXCLUDED_REPLICATES = []

# =============================================================================
# PROVIDER-LEVEL FILTERS
# =============================================================================
# Providers excluded from all data portal / analysis views.
EXCLUDED_PROVIDERS = [
    "jaguar",  # excluded 2026-09: see issue #472/PR #472, unreliable provider data
]

# =============================================================================
# DATE-LEVEL FILTERS
# =============================================================================
# Centralizes the year cutoff duplicated as a magic number in
# mv_usda_county_production.py (year >= 2017) and mv_biomass_volume_estimate.py
# (data_year >= 2017). Not yet wired into those call sites (Phase 3).
MIN_PRODUCTION_DATA_YEAR = 2017


def get_min_year_filter(year_col):
    """Filter to exclude production records before MIN_PRODUCTION_DATA_YEAR."""
    return year_col >= MIN_PRODUCTION_DATA_YEAR


# =============================================================================
# QC STATUS GATEKEEPER
# =============================================================================
# Formal name for the existing qc_pass != "fail" check repeated across views.
# qc_pass remains a free-text string column (no enum migration) per the
# refactor's decisions, but every view can now go through one function
# instead of repeating the comparison. Not yet wired into call sites
# (Phase 2/3); resource_analysis_map below still inlines the check for now.
EXCLUDED_QC_STATUSES = ["fail"]


def get_qc_status_filter(qc_pass_col):
    """Filter to exclude records whose qc_pass status is in EXCLUDED_QC_STATUSES."""
    return qc_pass_col.notin_(EXCLUDED_QC_STATUSES)


# =============================================================================
# PHYSICALLY IMPOSSIBLE / CROSS-FIELD VALUE CHECKS  (issue #476)
# =============================================================================
# Named constants replacing magic numbers scattered across views.py and
# mv_biomass_composition.py. Not yet wired into those call sites (Phase 2/3).
PROXIMATE_SUM_MIN, PROXIMATE_SUM_MAX = 95, 105
COMPOSITIONAL_SUM_MIN, COMPOSITIONAL_SUM_MAX = 40, 105
ICP_MAX_PPM = 500_000
ULTIMATE_MAX_PERCENT = 100

# Allowed parameters for Ultimate Analysis
ULTIMATE_PARAMETERS = ["carbon", "nitrogen", "oxygen", "sulfur", "hydrogen"]

# Subquery for analytical averages (moisture, ash, lignin, sugar)
# Sugar = glucose + xylose
# QC: filtered to exclude "fail" - only include observations from analytical records that are not marked as failed
# NOTE: This subquery filters observation records based on their parent record's QC status
# via the resource_analysis_map which already filters by qc_pass != "fail"
analysis_metrics = select(
    Observation.record_id,
    Observation.record_type,
    case(
        (Parameter.name == "ash", "ash solids"),
        else_=Parameter.name
    ).label("parameter"),
    Observation.value
).join(Parameter, Observation.parameter_id == Parameter.id)\
 .where(Observation.record_type.in_([
     "compositional analysis", "proximate analysis", "ultimate analysis",
     "xrf analysis", "icp analysis", "calorimetry analysis",
     "xrd analysis", "ftnir analysis", "pretreatment",
     "gasification", "fermentation"
 ])).subquery()

# Map record_id to resource_id across all analytical types
# QC: filtered via get_qc_status_filter() - include only observations from records that are not marked as failed
resource_analysis_map = select(
    CompositionalRecord.resource_id, CompositionalRecord.record_id, literal("compositional analysis").label("type")
).where(get_qc_status_filter(CompositionalRecord.qc_pass)).union_all(
    select(ProximateRecord.resource_id, ProximateRecord.record_id, literal("proximate analysis").label("type")).where(get_qc_status_filter(ProximateRecord.qc_pass)),
    select(UltimateRecord.resource_id, UltimateRecord.record_id, literal("ultimate analysis").label("type")).where(get_qc_status_filter(UltimateRecord.qc_pass)),
    select(XrfRecord.resource_id, XrfRecord.record_id, literal("xrf analysis").label("type")).where(get_qc_status_filter(XrfRecord.qc_pass)),
    select(IcpRecord.resource_id, IcpRecord.record_id, literal("icp analysis").label("type")).where(get_qc_status_filter(IcpRecord.qc_pass)),
    select(CalorimetryRecord.resource_id, CalorimetryRecord.record_id, literal("calorimetry analysis").label("type")).where(get_qc_status_filter(CalorimetryRecord.qc_pass)),
    select(XrdRecord.resource_id, XrdRecord.record_id, literal("xrd analysis").label("type")).where(get_qc_status_filter(XrdRecord.qc_pass)),
    select(FtnirRecord.resource_id, FtnirRecord.record_id, literal("ftnir analysis").label("type")).where(get_qc_status_filter(FtnirRecord.qc_pass)),
    select(FermentationRecord.resource_id, FermentationRecord.record_id, literal("fermentation").label("type")).where(get_qc_status_filter(FermentationRecord.qc_pass)),
    select(GasificationRecord.resource_id, GasificationRecord.record_id, literal("gasification").label("type")).where(get_qc_status_filter(GasificationRecord.qc_pass)),
    select(PretreatmentRecord.resource_id, PretreatmentRecord.record_id, literal("pretreatment").label("type")).where(get_qc_status_filter(PretreatmentRecord.qc_pass))
).subquery()

# Direct expressions for carbon, hydrogen, nitrogen averages
carbon_avg_expr = func.avg(case((
    and_(
        resource_analysis_map.c.type == "ultimate analysis",
        func.lower(analysis_metrics.c.parameter) == "carbon"
    ),
    analysis_metrics.c.value
)))

hydrogen_avg_expr = func.avg(case((
    and_(
        resource_analysis_map.c.type == "ultimate analysis",
        func.lower(analysis_metrics.c.parameter) == "hydrogen"
    ),
    analysis_metrics.c.value
)))

nitrogen_avg_expr = func.avg(case((
    and_(
        resource_analysis_map.c.type == "ultimate analysis",
        func.lower(analysis_metrics.c.parameter) == "nitrogen"
    ),
    analysis_metrics.c.value
)))

cn_ratio_expr = case(
    (
        and_(
            carbon_avg_expr.is_not(None),
            nitrogen_avg_expr.is_not(None),
            nitrogen_avg_expr != 0
        ),
        carbon_avg_expr / nitrogen_avg_expr
    ),
    else_=None
)

# Helper functions for expressions that need to be created dynamically
def get_carbon_avg_expr():
    """Expression for average carbon percentage from ultimate analysis."""
    return carbon_avg_expr

def get_hydrogen_avg_expr():
    """Expression for average hydrogen percentage from ultimate analysis."""
    return hydrogen_avg_expr

def get_nitrogen_avg_expr():
    """Expression for average nitrogen percentage from ultimate analysis."""
    return nitrogen_avg_expr

def get_cn_ratio_expr():
    """Expression for carbon-to-nitrogen ratio."""
    return cn_ratio_expr


def get_resource_filter(resource_model):
    """Filter to exclude problematic resources."""
    return and_(
        func.lower(resource_model.name).not_in(EXCLUDED_RESOURCES)
    )


def get_provider_filter(provider_model):
    """Filter to exclude problematic providers."""
    return or_(
        provider_model.id.is_(None),
        func.lower(provider_model.codename).not_in(EXCLUDED_PROVIDERS)
    )


def get_ultimate_filter(analysis_type_col, parameter_name_col, value_col=None):
    """Filter for ultimate analysis parameters.

    Checks if parameter is in the whitelist and optionally if value <= 100.
    """
    filters = [
        or_(
            analysis_type_col.notin_(["ultimate", "ultimate analysis", "ultimate_analysis"]),
            func.lower(parameter_name_col).in_(ULTIMATE_PARAMETERS)
        )
    ]
    if value_col is not None:
        filters.append(
            or_(
                analysis_type_col.notin_(["ultimate", "ultimate analysis", "ultimate_analysis"]),
                value_col <= ULTIMATE_MAX_PERCENT
            )
        )
    return and_(*filters)


def get_icp_filter(analysis_type_col, unit_name_col, value_col=None):
    """Filter for ICP analysis units.

    Checks if the unit is ppm and optionally if value <= ICP_MAX_PPM (issue
    #476: the physically-impossible-value cap already applied in
    mv_biomass_composition.py but missing from views.py's ANALYSIS_DATA_VIEW).
    """
    filters = [
        or_(
            analysis_type_col.notin_(["icp", "icp analysis", "icp_analysis", "icp-oes", "icp-ms"]),
            func.lower(unit_name_col) == "ppm"
        )
    ]
    if value_col is not None:
        filters.append(
            or_(
                analysis_type_col.notin_(["icp", "icp analysis", "icp_analysis", "icp-oes", "icp-ms"]),
                value_col <= ICP_MAX_PPM
            )
        )
    return and_(*filters)


def get_sum_constraints_subquery(measurements_subquery):
    """Calculate proximate and compositional sums per experiment for QC filtering.

    Args:
        measurements_subquery: A subquery containing at least:
            - resource_id
            - experiment_id
            - analysis_type
            - parameter_name
            - value
    """
    return select(
        measurements_subquery.c.resource_id,
        measurements_subquery.c.experiment_id,
        measurements_subquery.c.analysis_type,
        (
            func.coalesce(
                func.avg(case((measurements_subquery.c.parameter_name == "moisture", measurements_subquery.c.value))), 0
            )
            + func.coalesce(
                func.avg(case((measurements_subquery.c.parameter_name == "ash solids", measurements_subquery.c.value))), 0
            )
            + func.coalesce(
                func.avg(
                    case((measurements_subquery.c.parameter_name == "volatile solids", measurements_subquery.c.value))
                ),
                100
                - func.coalesce(
                    func.avg(
                        case((measurements_subquery.c.parameter_name == "fixed carbon", measurements_subquery.c.value))
                    ),
                    0,
                ),
            )
        ).label("proximate_sum"),
        (
            func.coalesce(
                func.avg(case((measurements_subquery.c.parameter_name == "glucan", measurements_subquery.c.value))), 0
            )
            + func.coalesce(
                func.avg(case((measurements_subquery.c.parameter_name == "xylan", measurements_subquery.c.value))), 0
            )
            + func.coalesce(
                func.avg(case((measurements_subquery.c.parameter_name == "lignin", measurements_subquery.c.value))),
                func.avg(case((measurements_subquery.c.parameter_name == "lignin+", measurements_subquery.c.value))),
            )
        ).label("compositional_sum"),
    ).group_by(
        measurements_subquery.c.resource_id,
        measurements_subquery.c.experiment_id,
        measurements_subquery.c.analysis_type,
    ).subquery()


# =============================================================================
# DROP VISIBILITY (issues #475, #477, #478 touch-points)
# =============================================================================
# Lightweight logging helper so callers (e.g. refresh_all_views) can report
# how many rows a named filter dimension removed, without building a new
# logging subsystem. This does not change filter behavior; it only makes
# existing drops visible, addressing the "silent data drops aren't logged"
# half of issue #478 for the view layer. The broader ETL-side logging gap
# in #478 is out of scope for this refactor.
def log_filter_summary(label, before_count, after_count):
    """Print how many rows a named filter dimension removed.

    Args:
        label: Human-readable name of the filter dimension (e.g. "resource blacklist").
        before_count: Row count before this filter was applied.
        after_count: Row count after this filter was applied.
    """
    removed = before_count - after_count
    pct = (removed / before_count * 100) if before_count else 0
    print(f"[filter] {label}: {before_count} -> {after_count} (removed {removed}, {pct:.1f}%)")
