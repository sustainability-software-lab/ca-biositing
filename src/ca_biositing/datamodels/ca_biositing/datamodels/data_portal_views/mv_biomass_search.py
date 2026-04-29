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
from ca_biositing.datamodels.models.resource_information.primary_ag_product import PrimaryAgProduct
from ca_biositing.datamodels.models.resource_information.resource_transport_record import ResourceTransportRecord
from ca_biositing.datamodels.models.resource_information.resource_storage_record import ResourceStorageRecord
from ca_biositing.datamodels.models.external_data.resource_usda_commodity_map import ResourceUsdaCommodityMap
from ca_biositing.datamodels.models.external_data.billion_ton import BillionTon2023Record
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
    get_cn_ratio_expr
)
from .mv_biomass_volume_estimate import mv_biomass_volume_estimate


# 1. Subquery for primary product fallback from USDA mapping
primary_product_fallback_sq = select(
    ResourceUsdaCommodityMap.resource_id,
    func.max(PrimaryAgProduct.name).label("primary_product_fallback")
).join(PrimaryAgProduct, ResourceUsdaCommodityMap.primary_ag_product_id == PrimaryAgProduct.id)\
 .where(ResourceUsdaCommodityMap.resource_id.is_not(None))\
 .group_by(ResourceUsdaCommodityMap.resource_id).subquery()

# 2. Refined Analysis Metrics Subquery
# We rebuild this to ensure exact alignment with the working SQL which uses explicit QC filters
# and specific join criteria.
analysis_sources = select(
    cast(CompositionalRecord.resource_id, Integer).label("resource_id"),
    cast(CompositionalRecord.record_id, String).label("record_id"),
    literal("compositional analysis").label("type")
).where(CompositionalRecord.qc_pass != "fail").union_all(
    select(cast(ProximateRecord.resource_id, Integer), cast(ProximateRecord.record_id, String), literal("proximate analysis")).where(ProximateRecord.qc_pass != "fail"),
    select(cast(UltimateRecord.resource_id, Integer), cast(UltimateRecord.record_id, String), literal("ultimate analysis")).where(UltimateRecord.qc_pass != "fail"),
    select(cast(XrfRecord.resource_id, Integer), cast(XrfRecord.record_id, String), literal("xrf analysis")).where(XrfRecord.qc_pass != "fail"),
    select(cast(IcpRecord.resource_id, Integer), cast(IcpRecord.record_id, String), literal("icp analysis")).where(IcpRecord.qc_pass != "fail"),
    select(cast(CalorimetryRecord.resource_id, Integer), cast(CalorimetryRecord.record_id, String), literal("calorimetry analysis")).where(CalorimetryRecord.qc_pass != "fail"),
    select(cast(XrdRecord.resource_id, Integer), cast(XrdRecord.record_id, String), literal("xrd analysis")).where(XrdRecord.qc_pass != "fail"),
    select(cast(FtnirRecord.resource_id, Integer), cast(FtnirRecord.record_id, String), literal("ftnir analysis")).where(FtnirRecord.qc_pass != "fail"),
    select(cast(FermentationRecord.resource_id, Integer), cast(FermentationRecord.record_id, String), literal("fermentation")).where(FermentationRecord.qc_pass != "fail"),
    select(cast(GasificationRecord.resource_id, Integer), cast(GasificationRecord.record_id, String), literal("gasification")).where(GasificationRecord.qc_pass != "fail"),
    select(cast(PretreatmentRecord.resource_id, Integer), cast(PretreatmentRecord.record_id, String), literal("pretreatment")).where(PretreatmentRecord.qc_pass != "fail")
).subquery()

observations_filtered = select(
    cast(Observation.record_id, String).label("record_id"),
    cast(Observation.record_type, String).label("record_type"),
    Parameter.name.label("parameter"),
    Observation.value
).join(Parameter, Observation.parameter_id == Parameter.id)\
 .where(Observation.record_type.in_([
     "compositional analysis", "proximate analysis", "ultimate analysis",
     "xrf analysis", "icp analysis", "calorimetry analysis",
     "xrd analysis", "ftnir analysis", "pretreatment",
     "gasification", "fermentation"
 ])).subquery()

