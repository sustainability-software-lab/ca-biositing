"""
mv_volume_estimation.py

Volume estimation views combining production-based and census-based residue calculations.

This module provides multi-path volume estimation:
1. Production-based (Path A): county_ag_report_record × residue_factors (weight type) for most agricultural residues
2. Census-based (Path B): USDA census acres × prune_trim_yield for orchard crops (weight-type)
3. Commodity-direct (Path C): county_ag_report_record production value IS the resource volume (e.g. almond hulls)
4. Acreage-based (Path D): USDA census harvested/bearing/BNB acres × area-type residue factors

Acreage parameter selection (Paths B & D):
- Orchard crops (almonds, walnuts, grapes): 'area bearing & non-bearing' preferred over 'area bearing'
- Field crops (cotton, wheat): 'area harvested'
- Implemented via COALESCE(avg(BNB), avg(bearing), avg(harvested)) logic per census record

Required indexes:
    CREATE UNIQUE INDEX idx_mv_biomass_volume_estimate_id ON data_portal.mv_biomass_volume_estimate (id)
    CREATE INDEX idx_mv_biomass_volume_estimate_resource_id ON data_portal.mv_biomass_volume_estimate (resource_id)
    CREATE INDEX idx_mv_biomass_volume_estimate_geoid ON data_portal.mv_biomass_volume_estimate (geoid)
    CREATE INDEX idx_mv_biomass_volume_estimate_resource_year ON data_portal.mv_biomass_volume_estimate (resource_id, dataset_year)
"""

from sqlalchemy import select, func, union_all, literal, case, cast, String, Integer, Numeric, and_, or_, text
from sqlalchemy.orm import aliased

from ca_biositing.datamodels.data_portal_views.common import get_resource_filter
from ca_biositing.datamodels.models.resource_information.resource import Resource
from ca_biositing.datamodels.models.resource_information.primary_ag_product import PrimaryAgProduct
from ca_biositing.datamodels.models.resource_information.residue_factor import ResidueFactor
from ca_biositing.datamodels.models.external_data.county_ag_report_record import CountyAgReportRecord
from ca_biositing.datamodels.models.external_data.usda_census import UsdaCensusRecord, UsdaCommodity
from ca_biositing.datamodels.models.external_data.resource_usda_commodity_map import ResourceUsdaCommodityMap
from ca_biositing.datamodels.models.places.place import Place
from ca_biositing.datamodels.models.methods_parameters_units.parameter import Parameter
from ca_biositing.datamodels.models.methods_parameters_units.unit import Unit
from ca_biositing.datamodels.models.general_analysis.observation import Observation


# ── Shared observation parameter/unit IDs ──────────────────────────────────
# These IDs are stable across environments (seeded from migrations).
_acreage_unit_id = 18    # unit.id for 'acres'
_param_bearing_id = 5    # parameter.id for 'area bearing'
_param_bnb_id = 7        # parameter.id for 'area bearing & non-bearing'
_param_harvested_id = 3  # parameter.id for 'area harvested'


