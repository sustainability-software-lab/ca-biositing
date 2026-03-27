"""
Materialized view definitions using SQLAlchemy Core select() expressions.

This module defines all 7 materialized views for the ca_biositing schema:
- landiq_record_view: LandIQ spatial records with crop mapping
- landiq_tileset_view: LandIQ geospatial tile aggregation
- analysis_data_view: Aim1 analytical records union with spatial joins
- usda_census_view: USDA Census records with commodity and place joins
- usda_survey_view: USDA Survey records with commodity and place joins
- billion_ton_tileset_view: Billion Ton 2023 records with spatial joins
- analysis_average_view: Aggregated analysis statistics (raw SQL)

Views are created via Alembic migrations and can be refreshed via refresh_all_views().
"""

from sqlalchemy import cast, func, literal, literal_column, select, text, String, Float
from sqlalchemy.orm import aliased

# Import all models needed for view definitions
from .models import (
    # External data models
    LandiqRecord,
    Polygon,
    PrimaryAgProduct,
    UsdaCensusRecord,
    UsdaSurveyRecord,
    UsdaCommodity,
    ResourceUsdaCommodityMap,
    BillionTon2023Record,
    # General analysis models
    Observation,
    Parameter,
    Unit,
    DimensionType,
    # Aim1 record models
    ProximateRecord,
    UltimateRecord,
    CompositionalRecord,
    IcpRecord,
    XrfRecord,
    CalorimetryRecord,
    XrdRecord,
    # Aim2 record models
    FermentationRecord,
    PretreatmentRecord,
    # Sample models
    PreparedSample,
    FieldSample,
    LocationAddress,
    # Resource and place models
    Resource,
    Place,
)

# Schema for all materialized views
VIEW_SCHEMA = "ca_biositing"

# Raw column reference for geometry — bypasses GeoAlchemy2's ST_AsEWKB wrapping
_geom_col = literal_column("polygon.geom").label("geom")

# --- 1. landiq_record_view ---
LANDIQ_RECORD_VIEW = (
    select(
        LandiqRecord.record_id,
        _geom_col,
        Polygon.geoid,
        PrimaryAgProduct.name.label("crop_name"),
        LandiqRecord.acres,
        LandiqRecord.irrigated,
        LandiqRecord.confidence,
        LandiqRecord.dataset_id,
    )
    .join(Polygon, LandiqRecord.polygon_id == Polygon.id)
    .join(PrimaryAgProduct, LandiqRecord.main_crop == PrimaryAgProduct.id)
)

# --- 2. landiq_tileset_view ---
LANDIQ_TILESET_VIEW = (
    select(
        LandiqRecord.id,
        _geom_col,
        PrimaryAgProduct.name.label("main_crop"),
        LandiqRecord.acres,
        LandiqRecord.county,
        Polygon.geoid,
        LandiqRecord.dataset_id.label("tileset_id"),
    )
    .join(Polygon, LandiqRecord.polygon_id == Polygon.id)
    .join(PrimaryAgProduct, LandiqRecord.main_crop == PrimaryAgProduct.id)
)

