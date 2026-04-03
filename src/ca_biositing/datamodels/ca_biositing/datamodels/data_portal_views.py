from sqlalchemy import select, func, union_all, literal, case, cast, String, Integer, Numeric, Boolean, and_, or_, Text, Float, ARRAY, text
from sqlalchemy.dialects.postgresql import array as pg_array
from sqlalchemy.orm import aliased
from sqlalchemy.sql import expression
from ca_biositing.datamodels.models.resource_information.resource import Resource, ResourceClass, ResourceSubclass, ResourceMorphology
from ca_biositing.datamodels.models.resource_information.primary_ag_product import PrimaryAgProduct
from ca_biositing.datamodels.models.external_data.billion_ton import BillionTon2023Record
from ca_biositing.datamodels.models.general_analysis.observation import Observation
from ca_biositing.datamodels.models.methods_parameters_units.parameter import Parameter
from ca_biositing.datamodels.models.methods_parameters_units.unit import Unit
from ca_biositing.datamodels.models.methods_parameters_units.method import Method
from ca_biositing.datamodels.models.places.place import Place
from ca_biositing.datamodels.models.resource_information.resource_availability import ResourceAvailability
from ca_biositing.datamodels.models.resource_information.resource_storage_record import ResourceStorageRecord
from ca_biositing.datamodels.models.resource_information.resource_transport_record import ResourceTransportRecord
from ca_biositing.datamodels.models.resource_information.resource_price_record import ResourcePriceRecord
from ca_biositing.datamodels.models.resource_information.resource_end_use_record import ResourceEndUseRecord
from ca_biositing.datamodels.models.aim1_records.compositional_record import CompositionalRecord
from ca_biositing.datamodels.models.aim1_records.proximate_record import ProximateRecord
from ca_biositing.datamodels.models.aim1_records.ultimate_record import UltimateRecord
from ca_biositing.datamodels.models.aim1_records.xrf_record import XrfRecord
from ca_biositing.datamodels.models.aim1_records.icp_record import IcpRecord
from ca_biositing.datamodels.models.aim1_records.calorimetry_record import CalorimetryRecord
from ca_biositing.datamodels.models.aim1_records.xrd_record import XrdRecord
from ca_biositing.datamodels.models.aim1_records.ftnir_record import FtnirRecord
from ca_biositing.datamodels.models.aim2_records.fermentation_record import FermentationRecord
from ca_biositing.datamodels.models.aim2_records.strain import Strain
from ca_biositing.datamodels.models.aim2_records.gasification_record import GasificationRecord
from ca_biositing.datamodels.models.experiment_equipment.decon_vessel import DeconVessel
from ca_biositing.datamodels.models.aim2_records.pretreatment_record import PretreatmentRecord
from ca_biositing.datamodels.models.external_data.usda_survey import UsdaMarketRecord, UsdaMarketReport
from ca_biositing.datamodels.models.external_data.usda_census import UsdaCensusRecord, UsdaCommodity
from ca_biositing.datamodels.models.external_data.resource_usda_commodity_map import ResourceUsdaCommodityMap
from ca_biositing.datamodels.models.places.location_address import LocationAddress
from ca_biositing.datamodels.models.field_sampling.field_sample import FieldSample
from ca_biositing.datamodels.models.people.provider import Provider
from ca_biositing.datamodels.models.sample_preparation.prepared_sample import PreparedSample

# 4. mv_biomass_availability
# Aggregating to one row per resource
mv_biomass_availability = select(
    Resource.id.label("resource_id"),
    Resource.name.label("resource_name"),
    func.min(ResourceAvailability.from_month).label("from_month"),
    func.max(ResourceAvailability.to_month).label("to_month"),
    func.bool_or(ResourceAvailability.year_round).label("year_round"),
    func.avg(ResourceAvailability.residue_factor_dry_tons_acre).label("dry_tons_per_acre"),
    func.avg(ResourceAvailability.residue_factor_wet_tons_acre).label("wet_tons_per_acre")
).select_from(ResourceAvailability)\
 .join(Resource, ResourceAvailability.resource_id == Resource.id)\
 .group_by(Resource.id, Resource.name).subquery()

