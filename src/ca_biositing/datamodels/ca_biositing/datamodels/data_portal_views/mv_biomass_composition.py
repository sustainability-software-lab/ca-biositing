"""
mv_biomass_composition.py

Compositional analysis data aggregated across different analysis types
(compositional, proximate, ultimate, xrf, icp, calorimetry, xrd, ftnir, pretreatment).

Grouped by resource_id, analysis_type, parameter_name, unit, and geoid from field sample.

QC: filtered to pass only - only includes observations from records with qc_pass = "pass"

Required index:
    CREATE UNIQUE INDEX idx_mv_biomass_composition_id ON data_portal.mv_biomass_composition (id)
"""

from sqlalchemy import select, func, union_all, literal, case, and_, or_, cast
from sqlalchemy.types import Integer, Numeric, String
from ca_biositing.datamodels.data_portal_views.common import (
    get_resource_filter,
    get_ultimate_filter,
    get_icp_filter
)
from ca_biositing.datamodels.models.resource_information.resource import Resource
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
from ca_biositing.datamodels.models.sample_preparation.prepared_sample import PreparedSample
from ca_biositing.datamodels.models.field_sampling.field_sample import FieldSample
from ca_biositing.datamodels.models.places.location_address import LocationAddress
from ca_biositing.datamodels.models.places.place import Place


def get_composition_query(model, analysis_type):
    """Generate a select statement for a specific analysis record type with geoid from field sample.
    QC: filtered to exclude "fail" - only include records that are not marked as failed"""
    return select(
        model.resource_id,
        model.experiment_id,
        literal(analysis_type).label("analysis_type"),
        case(
            (Parameter.name == "ash", "ash solids"),
            else_=Parameter.name
        ).label("parameter_name"),
        Observation.value.label("value"),
        Unit.name.label("unit"),
        LocationAddress.geography_id.label("geoid")
    ).join(Observation, func.lower(Observation.record_id) == func.lower(model.record_id))\
     .join(Parameter, Observation.parameter_id == Parameter.id)\
     .outerjoin(Unit, Observation.unit_id == Unit.id)\
     .outerjoin(PreparedSample, model.prepared_sample_id == PreparedSample.id)\
     .outerjoin(FieldSample, PreparedSample.field_sample_id == FieldSample.id)\
     .outerjoin(LocationAddress, FieldSample.sampling_location_id == LocationAddress.id)\
     .where(
         and_(
             model.qc_pass != "fail",
             get_ultimate_filter(literal(analysis_type), Parameter.name),
             get_icp_filter(literal(analysis_type), Unit.name),
             or_(
                 literal(analysis_type) != "ultimate",
                 Observation.value <= 100
             )
         )
     )


comp_queries = [
    get_composition_query(CompositionalRecord, "compositional"),
    get_composition_query(ProximateRecord, "proximate"),
    get_composition_query(UltimateRecord, "ultimate"),
    get_composition_query(XrfRecord, "xrf"),
    get_composition_query(IcpRecord, "icp"),
    get_composition_query(CalorimetryRecord, "calorimetry"),
    get_composition_query(XrdRecord, "xrd"),
    get_composition_query(FtnirRecord, "ftnir"),
    get_composition_query(PretreatmentRecord, "pretreatment")
]

# Minimal queries for fermentation and gasification to flag presence in search
# These don't need full observation data, just detection of record existence
# Cast NULL values to match types from observation queries
fermentation_presence = select(
    FermentationRecord.resource_id,
    cast(literal(None), Integer).label("experiment_id"),
    literal("fermentation").label("analysis_type"),
    literal("fermentation").label("parameter_name"),
    cast(literal(None), Numeric).label("value"),
    cast(literal(None), String).label("unit"),
    cast(literal(None), String).label("geoid")
).where(FermentationRecord.qc_pass != "fail").distinct()

gasification_presence = select(
    GasificationRecord.resource_id,
    cast(literal(None), Integer).label("experiment_id"),
    literal("gasification").label("analysis_type"),
    literal("gasification").label("parameter_name"),
    cast(literal(None), Numeric).label("value"),
    cast(literal(None), String).label("unit"),
    cast(literal(None), String).label("geoid")
).where(GasificationRecord.qc_pass != "fail").distinct()

comp_queries.extend([fermentation_presence, gasification_presence])

all_measurements = union_all(*comp_queries).subquery()

