"""
mv_biomass_search.py

Comprehensive biomass search view combining resource metadata, analytical metrics,
availability data, and supply volume projections.

Required index:
    CREATE UNIQUE INDEX idx_mv_biomass_search_id ON data_portal.mv_biomass_search (id)
"""

from sqlalchemy import select, func, union_all, literal, case, cast, String, Integer, Numeric, Boolean, and_, or_, Text, Float, ARRAY, text
from sqlalchemy.dialects.postgresql import array as pg_array
from sqlalchemy.orm import aliased

from ca_biositing.datamodels.models.resource_information.resource import Resource, ResourceClass, ResourceSubclass, ResourceMorphology
from ca_biositing.datamodels.models.resource_information.resource_production_record import ResourceProductionRecord
from ca_biositing.datamodels.models.resource_information.primary_ag_product import PrimaryAgProduct
from ca_biositing.datamodels.models.resource_information.resource_transport_record import ResourceTransportRecord
from ca_biositing.datamodels.models.resource_information.resource_storage_record import ResourceStorageRecord
from ca_biositing.datamodels.models.external_data.resource_usda_commodity_map import ResourceUsdaCommodityMap
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

from .common import (
    analysis_metrics,
    resource_analysis_map,
    get_carbon_avg_expr,
    get_hydrogen_avg_expr,
    get_nitrogen_avg_expr,
    get_cn_ratio_expr,
    get_resource_filter
)
from .mv_biomass_volume_estimate import mv_biomass_volume_estimate
from .mv_biomass_composition import mv_biomass_composition


# 1. Subquery for primary product fallback from USDA mapping
primary_product_fallback_sq = select(
    ResourceUsdaCommodityMap.resource_id,
    func.max(PrimaryAgProduct.name).label("primary_product_fallback")
).join(PrimaryAgProduct, ResourceUsdaCommodityMap.primary_ag_product_id == PrimaryAgProduct.id)\
 .where(ResourceUsdaCommodityMap.resource_id.is_not(None))\
 .group_by(ResourceUsdaCommodityMap.resource_id).subquery()

# 2. Refined Analysis Metrics Subquery
# Pull metrics directly from mv_biomass_composition to ensure alignment
# and inherit its QC filters (sum constraints, parameter filtering, etc.)
comp_sq = mv_biomass_composition.subquery()