# Path A: Production-based volume estimation
# Uses county_ag_report_record × residue_factors for residue calculation
# Join path: CountyAgReportRecord -> PrimaryAgProduct -> Resource -> ResidueFactor
production_based_volumes = select(
    Resource.id.label("resource_id"),
    Resource.name.label("resource_name"),
    CountyAgReportRecord.geoid,
    Place.county_name.label("county"),
    Place.county_fips,
    Place.state_name.label("state"),
    CountyAgReportRecord.data_year.label("dataset_year"),
    CountyAgReportRecord.record_id,
    # Aggregate observations for production volume
    func.avg(case((Parameter.name == "production", Observation.value), else_=None)).label("primary_product_volume"),
    # Harvested acres for the crop
    func.avg(case((Parameter.name == "harvested acres", Observation.value), else_=None)).label("county_crop_acres"),
    # Capture unit from observations
    func.max(case((Parameter.name == "production", Unit.name), else_=None)).label("volume_unit"),
    # Residue factor values
    ResidueFactor.factor_min,
    ResidueFactor.factor_mid,
    ResidueFactor.factor_max,
    # Calculated volumes (min, mid, max)
    (func.avg(case((Parameter.name == "production", Observation.value), else_=None)) * ResidueFactor.factor_min).label("estimated_residue_volume_min"),
    (func.avg(case((Parameter.name == "production", Observation.value), else_=None)) * ResidueFactor.factor_mid).label("estimated_residue_volume_mid"),
    (func.avg(case((Parameter.name == "production", Observation.value), else_=None)) * ResidueFactor.factor_max).label("estimated_residue_volume_max"),
    literal("production_based").label("volume_source"),
    literal("dry_tons").label("biomass_unit")
).select_from(CountyAgReportRecord)\
 .join(Resource, CountyAgReportRecord.primary_ag_product_id == Resource.primary_ag_product_id)\
 .join(ResidueFactor, ResidueFactor.resource_id == Resource.id)\
 .join(Place, CountyAgReportRecord.geoid == Place.geoid)\
 .outerjoin(Observation, and_(Observation.record_id == CountyAgReportRecord.record_id, Observation.record_type == "county_ag_report_record"))\
 .outerjoin(Parameter, Observation.parameter_id == Parameter.id)\
 .outerjoin(Unit, Observation.unit_id == Unit.id)\
 .where(and_(
     ResidueFactor.factor_type == "weight",
     CountyAgReportRecord.data_year >= 2017,
     get_resource_filter(Resource),
     func.lower(Place.county_name).in_(["san joaquin", "stanislaus", "merced"])
 ))\
 .group_by(
     Resource.id,
     Resource.name,
     CountyAgReportRecord.geoid,
     Place.county_name,
     Place.county_fips,
     Place.state_name,
     CountyAgReportRecord.data_year,
     CountyAgReportRecord.record_id,
     ResidueFactor.factor_min,
     ResidueFactor.factor_mid,
     ResidueFactor.factor_max
 ).subquery()