# 1. mv_biomass_search

# Subquery for analytical averages (moisture, ash, lignin, sugar)
# Sugar = glucose + xylose
analysis_metrics = select(
    Observation.record_id,
    Observation.record_type,
    Parameter.name.label("parameter"),
    Observation.value
).join(Parameter, Observation.parameter_id == Parameter.id).subquery()

# Map record_id to resource_id across all analytical types
resource_analysis_map = union_all(
    select(CompositionalRecord.resource_id, CompositionalRecord.record_id, literal("compositional analysis").label("type")),
    select(ProximateRecord.resource_id, ProximateRecord.record_id, literal("proximate analysis").label("type")),
    select(UltimateRecord.resource_id, UltimateRecord.record_id, literal("ultimate analysis").label("type")),
    select(XrfRecord.resource_id, XrfRecord.record_id, literal("xrf analysis").label("type")),
    select(IcpRecord.resource_id, IcpRecord.record_id, literal("icp analysis").label("type")),
    select(CalorimetryRecord.resource_id, CalorimetryRecord.record_id, literal("calorimetry analysis").label("type")),
    select(XrdRecord.resource_id, XrdRecord.record_id, literal("xrd analysis").label("type")),
    select(FtnirRecord.resource_id, FtnirRecord.record_id, literal("ftnir analysis").label("type")),
    select(FermentationRecord.resource_id, FermentationRecord.record_id, literal("fermentation").label("type")),
    select(GasificationRecord.resource_id, GasificationRecord.record_id, literal("gasification").label("type")),
    select(PretreatmentRecord.resource_id, PretreatmentRecord.record_id, literal("pretreatment").label("type"))
).subquery()

carbon_avg_expr = func.avg(case((
    and_(
        resource_analysis_map.c.type == "ultimate analysis",
        func.lower(analysis_metrics.c.parameter) == "carbon"
    ),
    analysis_metrics.c.value
)))
hydrogen_avg_expr = func.avg(case((
    and_(
        resource_analysis_map.c.type == "ultimate analysis",
        func.lower(analysis_metrics.c.parameter) == "hydrogen"
    ),
    analysis_metrics.c.value
)))
nitrogen_avg_expr = func.avg(case((
    and_(
        resource_analysis_map.c.type == "ultimate analysis",
        func.lower(analysis_metrics.c.parameter) == "nitrogen"
    ),
    analysis_metrics.c.value
)))
cn_ratio_expr = case(
    (
        and_(
            carbon_avg_expr.is_not(None),
            nitrogen_avg_expr.is_not(None),
            nitrogen_avg_expr != 0
        ),
        carbon_avg_expr / nitrogen_avg_expr
    ),
    else_=None
)