# --- 3. analysis_data_view ---
AnalysisDimensionUnit = aliased(Unit, name="analysis_du")
ANALYSIS_DATA_VIEW = (
    select(
        Observation.id,
        Observation.record_id,
        Observation.record_type,
        Resource.id.label("resource_id"),
        func.lower(Resource.name).label("resource"),
        LocationAddress.geography_id.label("geoid"),
        func.lower(Parameter.name).label("parameter"),
        Observation.value,
        func.lower(Unit.name).label("unit"),
        func.lower(DimensionType.name).label("dimension"),
        Observation.dimension_value,
        func.lower(AnalysisDimensionUnit.name).label("dimension_unit"),
    )
    .join(Parameter, Observation.parameter_id == Parameter.id)
    .join(Unit, Observation.unit_id == Unit.id)
    .outerjoin(DimensionType, Observation.dimension_type_id == DimensionType.id)
    .outerjoin(AnalysisDimensionUnit, Observation.dimension_unit_id == AnalysisDimensionUnit.id)
    .outerjoin(
        ProximateRecord,
        (func.lower(Observation.record_id) == func.lower(ProximateRecord.record_id))
        & (func.lower(Observation.record_type).in_(["proximate analysis", "proximate_analysis"])),
    )
    .outerjoin(
        UltimateRecord,
        (func.lower(Observation.record_id) == func.lower(UltimateRecord.record_id))
        & (func.lower(Observation.record_type).in_(["ultimate analysis", "ultimate_analysis"])),
    )
    .outerjoin(
        CompositionalRecord,
        (func.lower(Observation.record_id) == func.lower(CompositionalRecord.record_id))
        & (func.lower(Observation.record_type).in_(["compositional analysis", "compositional_analysis"])),
    )
    .outerjoin(
        IcpRecord,
        (func.lower(Observation.record_id) == func.lower(IcpRecord.record_id))
        & (
            (func.lower(Observation.record_type) == "icp analysis")
            | (func.lower(Observation.record_type) == "icp_analysis")
            | (func.lower(Observation.record_type) == "icp-oes")
            | (func.lower(Observation.record_type) == "icp-ms")
        ),
    )
    .outerjoin(
        XrfRecord,
        (func.lower(Observation.record_id) == func.lower(XrfRecord.record_id))
        & (func.lower(Observation.record_type).in_(["xrf analysis", "xrf_analysis"])),
    )
    .outerjoin(
        CalorimetryRecord,
        (func.lower(Observation.record_id) == func.lower(CalorimetryRecord.record_id))
        & (func.lower(Observation.record_type).in_(["calorimetry analysis", "calorimetry_analysis"])),
    )
    .outerjoin(
        XrdRecord,
        (func.lower(Observation.record_id) == func.lower(XrdRecord.record_id))
        & (func.lower(Observation.record_type).in_(["xrd analysis", "xrd_analysis"])),
    )
    .outerjoin(
        FermentationRecord,
        (func.lower(Observation.record_id) == func.lower(FermentationRecord.record_id))
        & (func.lower(Observation.record_type) == "fermentation"),
    )
    .outerjoin(
        PretreatmentRecord,
        (func.lower(Observation.record_id) == func.lower(PretreatmentRecord.record_id))
        & (func.lower(Observation.record_type) == "pretreatment"),
    )
    .outerjoin(
        PreparedSample,
        PreparedSample.id
        == func.coalesce(
            ProximateRecord.prepared_sample_id,
            UltimateRecord.prepared_sample_id,
            CompositionalRecord.prepared_sample_id,
            IcpRecord.prepared_sample_id,
            XrfRecord.prepared_sample_id,
            CalorimetryRecord.prepared_sample_id,
            XrdRecord.prepared_sample_id,
            FermentationRecord.prepared_sample_id,
            PretreatmentRecord.prepared_sample_id,
        ),
    )
    .outerjoin(FieldSample, FieldSample.id == PreparedSample.field_sample_id)
    .outerjoin(
        Resource,
        Resource.id
        == func.coalesce(
            ProximateRecord.resource_id,
            UltimateRecord.resource_id,
            CompositionalRecord.resource_id,
            IcpRecord.resource_id,
            XrfRecord.resource_id,
            CalorimetryRecord.resource_id,
            XrdRecord.resource_id,
            FermentationRecord.resource_id,
            PretreatmentRecord.resource_id,
            FieldSample.resource_id,
        ),
    )
    .outerjoin(LocationAddress, LocationAddress.id == FieldSample.sampling_location_id)
    .where(
        func.lower(Observation.record_type).notin_(
            ["usda_census_record", "usda_survey_record"]
        )
    )
)

# --- 4. usda_census_view ---
# Create aliased Unit for dimension_unit
DimensionUnit = aliased(Unit, name="du")

# V1: original view using UsdaCommodity.name (api_name not yet added at this
# point in the migration chain; see migration 9c5c72c6d059). Updated to use
# api_name in migration b6aa2fc6cd42.
USDA_CENSUS_VIEW_V1 = (
    select(
        Observation.id,
        UsdaCommodity.name.label("usda_crop"),
        Place.geoid,
        func.lower(Parameter.name).label("parameter"),
        Observation.value,
        func.lower(Unit.name).label("unit"),
        func.lower(DimensionType.name).label("dimension"),
        Observation.dimension_value,
        func.lower(DimensionUnit.name).label("dimension_unit"),
    )
    .join(
        UsdaCensusRecord,
        (Observation.record_id == cast(UsdaCensusRecord.id, String))
        & (Observation.record_type == "usda_census_record"),
    )
    .join(UsdaCommodity, UsdaCensusRecord.commodity_code == UsdaCommodity.id)
    .join(Place, UsdaCensusRecord.geoid == Place.geoid)
    .join(Parameter, Observation.parameter_id == Parameter.id)
    .join(Unit, Observation.unit_id == Unit.id)
    .outerjoin(DimensionType, Observation.dimension_type_id == DimensionType.id)
    .outerjoin(DimensionUnit, Observation.dimension_unit_id == DimensionUnit.id)
)

