"""
mv_volume_estimation.py

Volume estimation views combining production-based and census-based residue calculations.

This module provides dual-path volume estimation:
1. Production-based: county_ag_report_record × residue_factors for most agricultural residues
2. Census-based: USDA census bearing_acres × prune_trim_yield for orchard crops

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


# Path A: Production-based volume estimation
# Uses county_ag_report_record × residue_factors for residue calculation
# Join path: CountyAgReportRecord -> PrimaryAgProduct -> Resource -> ResidueFactor
production_based_volumes = select(
    Resource.id.label("resource_id"),
    Resource.name.label("resource_name"),
    CountyAgReportRecord.geoid,
    Place.county_name.label("county"),
    Place.state_name.label("state"),
    CountyAgReportRecord.data_year.label("dataset_year"),
    CountyAgReportRecord.record_id,
    # Aggregate observations for production volume
    func.avg(case((Parameter.name == "production", Observation.value))).label("primary_product_volume"),
    # Harvested acres for the crop
    func.avg(case((Parameter.name == "harvested acres", Observation.value))).label("county_crop_acres"),
    # Capture unit from observations
    func.max(case((Parameter.name == "production", Unit.name))).label("volume_unit"),
    # Residue factor values
    ResidueFactor.factor_min,
    ResidueFactor.factor_mid,
    ResidueFactor.factor_max,
    # Calculated volumes (min, mid, max)
    (func.avg(case((Parameter.name == "production", Observation.value))) * ResidueFactor.factor_min).label("estimated_residue_volume_min"),
    (func.avg(case((Parameter.name == "production", Observation.value))) * ResidueFactor.factor_mid).label("estimated_residue_volume_mid"),
    (func.avg(case((Parameter.name == "production", Observation.value))) * ResidueFactor.factor_max).label("estimated_residue_volume_max"),
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
     get_resource_filter(Resource)
 ))\
 .group_by(
     Resource.id,
     Resource.name,
     CountyAgReportRecord.geoid,
     Place.county_name,
     Place.state_name,
     CountyAgReportRecord.data_year,
     CountyAgReportRecord.record_id,
     ResidueFactor.factor_min,
     ResidueFactor.factor_mid,
     ResidueFactor.factor_max
 ).subquery()


# Path B: Census-based volume estimation
# Uses USDA census bearing_acres × prune_trim_yield for orchard crops
census_based_volumes = select(
    Resource.id.label("resource_id"),
    Resource.name.label("resource_name"),
    UsdaCensusRecord.geoid,
    Place.county_name.label("county"),
    Place.state_name.label("state"),
    UsdaCensusRecord.year.label("dataset_year"),
    UsdaCensusRecord.id.label("record_id"),
    # Bearing acres data
    func.avg(Observation.value).label("bearing_acres"),
    func.avg(Observation.value).label("county_crop_acres"),
    literal("acres").label("volume_unit"),
    # Residue factor yield values
    ResidueFactor.prune_trim_yield,
    ResidueFactor.prune_trim_yield_unit_id,
    func.max(Unit.name).label("yield_unit"),
    # Calculated volumes (bearing_acres × prune_trim_yield)
    (func.avg(Observation.value) * ResidueFactor.prune_trim_yield).label("estimated_residue_volume_min"),
    (func.avg(Observation.value) * ResidueFactor.prune_trim_yield).label("estimated_residue_volume_mid"),
    (func.avg(Observation.value) * ResidueFactor.prune_trim_yield).label("estimated_residue_volume_max"),
    literal("census_bearing_acres").label("volume_source"),
    literal("dry_tons").label("biomass_unit")
).select_from(UsdaCensusRecord)\
 .join(UsdaCommodity, UsdaCensusRecord.commodity_code == UsdaCommodity.id)\
 .join(ResourceUsdaCommodityMap, ResourceUsdaCommodityMap.usda_commodity_id == UsdaCommodity.id)\
 .join(Resource, Resource.id == ResourceUsdaCommodityMap.resource_id)\
 .join(ResidueFactor, ResidueFactor.resource_id == Resource.id)\
 .join(Place, UsdaCensusRecord.geoid == Place.geoid)\
 .outerjoin(Observation, and_(Observation.record_id == cast(UsdaCensusRecord.id, String), Observation.record_type == "usda_census_record"))\
 .outerjoin(Unit, ResidueFactor.prune_trim_yield_unit_id == Unit.id)\
 .where(and_(
     ResidueFactor.prune_trim_yield.isnot(None),
     UsdaCensusRecord.year >= 2017,
     get_resource_filter(Resource)
 ))\
 .group_by(
     Resource.id,
     Resource.name,
     UsdaCensusRecord.geoid,
     Place.county_name,
     Place.state_name,
     UsdaCensusRecord.year,
     UsdaCensusRecord.id,
     ResidueFactor.prune_trim_yield,
     ResidueFactor.prune_trim_yield_unit_id
 ).subquery()


# Inline PAP-to-resource mapping for commodity-direct resources
# Based on names to ensure stability across environments:
# - 'almond hulls' (PAP 46)  → 'almond hulls' (Resource 19)
# - 'almond shells' (PAP 74) → 'almond shells' (Resource 5)
# - 'almond meats' (PAP 47)  → 'almond hulls' (Resource 19)
# - 'hay - alfalfa' (PAP 3)  → 'alfalfa' (Resource 24)
# - 'silage - alfalfa' (PAP 28) → 'alfalfa' (Resource 24)
# - 'alfalfa & mixtures' (PAP 78) → 'alfalfa' (Resource 24)
commodity_map = union_all(
    select(literal(46, Integer).label("pap_id"), literal(19, Integer).label("resource_id")),
    select(literal(74, Integer), literal(5, Integer)),
    select(literal(47, Integer), literal(19, Integer)),
    select(literal(3, Integer), literal(24, Integer)),
    select(literal(28, Integer), literal(24, Integer)),
    select(literal(78, Integer), literal(24, Integer))
).subquery("commodity_map")

# Path C: Commodity-direct resource volumes
# For resources (e.g. almond hulls, almond shells) that are themselves tracked
# as primary commodities in county_ag_report_record. The production observation
# value IS the resource volume — no residue factor multiplication needed.
commodity_direct_volumes = select(
    Resource.id.label("resource_id"),
    Resource.name.label("resource_name"),
    CountyAgReportRecord.geoid,
    Place.county_name.label("county"),
    Place.state_name.label("state"),
    CountyAgReportRecord.data_year.label("dataset_year"),
    CountyAgReportRecord.record_id,
    # Aggregate observations for production volume
    func.avg(case((Parameter.name == "production", Observation.value))).label("primary_product_volume"),
    cast(literal(None), Numeric).label("county_crop_acres"),
    # Capture unit from observations
    func.max(case((Parameter.name == "production", Unit.name))).label("volume_unit"),
    # Identity factor (direct measurement)
    cast(literal(None), Numeric).label("factor_min"),
    cast(literal(1.0), Numeric).label("factor_mid"),
    cast(literal(None), Numeric).label("factor_max"),
    # estimated_residue_volume = production value directly (factor = 1)
    func.avg(case((Parameter.name == "production", Observation.value))).label("estimated_residue_volume_min"),
    func.avg(case((Parameter.name == "production", Observation.value))).label("estimated_residue_volume_mid"),
    func.avg(case((Parameter.name == "production", Observation.value))).label("estimated_residue_volume_max"),
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
     get_resource_filter(Resource)
 ))\
 .group_by(
     Resource.id,
     Resource.name,
     CountyAgReportRecord.geoid,
     Place.county_name,
     Place.state_name,
     CountyAgReportRecord.data_year,
     CountyAgReportRecord.record_id,
 ).subquery()


# Combined volume estimation view
# Uses UNION ALL to combine multiple paths (A, B, C), with precedence logic for selection
# Use row_number with stable ordering on business key to ensure deterministic IDs
# Use offsets for branch IDs to ensure global uniqueness:
# - Path A (production_based): 0
# - Path B (census_based): 10,000,000
# - Path C (commodity_direct): 20,000,000
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
    ).select_from(commodity_direct_volumes)
)