resource_metrics = select(
    resource_analysis_map.c.resource_id,
    func.avg(case((analysis_metrics.c.parameter == "moisture", analysis_metrics.c.value))).label("moisture_percent"),
    func.avg(case((analysis_metrics.c.parameter == "ash", analysis_metrics.c.value))).label("ash_percent"),
    # Lignin content = sum of averages of lignin and lignin+
    # Returns NULL if neither parameter is present for the resource
    case(
        (
            or_(
                func.avg(case((analysis_metrics.c.parameter == "lignin", analysis_metrics.c.value))).is_not(None),
                func.avg(case((analysis_metrics.c.parameter == "lignin+", analysis_metrics.c.value))).is_not(None)
            ),
            func.coalesce(func.avg(case((analysis_metrics.c.parameter == "lignin", analysis_metrics.c.value))), 0) +
            func.coalesce(func.avg(case((analysis_metrics.c.parameter == "lignin+", analysis_metrics.c.value))), 0)
        ),
        else_=None
    ).label("lignin_percent"),
    # Sugar content = sum of averages of glucose and xylose
    # Returns NULL if neither parameter is present for the resource
    case(
        (
            or_(
                func.avg(case((analysis_metrics.c.parameter == "glucose", analysis_metrics.c.value))).is_not(None),
                func.avg(case((analysis_metrics.c.parameter == "xylose", analysis_metrics.c.value))).is_not(None)
            ),
            func.coalesce(func.avg(case((analysis_metrics.c.parameter == "glucose", analysis_metrics.c.value))), 0) +
            func.coalesce(func.avg(case((analysis_metrics.c.parameter == "xylose", analysis_metrics.c.value))), 0)
        ),
        else_=None
    ).label("sugar_content_percent"),
    carbon_avg_expr.label("carbon_percent"),
    hydrogen_avg_expr.label("hydrogen_percent"),
    cn_ratio_expr.label("cn_ratio"),
    # Flags
    func.bool_or(resource_analysis_map.c.type == "proximate analysis").label("has_proximate"),
    func.bool_or(resource_analysis_map.c.type == "compositional analysis").label("has_compositional"),
    func.bool_or(resource_analysis_map.c.type == "ultimate analysis").label("has_ultimate"),
    func.bool_or(resource_analysis_map.c.type == "xrf analysis").label("has_xrf"),
    func.bool_or(resource_analysis_map.c.type == "icp analysis").label("has_icp"),
    func.bool_or(resource_analysis_map.c.type == "calorimetry analysis").label("has_calorimetry"),
    func.bool_or(resource_analysis_map.c.type == "xrd analysis").label("has_xrd"),
    func.bool_or(resource_analysis_map.c.type == "ftnir analysis").label("has_ftnir"),
    func.bool_or(resource_analysis_map.c.type == "fermentation").label("has_fermentation"),
    func.bool_or(resource_analysis_map.c.type == "gasification").label("has_gasification"),
    func.bool_or(resource_analysis_map.c.type == "pretreatment").label("has_pretreatment")
).select_from(resource_analysis_map)\
 .join(analysis_metrics, and_(
    func.lower(resource_analysis_map.c.record_id) == func.lower(analysis_metrics.c.record_id),
    resource_analysis_map.c.type == analysis_metrics.c.record_type
 ), isouter=True)\
 .group_by(resource_analysis_map.c.resource_id).subquery()

# Tag thresholds (10th and 90th percentiles) across all biomass data
thresholds = select(
 func.percentile_cont(0.1).within_group(resource_metrics.c.moisture_percent).label("moisture_low"),
 func.percentile_cont(0.9).within_group(resource_metrics.c.moisture_percent).label("moisture_high"),
 func.percentile_cont(0.1).within_group(resource_metrics.c.ash_percent).label("ash_low"),
 func.percentile_cont(0.9).within_group(resource_metrics.c.ash_percent).label("ash_high"),
 func.percentile_cont(0.1).within_group(resource_metrics.c.lignin_percent).label("lignin_low"),
 func.percentile_cont(0.9).within_group(resource_metrics.c.lignin_percent).label("lignin_high"),
 func.percentile_cont(0.1).within_group(resource_metrics.c.sugar_content_percent).label("sugar_low"),
 func.percentile_cont(0.9).within_group(resource_metrics.c.sugar_content_percent).label("sugar_high")
).subquery()

# Resource tags generation
resource_tags = select(
    resource_metrics.c.resource_id,
    func.array_remove(
        pg_array([
            case((resource_metrics.c.moisture_percent <= thresholds.c.moisture_low, "low moisture"), else_=None),
            case((resource_metrics.c.moisture_percent >= thresholds.c.moisture_high, "high moisture"), else_=None),
            case((resource_metrics.c.ash_percent <= thresholds.c.ash_low, "low ash"), else_=None),
            case((resource_metrics.c.ash_percent >= thresholds.c.ash_high, "high ash"), else_=None),
            case((resource_metrics.c.lignin_percent <= thresholds.c.lignin_low, "low lignin"), else_=None),
            case((resource_metrics.c.lignin_percent >= thresholds.c.lignin_high, "high lignin"), else_=None),
            case((resource_metrics.c.sugar_content_percent <= thresholds.c.sugar_low, "low sugar"), else_=None),
            case((resource_metrics.c.sugar_content_percent >= thresholds.c.sugar_high, "high sugar"), else_=None)
        ]),
        None
    ).label("tags")
).select_from(resource_metrics).join(thresholds, literal(True)).subquery()

