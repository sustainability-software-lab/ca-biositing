"""Pytest fixtures for v1 API endpoint tests.

This module provides shared test fixtures including database setup,
test data, and test client configuration.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from ca_biositing.datamodels.database import get_session
from ca_biositing.datamodels.models import ApiUser
from ca_biositing.webservice.dependencies import get_current_user
from sqlmodel import SQLModel
from ca_biositing.datamodels.models import (
    CalorimetryRecord,
    CompositionalRecord,
    DimensionType,
    FermentationRecord,
    FieldSample,
    IcpRecord,
    LocationAddress,
    Observation,
    Parameter,
    Place,
    PreparedSample,
    PretreatmentRecord,
    PrimaryAgProduct,
    ProximateRecord,
    Resource,
    ResourceAvailability,
    ResourceUsdaCommodityMap,
    UltimateRecord,
    Unit,
    UsdaCensusRecord,
    UsdaCommodity,
    UsdaSurveyProgram,
    UsdaSurveyRecord,
    XrdRecord,
    XrfRecord,
)
from ca_biositing.webservice.main import app


@pytest.fixture(name="engine", scope="function")
def engine_fixture():
    """Create in-memory SQLite engine for testing.

    Returns:
        SQLAlchemy engine configured for testing
    """
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},  # Allow multi-threading for tests
        poolclass=None,  # Disable connection pooling for in-memory DB
    )

    # Manually create only the tables we need (avoiding Polygon with md5())
    with engine.begin() as connection:
        Unit.__table__.create(connection, checkfirst=True)
        DimensionType.__table__.create(connection, checkfirst=True)
        Parameter.__table__.create(connection, checkfirst=True)
        UsdaCommodity.__table__.create(connection, checkfirst=True)
        PrimaryAgProduct.__table__.create(connection, checkfirst=True)
        Resource.__table__.create(connection, checkfirst=True)
        ResourceUsdaCommodityMap.__table__.create(connection, checkfirst=True)
        UsdaCensusRecord.__table__.create(connection, checkfirst=True)
        UsdaSurveyProgram.__table__.create(connection, checkfirst=True)
        UsdaSurveyRecord.__table__.create(connection, checkfirst=True)
        Observation.__table__.create(connection, checkfirst=True)
        Place.__table__.create(connection, checkfirst=True)
        LocationAddress.__table__.create(connection, checkfirst=True)
        FieldSample.__table__.create(connection, checkfirst=True)
        PreparedSample.__table__.create(connection, checkfirst=True)
        ProximateRecord.__table__.create(connection, checkfirst=True)
        UltimateRecord.__table__.create(connection, checkfirst=True)
        CompositionalRecord.__table__.create(connection, checkfirst=True)
        IcpRecord.__table__.create(connection, checkfirst=True)
        XrfRecord.__table__.create(connection, checkfirst=True)
        CalorimetryRecord.__table__.create(connection, checkfirst=True)
        XrdRecord.__table__.create(connection, checkfirst=True)
        FermentationRecord.__table__.create(connection, checkfirst=True)
        PretreatmentRecord.__table__.create(connection, checkfirst=True)
        ResourceAvailability.__table__.create(connection, checkfirst=True)

    return engine


@pytest.fixture(name="session")
def session_fixture(engine):
    """Create test database session.

    Args:
        engine: SQLAlchemy engine fixture

    Yields:
        Database session for testing
    """
    connection = engine.connect()
    transaction = connection.begin()
    SessionLocal = sessionmaker(bind=connection)
    session = SessionLocal()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(name="client")
def client_fixture(session):
    """Create test client with overridden database session.

    Args:
        session: Database session fixture

    Yields:
        FastAPI test client
    """
    def override_get_session():
        yield session

    # Bypass JWT auth for feedstocks route tests — auth is tested separately
    def override_get_current_user():
        return ApiUser(
            id=1,
            username="testuser",
            hashed_password="",
            is_admin=True,
            disabled=False,
        )

    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_current_user] = override_get_current_user
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture(name="test_census_data")
def test_census_data_fixture(session: Session):
    """Create test census data in database.

    This fixture creates:
    - CORN and SOYBEANS commodities
    - corn_grain and soybean_meal resources
    - Census records for geoid 06001
    - Observations with parameters, units, and dimensions

    Args:
        session: Database session fixture

    Returns:
        Dictionary with test data IDs
    """
    # Create units
    unit_acres = Unit(id=1, name="acres")
    unit_bushels = Unit(id=2, name="bushels")
    unit_tons = Unit(id=3, name="tons")
    session.add_all([unit_acres, unit_bushels, unit_tons])

    # Create dimension types
    dim_type_area = DimensionType(id=1, name="area")
    session.add(dim_type_area)

    # Create parameters
    param_acres = Parameter(id=1, name="acres", standard_unit_id=1)
    param_production = Parameter(id=2, name="production", standard_unit_id=2)
    param_yield = Parameter(id=3, name="yield_per_acre", standard_unit_id=2)
    session.add_all([param_acres, param_production, param_yield])

    # Create commodities
    commodity_corn = UsdaCommodity(id=1, name="CORN LEGACY", api_name="corn", usda_code="00090")
    commodity_soybeans = UsdaCommodity(id=2, name="SOYBEANS", api_name=None, usda_code="00081")
    commodity_corn_all = UsdaCommodity(id=3, name="CORN ALL LEGACY", api_name="corn all", usda_code="00900")
    session.add_all([commodity_corn, commodity_soybeans, commodity_corn_all])

    # Create primary ag products (required for Resource FK)
    primary_ag_corn = PrimaryAgProduct(id=1, name="Corn")
    primary_ag_soybean = PrimaryAgProduct(id=2, name="Soybean")
    session.add_all([primary_ag_corn, primary_ag_soybean])

    # Create resources
    resource_corn_grain = Resource(id=1, name="corn_grain", primary_ag_product_id=1)
    resource_soybean_meal = Resource(id=2, name="soybean_meal", primary_ag_product_id=2)
    session.add_all([resource_corn_grain, resource_soybean_meal])

    # Create place records required by canonical USDA views
    place_06001 = Place(geoid="06001", state_name="California", county_name="Alameda")
    place_06047 = Place(geoid="06047", state_name="California", county_name="Merced")
    session.add_all([place_06001, place_06047])

    # Create resource-commodity mappings
    mapping_corn = ResourceUsdaCommodityMap(
        id=1,
        resource_id=1,
        usda_commodity_id=1,
        match_tier="exact"
    )
    mapping_soybean = ResourceUsdaCommodityMap(
        id=2,
        resource_id=2,
        usda_commodity_id=2,
        match_tier="exact"
    )
    session.add_all([mapping_corn, mapping_soybean])

    # Create census records
    census_corn = UsdaCensusRecord(
        id=1,
        dataset_id=1,
        geoid="06001",
        commodity_code=1,
        year=2022
    )
    census_soybeans = UsdaCensusRecord(
        id=2,
        dataset_id=1,
        geoid="06001",
        commodity_code=2,
        year=2022
    )
    census_corn_all = UsdaCensusRecord(
        id=3,
        dataset_id=1,
        geoid="06047",
        commodity_code=3,
        year=2022
    )
    session.add_all([census_corn, census_soybeans, census_corn_all])

    # Create observations for CORN using ETL format:
    # record_type = "usda_census_record", record_id = str(census_record.id)
    obs_corn_acres = Observation(
        id=1,
        record_id="1",
        dataset_id=1,
        record_type="usda_census_record",
        parameter_id=1,
        value=25000.0,
        unit_id=1,
    )
    obs_corn_production = Observation(
        id=2,
        record_id="1",
        dataset_id=1,
        record_type="usda_census_record",
        parameter_id=2,
        value=3750000.0,
        unit_id=2,
    )
    obs_corn_yield = Observation(
        id=3,
        record_id="1",
        dataset_id=1,
        record_type="usda_census_record",
        parameter_id=3,
        value=150.0,
        unit_id=2,
        dimension_type_id=1,
        dimension_value=1.0,
        dimension_unit_id=1,
    )

    # Create observations for SOYBEANS
    obs_soybeans_acres = Observation(
        id=4,
        record_id="2",
        dataset_id=1,
        record_type="usda_census_record",
        parameter_id=1,
        value=15000.0,
        unit_id=1,
    )
    obs_corn_all_acres = Observation(
        id=9,
        record_id="3",
        dataset_id=1,
        record_type="usda_census_record",
        parameter_id=1,
        value=18000.0,
        unit_id=1,
    )

    session.add_all([
        obs_corn_acres,
        obs_corn_production,
        obs_corn_yield,
        obs_soybeans_acres,
        obs_corn_all_acres,
    ])
    session.commit()

    return {
        "commodity_corn_id": 1,
        "commodity_soybeans_id": 2,
        "resource_corn_id": 1,
        "resource_soybean_id": 2,
        "census_corn_id": 1,
        "census_soybeans_id": 2,
        "census_corn_all_id": 3,
    }


@pytest.fixture(name="test_survey_data")
def test_survey_data_fixture(session: Session):
    """Create test survey data in database.

    This fixture creates:
    - CORN and SOYBEANS commodities (reuses from census)
    - corn_grain and soybean_meal resources (reuses from census)
    - Survey program
    - Survey records for geoid 06001
    - Observations with parameters, units, and dimensions

    Args:
        session: Database session fixture

    Returns:
        Dictionary with test data IDs
    """
    # Create units
    unit_acres = Unit(id=1, name="acres")
    unit_bushels = Unit(id=2, name="bushels")
    unit_tons = Unit(id=3, name="tons")
    session.add_all([unit_acres, unit_bushels, unit_tons])

    # Create dimension types
    dim_type_area = DimensionType(id=1, name="area")
    session.add(dim_type_area)

    # Create parameters
    param_acres = Parameter(id=1, name="acres", standard_unit_id=1)
    param_production = Parameter(id=2, name="production", standard_unit_id=2)
    param_yield = Parameter(id=3, name="yield_per_acre", standard_unit_id=2)
    session.add_all([param_acres, param_production, param_yield])

    # Create commodities
    commodity_corn = UsdaCommodity(id=1, name="CORN LEGACY", api_name="corn", usda_code="00090")
    commodity_soybeans = UsdaCommodity(id=2, name="SOYBEANS", api_name=None, usda_code="00081")
    commodity_corn_all = UsdaCommodity(id=3, name="CORN ALL LEGACY", api_name="corn all", usda_code="00900")
    session.add_all([commodity_corn, commodity_soybeans, commodity_corn_all])

    # Create primary ag products (required for Resource FK)
    primary_ag_corn = PrimaryAgProduct(id=1, name="Corn")
    primary_ag_soybean = PrimaryAgProduct(id=2, name="Soybean")
    session.add_all([primary_ag_corn, primary_ag_soybean])

    # Create resources
    resource_corn_grain = Resource(id=1, name="corn_grain", primary_ag_product_id=1)
    resource_soybean_meal = Resource(id=2, name="soybean_meal", primary_ag_product_id=2)
    session.add_all([resource_corn_grain, resource_soybean_meal])

    # Create place records required by canonical USDA views
    place_06001 = Place(geoid="06001", state_name="California", county_name="Alameda")
    place_06047 = Place(geoid="06047", state_name="California", county_name="Merced")
    session.add_all([place_06001, place_06047])

    # Create resource-commodity mappings
    mapping_corn = ResourceUsdaCommodityMap(
        id=1,
        resource_id=1,
        usda_commodity_id=1,
        match_tier="exact"
    )
    mapping_soybean = ResourceUsdaCommodityMap(
        id=2,
        resource_id=2,
        usda_commodity_id=2,
        match_tier="exact"
    )
    session.add_all([mapping_corn, mapping_soybean])

    # Create survey program
    survey_program = UsdaSurveyProgram(id=1, name="NASS Weekly Survey")
    session.add(survey_program)

    # Create survey records
    survey_corn = UsdaSurveyRecord(
        id=1,
        dataset_id=1,
        geoid="06001",
        commodity_code=1,
        year=2022,
        survey_program_id=1,
        survey_period="2022-Q1",
        reference_month="January",
        seasonal_flag=True
    )
    survey_soybeans = UsdaSurveyRecord(
        id=2,
        dataset_id=1,
        geoid="06001",
        commodity_code=2,
        year=2022,
        survey_program_id=1,
        survey_period="2022-Q1",
        reference_month="January",
        seasonal_flag=False
    )
    survey_corn_all = UsdaSurveyRecord(
        id=3,
        dataset_id=1,
        geoid="06047",
        commodity_code=3,
        year=2022,
        survey_program_id=1,
        survey_period="2022-Q1",
        reference_month="January",
        seasonal_flag=True
    )
    session.add_all([survey_corn, survey_soybeans, survey_corn_all])

    # Create observations for CORN using ETL format:
    # record_type = "usda_survey_record", record_id = str(survey_record.id)
    obs_corn_acres = Observation(
        id=5,
        record_id="1",
        dataset_id=1,
        record_type="usda_survey_record",
        parameter_id=1,
        value=28000.0,
        unit_id=1,
    )
    obs_corn_production = Observation(
        id=6,
        record_id="1",
        dataset_id=1,
        record_type="usda_survey_record",
        parameter_id=2,
        value=4200000.0,
        unit_id=2,
    )
    obs_corn_yield = Observation(
        id=7,
        record_id="1",
        dataset_id=1,
        record_type="usda_survey_record",
        parameter_id=3,
        value=155.0,
        unit_id=2,
        dimension_type_id=1,
        dimension_value=1.0,
        dimension_unit_id=1,
    )

    # Create observations for SOYBEANS
    obs_soybeans_acres = Observation(
        id=8,
        record_id="2",
        dataset_id=1,
        record_type="usda_survey_record",
        parameter_id=1,
        value=17000.0,
        unit_id=1,
    )
    obs_corn_all_acres = Observation(
        id=10,
        record_id="3",
        dataset_id=1,
        record_type="usda_survey_record",
        parameter_id=1,
        value=19000.0,
        unit_id=1,
    )

    session.add_all([
        obs_corn_acres,
        obs_corn_production,
        obs_corn_yield,
        obs_soybeans_acres,
        obs_corn_all_acres,
    ])
    session.commit()

    return {
        "commodity_corn_id": 1,
        "commodity_soybeans_id": 2,
        "resource_corn_id": 1,
        "resource_soybean_id": 2,
        "survey_corn_id": 1,
        "survey_soybeans_id": 2,
        "survey_corn_all_id": 3,
        "survey_program_id": 1,
    }


@pytest.fixture(name="test_analysis_data")
def test_analysis_data_fixture(session: Session):
    """Create test analysis data in database.

    This fixture creates:
    - almond_hulls and corn_stover resources
    - Place, LocationAddress, FieldSample, PreparedSample chain for geoid linkage
    - Proximate, Ultimate, and Compositional analysis records
    - Observations with analysis parameters

    Args:
        session: Database session fixture

    Returns:
        Dictionary with test data IDs
    """
    # Create units (reuse IDs from census or create new ones)
    unit_percent = Unit(id=10, name="percent")
    unit_mg_g = Unit(id=11, name="mg/g")
    session.add_all([unit_percent, unit_mg_g])

    # Create parameters for analysis
    param_ash = Parameter(id=10, name="ash", standard_unit_id=10)
    param_moisture = Parameter(id=11, name="moisture", standard_unit_id=10)
    param_volatile_solids = Parameter(id=14, name="volatile solids", standard_unit_id=10)
    param_carbon = Parameter(id=12, name="carbon", standard_unit_id=10)
    param_cellulose = Parameter(id=13, name="cellulose", standard_unit_id=10)
    param_glucan = Parameter(id=15, name="glucan", standard_unit_id=10)
    param_xylan = Parameter(id=16, name="xylan", standard_unit_id=10)
    param_lignin = Parameter(id=17, name="lignin", standard_unit_id=10)
    session.add_all([
        param_ash, param_moisture, param_volatile_solids, param_carbon,
        param_cellulose, param_glucan, param_xylan, param_lignin
    ])

    # Create primary ag products (required for Resource FK)
    primary_ag_almond = PrimaryAgProduct(id=10, name="Almond")
    primary_ag_corn_stover = PrimaryAgProduct(id=11, name="Corn Stover")
    session.add_all([primary_ag_almond, primary_ag_corn_stover])

    # Create resources
    resource_almond_hulls = Resource(id=10, name="almond_hulls", primary_ag_product_id=10)
    resource_corn_stover = Resource(id=11, name="corn_stover", primary_ag_product_id=11)
    session.add_all([resource_almond_hulls, resource_corn_stover])

    # Create Place (geoid) for location linkage
    place_06001 = Place(geoid="06001", state_name="California", county_name="Alameda")
    place_06013 = Place(geoid="06013", state_name="California", county_name="Contra Costa")
    session.add_all([place_06001, place_06013])

    # Create LocationAddress linked to Place
    location_1 = LocationAddress(id=1, geography_id="06001", city="Oakland")
    location_2 = LocationAddress(id=2, geography_id="06013", city="Martinez")
    session.add_all([location_1, location_2])

    # Create FieldSample linked to LocationAddress
    field_sample_1 = FieldSample(
        id=1,
        name="Almond Hulls Sample 1",
        resource_id=10,
        sampling_location_id=1
    )
    field_sample_2 = FieldSample(
        id=2,
        name="Corn Stover Sample 1",
        resource_id=11,
        sampling_location_id=2
    )
    session.add_all([field_sample_1, field_sample_2])

    # Create PreparedSample linked to FieldSample
    prepared_sample_1 = PreparedSample(id=1, name="Prep Sample 1", field_sample_id=1)
    prepared_sample_2 = PreparedSample(id=2, name="Prep Sample 2", field_sample_id=2)
    session.add_all([prepared_sample_1, prepared_sample_2])

    # Create analysis records linked to resources and prepared samples
    # Note: Multiple records per prepared_sample (one per parameter measured)

    # Proximate analysis for almond hulls - ash measurement
    proximate_almond_ash = ProximateRecord(
        id=1,
        record_id="prox_almond_1_ash",
        dataset_id=1,
        resource_id=10,
        prepared_sample_id=1
    )
    # Proximate analysis for almond hulls - moisture measurement
    proximate_almond_moisture = ProximateRecord(
        id=2,
        record_id="prox_almond_1_moisture",
        dataset_id=1,
        resource_id=10,
        prepared_sample_id=1,
        experiment_id=1
    )
    # Proximate analysis for almond hulls - volatile solids (to satisfy sum filter)
    proximate_almond_vs = ProximateRecord(
        id=3,
        record_id="prox_almond_1_vs",
        dataset_id=1,
        resource_id=10,
        prepared_sample_id=1,
        experiment_id=1
    )
    # Ultimate analysis for almond hulls - carbon measurement
    ultimate_almond_carbon = UltimateRecord(
        id=1,
        record_id="ult_almond_1_carbon",
        dataset_id=1,
        resource_id=10,
        prepared_sample_id=1
    )
    # Compositional analysis for corn stover - cellulose measurement
    compositional_corn_cellulose = CompositionalRecord(
        id=1,
        record_id="comp_corn_1_cellulose",
        dataset_id=1,
        resource_id=11,
        prepared_sample_id=2
    )
    # Add experiment IDs to other records for correct grouping
    proximate_almond_ash.experiment_id = 1
    ultimate_almond_carbon.experiment_id = 1

    # Compositional analysis for corn stover - additional params for sum filter
    compositional_corn_glucan = CompositionalRecord(
        id=2,
        record_id="comp_corn_1_glucan",
        dataset_id=1,
        resource_id=11,
        prepared_sample_id=2,
        experiment_id=2
    )
    compositional_corn_xylan = CompositionalRecord(
        id=3,
        record_id="comp_corn_1_xylan",
        dataset_id=1,
        resource_id=11,
        prepared_sample_id=2,
        experiment_id=2
    )
    compositional_corn_lignin = CompositionalRecord(
        id=4,
        record_id="comp_corn_1_lignin",
        dataset_id=1,
        resource_id=11,
        prepared_sample_id=2,
        experiment_id=2
    )
    compositional_corn_cellulose.experiment_id = 2

    session.add_all([
        proximate_almond_ash,
        proximate_almond_moisture,
        proximate_almond_vs,
        ultimate_almond_carbon,
        compositional_corn_cellulose,
        compositional_corn_glucan,
        compositional_corn_xylan,
        compositional_corn_lignin,
    ])

    # Create observations for proximate analysis (almond hulls, geoid 06001)
    # Note: Each observation must have a UNIQUE record_id
    obs_prox_ash = Observation(
        id=100,
        record_id="prox_almond_1_ash",
        dataset_id=1,
        record_type="proximate analysis",
        parameter_id=10,
        value=5.2,
        unit_id=10,
    )
    obs_prox_moisture = Observation(
        id=101,
        record_id="prox_almond_1_moisture",
        dataset_id=1,
        record_type="proximate analysis",
        parameter_id=11,
        value=8.5,
        unit_id=10,
    )

    # Create observations for ultimate analysis (almond hulls, geoid 06001)
    obs_ult_carbon = Observation(
        id=102,
        record_id="ult_almond_1_carbon",
        dataset_id=1,
        record_type="ultimate analysis",
        parameter_id=12,
        value=45.3,
        unit_id=10,
    )

    # Create observations for compositional analysis (corn stover, geoid 06013)
    obs_comp_cellulose = Observation(
        id=103,
        record_id="comp_corn_1_cellulose",
        dataset_id=1,
        record_type="compositional analysis",
        parameter_id=13,
        value=38.7,
        unit_id=10,
    )

    obs_prox_vs = Observation(
        id=104,
        record_id="prox_almond_1_vs",
        dataset_id=1,
        record_type="proximate analysis",
        parameter_id=14,
        value=86.3, # 5.2 (ash) + 8.5 (moisture) + 86.3 (vs) = 100.0
        unit_id=10,
    )

    # Create observations for compositional analysis (corn stover, geoid 06013)
    obs_comp_glucan = Observation(
        id=105,
        record_id="comp_corn_1_glucan",
        dataset_id=1,
        record_type="compositional analysis",
        parameter_id=15,
        value=35.0,
        unit_id=10,
    )
    obs_comp_xylan = Observation(
        id=106,
        record_id="comp_corn_1_xylan",
        dataset_id=1,
        record_type="compositional analysis",
        parameter_id=16,
        value=20.0,
        unit_id=10,
    )
    obs_comp_lignin = Observation(
        id=107,
        record_id="comp_corn_1_lignin",
        dataset_id=1,
        record_type="compositional analysis",
        parameter_id=17,
        value=25.0,
        unit_id=10,
    )
    # Total compositional sum: glucan (35) + xylan (20) + lignin (25) = 80.0 (satisfies >= 40 filter)

    session.add_all([
        obs_prox_ash,
        obs_prox_moisture,
        obs_prox_vs,
        obs_ult_carbon,
        obs_comp_cellulose,
        obs_comp_glucan,
        obs_comp_xylan,
        obs_comp_lignin,
    ])
    session.commit()

    return {
        "resource_almond_id": 10,
        "resource_corn_stover_id": 11,
        "proximate_almond_id": 1,
        "ultimate_almond_id": 1,
        "compositional_corn_id": 1,
    }


@pytest.fixture(name="test_availability_data")
def test_availability_data_fixture(session: Session):
    """Create test availability data in database.

    This fixture creates:
    - wheat_straw and rice_straw resources
    - Place records for geoids
    - ResourceAvailability records with from_month/to_month

    Args:
        session: Database session fixture

    Returns:
        Dictionary with test data IDs
    """
    # Create primary ag products (required for Resource FK)
    primary_ag_wheat = PrimaryAgProduct(id=20, name="Wheat")
    primary_ag_rice = PrimaryAgProduct(id=21, name="Rice")
    session.add_all([primary_ag_wheat, primary_ag_rice])

    # Create resources
    resource_wheat_straw = Resource(id=20, name="wheat_straw", primary_ag_product_id=20)
    resource_rice_straw = Resource(id=21, name="rice_straw", primary_ag_product_id=21)
    session.add_all([resource_wheat_straw, resource_rice_straw])

    # Create Place records (if not already created by analysis fixture)
    # Check if places exist first
    existing_place = session.execute(select(Place).where(Place.geoid == "06067")).scalar_one_or_none()
    if not existing_place:
        place_06067 = Place(geoid="06067", state_name="California", county_name="Sacramento")
        session.add(place_06067)

    existing_place_2 = session.execute(select(Place).where(Place.geoid == "06099")).scalar_one_or_none()
    if not existing_place_2:
        place_06099 = Place(geoid="06099", state_name="California", county_name="Stanislaus")
        session.add(place_06099)

    # Create ResourceAvailability records
    avail_wheat = ResourceAvailability(
        id=1,
        resource_id=20,
        geoid="06067",
        from_month=6,  # June
        to_month=8,    # August
        year_round=False
    )
    avail_rice = ResourceAvailability(
        id=2,
        resource_id=21,
        geoid="06099",
        from_month=9,   # September
        to_month=11,    # November
        year_round=False
    )
    session.add_all([avail_wheat, avail_rice])
    session.commit()

    return {
        "resource_wheat_id": 20,
        "resource_rice_id": 21,
        "avail_wheat_id": 1,
        "avail_rice_id": 2,
    }
