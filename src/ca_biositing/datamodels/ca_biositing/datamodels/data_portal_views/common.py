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

# Subquery for analytical averages (moisture, ash, lignin, sugar)
# Sugar = glucose + xylose
# QC: filtered to exclude "fail" - only include observations from analytical records that are not marked as failed
# NOTE: This subquery filters observation records based on their parent record's QC status
# via the resource_analysis_map which already filters by qc_pass != "fail"
analysis_metrics = select(
    Observation.record_id,
    Observation.record_type,
    Parameter.name.label("parameter"),
    Observation.value
).join(Parameter, Observation.parameter_id == Parameter.id)\
 .where(Observation.record_type.in_([
     "compositional analysis", "proximate analysis", "ultimate analysis",
     "xrf analysis", "icp analysis", "calorimetry analysis",
     "xrd analysis", "ftnir analysis", "pretreatment",
     "gasification", "fermentation"
 ])).subquery()

# Map record_id to resource_id across all analytical types
# QC: filtered to exclude "fail" - include only observations from records that are not marked as failed
resource_analysis_map = select(
    CompositionalRecord.resource_id, CompositionalRecord.record_id, literal("compositional analysis").label("type")
).where(CompositionalRecord.qc_pass != "fail").union_all(
    select(ProximateRecord.resource_id, ProximateRecord.record_id, literal("proximate analysis").label("type")).where(ProximateRecord.qc_pass != "fail"),
    select(UltimateRecord.resource_id, UltimateRecord.record_id, literal("ultimate analysis").label("type")).where(UltimateRecord.qc_pass != "fail"),
    select(XrfRecord.resource_id, XrfRecord.record_id, literal("xrf analysis").label("type")).where(XrfRecord.qc_pass != "fail"),
    select(IcpRecord.resource_id, IcpRecord.record_id, literal("icp analysis").label("type")).where(IcpRecord.qc_pass != "fail"),
    select(CalorimetryRecord.resource_id, CalorimetryRecord.record_id, literal("calorimetry analysis").label("type")).where(CalorimetryRecord.qc_pass != "fail"),
    select(XrdRecord.resource_id, XrdRecord.record_id, literal("xrd analysis").label("type")).where(XrdRecord.qc_pass != "fail"),
    select(FtnirRecord.resource_id, FtnirRecord.record_id, literal("ftnir analysis").label("type")).where(FtnirRecord.qc_pass != "fail"),
    select(FermentationRecord.resource_id, FermentationRecord.record_id, literal("fermentation").label("type")).where(FermentationRecord.qc_pass != "fail"),
    select(GasificationRecord.resource_id, GasificationRecord.record_id, literal("gasification").label("type")).where(GasificationRecord.qc_pass != "fail"),
    select(PretreatmentRecord.resource_id, PretreatmentRecord.record_id, literal("pretreatment").label("type")).where(PretreatmentRecord.qc_pass != "fail")
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