# Aggregated volume from Billion Ton
agg_vol = select(
    BillionTon2023Record.resource_id,
    func.sum(BillionTon2023Record.production).label("total_annual_volume"),
    func.count(func.distinct(BillionTon2023Record.geoid)).label("county_count"),
    func.max(Unit.name).label("volume_unit")
).join(Unit, BillionTon2023Record.production_unit_id == Unit.id)\
 .group_by(BillionTon2023Record.resource_id).subquery()

storage_notes = select(
    ResourceStorageRecord.resource_id,
    func.string_agg(func.distinct(ResourceStorageRecord.storage_description), literal("; ")).label("storage_notes")
).where(ResourceStorageRecord.resource_id.is_not(None))\
 .group_by(ResourceStorageRecord.resource_id).subquery()

transport_notes = select(
    ResourceTransportRecord.resource_id,
    func.string_agg(func.distinct(ResourceTransportRecord.transport_description), literal("; ")).label("transport_notes")
).where(ResourceTransportRecord.resource_id.is_not(None))\
 .group_by(ResourceTransportRecord.resource_id).subquery()

mv_biomass_search = select(
    Resource.id,
    Resource.name,
    Resource.resource_code,
    Resource.description,
    ResourceClass.name.label("resource_class"),
    ResourceSubclass.name.label("resource_subclass"),
    PrimaryAgProduct.name.label("primary_product"),
    ResourceMorphology.morphology_uri.label("image_url"),
    Resource.uri.label("literature_uri"),
    cast(agg_vol.c.total_annual_volume, Integer).label("total_annual_volume"),
    cast(agg_vol.c.county_count, Integer).label("county_count"),
    agg_vol.c.volume_unit,
    resource_metrics.c.moisture_percent,
    resource_metrics.c.sugar_content_percent,
    resource_metrics.c.ash_percent,
    resource_metrics.c.lignin_percent,
    cast(resource_metrics.c.carbon_percent, Float).label("carbon_percent"),
    cast(resource_metrics.c.hydrogen_percent, Float).label("hydrogen_percent"),
    cast(resource_metrics.c.cn_ratio, Float).label("cn_ratio"),
    func.coalesce(resource_tags.c.tags, cast(pg_array([]), ARRAY(String))).label("tags"),
    mv_biomass_availability.c.from_month.label("season_from_month"),
    mv_biomass_availability.c.to_month.label("season_to_month"),
    mv_biomass_availability.c.year_round,
    storage_notes.c.storage_notes.label("storage_notes"),
    transport_notes.c.transport_notes.label("transport_notes"),
    # Boolean flags
    func.coalesce(resource_metrics.c.has_proximate, False).label("has_proximate"),
    func.coalesce(resource_metrics.c.has_compositional, False).label("has_compositional"),
    func.coalesce(resource_metrics.c.has_ultimate, False).label("has_ultimate"),
    func.coalesce(resource_metrics.c.has_xrf, False).label("has_xrf"),
    func.coalesce(resource_metrics.c.has_icp, False).label("has_icp"),
    func.coalesce(resource_metrics.c.has_calorimetry, False).label("has_calorimetry"),
    func.coalesce(resource_metrics.c.has_xrd, False).label("has_xrd"),
    func.coalesce(resource_metrics.c.has_ftnir, False).label("has_ftnir"),
    func.coalesce(resource_metrics.c.has_fermentation, False).label("has_fermentation"),
    func.coalesce(resource_metrics.c.has_gasification, False).label("has_gasification"),
    func.coalesce(resource_metrics.c.has_pretreatment, False).label("has_pretreatment"),
    case((resource_metrics.c.moisture_percent != None, True), else_=False).label("has_moisture_data"),
    case((resource_metrics.c.sugar_content_percent > 0, True), else_=False).label("has_sugar_data"),
    case((ResourceMorphology.morphology_uri != None, True), else_=False).label("has_image"),
    case((agg_vol.c.total_annual_volume != None, True), else_=False).label("has_volume_data"),
    Resource.created_at,
    Resource.updated_at,
    func.to_tsvector(text("'english'"),
        func.coalesce(Resource.name, '') + ' ' +
        func.coalesce(Resource.description, '') + ' ' +
        func.coalesce(ResourceClass.name, '') + ' ' +
        func.coalesce(ResourceSubclass.name, '') + ' ' +
        func.coalesce(PrimaryAgProduct.name, '')
    ).label("search_vector")
).select_from(Resource)\
 .outerjoin(ResourceClass, Resource.resource_class_id == ResourceClass.id)\
 .outerjoin(ResourceSubclass, Resource.resource_subclass_id == ResourceSubclass.id)\
 .outerjoin(PrimaryAgProduct, Resource.primary_ag_product_id == PrimaryAgProduct.id)\
 .outerjoin(ResourceMorphology, ResourceMorphology.resource_id == Resource.id)\
 .outerjoin(agg_vol, agg_vol.c.resource_id == Resource.id)\
 .outerjoin(resource_metrics, resource_metrics.c.resource_id == Resource.id)\
 .outerjoin(resource_tags, resource_tags.c.resource_id == Resource.id)\
 .outerjoin(mv_biomass_availability, mv_biomass_availability.c.resource_id == Resource.id)\
 .outerjoin(storage_notes, storage_notes.c.resource_id == Resource.id)\
 .outerjoin(transport_notes, transport_notes.c.resource_id == Resource.id)\
 .where(Resource.name != "Sargassum")