# QC Analysis Filtering: Calculate sums per (resource, experiment, analysis_type)
# Only for analysis types that need filtering (proximate and compositional)
# Fermentation and gasification are shown in mv_biomass_search but don't use these sums
qc_analysis_stats = select(
    all_measurements.c.resource_id,
    all_measurements.c.experiment_id,
    all_measurements.c.analysis_type,
    (
        func.coalesce(func.avg(case((all_measurements.c.parameter_name == "moisture", all_measurements.c.value))), 0) +
        func.coalesce(func.avg(case((all_measurements.c.parameter_name == "ash solids", all_measurements.c.value))), 0) +
        func.coalesce(
            func.avg(case((all_measurements.c.parameter_name == "volatile solids", all_measurements.c.value))),
            100 - func.coalesce(func.avg(case((all_measurements.c.parameter_name == "fixed carbon", all_measurements.c.value))), 0)
        )
    ).label("proximate_sum"),
    (
        func.coalesce(func.avg(case((all_measurements.c.parameter_name == "glucan", all_measurements.c.value))), 0) +
        func.coalesce(func.avg(case((all_measurements.c.parameter_name == "xylan", all_measurements.c.value))), 0) +
        func.coalesce(
            func.avg(case((all_measurements.c.parameter_name == "lignin", all_measurements.c.value))),
            func.avg(case((all_measurements.c.parameter_name == "lignin+", all_measurements.c.value)))
        )
    ).label("compositional_sum"),
    func.max(
        case(
            (and_(all_measurements.c.analysis_type == "icp", all_measurements.c.unit == "ppm"), all_measurements.c.value),
            else_=0
        )
    ).label("max_icp_ppm")
).group_by(
    all_measurements.c.resource_id,
    all_measurements.c.experiment_id,
    all_measurements.c.analysis_type
).subquery()

mv_biomass_composition = select(
    func.row_number().over(order_by=(all_measurements.c.resource_id, all_measurements.c.geoid, all_measurements.c.analysis_type, all_measurements.c.parameter_name, all_measurements.c.unit)).label("id"),
    all_measurements.c.resource_id,
    Resource.name.label("resource_name"),
    all_measurements.c.analysis_type,
    all_measurements.c.parameter_name,
    all_measurements.c.geoid,
    Place.county_name.label("county"),
    all_measurements.c.unit,
    func.avg(all_measurements.c.value).label("avg_value"),
    func.min(all_measurements.c.value).label("min_value"),
    func.max(all_measurements.c.value).label("max_value"),
    func.stddev(all_measurements.c.value).label("std_dev"),
    func.count().label("observation_count")
).select_from(all_measurements)\
 .join(Resource, all_measurements.c.resource_id == Resource.id)\
 .outerjoin(Place, all_measurements.c.geoid == Place.geoid)\
 .join(
     qc_analysis_stats,
     and_(
         all_measurements.c.resource_id == qc_analysis_stats.c.resource_id,
         func.coalesce(all_measurements.c.experiment_id, -1) == func.coalesce(qc_analysis_stats.c.experiment_id, -1),
         all_measurements.c.analysis_type == qc_analysis_stats.c.analysis_type
     )
  )\
 .where(
      and_(
          get_resource_filter(Resource),
          or_(
              # For proximate: apply sum filter (95-105) or no data
              and_(
                  all_measurements.c.analysis_type == "proximate",
                  or_(
                      qc_analysis_stats.c.proximate_sum == 0,
                      and_(
                          qc_analysis_stats.c.proximate_sum >= 95,
                          qc_analysis_stats.c.proximate_sum <= 105
                      )
                  )
              ),
              # For compositional: apply sum filter (40-105) or no data
              and_(
                  all_measurements.c.analysis_type == "compositional",
                  or_(
                      qc_analysis_stats.c.compositional_sum == 0,
                      and_(
                          qc_analysis_stats.c.compositional_sum >= 40,
                          qc_analysis_stats.c.compositional_sum <= 105
                      )
                  )
              ),
              # For ICP: filter out experiments with any value > 500,000 ppm
              and_(
                  all_measurements.c.analysis_type == "icp",
                  or_(
                      qc_analysis_stats.c.max_icp_ppm == None,
                      qc_analysis_stats.c.max_icp_ppm <= 500000
                  )
              ),
              # For all other analysis types: no filtering, include all
              all_measurements.c.analysis_type.notin_(["proximate", "compositional", "icp"])
          )
      )
  )\
 .group_by(
     all_measurements.c.resource_id,
     Resource.name,
     all_measurements.c.analysis_type,
     all_measurements.c.parameter_name,
     all_measurements.c.geoid,
     Place.county_name,
     all_measurements.c.unit
 )