resource_metrics_v2 = select(
    comp_sq.c.resource_id,
    func.avg(case((comp_sq.c.parameter_name == "moisture", comp_sq.c.avg_value))).label("moisture_percent"),
    func.avg(case((comp_sq.c.parameter_name == "ash solids", comp_sq.c.avg_value))).label("ash_percent"),
    case(
        (
            or_(
                func.avg(case((comp_sq.c.parameter_name == "lignin", comp_sq.c.avg_value))).is_not(None),
                func.avg(case((comp_sq.c.parameter_name == "lignin+", comp_sq.c.avg_value))).is_not(None)
            ),
            func.coalesce(func.avg(case((comp_sq.c.parameter_name == "lignin", comp_sq.c.avg_value))), 0) +
            func.coalesce(func.avg(case((comp_sq.c.parameter_name == "lignin+", comp_sq.c.avg_value))), 0)
        ),
        else_=None
    ).label("lignin_percent"),
    case(
        (
            or_(
                func.avg(case((comp_sq.c.parameter_name == "glucan", comp_sq.c.avg_value))).is_not(None),
                func.avg(case((comp_sq.c.parameter_name == "xylan", comp_sq.c.avg_value))).is_not(None)
            ),
            func.coalesce(func.avg(case((comp_sq.c.parameter_name == "glucan", comp_sq.c.avg_value))), 0) +
            func.coalesce(func.avg(case((comp_sq.c.parameter_name == "xylan", comp_sq.c.avg_value))), 0)
        ),
        else_=None
    ).label("sugar_content_percent"),
    func.avg(case((comp_sq.c.parameter_name == "glucan", comp_sq.c.avg_value))).label("glucan_percent"),
    func.avg(case((comp_sq.c.parameter_name == "xylan", comp_sq.c.avg_value))).label("xylan_percent"),
    func.avg(case((
        and_(comp_sq.c.analysis_type == "ultimate", func.lower(comp_sq.c.parameter_name) == "carbon"),
        comp_sq.c.avg_value
    ))).label("carbon_percent"),
    func.avg(case((
        and_(comp_sq.c.analysis_type == "ultimate", func.lower(comp_sq.c.parameter_name) == "hydrogen"),
        comp_sq.c.avg_value
    ))).label("hydrogen_percent"),
    case(
        (
            and_(
                func.avg(case((and_(comp_sq.c.analysis_type == "ultimate", func.lower(comp_sq.c.parameter_name) == "carbon"), comp_sq.c.avg_value))).is_not(None),
                func.avg(case((and_(comp_sq.c.analysis_type == "ultimate", func.lower(comp_sq.c.parameter_name) == "nitrogen"), comp_sq.c.avg_value))).is_not(None),
                func.avg(case((and_(comp_sq.c.analysis_type == "ultimate", func.lower(comp_sq.c.parameter_name) == "nitrogen"), comp_sq.c.avg_value))) != 0
            ),
            func.avg(case((and_(comp_sq.c.analysis_type == "ultimate", func.lower(comp_sq.c.parameter_name) == "carbon"), comp_sq.c.avg_value))) /
            cast(func.avg(case((and_(comp_sq.c.analysis_type == "ultimate", func.lower(comp_sq.c.parameter_name) == "nitrogen"), comp_sq.c.avg_value))), Numeric)
        ),
        else_=None
    ).label("cn_ratio"),
    # Flags derived from analysis_type presence in composition view
    func.bool_or(comp_sq.c.analysis_type == "proximate").label("has_proximate"),
    func.bool_or(comp_sq.c.analysis_type == "compositional").label("has_compositional"),
    func.bool_or(comp_sq.c.analysis_type == "ultimate").label("has_ultimate"),
    func.bool_or(comp_sq.c.analysis_type == "xrf").label("has_xrf"),
    func.bool_or(comp_sq.c.analysis_type == "icp").label("has_icp"),
    func.bool_or(comp_sq.c.analysis_type == "calorimetry").label("has_calorimetry"),
    func.bool_or(comp_sq.c.analysis_type == "xrd").label("has_xrd"),
    func.bool_or(comp_sq.c.analysis_type == "ftnir").label("has_ftnir"),
    func.bool_or(comp_sq.c.analysis_type == "fermentation").label("has_fermentation"),
    func.bool_or(comp_sq.c.analysis_type == "gasification").label("has_gasification"),
    func.bool_or(comp_sq.c.analysis_type == "pretreatment").label("has_pretreatment")
).group_by(comp_sq.c.resource_id).subquery()

# 3. Tag thresholds calculated from the QC-filtered metrics
thresholds_v2 = select(
    func.percentile_cont(0.1).within_group(resource_metrics_v2.c.moisture_percent).label("moisture_low"),
    func.percentile_cont(0.9).within_group(resource_metrics_v2.c.moisture_percent).label("moisture_high"),
    func.percentile_cont(0.1).within_group(resource_metrics_v2.c.ash_percent).label("ash_low"),
    func.percentile_cont(0.9).within_group(resource_metrics_v2.c.ash_percent).label("ash_high"),
    func.percentile_cont(0.1).within_group(resource_metrics_v2.c.lignin_percent).label("lignin_low"),
    func.percentile_cont(0.9).within_group(resource_metrics_v2.c.lignin_percent).label("lignin_high"),
    func.percentile_cont(0.1).within_group(resource_metrics_v2.c.sugar_content_percent).label("sugar_low"),
    func.percentile_cont(0.9).within_group(resource_metrics_v2.c.sugar_content_percent).label("sugar_high"),
    func.percentile_cont(0.1).within_group(resource_metrics_v2.c.glucan_percent).label("glucan_low"),
    func.percentile_cont(0.9).within_group(resource_metrics_v2.c.glucan_percent).label("glucan_high"),
    func.percentile_cont(0.1).within_group(resource_metrics_v2.c.xylan_percent).label("xylan_low"),
    func.percentile_cont(0.9).within_group(resource_metrics_v2.c.xylan_percent).label("xylan_high")
).subquery()