# Path B: Census-based volume estimation
# Uses USDA census acres × prune_trim_yield for non-area-type resources
# that have a prune_trim_yield factor (e.g. grape vines, almond woodchips).
#
# Acreage parameter selection (via conditional aggregation + COALESCE):
#   - Orchard crops (almonds, walnuts, grapes): 'area bearing & non-bearing'
#     preferred over 'area bearing' to include pruning/trimming from all managed trees.
#   - Resources where factor_type != 'area', since area-type resources are handled by Path D.
#
# Resources currently covered:
#   - grape vines      (resource  8, weight type) → all grapes (usda_commodity 7)
#   - almond woodchips (resource 34, weight type) → almonds (usda_commodity 2)
census_based_volumes = select(
    Resource.id.label("resource_id"),
    Resource.name.label("resource_name"),
    UsdaCensusRecord.geoid,
    Place.county_name.label("county"),
    Place.county_fips,
    Place.state_name.label("state"),
    UsdaCensusRecord.year.label("dataset_year"),
    UsdaCensusRecord.id.label("record_id"),
    # Acreage: COALESCE(area bearing & non-bearing, area bearing)
    # Prefer bearing & non-bearing to capture total managed footprint for pruning.
    func.coalesce(
        func.avg(case((Observation.parameter_id == _param_bnb_id, Observation.value), else_=None)),
        func.avg(case((Observation.parameter_id == _param_bearing_id, Observation.value), else_=None))
    ).label("bearing_acres"),
    func.coalesce(
        func.avg(case((Observation.parameter_id == _param_bnb_id, Observation.value), else_=None)),
        func.avg(case((Observation.parameter_id == _param_bearing_id, Observation.value), else_=None))
    ).label("county_crop_acres"),
    literal("acres").label("volume_unit"),
    # Residue factor yield values
    ResidueFactor.prune_trim_yield,
    ResidueFactor.prune_trim_yield_unit_id,
    func.max(Unit.name).label("yield_unit"),
    # Calculated volumes (acres × prune_trim_yield)
    (
        func.coalesce(
            func.avg(case((Observation.parameter_id == _param_bnb_id, Observation.value), else_=None)),
            func.avg(case((Observation.parameter_id == _param_bearing_id, Observation.value), else_=None))
        ) * ResidueFactor.prune_trim_yield
    ).label("estimated_residue_volume_min"),
    (
        func.coalesce(
            func.avg(case((Observation.parameter_id == _param_bnb_id, Observation.value), else_=None)),
            func.avg(case((Observation.parameter_id == _param_bearing_id, Observation.value), else_=None))
        ) * ResidueFactor.prune_trim_yield
    ).label("estimated_residue_volume_mid"),
    (
        func.coalesce(
            func.avg(case((Observation.parameter_id == _param_bnb_id, Observation.value), else_=None)),
            func.avg(case((Observation.parameter_id == _param_bearing_id, Observation.value), else_=None))
        ) * ResidueFactor.prune_trim_yield
    ).label("estimated_residue_volume_max"),
    literal("prune_acres").label("volume_source"),
    literal("dry_tons").label("biomass_unit")
).select_from(UsdaCensusRecord)\
 .join(UsdaCommodity, UsdaCensusRecord.commodity_code == UsdaCommodity.id)\
 .join(ResourceUsdaCommodityMap, ResourceUsdaCommodityMap.usda_commodity_id == UsdaCommodity.id)\
 .join(Resource, Resource.id == ResourceUsdaCommodityMap.resource_id)\
 .join(ResidueFactor, ResidueFactor.resource_id == Resource.id)\
 .join(Place, UsdaCensusRecord.geoid == Place.geoid)\
 .outerjoin(Observation, and_(
     Observation.record_id == cast(UsdaCensusRecord.id, String),
     Observation.record_type == "usda_census_record",
     Observation.unit_id == _acreage_unit_id,
     or_(
         Observation.parameter_id == _param_bnb_id,
         Observation.parameter_id == _param_bearing_id
     )
 ))\
 .outerjoin(Unit, ResidueFactor.prune_trim_yield_unit_id == Unit.id)\
 .where(and_(
     ResidueFactor.prune_trim_yield.isnot(None),
     ResidueFactor.factor_type != "area",
     UsdaCensusRecord.year >= 2017,
     get_resource_filter(Resource),
     func.lower(Place.county_name).in_(["san joaquin", "stanislaus", "merced"])
 ))\
 .group_by(
     Resource.id,
     Resource.name,
     UsdaCensusRecord.geoid,
     Place.county_name,
     Place.county_fips,
     Place.state_name,
     UsdaCensusRecord.year,
     UsdaCensusRecord.id,
     ResidueFactor.prune_trim_yield,
     ResidueFactor.prune_trim_yield_unit_id
 ).subquery()


# Matches CountyAgReportRecord.primary_ag_product_id (via name) to Resource.id (via name).
mapping_names = union_all(
    select(literal("almond hulls").label("pap_name"), literal("almond hulls").label("res_name")),
    select(literal("almond shells"), literal("almond shells")),
    select(literal("almond meats"), literal("almond hulls")),
    select(literal("hay - alfalfa"), literal("alfalfa")),
    select(literal("silage - alfalfa"), literal("alfalfa")),
    select(literal("alfalfa & mixtures"), literal("alfalfa")),
    select(literal("alfalfa & alfalfa mixtures"), literal("alfalfa"))
).subquery("mapping_names")

commodity_map = select(
    PrimaryAgProduct.id.label("pap_id"),
    Resource.id.label("resource_id")
).select_from(mapping_names)\
 .join(PrimaryAgProduct, func.lower(PrimaryAgProduct.name) == mapping_names.c.pap_name)\
 .join(Resource, func.lower(Resource.name) == mapping_names.c.res_name)\
 .subquery("commodity_map")