resource_metrics_v2 = select(
    analysis_sources.c.resource_id,
    func.avg(case((observations_filtered.c.parameter == "moisture", observations_filtered.c.value))).label("moisture_percent"),
    func.avg(case((observations_filtered.c.parameter == "ash", observations_filtered.c.value))).label("ash_percent"),
    case(
        (
            or_(
                func.avg(case((observations_filtered.c.parameter == "lignin", observations_filtered.c.value))).is_not(None),
                func.avg(case((observations_filtered.c.parameter == "lignin+", observations_filtered.c.value))).is_not(None)
            ),
            func.coalesce(func.avg(case((observations_filtered.c.parameter == "lignin", observations_filtered.c.value))), 0) +
            func.coalesce(func.avg(case((observations_filtered.c.parameter == "lignin+", observations_filtered.c.value))), 0)
        ),
        else_=None
    ).label("lignin_percent"),
    case(
        (
            or_(
                func.avg(case((observations_filtered.c.parameter == "glucose", observations_filtered.c.value))).is_not(None),
                func.avg(case((observations_filtered.c.parameter == "xylose", observations_filtered.c.value))).is_not(None)
            ),
            func.coalesce(func.avg(case((observations_filtered.c.parameter == "glucose", observations_filtered.c.value))), 0) +
            func.coalesce(func.avg(case((observations_filtered.c.parameter == "xylose", observations_filtered.c.value))), 0)
        ),
        else_=None
    ).label("sugar_content_percent"),
    func.avg(case((observations_filtered.c.parameter == "glucose", observations_filtered.c.value))).label("glucan_percent"),
    func.avg(case((observations_filtered.c.parameter == "xylose", observations_filtered.c.value))).label("xylan_percent"),
    func.avg(case((
        and_(analysis_sources.c.type == "ultimate analysis", func.lower(observations_filtered.c.parameter) == "carbon"),
        observations_filtered.c.value
    ))).label("carbon_percent"),
    func.avg(case((
        and_(analysis_sources.c.type == "ultimate analysis", func.lower(observations_filtered.c.parameter) == "hydrogen"),
        observations_filtered.c.value
    ))).label("hydrogen_percent"),
    case(
        (
            and_(
                func.avg(case((and_(analysis_sources.c.type == "ultimate analysis", func.lower(observations_filtered.c.parameter) == "carbon"), observations_filtered.c.value))).is_not(None),
                func.avg(case((and_(analysis_sources.c.type == "ultimate analysis", func.lower(observations_filtered.c.parameter) == "nitrogen"), observations_filtered.c.value))).is_not(None),
                func.avg(case((and_(analysis_sources.c.type == "ultimate analysis", func.lower(observations_filtered.c.parameter) == "nitrogen"), observations_filtered.c.value))) != 0
            ),
            func.avg(case((and_(analysis_sources.c.type == "ultimate analysis", func.lower(observations_filtered.c.parameter) == "carbon"), observations_filtered.c.value))) /
            cast(func.avg(case((and_(analysis_sources.c.type == "ultimate analysis", func.lower(observations_filtered.c.parameter) == "nitrogen"), observations_filtered.c.value))), Numeric)
        ),
        else_=None
    ).label("cn_ratio"),
    # Flags
    func.bool_or(analysis_sources.c.type == "proximate analysis").label("has_proximate"),
    func.bool_or(analysis_sources.c.type == "compositional analysis").label("has_compositional"),
    func.bool_or(analysis_sources.c.type == "ultimate analysis").label("has_ultimate"),
    func.bool_or(analysis_sources.c.type == "xrf analysis").label("has_xrf"),
    func.bool_or(analysis_sources.c.type == "icp analysis").label("has_icp"),
    func.bool_or(analysis_sources.c.type == "calorimetry analysis").label("has_calorimetry"),
    func.bool_or(analysis_sources.c.type == "xrd analysis").label("has_xrd"),
    func.bool_or(analysis_sources.c.type == "ftnir analysis").label("has_ftnir"),
    func.bool_or(analysis_sources.c.type == "fermentation").label("has_fermentation"),
    func.bool_or(analysis_sources.c.type == "gasification").label("has_gasification"),
    func.bool_or(analysis_sources.c.type == "pretreatment").label("has_pretreatment")
).select_from(analysis_sources)\
 .join(observations_filtered, and_(
     func.lower(analysis_sources.c.record_id) == func.lower(observations_filtered.c.record_id),
     observations_filtered.c.record_type == analysis_sources.c.type
 ), isouter=True)\
 .group_by(analysis_sources.c.resource_id).subquery()

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
             case((resource_metrics_v2.c.ash_percent <= thresholds_v2.c.ash_low, "low ash"), else_=None),
             case((resource_metrics_v2.c.ash_percent >= thresholds_v2.c.ash_high, "high ash"), else_=None),
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

# Aggregated volume from Billion Ton
agg_vol = select(
     BillionTon2023Record.resource_id,
     func.sum(BillionTon2023Record.production).label("total_annual_volume"),
     func.count(func.distinct(BillionTon2023Record.geoid)).label("county_count"),
     func.max(Unit.name).label("volume_unit")
 ).join(Unit, BillionTon2023Record.production_unit_id == Unit.id)\
  .group_by(BillionTon2023Record.resource_id).subquery()

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
volume_agg = select(
    mv_biomass_volume_estimate.c.resource_id,
    func.sum(mv_biomass_volume_estimate.c.estimated_residue_volume_min).label("calculated_estimate_volume_min"),
    func.sum(mv_biomass_volume_estimate.c.estimated_residue_volume_max).label("calculated_estimate_volume_max"),
    func.sum(mv_biomass_volume_estimate.c.estimated_residue_volume_mid).label("calculated_estimate_volume_mid")
).select_from(mv_biomass_volume_estimate)\
 .where(mv_biomass_volume_estimate.c.dataset_year == 2024)\
 .group_by(mv_biomass_volume_estimate.c.resource_id).subquery()

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
     case((agg_vol.c.total_annual_volume != None, True), else_=False).label("has_volume_data"),
     # Calculated volume estimates
     volume_agg.c.calculated_estimate_volume_min,
     volume_agg.c.calculated_estimate_volume_max,
     volume_agg.c.calculated_estimate_volume_mid,
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
  .where(
      and_(
          func.lower(Resource.name) != "sargassum",
          func.lower(Resource.name) != "lab media",
      )
  )