# 2. mv_biomass_composition
def get_composition_query(model, analysis_type):
    return select(
        model.resource_id,
        literal(analysis_type).label("analysis_type"),
        Parameter.name.label("parameter_name"),
        Observation.value.label("value"),
        Unit.name.label("unit")
    ).join(Observation, Observation.record_id == model.record_id)\
     .join(Parameter, Observation.parameter_id == Parameter.id)\
     .outerjoin(Unit, Observation.unit_id == Unit.id)

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

all_measurements = union_all(*comp_queries).subquery()

mv_biomass_composition = select(
    func.row_number().over(order_by=(all_measurements.c.resource_id, all_measurements.c.analysis_type, all_measurements.c.parameter_name, all_measurements.c.unit)).label("id"),
    all_measurements.c.resource_id,
    Resource.name.label("resource_name"),
    all_measurements.c.analysis_type,
    all_measurements.c.parameter_name,
    all_measurements.c.unit,
    func.avg(all_measurements.c.value).label("avg_value"),
    func.min(all_measurements.c.value).label("min_value"),
    func.max(all_measurements.c.value).label("max_value"),
    func.stddev(all_measurements.c.value).label("std_dev"),
    func.count().label("observation_count")
).select_from(all_measurements)\
 .join(Resource, all_measurements.c.resource_id == Resource.id)\
 .group_by(
    all_measurements.c.resource_id,
    Resource.name,
    all_measurements.c.analysis_type,
    all_measurements.c.parameter_name,
    all_measurements.c.unit
)


# 3. mv_biomass_county_production
# Deprecated. The frontend now uses mv_usda_county_production.
# 5. mv_biomass_sample_stats
def get_sample_stats_query(model):
    return select(
        model.resource_id,
        model.prepared_sample_id,
        model.dataset_id
    )

sample_queries = [
    get_sample_stats_query(CompositionalRecord),
    get_sample_stats_query(ProximateRecord),
    get_sample_stats_query(UltimateRecord),
    get_sample_stats_query(XrfRecord),
    get_sample_stats_query(IcpRecord),
    get_sample_stats_query(CalorimetryRecord),
    get_sample_stats_query(XrdRecord),
    get_sample_stats_query(FtnirRecord),
    get_sample_stats_query(FermentationRecord),
    get_sample_stats_query(GasificationRecord),
    get_sample_stats_query(PretreatmentRecord)
]

all_samples = union_all(*sample_queries).subquery()