# Path C: Commodity-direct resource volumes
# For resources (e.g. almond hulls, almond shells) that are themselves tracked
# as primary commodities in county_ag_report_record. The production observation
# value IS the resource volume — no residue factor multiplication needed.
commodity_direct_volumes = select(
    Resource.id.label("resource_id"),
    Resource.name.label("resource_name"),
    CountyAgReportRecord.geoid,
    Place.county_name.label("county"),
    Place.county_fips,
    Place.state_name.label("state"),
    CountyAgReportRecord.data_year.label("dataset_year"),
    CountyAgReportRecord.record_id,
    # Aggregate observations for production volume
    func.avg(case((Parameter.name == "production", Observation.value), else_=None)).label("primary_product_volume"),
    cast(literal(None), Numeric).label("county_crop_acres"),
    # Capture unit from observations
    func.max(case((Parameter.name == "production", Unit.name), else_=None)).label("volume_unit"),
    # Identity factor (direct measurement)
    cast(literal(None), Numeric).label("factor_min"),
    cast(literal(1.0), Numeric).label("factor_mid"),
    cast(literal(None), Numeric).label("factor_max"),
    # estimated_residue_volume = production value directly (factor = 1)
    func.avg(case((Parameter.name == "production", Observation.value), else_=None)).label("estimated_residue_volume_min"),
    func.avg(case((Parameter.name == "production", Observation.value), else_=None)).label("estimated_residue_volume_mid"),
    func.avg(case((Parameter.name == "production", Observation.value), else_=None)).label("estimated_residue_volume_max"),
    literal("commodity_direct").label("volume_source"),
    literal("tons").label("biomass_unit")
).select_from(CountyAgReportRecord)\
 .join(commodity_map, commodity_map.c.pap_id == CountyAgReportRecord.primary_ag_product_id)\
 .join(Resource, Resource.id == commodity_map.c.resource_id)\
 .join(Place, CountyAgReportRecord.geoid == Place.geoid)\
 .outerjoin(Observation, and_(
     Observation.record_id == CountyAgReportRecord.record_id,
     Observation.record_type == "county_ag_report_record"
 ))\
 .outerjoin(Parameter, Observation.parameter_id == Parameter.id)\
 .outerjoin(Unit, Observation.unit_id == Unit.id)\
 .where(and_(
     CountyAgReportRecord.data_year >= 2017,
     get_resource_filter(Resource),
     func.lower(Place.county_name).in_(["san joaquin", "stanislaus", "merced"])
 ))\
 .group_by(
     Resource.id,
     Resource.name,
     CountyAgReportRecord.geoid,
     Place.county_name,
     Place.county_fips,
     Place.state_name,
     CountyAgReportRecord.data_year,
     CountyAgReportRecord.record_id,
 ).subquery()


