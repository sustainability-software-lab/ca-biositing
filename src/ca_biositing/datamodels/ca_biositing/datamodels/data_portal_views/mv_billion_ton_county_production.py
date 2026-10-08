"""
mv_billion_ton_county_production.py

DEPRECATED/LEGACY VIEW - County-level biomass production data from Billion Ton 2023 dataset.

Note: Will NOT be included in API responses (legacy view only).
This view is retained for reference but has been superseded by updated production views
that integrate additional qualitative and quantitative data sources.

No resource/provider/QC filtering (EXCLUDED_RESOURCES, EXCLUDED_PROVIDERS,
get_qc_status_filter, etc. from common.py) is applied here. This is
deliberate, not an oversight: this view surfaces raw Billion Ton 2023
government data for reference, and it is excluded from API responses
entirely (see note above), so the data-quality filters that gate the
analysis-facing views don't apply.

Required index:
    CREATE UNIQUE INDEX idx_mv_billion_ton_county_production_id ON data_portal.mv_billion_ton_county_production (id)
"""

from sqlalchemy import select, func, literal
from sqlalchemy.orm import aliased

from ca_biositing.datamodels.models.resource_information.resource import Resource, ResourceClass
from ca_biositing.datamodels.models.external_data.billion_ton import BillionTon2023Record
from ca_biositing.datamodels.models.methods_parameters_units.unit import Unit
from ca_biositing.datamodels.models.places.place import Place


EU = aliased(Unit, name="eu")

mv_billion_ton_county_production = select(
    func.row_number().over(order_by=(BillionTon2023Record.resource_id, Place.geoid, BillionTon2023Record.scenario_name, BillionTon2023Record.price_offered_usd)).label("id"),
    BillionTon2023Record.resource_id,
    Resource.name.label("resource_name"),
    ResourceClass.name.label("resource_class"),
    Place.geoid,
    Place.county_name.label("county"),
    Place.state_name.label("state"),
    BillionTon2023Record.scenario_name.label("scenario"),
    BillionTon2023Record.price_offered_usd,
    BillionTon2023Record.production,
    Unit.name.label("production_unit"),
    BillionTon2023Record.production_energy_content.label("energy_content"),
    EU.name.label("energy_unit"),
    BillionTon2023Record.product_density_dtpersqmi.label("density_dt_per_sqmi"),
    BillionTon2023Record.county_square_miles,
    literal(2023).label("year")
).select_from(BillionTon2023Record)\
 .join(Resource, BillionTon2023Record.resource_id == Resource.id)\
 .outerjoin(ResourceClass, Resource.resource_class_id == ResourceClass.id)\
 .join(Place, BillionTon2023Record.geoid == Place.geoid)\
 .outerjoin(Unit, BillionTon2023Record.production_unit_id == Unit.id)\
 .outerjoin(EU, BillionTon2023Record.energy_content_unit_id == EU.id)
