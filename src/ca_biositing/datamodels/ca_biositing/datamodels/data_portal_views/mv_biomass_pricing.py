"""
mv_biomass_pricing.py

Market pricing data from USDA survey records aggregated by commodity and location.

Required index:
    CREATE UNIQUE INDEX idx_mv_biomass_pricing_id ON data_portal.mv_biomass_pricing (id)
"""

from sqlalchemy import select, func, cast, String, and_

from ca_biositing.datamodels.models.general_analysis.observation import Observation
from ca_biositing.datamodels.models.methods_parameters_units.parameter import Parameter
from ca_biositing.datamodels.models.methods_parameters_units.unit import Unit
from ca_biositing.datamodels.models.external_data.usda_survey import UsdaMarketRecord, UsdaMarketReport
from ca_biositing.datamodels.models.external_data.usda_census import UsdaCommodity
from ca_biositing.datamodels.models.places.location_address import LocationAddress
from ca_biositing.datamodels.models.places.place import Place
from ca_biositing.datamodels.models.resource_information.resource_price_record import ResourcePriceRecord
from ca_biositing.datamodels.models.resource_information.resource import Resource
from ca_biositing.datamodels.models.external_data.resource_usda_commodity_map import ResourceUsdaCommodityMap


# Aggregating market pricing from USDA survey data and resource price records
# Parameter synonyms (lowercase)
price_param_names = (
    "price received",
    "price paid",
    "price avg",
    "price production weighted average",
    "price production weighted avg",
    "weighted_average_price",
    "price",
    "weighted average price",
)

pricing_obs = select(
    Observation.record_id,
    func.avg(Observation.value).label("price_avg"),
    func.min(Observation.value).label("price_min"),
    func.max(Observation.value).label("price_max"),
    Unit.name.label("price_unit")
).join(Parameter, Observation.parameter_id == Parameter.id)\
 .outerjoin(Unit, Observation.unit_id == Unit.id)\
 .where(and_(func.lower(Parameter.name).in_(price_param_names), Observation.value != None, Observation.record_type.in_("usda_market_record", "resource_price_record")))\
 .group_by(Observation.record_id, Unit.name).subquery()

# USDA-derived rows but only where the USDA commodity maps to a Resource (exclude primary-ag-only commodities)
usda_sel = select(
    UsdaCommodity.name.label("commodity_name"),
    Place.geoid,
    Place.county_name.label("county"),
    Place.state_name.label("state"),
    UsdaMarketRecord.report_date,
    UsdaMarketRecord.market_type_category,
    UsdaMarketRecord.sale_type,
    pricing_obs.c.price_min,
    pricing_obs.c.price_max,
    pricing_obs.c.price_avg,
    pricing_obs.c.price_unit,
).select_from(UsdaMarketRecord)\
 .join(UsdaMarketReport, UsdaMarketRecord.report_id == UsdaMarketReport.id)\
 .join(UsdaCommodity, UsdaMarketRecord.commodity_id == UsdaCommodity.id)\
 .outerjoin(LocationAddress, UsdaMarketReport.office_city_id == LocationAddress.id)\
 .outerjoin(Place, LocationAddress.geography_id == Place.geoid)\
 .join(ResourceUsdaCommodityMap, UsdaCommodity.id == ResourceUsdaCommodityMap.usda_commodity_id)\
 .where(ResourceUsdaCommodityMap.resource_id != None)\
 .outerjoin(pricing_obs, cast(UsdaMarketRecord.id, String) == pricing_obs.c.record_id)

# Resource-sourced price records (e.g., county ag reports / ETL resource_price_record)
resource_sel = select(
    Resource.name.label("commodity_name"),
    ResourcePriceRecord.geoid,
    Place.county_name.label("county"),
    Place.state_name.label("state"),
    ResourcePriceRecord.report_start_date.label("report_date"),
    cast(None, String).label("market_type_category"),
    ResourcePriceRecord.freight_terms.label("sale_type"),
    pricing_obs.c.price_min,
    pricing_obs.c.price_max,
    pricing_obs.c.price_avg,
    pricing_obs.c.price_unit,
).select_from(ResourcePriceRecord)\
 .outerjoin(Resource, ResourcePriceRecord.resource_id == Resource.id)\
 .outerjoin(Place, ResourcePriceRecord.geoid == Place.geoid)\
 .outerjoin(pricing_obs, cast(ResourcePriceRecord.id, String) == pricing_obs.c.record_id)

# Combine USDA-derived and resource-derived pricing into one canonical set
combined = usda_sel.union_all(resource_sel).subquery()

mv_biomass_pricing = select(
    func.row_number().over(order_by=combined.c.commodity_name).label("id"),
    combined.c.commodity_name,
    combined.c.geoid,
    combined.c.county,
    combined.c.state,
    combined.c.report_date,
    combined.c.market_type_category,
    combined.c.sale_type,
    combined.c.price_min,
    combined.c.price_max,
    combined.c.price_avg,
    combined.c.price_unit,
).select_from(combined)