# Path D: Acreage-based volume estimation
# Uses USDA census harvested/bearing acres × area-type residue factors.
# Join path: UsdaCensusRecord -> ResourceUsdaCommodityMap -> Resource -> ResidueFactor (area)
#
# Acreage parameter selection (via conditional aggregation + COALESCE):
#   - Orchard crops (almonds, walnuts, grapes): 'area bearing & non-bearing'
#     Pruning/trimming waste is generated from all trees regardless of bearing status.
#   - Field crops (cotton, wheat): 'area harvested'
#   COALESCE picks whichever is non-NULL for a given census record — each commodity
#   only has one of these two parameter types, so there is no ambiguity.
#
# Resources covered (factor_type='area', with usda_commodity_map entry):
#   - almond branches  (resource 51) → almonds (usda_commodity 2)
#   - cotton stem mix  (resource  4) → cotton upland (usda_commodity 5)
#   - grape stem       (resource 47) → all grapes (usda_commodity 7)
#   - walnut tree sticks (resource 25) → walnuts english (usda_commodity 20)
#   - wheat straw      (resource 40) → wheat (usda_commodity 21)
#   Note: grape vine prunings (resource 32) has no usda_commodity_map entry — excluded.
acreage_based_volumes = select(
 Resource.id.label("resource_id"),
 Resource.name.label("resource_name"),
 UsdaCensusRecord.geoid,
 Place.county_name.label("county"),
 Place.county_fips,
 Place.state_name.label("state"),
 UsdaCensusRecord.year.label("dataset_year"),
 cast(UsdaCensusRecord.id, String).label("record_id"),
 # Acreage: COALESCE(area bearing & non-bearing, area harvested)
 # Each commodity only has one of these two parameters, so COALESCE selects the right one.
 func.coalesce(
     func.avg(case((Observation.parameter_id == _param_bnb_id, Observation.value), else_=None)),
     func.avg(case((Observation.parameter_id == _param_harvested_id, Observation.value), else_=None))
 ).label("county_crop_acres"),
 # Residue factor values (COALESCE with prune_trim_yield for acreage-based estimation)
 # Most area-type resources use prune_trim_yield as the primary tons/acre factor.
 # Wheat straw uses factor_min/mid/max (0.6/0.7/0.8).
 func.coalesce(ResidueFactor.prune_trim_yield, ResidueFactor.factor_min).label("factor_min"),
 func.coalesce(ResidueFactor.prune_trim_yield, ResidueFactor.factor_mid).label("factor_mid"),
 func.coalesce(ResidueFactor.prune_trim_yield, ResidueFactor.factor_max).label("factor_max"),
 # Calculated volumes: acres × factor (NULL when factor is NULL)
 (
     func.coalesce(
         func.avg(case((Observation.parameter_id == _param_bnb_id, Observation.value), else_=None)),
         func.avg(case((Observation.parameter_id == _param_harvested_id, Observation.value), else_=None))
     ) * func.coalesce(ResidueFactor.prune_trim_yield, ResidueFactor.factor_min)
 ).label("estimated_residue_volume_min"),
 (
     func.coalesce(
         func.avg(case((Observation.parameter_id == _param_bnb_id, Observation.value), else_=None)),
         func.avg(case((Observation.parameter_id == _param_harvested_id, Observation.value), else_=None))
     ) * func.coalesce(ResidueFactor.prune_trim_yield, ResidueFactor.factor_mid)
 ).label("estimated_residue_volume_mid"),
 (
     func.coalesce(
         func.avg(case((Observation.parameter_id == _param_bnb_id, Observation.value), else_=None)),
         func.avg(case((Observation.parameter_id == _param_harvested_id, Observation.value), else_=None))
     ) * func.coalesce(ResidueFactor.prune_trim_yield, ResidueFactor.factor_max)
 ).label("estimated_residue_volume_max"),
 literal("acreage_based").label("volume_source"),
 literal("dry_tons").label("biomass_unit")
).select_from(UsdaCensusRecord)\
.join(ResourceUsdaCommodityMap, ResourceUsdaCommodityMap.usda_commodity_id == UsdaCensusRecord.commodity_code)\
.join(Resource, Resource.id == ResourceUsdaCommodityMap.resource_id)\
.join(ResidueFactor, and_(
  ResidueFactor.resource_id == Resource.id,
  ResidueFactor.factor_type == "area"
))\
.join(Place, UsdaCensusRecord.geoid == Place.geoid)\
.outerjoin(Observation, and_(
  Observation.record_id == cast(UsdaCensusRecord.id, String),
  Observation.record_type == "usda_census_record",
  Observation.unit_id == _acreage_unit_id,
  or_(
      Observation.parameter_id == _param_bnb_id,
      Observation.parameter_id == _param_harvested_id
  )
))\
.where(and_(
  UsdaCensusRecord.year >= 2017,
  get_resource_filter(Resource),
  func.lower(Place.county_name).in_(["san joaquin", "stanislaus", "merced"])
))\
.group_by(
  Resource.id,
  Resource.name,
  UsdaCensusRecord.geoid,
  Place.county_name,
  Place.county_fips,
  Place.state_name,
  UsdaCensusRecord.year,
  UsdaCensusRecord.id,
  ResidueFactor.prune_trim_yield,
  ResidueFactor.factor_min,
  ResidueFactor.factor_mid,
  ResidueFactor.factor_max,
).subquery()