# 4. Resource tags generation joining on true
resource_tags_v2 = select(
     resource_metrics_v2.c.resource_id,
     func.array_remove(
         pg_array([
             case((resource_metrics_v2.c.moisture_percent <= thresholds_v2.c.moisture_low, "low moisture"), else_=None),
             case((resource_metrics_v2.c.moisture_percent >= thresholds_v2.c.moisture_high, "high moisture"), else_=None),
             case((resource_metrics_v2.c.ash_percent <= thresholds_v2.c.ash_low, "low ash solids"), else_=None),
             case((resource_metrics_v2.c.ash_percent >= thresholds_v2.c.ash_high, "high ash solids"), else_=None),
             case((resource_metrics_v2.c.lignin_percent <= thresholds_v2.c.lignin_low, "low lignin"), else_=None),
             case((resource_metrics_v2.c.lignin_percent >= thresholds_v2.c.lignin_high, "high lignin"), else_=None),
             case((resource_metrics_v2.c.glucan_percent <= thresholds_v2.c.glucan_low, "low glucan"), else_=None),
             case((resource_metrics_v2.c.glucan_percent >= thresholds_v2.c.glucan_high, "high glucan"), else_=None),
             case((resource_metrics_v2.c.xylan_percent <= thresholds_v2.c.xylan_low, "low xylan"), else_=None),
             case((resource_metrics_v2.c.xylan_percent >= thresholds_v2.c.xylan_high, "high xylan"), else_=None)
         ]),
         None
     ).label("tags")
 ).select_from(resource_metrics_v2).join(thresholds_v2, literal(True)).subquery()

# Aggregated volume from resource production records + observations
# Value is sum cross all NSJV counties for the most recent year of data for each resource
# (excluding "NSJV" itself which is an outlier and not mappable to a single geoid)
production_obs = select(
    cast(Observation.record_id, Integer).label("production_record_id"),
    Observation.value.label("production_value"),
    Observation.unit_id.label("unit_id"),
).join(Parameter, Observation.parameter_id == Parameter.id)\
 .where(and_(
     Observation.record_type == "resource_production_record",
     Observation.value.is_not(None),
     func.lower(Parameter.name).like("%production%"),
 )).subquery()

latest_production_year = select(
    ResourceProductionRecord.resource_id.label("resource_id"),
    func.max(ResourceProductionRecord.report_date).label("latest_report_date"),
).select_from(ResourceProductionRecord)\
 .join(production_obs, production_obs.c.production_record_id == ResourceProductionRecord.id)\
 \
 .group_by(ResourceProductionRecord.resource_id).subquery()

agg_vol = select(
     ResourceProductionRecord.resource_id,
     func.sum(production_obs.c.production_value).label("total_annual_volume"),
     func.count(func.distinct(ResourceProductionRecord.geoid)).label("county_count"),
     func.max(Unit.name).label("volume_unit"),
     cast(func.extract('year', latest_production_year.c.latest_report_date), Integer).label("total_annual_volume_year")
 ).select_from(ResourceProductionRecord)\
  .join(production_obs, production_obs.c.production_record_id == ResourceProductionRecord.id)\
  .join(latest_production_year, and_(
      latest_production_year.c.resource_id == ResourceProductionRecord.resource_id,
      latest_production_year.c.latest_report_date == ResourceProductionRecord.report_date,
  ))\
  .outerjoin(Unit, production_obs.c.unit_id == Unit.id)\
  \
  .group_by(ResourceProductionRecord.resource_id, latest_production_year.c.latest_report_date).subquery()