USDA_CENSUS_VIEW = (
    select(
        Observation.id,
        func.lower(UsdaCommodity.api_name).label("usda_crop"),
        Place.geoid,
        func.lower(Parameter.name).label("parameter"),
        Observation.value,
        func.lower(Unit.name).label("unit"),
        func.lower(DimensionType.name).label("dimension"),
        Observation.dimension_value,
        func.lower(DimensionUnit.name).label("dimension_unit"),
        UsdaCommodity.id.label("commodity_id"),
        UsdaCensusRecord.id.label("source_record_id"),
        UsdaCensusRecord.year.label("record_year"),
    )
    .join(
        UsdaCensusRecord,
        (Observation.record_id == cast(UsdaCensusRecord.id, String))
        & (Observation.record_type == "usda_census_record"),
    )
    .join(UsdaCommodity, UsdaCensusRecord.commodity_code == UsdaCommodity.id)
    .join(Place, UsdaCensusRecord.geoid == Place.geoid)
    .join(Parameter, Observation.parameter_id == Parameter.id)
    .join(Unit, Observation.unit_id == Unit.id)
    .outerjoin(DimensionType, Observation.dimension_type_id == DimensionType.id)
    .outerjoin(DimensionUnit, Observation.dimension_unit_id == DimensionUnit.id)
)

# --- 5. usda_survey_view ---
# V1: original view using UsdaCommodity.name (see USDA_CENSUS_VIEW_V1 note above)
USDA_SURVEY_VIEW_V1 = (
    select(
        Observation.id,
        UsdaCommodity.name.label("usda_crop"),
        Place.geoid,
        func.lower(Parameter.name).label("parameter"),
        Observation.value,
        func.lower(Unit.name).label("unit"),
        func.lower(DimensionType.name).label("dimension"),
        Observation.dimension_value,
        func.lower(DimensionUnit.name).label("dimension_unit"),
    )
    .join(
        UsdaSurveyRecord,
        (Observation.record_id == cast(UsdaSurveyRecord.id, String))
        & (Observation.record_type == "usda_survey_record"),
    )
    .join(UsdaCommodity, UsdaSurveyRecord.commodity_code == UsdaCommodity.id)
    .join(Place, UsdaSurveyRecord.geoid == Place.geoid)
    .join(Parameter, Observation.parameter_id == Parameter.id)
    .join(Unit, Observation.unit_id == Unit.id)
    .outerjoin(DimensionType, Observation.dimension_type_id == DimensionType.id)
    .outerjoin(DimensionUnit, Observation.dimension_unit_id == DimensionUnit.id)
)

# Mirrors usda_census_view with UsdaSurveyRecord
USDA_SURVEY_VIEW = (
    select(
        Observation.id,
        func.lower(UsdaCommodity.api_name).label("usda_crop"),
        Place.geoid,
        func.lower(Parameter.name).label("parameter"),
        Observation.value,
        func.lower(Unit.name).label("unit"),
        func.lower(DimensionType.name).label("dimension"),
        Observation.dimension_value,
        func.lower(DimensionUnit.name).label("dimension_unit"),
        UsdaCommodity.id.label("commodity_id"),
        UsdaSurveyRecord.id.label("source_record_id"),
        UsdaSurveyRecord.year.label("record_year"),
        UsdaSurveyRecord.survey_program_id,
        UsdaSurveyRecord.survey_period,
        UsdaSurveyRecord.reference_month,
        UsdaSurveyRecord.seasonal_flag,
    )
    .join(
        UsdaSurveyRecord,
        (Observation.record_id == cast(UsdaSurveyRecord.id, String))
        & (Observation.record_type == "usda_survey_record"),
    )
    .join(UsdaCommodity, UsdaSurveyRecord.commodity_code == UsdaCommodity.id)
    .join(Place, UsdaSurveyRecord.geoid == Place.geoid)
    .join(Parameter, Observation.parameter_id == Parameter.id)
    .join(Unit, Observation.unit_id == Unit.id)
    .outerjoin(DimensionType, Observation.dimension_type_id == DimensionType.id)
    .outerjoin(DimensionUnit, Observation.dimension_unit_id == DimensionUnit.id)
)

