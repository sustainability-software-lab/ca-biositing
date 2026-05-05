"""
mv_biomass_pricing.py

Market pricing data from USDA survey records aggregated by commodity and location.

Required index:
    CREATE UNIQUE INDEX idx_mv_biomass_pricing_id ON data_portal.mv_biomass_pricing (id)
"""

from sqlalchemy import select, func, cast, String, and_

from ca_biositing.datamodels.models.resource_information.resource import Resource
from ca_biositing.datamodels.models.external_data.resource_usda_commodity_map import ResourceUsdaCommodityMap
from ca_biositing.datamodels.models.general_analysis.observation import Observation
from ca_biositing.datamodels.models.methods_parameters_units.parameter import Parameter
from ca_biositing.datamodels.models.methods_parameters_units.unit import Unit
from ca_biositing.datamodels.models.external_data.usda_survey import UsdaMarketRecord, UsdaMarketReport
from ca_biositing.datamodels.models.external_data.usda_census import UsdaCommodity
from ca_biositing.datamodels.models.data_sources_metadata.data_source import DataSource
from ca_biositing.datamodels.models.places.location_address import LocationAddress
from ca_biositing.datamodels.models.places.place import Place


# Aggregating market pricing from USDA survey data
pricing_obs = select(
    Observation.record_id,
    func.avg(Observation.value).label("price_avg"),
    func.min(Observation.value).label("price_min"),
    func.max(Observation.value).label("price_max"),
    Unit.name.label("price_unit")
).join(Parameter, Observation.parameter_id == Parameter.id)\
 .outerjoin(Unit, Observation.unit_id == Unit.id)\
 .where(and_(Observation.record_type == "usda_market_record", func.lower(Parameter.name) == "price received"))\
 .group_by(Observation.record_id, Unit.name).subquery()

mv_biomass_pricing = select(
     func.row_number().over(order_by=UsdaMarketRecord.id).label("id"),
     Resource.id.label("resource_id"),
     Resource.name.label("resource_name"),
     Place.geoid,
     Place.county_name.label("county"),
     Place.state_name.label("state"),
     UsdaMarketRecord.report_date,
     DataSource.name.label("report_source"),
     UsdaMarketRecord.market_type_category,
     UsdaMarketRecord.sale_type,
     pricing_obs.c.price_min,
     pricing_obs.c.price_max,
     pricing_obs.c.price_avg,
     pricing_obs.c.price_unit
 ).select_from(UsdaMarketRecord)\
  .join(UsdaMarketReport, UsdaMarketRecord.report_id == UsdaMarketReport.id)\
  .join(UsdaCommodity, UsdaMarketRecord.commodity_id == UsdaCommodity.id)\
  .outerjoin(DataSource, UsdaMarketReport.source_id == DataSource.id)\
  .join(ResourceUsdaCommodityMap, ResourceUsdaCommodityMap.usda_commodity_id == UsdaCommodity.id)\
  .join(Resource, Resource.id == ResourceUsdaCommodityMap.resource_id)\
  .outerjoin(LocationAddress, UsdaMarketReport.office_city_id == LocationAddress.id)\
  .outerjoin(Place, LocationAddress.geography_id == Place.geoid)\
  .join(pricing_obs, cast(UsdaMarketRecord.id, String) == pricing_obs.c.record_id)
