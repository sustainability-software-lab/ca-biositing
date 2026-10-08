"""
mv_usda_county_production.py

USDA Census-based county production data bridged with BioCirV resources and residue factors.

No resource/provider/QC filtering (EXCLUDED_RESOURCES, EXCLUDED_PROVIDERS,
get_qc_status_filter, etc. from common.py) is applied here. This is
deliberate: this view bridges raw USDA Census production data to BioCirV
resources via ResourceUsdaCommodityMap, and that external data isn't subject
to the lab-analysis QC/resource/provider exclusions that gate the
analysis-facing views. The only filter applied is the production-year
cutoff (get_min_year_filter / MIN_PRODUCTION_DATA_YEAR).

Required index:
    CREATE UNIQUE INDEX idx_mv_usda_county_production_id ON data_portal.mv_usda_county_production (id)
"""

from sqlalchemy import select, func, cast, String, and_, case, literal

from ca_biositing.datamodels.data_portal_views.common import get_min_year_filter
from ca_biositing.datamodels.models.resource_information.resource import Resource
from ca_biositing.datamodels.models.resource_information.primary_ag_product import PrimaryAgProduct
from ca_biositing.datamodels.models.resource_information.resource_availability import ResourceAvailability
from ca_biositing.datamodels.models.external_data.usda_census import UsdaCensusRecord
from ca_biositing.datamodels.models.external_data.resource_usda_commodity_map import ResourceUsdaCommodityMap
from ca_biositing.datamodels.models.general_analysis.observation import Observation
from ca_biositing.datamodels.models.methods_parameters_units.parameter import Parameter
from ca_biositing.datamodels.models.methods_parameters_units.unit import Unit
from ca_biositing.datamodels.models.places.place import Place


# Aggregating census observations at record_id grain
census_obs = select(
    Observation.record_id,
    # Aggregate to record_id grain, picking production and acres
    # For production, we want to capture whatever unit is available if tons isn't there
    func.avg(case((func.lower(Parameter.name) == "production", Observation.value))).label("primary_product_volume"),
    # Capture the unit name for the production value
    func.max(case((func.lower(Parameter.name) == "production", Unit.name))).label("volume_unit"),
    # Filter for 'acres' unit when getting production area
    func.avg(case((and_(
        func.lower(Parameter.name).in_(["area bearing", "area harvested", "area in production"]),
        func.lower(Unit.name) == "acres"
    ), Observation.value))).label("production_acres")
).join(Parameter, Observation.parameter_id == Parameter.id)\
 .outerjoin(Unit, Observation.unit_id == Unit.id)\
 .where(Observation.record_type == "usda_census_record")\
 .group_by(Observation.record_id).subquery()

# Availability fallback logic: prefer county geoid, fallback to statewide '06000'
ra_fallback = select(
    ResourceAvailability.resource_id,
    ResourceAvailability.geoid,
    ResourceAvailability.residue_factor_dry_tons_acre
).subquery()

mv_usda_county_production = select(
    func.row_number().over(order_by=(Resource.id, Place.geoid, UsdaCensusRecord.year)).label("id"),
    Resource.id.label("resource_id"),
    Resource.name.label("resource_name"),
    PrimaryAgProduct.name.label("primary_ag_product"),
    Place.geoid,
    Place.county_name.label("county"),
    Place.state_name.label("state"),
    UsdaCensusRecord.year.label("dataset_year"),
    func.avg(census_obs.c.primary_product_volume).label("primary_product_volume"),
    func.max(census_obs.c.volume_unit).label("volume_unit"),
    func.avg(census_obs.c.production_acres).label("production_acres"),
    literal(None).label("known_biomass_volume"),
    # Use COALESCE to fallback to state-level residue factor if county-level is missing
    (func.avg(census_obs.c.production_acres) * func.coalesce(
        func.max(case((ra_fallback.c.geoid == Place.geoid, ra_fallback.c.residue_factor_dry_tons_acre))),
        func.max(case((ra_fallback.c.geoid == '06000', ra_fallback.c.residue_factor_dry_tons_acre)))
    )).label("calculated_estimate_volume"),
    literal("dry_tons_acre").label("biomass_unit")
).select_from(UsdaCensusRecord)\
 .join(ResourceUsdaCommodityMap, UsdaCensusRecord.commodity_code == ResourceUsdaCommodityMap.usda_commodity_id)\
 .join(Resource, ResourceUsdaCommodityMap.resource_id == Resource.id)\
 .join(PrimaryAgProduct, Resource.primary_ag_product_id == PrimaryAgProduct.id)\
 .join(Place, UsdaCensusRecord.geoid == Place.geoid)\
 .join(census_obs, cast(UsdaCensusRecord.id, String) == census_obs.c.record_id)\
 .outerjoin(ra_fallback, Resource.id == ra_fallback.c.resource_id)\
 .where(get_min_year_filter(UsdaCensusRecord.year))\
 .group_by(Resource.id, Resource.name, PrimaryAgProduct.name, Place.geoid, Place.county_name, Place.state_name, UsdaCensusRecord.year)