# Biomass availability aggregation
from .mv_biomass_availability import mv_biomass_availability

# Transport notes subquery (latest observation per resource)
transport_notes_sq = select(
    ResourceTransportRecord.resource_id,
    func.max(ResourceTransportRecord.transport_description).label("transport_notes")
).group_by(ResourceTransportRecord.resource_id).subquery()

# Storage notes subquery (latest observation per resource)
storage_notes_sq = select(
    ResourceStorageRecord.resource_id,
    func.max(ResourceStorageRecord.storage_description).label("storage_notes")
).group_by(ResourceStorageRecord.resource_id).subquery()

# Volume estimation aggregation (state-wide sum for latest data year)
# First, get the most recent year per resource
volume_year_sq = select(
     mv_biomass_volume_estimate.c.resource_id,
     func.max(mv_biomass_volume_estimate.c.dataset_year).label("volume_estimate_year")
  ).select_from(mv_biomass_volume_estimate)\
   .group_by(mv_biomass_volume_estimate.c.resource_id).subquery()

# Then aggregate volumes for the most recent year only
volume_agg = select(
     mv_biomass_volume_estimate.c.resource_id,
     func.sum(mv_biomass_volume_estimate.c.estimated_residue_volume_min).label("calculated_estimate_volume_min"),
     func.sum(mv_biomass_volume_estimate.c.estimated_residue_volume_max).label("calculated_estimate_volume_max"),
     func.sum(mv_biomass_volume_estimate.c.estimated_residue_volume_mid).label("calculated_estimate_volume_mid"),
     volume_year_sq.c.volume_estimate_year
  ).select_from(mv_biomass_volume_estimate)\
   .join(volume_year_sq, and_(
       mv_biomass_volume_estimate.c.resource_id == volume_year_sq.c.resource_id,
       mv_biomass_volume_estimate.c.dataset_year == volume_year_sq.c.volume_estimate_year,
   ))\
   .group_by(mv_biomass_volume_estimate.c.resource_id, volume_year_sq.c.volume_estimate_year).subquery()