# Path E: Census Production-based volume estimation
# Uses USDA census production values × residue_factors (weight type)
# This is specifically for crops like corn where we have census production data but not county ag report data
census_production_based_volumes = select(
    Resource.id.label("resource_id"),
    Resource.name.label("resource_name"),
    UsdaCensusRecord.geoid,
    Place.county_name.label("county"),
    Place.county_fips,
    Place.state_name.label("state"),
    UsdaCensusRecord.year.label("dataset_year"),
    cast(UsdaCensusRecord.id, String).label("record_id"),
    # Aggregate observations for production volume (preferring tons)
    func.avg(case((and_(Parameter.name == "production", Unit.name == "tons"), Observation.value), else_=None)).label("primary_product_volume"),
    # Harvested acres for the crop
    func.avg(case((Parameter.name == "harvested acres", Observation.value), else_=None)).label("county_crop_acres"),
    # Capture unit from observations
    func.max(case((and_(Parameter.name == "production", Unit.name == "tons"), Unit.name), else_=None)).label("volume_unit"),
    # Residue factor values
    ResidueFactor.factor_min,
    ResidueFactor.factor_mid,
    ResidueFactor.factor_max,
    # Calculated volumes (min, mid, max)
    (func.avg(case((and_(Parameter.name == "production", Unit.name == "tons"), Observation.value), else_=None)) * ResidueFactor.factor_min).label("estimated_residue_volume_min"),
    (func.avg(case((and_(Parameter.name == "production", Unit.name == "tons"), Observation.value), else_=None)) * ResidueFactor.factor_mid).label("estimated_residue_volume_mid"),
    (func.avg(case((and_(Parameter.name == "production", Unit.name == "tons"), Observation.value), else_=None)) * ResidueFactor.factor_max).label("estimated_residue_volume_max"),
    literal("census_production_based").label("volume_source"),
    literal("dry_tons").label("biomass_unit")
).select_from(UsdaCensusRecord) .join(ResourceUsdaCommodityMap, ResourceUsdaCommodityMap.usda_commodity_id == UsdaCensusRecord.commodity_code) .join(Resource, Resource.id == ResourceUsdaCommodityMap.resource_id) .join(ResidueFactor, ResidueFactor.resource_id == Resource.id) .join(Place, UsdaCensusRecord.geoid == Place.geoid) .outerjoin(Observation, and_(
     Observation.record_id == cast(UsdaCensusRecord.id, String),
     Observation.record_type == "usda_census_record"
 )) .outerjoin(Parameter, Observation.parameter_id == Parameter.id) .outerjoin(Unit, Observation.unit_id == Unit.id) .where(and_(
     ResidueFactor.factor_type == "weight",
     UsdaCensusRecord.year >= 2017,
     get_resource_filter(Resource),
     func.lower(Place.county_name).in_(["san joaquin", "stanislaus", "merced"]),
     # Only include resources that don't have production data in county ag reports
     # to avoid double counting
     ~Resource.id.in_(
         select(Resource.id)
         .join(PrimaryAgProduct, Resource.primary_ag_product_id == PrimaryAgProduct.id)
         .join(CountyAgReportRecord, CountyAgReportRecord.primary_ag_product_id == PrimaryAgProduct.id)
     )
 )) .group_by(
     Resource.id,
     Resource.name,
     UsdaCensusRecord.geoid,
     Place.county_name,
     Place.county_fips,
     Place.state_name,
     UsdaCensusRecord.year,
     UsdaCensusRecord.id,
     ResidueFactor.factor_min,
     ResidueFactor.factor_mid,
     ResidueFactor.factor_max
 ).subquery()