mv_biomass_sample_stats = select(
    Resource.id.label("resource_id"),
    Resource.name.label("resource_name"),
    func.count(func.distinct(all_samples.c.prepared_sample_id)).label("sample_count"),
    func.count(func.distinct(Provider.id)).label("supplier_count"),
    func.count(func.distinct(all_samples.c.dataset_id)).label("dataset_count"),
    func.count().label("total_record_count")
).select_from(Resource)\
 .outerjoin(all_samples, all_samples.c.resource_id == Resource.id)\
 .outerjoin(PreparedSample, cast(all_samples.c.prepared_sample_id, Integer) == PreparedSample.id)\
 .outerjoin(FieldSample, PreparedSample.field_sample_id == FieldSample.id)\
 .outerjoin(Provider, FieldSample.provider_id == Provider.id)\
 .group_by(Resource.id, Resource.name)


# 6. mv_biomass_fermentation
PM = aliased(Method, name="pm")
EM = aliased(Method, name="em")

mv_biomass_fermentation = select(
    func.row_number().over(order_by=(FermentationRecord.resource_id, Strain.name, PM.name, EM.name, Parameter.name, Unit.name)).label("id"),
    FermentationRecord.resource_id,
    Resource.name.label("resource_name"),
    Strain.name.label("strain_name"),
    PM.name.label("pretreatment_method"),
    EM.name.label("enzyme_name"),
    Parameter.name.label("product_name"),
    func.avg(Observation.value).label("avg_value"),
    func.min(Observation.value).label("min_value"),
    func.max(Observation.value).label("max_value"),
    func.stddev(Observation.value).label("std_dev"),
    func.count().label("observation_count"),
    Unit.name.label("unit")
).select_from(FermentationRecord)\
 .join(Resource, FermentationRecord.resource_id == Resource.id)\
 .outerjoin(Strain, FermentationRecord.strain_id == Strain.id)\
 .outerjoin(PM, FermentationRecord.pretreatment_method_id == PM.id)\
 .outerjoin(EM, FermentationRecord.eh_method_id == EM.id)\
 .join(Observation, func.lower(Observation.record_id) == func.lower(FermentationRecord.record_id))\
 .join(Parameter, Observation.parameter_id == Parameter.id)\
 .outerjoin(Unit, Observation.unit_id == Unit.id)\
 .group_by(FermentationRecord.resource_id, Resource.name, Strain.name, PM.name, EM.name, Parameter.name, Unit.name)


# 7. mv_biomass_gasification
mv_biomass_gasification = select(
    func.row_number().over(order_by=(GasificationRecord.resource_id, DeconVessel.name, Parameter.name, Unit.name)).label("id"),
    GasificationRecord.resource_id,
    Resource.name.label("resource_name"),
    DeconVessel.name.label("reactor_type"),
    Parameter.name.label("parameter_name"),
    func.avg(Observation.value).label("avg_value"),
    func.min(Observation.value).label("min_value"),
    func.max(Observation.value).label("max_value"),
    func.stddev(Observation.value).label("std_dev"),
    func.count().label("observation_count"),
    Unit.name.label("unit")
).select_from(GasificationRecord)\
 .join(Resource, GasificationRecord.resource_id == Resource.id)\
 .outerjoin(DeconVessel, GasificationRecord.reactor_type_id == DeconVessel.id)\
 .join(Observation, func.lower(Observation.record_id) == func.lower(GasificationRecord.record_id))\
 .join(Parameter, Observation.parameter_id == Parameter.id)\
 .outerjoin(Unit, Observation.unit_id == Unit.id)\
 .group_by(
     GasificationRecord.resource_id,
     Resource.name,
     DeconVessel.name,
     Parameter.name,
     Unit.name
 )


pricing_obs = select(
    Observation.record_id,
    func.avg(
        case(
            (
                func.lower(Parameter.name).in_(["price", "price received"]),
                Observation.value,
            )
        )
    ).label("price"),
    func.max(
        case(
            (
                func.lower(Parameter.name).in_(["price", "price received"]),
                Unit.name,
            )
        )
    ).label("price_unit"),
).select_from(Observation)\
 .join(Parameter, Observation.parameter_id == Parameter.id)\
 .outerjoin(Unit, Observation.unit_id == Unit.id)\
 .where(func.lower(Observation.record_type) == "resource_price_record")\
 .group_by(Observation.record_id).subquery()

