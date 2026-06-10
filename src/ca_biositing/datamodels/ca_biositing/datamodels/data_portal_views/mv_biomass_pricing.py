"""mv_biomass_pricing.py

Market pricing data combining USDA market records and `resource_price_record`.

Required index:
    CREATE UNIQUE INDEX idx_mv_biomass_pricing_id ON data_portal.mv_biomass_pricing (id)
"""

from sqlalchemy import select, func, cast, String, and_

from ca_biositing.datamodels.data_portal_views.common import get_resource_filter
from ca_biositing.datamodels.models.data_sources_metadata.data_source import DataSource
from ca_biositing.datamodels.models.external_data.resource_usda_commodity_map import (
    ResourceUsdaCommodityMap,
)
from ca_biositing.datamodels.models.external_data.usda_census import UsdaCommodity
from ca_biositing.datamodels.models.external_data.usda_survey import (
    UsdaMarketRecord,
    UsdaMarketReport,
)
from ca_biositing.datamodels.models.general_analysis.observation import Observation
from ca_biositing.datamodels.models.methods_parameters_units.parameter import Parameter
from ca_biositing.datamodels.models.methods_parameters_units.unit import Unit
from ca_biositing.datamodels.models.places.location_address import LocationAddress
from ca_biositing.datamodels.models.places.place import Place
from ca_biositing.datamodels.models.resource_information.resource import Resource
from ca_biositing.datamodels.models.resource_information.resource_price_record import (
    ResourcePriceRecord,
)


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
 .where(and_(
     func.lower(Parameter.name).in_(price_param_names),
     Observation.value.is_not(None),
     Observation.record_type.in_(["usda_market_record", "resource_price_record"]),
 ))\
 .group_by(Observation.record_id, Unit.name).subquery()

# USDA-derived rows but only where the USDA commodity maps to a Resource
# (exclude primary-ag-only commodities)
usda_sel = select(
    Resource.id.label("resource_id"),
    Resource.name.label("resource_name"),
    Place.geoid,
    Place.county_name.label("county"),
    Place.county_fips,
    Place.state_name.label("state"),
    UsdaMarketRecord.report_date,
    DataSource.name.label("report_source"),
    UsdaMarketRecord.market_type_category,
    UsdaMarketRecord.sale_type,
    pricing_obs.c.price_min,
    pricing_obs.c.price_max,
    pricing_obs.c.price_avg,
    pricing_obs.c.price_unit,
).select_from(UsdaMarketRecord)\
 .join(UsdaMarketReport, UsdaMarketRecord.report_id == UsdaMarketReport.id)\
 .join(UsdaCommodity, UsdaMarketRecord.commodity_id == UsdaCommodity.id)\
 .outerjoin(DataSource, UsdaMarketReport.source_id == DataSource.id)\
 .outerjoin(LocationAddress, UsdaMarketReport.office_city_id == LocationAddress.id)\
 .outerjoin(Place, LocationAddress.geography_id == Place.geoid)\
 .join(ResourceUsdaCommodityMap, UsdaCommodity.id == ResourceUsdaCommodityMap.usda_commodity_id)\
 .join(Resource, Resource.id == ResourceUsdaCommodityMap.resource_id)\
 .outerjoin(pricing_obs, cast(UsdaMarketRecord.id, String) == pricing_obs.c.record_id)\
 .where(and_(
     ResourceUsdaCommodityMap.resource_id.is_not(None),
     get_resource_filter(Resource),
 ))

# Resource-sourced price records (e.g., county ag reports / ETL resource_price_record)
resource_sel = select(
    Resource.id.label("resource_id"),
    Resource.name.label("resource_name"),
    ResourcePriceRecord.geoid,
    Place.county_name.label("county"),
    Place.county_fips,
    Place.state_name.label("state"),
    ResourcePriceRecord.report_start_date.label("report_date"),
    DataSource.name.label("report_source"),
    cast(None, String).label("market_type_category"),
    ResourcePriceRecord.freight_terms.label("sale_type"),
    pricing_obs.c.price_min,
    pricing_obs.c.price_max,
    pricing_obs.c.price_avg,
    pricing_obs.c.price_unit,
).select_from(ResourcePriceRecord)\
 .join(Resource, ResourcePriceRecord.resource_id == Resource.id)\
 .outerjoin(DataSource, ResourcePriceRecord.source_id == DataSource.id)\
 .outerjoin(Place, ResourcePriceRecord.geoid == Place.geoid)\
 .outerjoin(pricing_obs, cast(ResourcePriceRecord.id, String) == pricing_obs.c.record_id)\
 .where(get_resource_filter(Resource))

# Combine USDA-derived and resource-derived pricing into one canonical set
combined = usda_sel.union_all(resource_sel).subquery()

mv_biomass_pricing = select(
    func.row_number().over(order_by=combined.c.resource_id).label("id"),
    combined.c.resource_id,
    combined.c.resource_name,
    combined.c.geoid,
    combined.c.county,
    combined.c.county_fips,
    combined.c.state,
    combined.c.report_date,
    combined.c.report_source,
    combined.c.market_type_category,
    combined.c.sale_type,
    combined.c.price_min,
    combined.c.price_max,
    combined.c.price_avg,
    combined.c.price_unit,
).select_from(combined)