# Combined volume estimation view
# Uses UNION ALL to combine multiple paths (A, B, C, D), with precedence logic for selection
# Use row_number with stable ordering on business key to ensure deterministic IDs
# Use offsets for branch IDs to ensure global uniqueness:
# - Path A (production_based):  0
# - Path B (census_based):      10,000,000
# - Path C (commodity_direct):  20,000,000
# - Path D (acreage_based):     30,000,000
mv_biomass_volume_estimate = union_all(
    select(
        func.row_number().over(
            order_by=(
                production_based_volumes.c.resource_id,
                production_based_volumes.c.geoid,
                production_based_volumes.c.dataset_year,
                production_based_volumes.c.volume_source,
                production_based_volumes.c.resource_name,
                production_based_volumes.c.county,
                production_based_volumes.c.state
            )
        ).label("id"),
        production_based_volumes.c.resource_id,
        production_based_volumes.c.resource_name,
        production_based_volumes.c.geoid,
        production_based_volumes.c.county,
        production_based_volumes.c.county_fips,
        production_based_volumes.c.state,
        production_based_volumes.c.dataset_year,
        cast(production_based_volumes.c.primary_product_volume, Numeric).label("production_volume"),
        cast(production_based_volumes.c.county_crop_acres, Numeric).label("county_crop_acres"),
        cast(production_based_volumes.c.volume_unit, String).label("production_unit"),
        cast(production_based_volumes.c.factor_min, Numeric).label("factor_min"),
        cast(production_based_volumes.c.factor_mid, Numeric).label("factor_mid"),
        cast(production_based_volumes.c.factor_max, Numeric).label("factor_max"),
        cast(production_based_volumes.c.estimated_residue_volume_min, Numeric).label("estimated_residue_volume_min"),
        cast(production_based_volumes.c.estimated_residue_volume_mid, Numeric).label("estimated_residue_volume_mid"),
        cast(production_based_volumes.c.estimated_residue_volume_max, Numeric).label("estimated_residue_volume_max"),
        cast(production_based_volumes.c.volume_source, String).label("volume_source"),
        cast(production_based_volumes.c.biomass_unit, String).label("biomass_unit")
    ).select_from(production_based_volumes),
    select(
        (func.row_number().over(
            order_by=(
                census_based_volumes.c.resource_id,
                census_based_volumes.c.geoid,
                census_based_volumes.c.dataset_year,
                census_based_volumes.c.volume_source,
                census_based_volumes.c.resource_name,
                census_based_volumes.c.county,
                census_based_volumes.c.state
            )
        ) + 10000000).label("id"),
        census_based_volumes.c.resource_id,
        census_based_volumes.c.resource_name,
        census_based_volumes.c.geoid,
        census_based_volumes.c.county,
        census_based_volumes.c.county_fips,
        census_based_volumes.c.state,
        census_based_volumes.c.dataset_year,
        cast(census_based_volumes.c.bearing_acres, Numeric).label("production_volume"),
        cast(census_based_volumes.c.county_crop_acres, Numeric).label("county_crop_acres"),
        cast(census_based_volumes.c.volume_unit, String).label("production_unit"),
        cast(literal(None), Numeric).label("factor_min"),
        cast(literal(None), Numeric).label("factor_mid"),
        cast(literal(None), Numeric).label("factor_max"),
        cast(census_based_volumes.c.estimated_residue_volume_min, Numeric).label("estimated_residue_volume_min"),
        cast(census_based_volumes.c.estimated_residue_volume_mid, Numeric).label("estimated_residue_volume_mid"),
        cast(census_based_volumes.c.estimated_residue_volume_max, Numeric).label("estimated_residue_volume_max"),
        cast(census_based_volumes.c.volume_source, String).label("volume_source"),
        cast(census_based_volumes.c.biomass_unit, String).label("biomass_unit")
    ).select_from(census_based_volumes),
    select(
        (func.row_number().over(
            order_by=(
                commodity_direct_volumes.c.resource_id,
                commodity_direct_volumes.c.geoid,
                commodity_direct_volumes.c.dataset_year,
                commodity_direct_volumes.c.volume_source,
                commodity_direct_volumes.c.resource_name,
                commodity_direct_volumes.c.county,
                commodity_direct_volumes.c.state
            )
        ) + 20000000).label("id"),
        commodity_direct_volumes.c.resource_id,
        commodity_direct_volumes.c.resource_name,
        commodity_direct_volumes.c.geoid,
        commodity_direct_volumes.c.county,
        commodity_direct_volumes.c.county_fips,
        commodity_direct_volumes.c.state,
        commodity_direct_volumes.c.dataset_year,
        cast(commodity_direct_volumes.c.primary_product_volume, Numeric).label("production_volume"),
        cast(commodity_direct_volumes.c.county_crop_acres, Numeric).label("county_crop_acres"),
        cast(commodity_direct_volumes.c.volume_unit, String).label("production_unit"),
        cast(commodity_direct_volumes.c.factor_min, Numeric).label("factor_min"),
        cast(commodity_direct_volumes.c.factor_mid, Numeric).label("factor_mid"),
        cast(commodity_direct_volumes.c.factor_max, Numeric).label("factor_max"),
        cast(commodity_direct_volumes.c.estimated_residue_volume_min, Numeric).label("estimated_residue_volume_min"),
        cast(commodity_direct_volumes.c.estimated_residue_volume_mid, Numeric).label("estimated_residue_volume_mid"),
        cast(commodity_direct_volumes.c.estimated_residue_volume_max, Numeric).label("estimated_residue_volume_max"),
        cast(commodity_direct_volumes.c.volume_source, String).label("volume_source"),
        cast(commodity_direct_volumes.c.biomass_unit, String).label("biomass_unit")
    ).select_from(commodity_direct_volumes),
    select(
        (func.row_number().over(
            order_by=(
                acreage_based_volumes.c.resource_id,
                acreage_based_volumes.c.geoid,
                acreage_based_volumes.c.dataset_year,
                acreage_based_volumes.c.volume_source,
                acreage_based_volumes.c.resource_name,
                acreage_based_volumes.c.county,
                acreage_based_volumes.c.state
            )
        ) + 30000000).label("id"),
        acreage_based_volumes.c.resource_id,
        acreage_based_volumes.c.resource_name,
        acreage_based_volumes.c.geoid,
        acreage_based_volumes.c.county,
        acreage_based_volumes.c.county_fips,
        acreage_based_volumes.c.state,
        acreage_based_volumes.c.dataset_year,
        cast(acreage_based_volumes.c.county_crop_acres, Numeric).label("production_volume"),
        cast(acreage_based_volumes.c.county_crop_acres, Numeric).label("county_crop_acres"),
        cast(literal("acres"), String).label("production_unit"),
        cast(acreage_based_volumes.c.factor_min, Numeric).label("factor_min"),
        cast(acreage_based_volumes.c.factor_mid, Numeric).label("factor_mid"),
        cast(acreage_based_volumes.c.factor_max, Numeric).label("factor_max"),
        cast(acreage_based_volumes.c.estimated_residue_volume_min, Numeric).label("estimated_residue_volume_min"),
        cast(acreage_based_volumes.c.estimated_residue_volume_mid, Numeric).label("estimated_residue_volume_mid"),
        cast(acreage_based_volumes.c.estimated_residue_volume_max, Numeric).label("estimated_residue_volume_max"),
        cast(acreage_based_volumes.c.volume_source, String).label("volume_source"),
        cast(acreage_based_volumes.c.biomass_unit, String).label("biomass_unit")
    ).select_from(acreage_based_volumes),
    select(
        (func.row_number().over(
            order_by=(
                census_production_based_volumes.c.resource_id,
                census_production_based_volumes.c.geoid,
                census_production_based_volumes.c.dataset_year,
                census_production_based_volumes.c.volume_source,
                census_production_based_volumes.c.resource_name,
                census_production_based_volumes.c.county,
                census_production_based_volumes.c.state
            )
        ) + 40000000).label("id"),
        census_production_based_volumes.c.resource_id,
        census_production_based_volumes.c.resource_name,
        census_production_based_volumes.c.geoid,
        census_production_based_volumes.c.county,
        census_production_based_volumes.c.county_fips,
        census_production_based_volumes.c.state,
        census_production_based_volumes.c.dataset_year,
        cast(census_production_based_volumes.c.primary_product_volume, Numeric).label("production_volume"),
        cast(census_production_based_volumes.c.county_crop_acres, Numeric).label("county_crop_acres"),
        cast(census_production_based_volumes.c.volume_unit, String).label("production_unit"),
        cast(census_production_based_volumes.c.factor_min, Numeric).label("factor_min"),
        cast(census_production_based_volumes.c.factor_mid, Numeric).label("factor_mid"),
        cast(census_production_based_volumes.c.factor_max, Numeric).label("factor_max"),
        cast(census_production_based_volumes.c.estimated_residue_volume_min, Numeric).label("estimated_residue_volume_min"),
        cast(census_production_based_volumes.c.estimated_residue_volume_mid, Numeric).label("estimated_residue_volume_mid"),
        cast(census_production_based_volumes.c.estimated_residue_volume_max, Numeric).label("estimated_residue_volume_max"),
        cast(census_production_based_volumes.c.volume_source, String).label("volume_source"),
        cast(census_production_based_volumes.c.biomass_unit, String).label("biomass_unit")
    ).select_from(census_production_based_volumes)
)