# --- 6. usda_resource_commodity_view ---
# Lightweight view: maps each resource name to its USDA commodity ID.
# Used by discovery endpoints to list queryable resources without service-layer joins.
# A commodity may map to multiple resources; this view preserves all mappings.
USDA_RESOURCE_COMMODITY_VIEW = (
    select(
        Resource.name.label("resource"),
        ResourceUsdaCommodityMap.usda_commodity_id.label("commodity_id"),
    )
    .join(ResourceUsdaCommodityMap, ResourceUsdaCommodityMap.resource_id == Resource.id)
    .where(
        ResourceUsdaCommodityMap.usda_commodity_id.is_not(None),
        Resource.name.is_not(None),
    )
)

# --- 7. billion_ton_tileset_view ---
BILLION_TON_TILESET_VIEW = (
    select(
        BillionTon2023Record.id,
        Resource.name.label("resource"),
        func.lower(Place.county_name).label("county"),
        literal("production").label("parameter"),
        cast(BillionTon2023Record.production, Float).label("value"),
        func.lower(Unit.name).label("unit"),
        BillionTon2023Record.etl_run_id.label("tileset_id"),
    )
    .join(Resource, BillionTon2023Record.resource_id == Resource.id)
    .join(Place, BillionTon2023Record.geoid == Place.geoid)
    .join(Unit, BillionTon2023Record.production_unit_id == Unit.id)
)

# --- 7. analysis_average_view --- (SPECIAL CASE: depends on analysis_data_view)
# Cannot use Core select() against models because it aggregates another mat view.
# Use raw SQL string instead:
ANALYSIS_AVERAGE_VIEW_SQL = """
    SELECT resource, geoid, parameter,
           AVG(value) as average_value,
           STDDEV(value) as standard_deviation,
           unit, COUNT(*) as observation_count
    FROM ca_biositing.analysis_data_view
    GROUP BY resource, geoid, parameter, unit
"""

# Ordered list for creation (respects inter-view dependencies).
# USDA views use the V1 definitions (UsdaCommodity.name) because this list is
# used by the initial migration (9c5c72c6d059), before api_name is added in
# a085cd4a462e. Migration b6aa2fc6cd42 updates them to use api_name directly
# via USDA_CENSUS_VIEW / USDA_SURVEY_VIEW.
VIEW_DEFINITIONS = [
    ("landiq_record_view", LANDIQ_RECORD_VIEW),
    ("landiq_tileset_view", LANDIQ_TILESET_VIEW),
    ("analysis_data_view", ANALYSIS_DATA_VIEW),
    ("usda_census_view", USDA_CENSUS_VIEW_V1),
    ("usda_survey_view", USDA_SURVEY_VIEW_V1),
    ("billion_ton_tileset_view", BILLION_TON_TILESET_VIEW),
    # analysis_average_view is last (depends on analysis_data_view)
]

# Views requiring GIST spatial indexes
SPATIAL_VIEW_INDEXES = [
    ("idx_landiq_record_view_geom", "landiq_record_view", "geom"),
    ("idx_landiq_tileset_view_geom", "landiq_tileset_view", "geom"),
]


def refresh_all_views(engine):
    """Refresh all materialized views in dependency order.

    Args:
        engine: SQLAlchemy engine instance connected to the database.

    Example:
        from ca_biositing.datamodels.database import get_engine
        from ca_biositing.datamodels.views import refresh_all_views

        engine = get_engine()
        refresh_all_views(engine)
    """
    with engine.connect() as conn:
        # 1. Refresh ca_biositing schema views
        for view_name, _ in VIEW_DEFINITIONS:
            conn.execute(text(f"REFRESH MATERIALIZED VIEW {VIEW_SCHEMA}.{view_name}"))
        conn.execute(text(f"REFRESH MATERIALIZED VIEW {VIEW_SCHEMA}.usda_resource_commodity_view"))
        conn.execute(text(f"REFRESH MATERIALIZED VIEW {VIEW_SCHEMA}.analysis_average_view"))

        # 2. Refresh data_portal schema views
        data_portal_views = [
            "mv_biomass_search",
            "mv_biomass_composition",
            "mv_biomass_county_production",
            "mv_usda_county_production",
            "mv_biomass_availability",
            "mv_biomass_sample_stats",
            "mv_biomass_fermentation",
            "mv_biomass_gasification",
            "mv_biomass_pricing",
        ]
        for view_name in data_portal_views:
            conn.execute(text(f"REFRESH MATERIALIZED VIEW CONCURRENTLY data_portal.{view_name}"))

        conn.commit()