mv_biomass_pricing = select(
    func.row_number().over(
        order_by=(
            func.coalesce(PrimaryAgProduct.name, Resource.name, literal("unknown")),
            Place.geoid,
            ResourcePriceRecord.report_start_date,
        )
    ).label("id"),
    func.coalesce(PrimaryAgProduct.name, Resource.name, literal("unknown")).label("commodity_name"),
    Place.county_name.label("county"),
    Place.geoid,
    ResourcePriceRecord.report_start_date.label("report_date"),
    cast(func.avg(pricing_obs.c.price), Float).label("price"),
    func.max(pricing_obs.c.price_unit).label("price_unit"),
).select_from(ResourcePriceRecord)\
 .outerjoin(Resource, ResourcePriceRecord.resource_id == Resource.id)\
 .outerjoin(PrimaryAgProduct, ResourcePriceRecord.primary_ag_product_id == PrimaryAgProduct.id)\
 .outerjoin(pricing_obs, cast(ResourcePriceRecord.id, String) == pricing_obs.c.record_id)\
 .outerjoin(Place, ResourcePriceRecord.geoid == Place.geoid)\
 .group_by(
    func.coalesce(PrimaryAgProduct.name, Resource.name, literal("unknown")),
    Place.county_name,
    Place.geoid,
    ResourcePriceRecord.report_start_date,
 )


# 9. mv_biomass_end_uses
end_use_obs = select(
    Observation.record_id,
    func.avg(
        case(
            (
                func.lower(Parameter.name).in_(
                    [
                        "percent of volume",
                        "percent_of_volume",
                        "percentage of volume",
                        "volume percent",
                    ]
                ),
                Observation.value,
            )
        )
    ).label("percent_of_volume"),
    func.max(
        case(
            (
                func.lower(Parameter.name).in_(
                    [
                        "percent of volume",
                        "percent_of_volume",
                        "percentage of volume",
                        "volume percent",
                    ]
                ),
                Unit.name,
            )
        )
    ).label("unit"),
    func.max(
        case(
            (
                func.lower(Parameter.name) == "trending",
                cast(Observation.value, String),
            )
        )
    ).label("trending"),
).select_from(Observation)\
 .join(Parameter, Observation.parameter_id == Parameter.id)\
 .outerjoin(Unit, Observation.unit_id == Unit.id)\
 .where(func.lower(Observation.record_type) == "resource_end_use_record")\
 .group_by(Observation.record_id).subquery()

mv_biomass_end_uses = select(
    ResourceEndUseRecord.resource_id,
    Resource.name.label("resource_name"),
    func.coalesce(Method.name, literal("unknown")).label("use_case"),
    cast(end_use_obs.c.percent_of_volume, Float).label("percentage_low"),
    cast(literal(None), Float).label("percentage_high"),
    cast(end_use_obs.c.trending, Text).label("trend"),
    cast(literal(None), Float).label("value_low_usd"),
    cast(literal(None), Float).label("value_high_usd"),
    cast(literal(None), Text).label("value_notes"),
).select_from(ResourceEndUseRecord)\
 .join(Resource, ResourceEndUseRecord.resource_id == Resource.id)\
 .outerjoin(Method, ResourceEndUseRecord.method_id == Method.id)\
 .outerjoin(end_use_obs, cast(ResourceEndUseRecord.id, String) == end_use_obs.c.record_id)\
 .where(ResourceEndUseRecord.resource_id.is_not(None))\
 .group_by(
    ResourceEndUseRecord.resource_id,
    Resource.name,
    func.coalesce(Method.name, literal("unknown")),
    end_use_obs.c.percent_of_volume,
    end_use_obs.c.trending,
 )


# 10. mv_usda_county_production
# Bridging USDA Census data with BioCirV Resources and residue factors
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
 .group_by(Resource.id, Resource.name, PrimaryAgProduct.name, Place.geoid, Place.county_name, Place.state_name, UsdaCensusRecord.year)