mv_biomass_search = select(
     Resource.id,
     Resource.name,
     Resource.resource_code,
     Resource.description,
     ResourceClass.name.label("resource_class"),
     ResourceSubclass.name.label("resource_subclass"),
     func.coalesce(PrimaryAgProduct.name, primary_product_fallback_sq.c.primary_product_fallback).label("primary_product"),
     ResourceMorphology.morphology_uri.label("image_url"),
     Resource.uri.label("literature_uri"),
     agg_vol.c.total_annual_volume,
     agg_vol.c.county_count,
     agg_vol.c.volume_unit,
     agg_vol.c.total_annual_volume_year,
     resource_metrics_v2.c.moisture_percent,
     resource_metrics_v2.c.sugar_content_percent,
     resource_metrics_v2.c.glucan_percent,
     resource_metrics_v2.c.xylan_percent,
     resource_metrics_v2.c.ash_percent,
     resource_metrics_v2.c.lignin_percent,
     resource_metrics_v2.c.carbon_percent,
     resource_metrics_v2.c.hydrogen_percent,
     resource_metrics_v2.c.cn_ratio,
     transport_notes_sq.c.transport_notes,
     storage_notes_sq.c.storage_notes,
     func.coalesce(resource_tags_v2.c.tags, cast(pg_array([]), ARRAY(String))).label("tags"),
     mv_biomass_availability.c.from_month.label("season_from_month"),
     mv_biomass_availability.c.to_month.label("season_to_month"),
     mv_biomass_availability.c.year_round,
     # Boolean flags
     func.coalesce(resource_metrics_v2.c.has_proximate, False).label("has_proximate"),
     func.coalesce(resource_metrics_v2.c.has_compositional, False).label("has_compositional"),
     func.coalesce(resource_metrics_v2.c.has_ultimate, False).label("has_ultimate"),
     func.coalesce(resource_metrics_v2.c.has_xrf, False).label("has_xrf"),
     func.coalesce(resource_metrics_v2.c.has_icp, False).label("has_icp"),
     func.coalesce(resource_metrics_v2.c.has_calorimetry, False).label("has_calorimetry"),
     func.coalesce(resource_metrics_v2.c.has_xrd, False).label("has_xrd"),
     func.coalesce(resource_metrics_v2.c.has_ftnir, False).label("has_ftnir"),
     func.coalesce(resource_metrics_v2.c.has_fermentation, False).label("has_fermentation"),
     func.coalesce(resource_metrics_v2.c.has_gasification, False).label("has_gasification"),
     func.coalesce(resource_metrics_v2.c.has_pretreatment, False).label("has_pretreatment"),
     case((resource_metrics_v2.c.moisture_percent != None, True), else_=False).label("has_moisture_data"),
     case((resource_metrics_v2.c.sugar_content_percent > 0, True), else_=False).label("has_sugar_data"),
     case((ResourceMorphology.morphology_uri != None, True), else_=False).label("has_image"),
     case((
         or_(
             agg_vol.c.total_annual_volume.is_not(None),
             volume_agg.c.calculated_estimate_volume_min.is_not(None),
             volume_agg.c.calculated_estimate_volume_mid.is_not(None),
             volume_agg.c.calculated_estimate_volume_max.is_not(None),
         ),
         True,
     ), else_=False).label("has_volume_data"),
     # Calculated volume estimates
     volume_agg.c.calculated_estimate_volume_min,
     volume_agg.c.calculated_estimate_volume_max,
     volume_agg.c.calculated_estimate_volume_mid,
     volume_agg.c.volume_estimate_year,
     Resource.created_at,
     Resource.updated_at,
     func.to_tsvector(text("'english'"),
         func.coalesce(Resource.name, '') + ' ' +
         func.coalesce(Resource.description, '') + ' ' +
         func.coalesce(ResourceClass.name, '') + ' ' +
         func.coalesce(ResourceSubclass.name, '') + ' ' +
         func.coalesce(func.coalesce(PrimaryAgProduct.name, primary_product_fallback_sq.c.primary_product_fallback), '')
     ).label("search_vector")
  ).select_from(Resource)\
   .outerjoin(ResourceClass, Resource.resource_class_id == ResourceClass.id)\
   .outerjoin(ResourceSubclass, Resource.resource_subclass_id == ResourceSubclass.id)\
   .outerjoin(PrimaryAgProduct, Resource.primary_ag_product_id == PrimaryAgProduct.id)\
   .outerjoin(primary_product_fallback_sq, primary_product_fallback_sq.c.resource_id == Resource.id)\
   .outerjoin(ResourceMorphology, ResourceMorphology.resource_id == Resource.id)\
   .outerjoin(agg_vol, agg_vol.c.resource_id == Resource.id)\
   .outerjoin(volume_agg, volume_agg.c.resource_id == Resource.id)\
   .outerjoin(resource_metrics_v2, resource_metrics_v2.c.resource_id == Resource.id)\
   .outerjoin(resource_tags_v2, resource_tags_v2.c.resource_id == Resource.id)\
   .outerjoin(mv_biomass_availability, mv_biomass_availability.c.resource_id == Resource.id)\
   .outerjoin(transport_notes_sq, transport_notes_sq.c.resource_id == Resource.id)\
   .outerjoin(storage_notes_sq, storage_notes_sq.c.resource_id == Resource.id)\
   .where(get_resource_filter(Resource))
