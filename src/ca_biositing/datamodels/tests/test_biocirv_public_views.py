"""Tests for `biocirv_public` materialized view definitions.

Covers:
1. PostgreSQL dialect compilation (`literal_binds=True`) for the 2 Stage 1 views
   (`mv_resources` and `mv_analytical_summary`).
2. Strict privacy & Stage 1 scope assertions on compiled SQL (no PII/fine-location/note
   columns, no Stage 2 analysis tables).
3. Functional SQLite query execution verifying:
   - All `common.py` QC & privacy filters (`get_resource_filter`, `get_provider_filter`,
     `get_qc_status_filter` including `qc_pass IS NULL` exclusion, `get_etl_load_date_filter`,
     `get_icp_filter`, and `get_sum_constraints_subquery`).
   - NULL-safe `coalesce(experiment_id, -1)` sum-constraint join for records with
     `experiment_id IS NULL`.
   - Collision-safe compound-predicate polymorphic outerjoin on `(record_id, record_type)`.
   - `COUNT(DISTINCT ...)` entity counts and deduplicated resource metadata in `mv_resources`.
   - Technical replicate `mean_value` and `std_dev` in `mv_analytical_summary`.
4. Alembic migration `0028` isolation (never drops pre-existing `data_portal` or `ca_biositing` views).
"""

from __future__ import annotations

import math
from datetime import datetime
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Session

from ca_biositing.datamodels.biocirv_public_views import (
    BIOCIRV_PUBLIC_VIEW_NAMES,
    mv_analytical_summary,
    mv_resources,
    register_sqlite_udfs,
)
from ca_biositing.datamodels.models.aim1_records import (
    CalorimetryRecord,
    CompositionalRecord,
    IcpRecord,
    ProximateRecord,
    UltimateRecord,
    XrfRecord,
)
from ca_biositing.datamodels.models.experiment_equipment.experiment import Experiment
from ca_biositing.datamodels.models.field_sampling import (
    AgTreatment,
    CollectionMethod,
    FieldSample,
    FieldSampleCondition,
    FieldStorageMethod,
    HarvestMethod,
    ProcessingMethod,
)
from ca_biositing.datamodels.models.general_analysis.dimension_type import DimensionType
from ca_biositing.datamodels.models.general_analysis.observation import Observation
from ca_biositing.datamodels.models.methods_parameters_units.method import (
    Method,
    MethodAbbrev,
    MethodCategory,
    MethodStandard,
)
from ca_biositing.datamodels.models.methods_parameters_units.parameter import Parameter
from ca_biositing.datamodels.models.methods_parameters_units.unit import Unit
from ca_biositing.datamodels.models.people.contact import Contact
from ca_biositing.datamodels.models.people.provider import Provider
from ca_biositing.datamodels.models.places.location_address import LocationAddress
from ca_biositing.datamodels.models.places.place import Place
from ca_biositing.datamodels.models.resource_information.primary_ag_product import (
    PrimaryAgProduct,
)
from ca_biositing.datamodels.models.resource_information.resource import (
    Resource,
    ResourceClass,
    ResourceSubclass,
)
from ca_biositing.datamodels.models.sample_preparation.preparation_method import (
    PreparationMethod,
    PreparationMethodAbbreviation,
)
from ca_biositing.datamodels.models.sample_preparation.prepared_sample import (
    PreparedSample,
)

ALL_PUBLIC_VIEWS = {
    "mv_resources": mv_resources,
    "mv_analytical_summary": mv_analytical_summary,
}


def compile_pg(stmt) -> str:
    """Compile a SQLAlchemy select() statement to PostgreSQL SQL with literal binds."""
    return str(
        stmt.compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )


def test_biocirv_public_view_names_order():
    """Verify BIOCIRV_PUBLIC_VIEW_NAMES matches the 2 Stage 1 materialized views."""
    assert set(BIOCIRV_PUBLIC_VIEW_NAMES) == set(ALL_PUBLIC_VIEWS.keys())


@pytest.mark.parametrize("view_name,view_stmt", list(ALL_PUBLIC_VIEWS.items()))
def test_compile_all_biocirv_public_views_to_postgres(view_name, view_stmt):
    """All 5 biocirv_public views must compile cleanly to PostgreSQL SQL."""
    sql = compile_pg(view_stmt).lower()
    assert "select" in sql
    # Common QC filters must be embedded in every view (directly or via subquery)
    assert "sargassum" in sql
    assert "jaguar" in sql
    assert "fail" in sql
    assert "500000" in sql
    assert "95" in sql
    assert "105" in sql
    assert "40" in sql


@pytest.mark.parametrize("view_name,view_stmt", list(ALL_PUBLIC_VIEWS.items()))
def test_no_surrogate_database_id_columns_in_views(view_name, view_stmt):
    """Verify no internal integer surrogate ID columns are exposed in any biocirv_public view."""
    exposed_columns = {col.key for col in view_stmt.selected_columns}
    forbidden_id_columns = {
        "id",
        "observation_id",
        "resource_id",
        "prepared_sample_id",
        "field_sample_id",
        "experiment_id",
        "raw_data_id",
    }
    leaked = exposed_columns & forbidden_id_columns
    assert not leaked, (
        f"Surrogate database ID column(s) {sorted(leaked)} exposed in {view_name}"
    )


@pytest.mark.parametrize("view_name,view_stmt", list(ALL_PUBLIC_VIEWS.items()))
def test_privacy_and_scope_redaction_in_compiled_sql(view_name, view_stmt):
    """Verify no street/coordinate/contact/note columns or Stage 2 tables leak into SQL."""
    sql = compile_pg(view_stmt).lower()

    forbidden_tokens = [
        "address_line1",
        "address_line2",
        "location_address.city",
        "location_address.zip",
        "location_address.lat",
        "location_address.lon",
        ".note",
        "collector_id",
        "preparer_id",
        "analyst_id",
        "xrf_record",
        "calorimetry_record",
        "ultimate_record",
        "xrd_record",
        "ftnir_record",
        "fermentation_record",
        "gasification_record",
        "pretreatment_record",
    ]
    for token in forbidden_tokens:
        assert token not in sql, f"Forbidden token {token!r} found in {view_name} SQL"


def test_biocirv_public_view_columns_match_stage1_contract():
    """Verify each view exposes the exact minimal Stage 1 column list in order."""
    assert [c.key for c in mv_analytical_summary.selected_columns] == [
        "resource_name",
        "analysis_type",
        "parameter_name",
        "unit_name",
        "mean_value",
        "std_dev",
        "min_value",
        "max_value",
        "observation_count",
        "prepared_sample_count",
        "field_sample_count",
        "provider_count",
    ]
    assert [c.key for c in mv_resources.selected_columns] == [
        "resource_name",
        "description",
        "resource_class",
        "primary_ag_product",
        "field_sample_count",
        "prepared_sample_count",
        "provider_count",
        "observation_count",
        "has_proximate",
        "has_compositional",
        "has_icp",
    ]


def test_migration_0028_is_scoped_exclusively_to_biocirv_public():
    """Verify migration 0028 does not drop or recreate pre-existing data_portal/ca_biositing views."""
    repo_root = Path(__file__).resolve().parents[4]
    migration_path = (
        repo_root
        / "alembic"
        / "versions"
        / "0028_create_biocirv_public_schema_and_views.py"
    )
    content = migration_path.read_text(encoding="utf-8")

    unrelated_views = [
        "mv_biomass_search",
        "mv_biomass_composition",
        "mv_biomass_volume_estimate",
        "mv_biomass_availability",
        "mv_biomass_sample_stats",
        "mv_biomass_fermentation",
        "mv_biomass_gasification",
        "mv_biomass_pricing",
        "mv_biomass_end_uses",
        "mv_usda_county_production",
        "analysis_data_view",
        "analysis_average_view",
        "usda_census_view",
    ]
    for view_name in unrelated_views:
        assert view_name not in content, (
            f"Migration 0028 must not touch unrelated view {view_name}"
        )
    assert "CREATE SCHEMA IF NOT EXISTS biocirv_public" in content
    assert "DROP SCHEMA IF EXISTS biocirv_public" in content


@pytest.fixture(name="biocirv_engine")
def biocirv_engine_fixture():
    """Create an in-memory SQLite engine with the tables required for biocirv_public views."""
    engine = create_engine("sqlite:///:memory:")
    register_sqlite_udfs(engine)

    tables = [
        Contact.__table__,
        Unit.__table__,
        DimensionType.__table__,
        Parameter.__table__,
        MethodAbbrev.__table__,
        MethodCategory.__table__,
        MethodStandard.__table__,
        Method.__table__,
        Place.__table__,
        LocationAddress.__table__,
        Experiment.__table__,
        Provider.__table__,
        PrimaryAgProduct.__table__,
        ResourceClass.__table__,
        ResourceSubclass.__table__,
        Resource.__table__,
        AgTreatment.__table__,
        ProcessingMethod.__table__,
        HarvestMethod.__table__,
        CollectionMethod.__table__,
        FieldStorageMethod.__table__,
        FieldSample.__table__,
        FieldSampleCondition.__table__,
        PreparationMethodAbbreviation.__table__,
        PreparationMethod.__table__,
        PreparedSample.__table__,
        ProximateRecord.__table__,
        CompositionalRecord.__table__,
        XrfRecord.__table__,
        IcpRecord.__table__,
        CalorimetryRecord.__table__,
        UltimateRecord.__table__,
        Observation.__table__,
    ]
    with engine.begin() as conn:
        for table in tables:
            table.create(conn, checkfirst=True)

    return engine


def test_functional_execution_and_qc_governance(biocirv_engine):
    """Execute all 5 views against seeded SQLite data and verify QC, fan-out, and aggregation."""
    with Session(biocirv_engine) as session:
        # 1. Lookup tables
        u_pct = Unit(id=1, name="%")
        u_mjk = Unit(id=2, name="MJ/kg")
        u_ppm = Unit(id=3, name="ppm")
        u_days = Unit(id=4, name="days")
        session.add_all([u_pct, u_mjk, u_ppm, u_days])

        p_moisture = Parameter(id=1, name="moisture", standard_unit_id=1)
        p_ash = Parameter(id=2, name="ash solids", standard_unit_id=1)
        p_vs = Parameter(id=8, name="volatile solids", standard_unit_id=1)
        p_glucan = Parameter(id=3, name="glucan", standard_unit_id=1)
        p_xylan = Parameter(id=9, name="xylan", standard_unit_id=1)
        p_lignin = Parameter(id=10, name="lignin", standard_unit_id=1)
        p_hhv = Parameter(id=4, name="higher_heating_value", standard_unit_id=2)
        p_ca = Parameter(id=5, name="calcium", standard_unit_id=3)
        p_fe = Parameter(id=6, name="iron", standard_unit_id=3)
        p_carbon = Parameter(id=7, name="carbon", standard_unit_id=1)
        session.add_all(
            [
                p_moisture,
                p_ash,
                p_vs,
                p_glucan,
                p_xylan,
                p_lignin,
                p_hhv,
                p_ca,
                p_fe,
                p_carbon,
            ]
        )

        m_abbr = MethodAbbrev(id=1, name="NREL-TP")
        m_cat = MethodCategory(id=1, name="Proximate")
        m_std = MethodStandard(id=1, name="ASTM E1755")
        method = Method(
            id=1,
            name="NREL Proximate",
            method_abbrev_id=1,
            method_category_id=1,
            method_standard_id=1,
        )
        session.add_all([m_abbr, m_cat, m_std, method])

        place_sj = Place(
            geoid="06077",
            state_name="California",
            state_fips="06",
            county_name="San Joaquin",
            county_fips="077",
        )
        loc_sj = LocationAddress(
            id=1,
            geography_id="06077",
            address_line1="123 Secret Farm Rd",
            city="Stockton",
            zip="95202",
            lat=37.9577,
            lon=-121.2908,
        )
        session.add_all([place_sj, loc_sj])

        prov_valid = Provider(id=1, codename="PROVIDER_ALPHA")
        prov_jaguar = Provider(id=2, codename="Jaguar")
        session.add_all([prov_valid, prov_jaguar])

        rc = ResourceClass(id=1, name="Agricultural Byproduct")
        rsc = ResourceSubclass(id=1, name="Nut Shell/Hull")
        pag = PrimaryAgProduct(id=1, name="Almonds")
        res_almond = Resource(
            id=1,
            name="almond_hulls",
            resource_code="ALM-HULL",
            description="Almond hulls",
            resource_class_id=1,
            resource_subclass_id=1,
            primary_ag_product_id=1,
        )
        res_sargassum = Resource(id=2, name="sargassum", resource_code="SARG")
        session.add_all([rc, rsc, pag, res_almond, res_sargassum])

        ag1 = AgTreatment(id=1, name="organic")
        ag2 = AgTreatment(id=2, name="irrigated")
        pm1 = ProcessingMethod(id=1, name="hulled")
        pm2 = ProcessingMethod(id=2, name="screened")
        hm = HarvestMethod(id=1, name="shaker")
        cm = CollectionMethod(id=1, name="hand_grab")
        fsm = FieldStorageMethod(id=1, name="covered_pile")
        session.add_all([ag1, ag2, pm1, pm2, hm, cm, fsm])

        fs_valid = FieldSample(
            id=10,
            name="FS-ALM-001",
            resource_id=1,
            provider_id=1,
            sampling_location_id=1,
            harvest_method_id=1,
            collection_method_id=1,
            field_storage_method_id=1,
            field_storage_duration_value=14,
            field_storage_duration_unit_id=4,
            note="Sensitive grower note",
        )
        fs_jaguar = FieldSample(
            id=11,
            name="FS-JAG-001",
            resource_id=1,
            provider_id=2,
            sampling_location_id=1,
        )
        session.add_all([fs_valid, fs_jaguar])

        # Multiple FieldSampleCondition rows for fs_valid (tests fan-out prevention)
        fsc1 = FieldSampleCondition(
            id=1, field_sample_id=10, ag_treatment_id=1, processing_method_id=1
        )
        fsc2 = FieldSampleCondition(
            id=2, field_sample_id=10, ag_treatment_id=2, processing_method_id=2
        )
        fsc3_dup = FieldSampleCondition(
            id=3, field_sample_id=10, ag_treatment_id=1, processing_method_id=1
        )
        session.add_all([fsc1, fsc2, fsc3_dup])

        pma = PreparationMethodAbbreviation(id=1, name="MILL-2MM")
        prep_method = PreparationMethod(
            id=1,
            name="Knife Mill 2mm",
            prep_method_abbrev_id=1,
            prep_temp_c=45,
            drying_step=True,
        )
        ps_valid = PreparedSample(
            id=100,
            name="PS-ALM-001",
            field_sample_id=10,
            prep_method_id=1,
            note="Sensitive prep note",
        )
        ps_jaguar = PreparedSample(
            id=101,
            name="PS-JAG-001",
            field_sample_id=11,
            prep_method_id=1,
        )
        session.add_all([pma, prep_method, ps_valid, ps_jaguar])

        exp1 = Experiment(id=1, name="EXP-001")
        exp_bad_sum = Experiment(id=2, name="EXP-BAD-SUM")
        session.add_all([exp1, exp_bad_sum])

        # Passing Proximate replicates with experiment_id = NULL (tests coalesce(-1) join!)
        prox_rep1 = ProximateRecord(
            id=1,
            record_id="PROX-REP-1",
            resource_id=1,
            prepared_sample_id=100,
            method_id=1,
            experiment_id=None,
            technical_replicate_no=1,
            technical_replicate_total=2,
            qc_pass="pass",
        )
        prox_rep2 = ProximateRecord(
            id=2,
            record_id="PROX-REP-2",
            resource_id=1,
            prepared_sample_id=100,
            method_id=1,
            experiment_id=None,
            technical_replicate_no=2,
            technical_replicate_total=2,
            qc_pass="pass",
        )
        # Passing Compositional record with experiment_id = 1
        comp_rep1 = CompositionalRecord(
            id=1,
            record_id="COMP-REP-1",
            resource_id=1,
            prepared_sample_id=100,
            method_id=1,
            experiment_id=1,
            technical_replicate_no=1,
            technical_replicate_total=1,
            qc_pass="pass",
        )
        # Passing Calorimetry record
        cal_rep1 = CalorimetryRecord(
            id=1,
            record_id="CAL-REP-1",
            resource_id=1,
            prepared_sample_id=100,
            method_id=1,
            experiment_id=1,
            technical_replicate_no=1,
            technical_replicate_total=1,
            qc_pass="pass",
        )
        # Passing ICP record
        icp_rep1 = IcpRecord(
            id=1,
            record_id="ICP-REP-1",
            resource_id=1,
            prepared_sample_id=100,
            method_id=1,
            experiment_id=1,
            technical_replicate_no=1,
            technical_replicate_total=1,
            qc_pass="pass",
        )
        # Failing QC record (should be excluded)
        prox_fail = ProximateRecord(
            id=3,
            record_id="PROX-FAIL",
            resource_id=1,
            prepared_sample_id=100,
            method_id=1,
            experiment_id=1,
            qc_pass="fail",
        )
        # Unreviewed NULL qc_pass record (should be excluded — Blocking Bug #2)
        prox_null_qc = ProximateRecord(
            id=7,
            record_id="PROX-NULL-QC",
            resource_id=1,
            prepared_sample_id=100,
            method_id=1,
            experiment_id=1,
            qc_pass=None,
        )
        # Jaguar provider record (should be excluded)
        prox_jaguar = ProximateRecord(
            id=4,
            record_id="PROX-JAGUAR",
            resource_id=1,
            prepared_sample_id=101,
            method_id=1,
            experiment_id=1,
            qc_pass="pass",
        )
        # Sargassum resource record (should be excluded)
        prox_sargassum = ProximateRecord(
            id=5,
            record_id="PROX-SARGASSUM",
            resource_id=2,
            prepared_sample_id=100,
            method_id=1,
            experiment_id=1,
            qc_pass="pass",
        )
        # Bad sum experiment (> 105% average sum -> should be excluded by sum constraint)
        prox_bad_sum = ProximateRecord(
            id=6,
            record_id="PROX-BAD-SUM",
            resource_id=1,
            prepared_sample_id=100,
            method_id=1,
            experiment_id=2,
            qc_pass="pass",
        )
        # Stage 1 CompositionalRecord with colliding record_id "PROX-REP-1" and qc_pass="fail"
        # Verifies that compound join on (record_id, record_type) prevents cross-type collision
        comp_colliding = CompositionalRecord(
            id=2,
            record_id="PROX-REP-1",
            resource_id=2,
            prepared_sample_id=101,
            method_id=1,
            experiment_id=1,
            qc_pass="fail",
        )
        # Deferred Stage 2 XrfRecord with colliding record_id "PROX-REP-1" and qc_pass="fail"
        xrf_colliding = XrfRecord(
            id=1,
            record_id="PROX-REP-1",
            resource_id=2,
            prepared_sample_id=101,
            method_id=1,
            experiment_id=1,
            qc_pass="fail",
        )
        # Stage 2 UltimateRecord with colliding record_id "PROX-REP-1"
        ult_colliding = UltimateRecord(
            id=1,
            record_id="PROX-REP-1",
            resource_id=1,
            prepared_sample_id=100,
            method_id=1,
            experiment_id=1,
            qc_pass="pass",
        )
        session.add_all(
            [
                prox_rep1,
                prox_rep2,
                comp_rep1,
                cal_rep1,
                icp_rep1,
                prox_fail,
                prox_null_qc,
                prox_jaguar,
                prox_sargassum,
                prox_bad_sum,
                comp_colliding,
                xrf_colliding,
                ult_colliding,
            ]
        )

        # Observations:
        # 1-2: Moisture replicate 1 (8.0%) and replicate 2 (10.0%) -> mean=9.0, std_dev=sqrt(2)
        # 3: Ash solids replicate 1 (5.0%)
        # 16: Volatile solids replicate 1 (86.0%) -> proximate_sum = 9.0 + 5.0 + 86.0 = 100.0 (in [95, 105])
        # 4: Glucan compositional (32.5%)
        # 17: Xylan compositional (15.0%)
        # 18: Lignin compositional (20.0%) -> compositional_sum = 67.5 (in [40, 105])
        # 5: HHV calorimetry (18.4 MJ/kg)
        # 6: Calcium ICP (12500.0 ppm)
        # Excluded observations:
        # 9: Out-of-bounds ICP (> 500,000 ppm) on icp_rep1
        # 10: Observation on prox_fail
        # 11: Observation on prox_jaguar
        # 12: Observation on prox_sargassum
        # 13-14: Observations on prox_bad_sum (60% moisture + 55% ash = 115% > 105%)
        # 15: Observation on UltimateRecord (record_type="ultimate_record", record_id="PROX-REP-1")
        session.add_all(
            [
                Observation(
                    id=1,
                    record_id="PROX-REP-1",
                    record_type="proximate_record",
                    parameter_id=1,
                    value=8.0,
                    unit_id=1,
                ),
                Observation(
                    id=2,
                    record_id="PROX-REP-2",
                    record_type="proximate_record",
                    parameter_id=1,
                    value=10.0,
                    unit_id=1,
                ),
                Observation(
                    id=3,
                    record_id="PROX-REP-1",
                    record_type="proximate_record",
                    parameter_id=2,
                    value=5.0,
                    unit_id=1,
                ),
                Observation(
                    id=16,
                    record_id="PROX-REP-1",
                    record_type="proximate_record",
                    parameter_id=8,
                    value=86.0,
                    unit_id=1,
                ),
                Observation(
                    id=4,
                    record_id="COMP-REP-1",
                    record_type="compositional_record",
                    parameter_id=3,
                    value=32.5,
                    unit_id=1,
                ),
                Observation(
                    id=17,
                    record_id="COMP-REP-1",
                    record_type="compositional_record",
                    parameter_id=9,
                    value=15.0,
                    unit_id=1,
                ),
                Observation(
                    id=18,
                    record_id="COMP-REP-1",
                    record_type="compositional_record",
                    parameter_id=10,
                    value=20.0,
                    unit_id=1,
                ),
                Observation(
                    id=5,
                    record_id="CAL-REP-1",
                    record_type="calorimetry_record",
                    parameter_id=4,
                    value=18.4,
                    unit_id=2,
                ),
                Observation(
                    id=6,
                    record_id="ICP-REP-1",
                    record_type="icp_record",
                    parameter_id=5,
                    value=12500.0,
                    unit_id=3,
                ),
                Observation(
                    id=9,
                    record_id="ICP-REP-1",
                    record_type="icp_record",
                    parameter_id=6,
                    value=600000.0,
                    unit_id=3,
                ),
                Observation(
                    id=10,
                    record_id="PROX-FAIL",
                    record_type="proximate_record",
                    parameter_id=1,
                    value=9.0,
                    unit_id=1,
                ),
                Observation(
                    id=11,
                    record_id="PROX-JAGUAR",
                    record_type="proximate_record",
                    parameter_id=1,
                    value=9.0,
                    unit_id=1,
                ),
                Observation(
                    id=12,
                    record_id="PROX-SARGASSUM",
                    record_type="proximate_record",
                    parameter_id=1,
                    value=9.0,
                    unit_id=1,
                ),
                Observation(
                    id=13,
                    record_id="PROX-BAD-SUM",
                    record_type="proximate_record",
                    parameter_id=1,
                    value=60.0,
                    unit_id=1,
                ),
                Observation(
                    id=14,
                    record_id="PROX-BAD-SUM",
                    record_type="proximate_record",
                    parameter_id=2,
                    value=55.0,
                    unit_id=1,
                ),
                Observation(
                    id=15,
                    record_id="PROX-REP-1",
                    record_type="ultimate_record",
                    parameter_id=7,
                    value=45.0,
                    unit_id=1,
                ),
                Observation(
                    id=19,
                    record_id="PROX-NULL-QC",
                    record_type="proximate_record",
                    parameter_id=1,
                    value=9.5,
                    unit_id=1,
                ),
            ]
        )
        session.commit()

        # --- Assert View 1: mv_resources (COUNT(DISTINCT ...)) ---
        res_rows = session.execute(mv_resources).mappings().all()
        assert len(res_rows) == 1
        r_row = res_rows[0]
        assert r_row["resource_name"] == "almond_hulls"
        assert r_row["field_sample_count"] == 1
        assert r_row["prepared_sample_count"] == 1
        assert r_row["provider_count"] == 1
        assert r_row["observation_count"] == 8
        assert r_row["has_proximate"] is True
        assert r_row["has_compositional"] is True
        assert r_row["has_icp"] is True
        assert "has_xrf" not in r_row
        assert "has_calorimetry" not in r_row

        # --- Assert View 2: mv_analytical_summary ---
        as_rows = session.execute(mv_analytical_summary).mappings().all()
        as_by_param = {r["parameter_name"]: r for r in as_rows}
        assert set(as_by_param.keys()) == {
            "moisture",
            "ash solids",
            "volatile solids",
            "glucan",
            "xylan",
            "lignin",
            "calcium",
        }
        assert float(as_by_param["moisture"]["mean_value"]) == pytest.approx(9.0)
        assert float(as_by_param["moisture"]["std_dev"]) == pytest.approx(math.sqrt(2.0))
        assert float(as_by_param["moisture"]["min_value"]) == pytest.approx(8.0)
        assert float(as_by_param["moisture"]["max_value"]) == pytest.approx(10.0)
        assert as_by_param["moisture"]["observation_count"] == 2
        assert as_by_param["moisture"]["prepared_sample_count"] == 1
        assert as_by_param["moisture"]["field_sample_count"] == 1
        assert as_by_param["moisture"]["provider_count"] == 1

        # --- Assert ETL Load Date Cutoff (MAX_ETL_LOAD_DATE = 2026-12-31) ---
        prox_on_cutoff = ProximateRecord(
            id=98,
            record_id="PROX-ON-CUTOFF",
            resource_id=1,
            prepared_sample_id=100,
            method_id=1,
            experiment_id=None,
            technical_replicate_no=3,
            qc_pass="pass",
            created_at=datetime(2026, 12, 31, 12, 0, 0),
        )
        obs_on_cutoff = Observation(
            id=98,
            record_id="PROX-ON-CUTOFF",
            record_type="proximate_record",
            parameter_id=1,
            value=9.0,
            unit_id=1,
        )
        prox_future = ProximateRecord(
            id=99,
            record_id="PROX-FUTURE",
            resource_id=1,
            prepared_sample_id=100,
            method_id=1,
            experiment_id=None,
            technical_replicate_no=4,
            qc_pass="pass",
            created_at=datetime(2027, 1, 1, 12, 0, 0),
        )
        obs_future = Observation(
            id=99,
            record_id="PROX-FUTURE",
            record_type="proximate_record",
            parameter_id=1,
            value=11.0,
            unit_id=1,
        )
        session.add_all([prox_on_cutoff, obs_on_cutoff, prox_future, obs_future])
        session.commit()

        as_after_future = {
            r["parameter_name"]: r
            for r in session.execute(mv_analytical_summary).mappings().all()
        }
        assert as_after_future["moisture"]["observation_count"] == 3

        # --- Assert Duplicate Case/Whitespace Resource Normalization & Non-Frankenstein Metadata ---
        rc_secondary = ResourceClass(id=2, name="ZZZ Secondary Class")
        pag_walnut = PrimaryAgProduct(id=2, name="Walnuts")
        pag_secondary = PrimaryAgProduct(id=3, name="AAA Secondary Product")
        res_walnut_canonical = Resource(
            id=20,
            name=" Walnut Shells ",
            resource_code="WAL-01",
            description="Primary canonical walnut description",
            resource_class_id=1,
            primary_ag_product_id=2,
        )
        res_walnut_dup = Resource(
            id=21,
            name="walnut shells",
            resource_code="WAL-02",
            description="AAA Secondary description that would win independent MIN()",
            resource_class_id=2,
            primary_ag_product_id=3,
        )
        icp_walnut_1 = IcpRecord(
            id=20,
            record_id="ICP-WAL-1",
            resource_id=20,
            prepared_sample_id=100,
            method_id=1,
            experiment_id=1,
            technical_replicate_no=1,
            qc_pass="pass",
        )
        icp_walnut_2 = IcpRecord(
            id=21,
            record_id="ICP-WAL-2",
            resource_id=21,
            prepared_sample_id=100,
            method_id=1,
            experiment_id=1,
            technical_replicate_no=2,
            qc_pass="pass",
        )
        obs_walnut_1 = Observation(
            id=120,
            record_id="ICP-WAL-1",
            record_type="icp_record",
            parameter_id=5,
            value=1000.0,
            unit_id=3,
        )
        obs_walnut_2 = Observation(
            id=121,
            record_id="ICP-WAL-2",
            record_type="icp_record",
            parameter_id=5,
            value=2000.0,
            unit_id=3,
        )
        session.add_all(
            [
                rc_secondary,
                pag_walnut,
                pag_secondary,
                res_walnut_canonical,
                res_walnut_dup,
                icp_walnut_1,
                icp_walnut_2,
                obs_walnut_1,
                obs_walnut_2,
            ]
        )
        session.commit()

        res_by_name = {
            r["resource_name"]: r
            for r in session.execute(mv_resources).mappings().all()
        }
        assert set(res_by_name.keys()) == {"almond_hulls", "walnut shells"}
        walnut_meta = res_by_name["walnut shells"]
        assert walnut_meta["description"] == "Primary canonical walnut description"
        assert walnut_meta["resource_class"] == "Agricultural Byproduct"
        assert walnut_meta["primary_ag_product"] == "Walnuts"
        assert walnut_meta["observation_count"] == 2

        walnut_summaries = [
            r
            for r in session.execute(mv_analytical_summary).mappings().all()
            if "walnut" in r["resource_name"].lower()
        ]
        assert len(walnut_summaries) == 1
        assert walnut_summaries[0]["resource_name"] == "walnut shells"
        assert walnut_summaries[0]["observation_count"] == 2
        assert float(walnut_summaries[0]["mean_value"]) == pytest.approx(1500.0)


def test_refresh_all_views_warns_on_zero_rows_when_log_summary_is_false(
    capsys: pytest.CaptureFixture[str],
):
    """Verify refresh_all_views() emits the 0-row drop warning even when log_summary=False."""
    from ca_biositing.datamodels.views import refresh_all_views

    counts = {
        "biocirv_public.mv_resources": [36, 0],
        "biocirv_public.mv_analytical_summary": [451, 451],
    }

    class _FakeResult:
        def __init__(self, scalar_val=None, scalars_list=None):
            self._scalar_val = scalar_val
            self._scalars_list = scalars_list or []

        def scalar(self):
            return self._scalar_val

        def scalars(self):
            return self

        def all(self):
            return self._scalars_list

    class _FakeConn:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, stmt):
            sql = str(stmt)
            if "FROM pg_matviews" in sql:
                return _FakeResult(scalars_list=[])
            for table_key, seq in counts.items():
                if f"SELECT COUNT(*) FROM {table_key}" in sql:
                    return _FakeResult(scalar_val=seq.pop(0))
            return _FakeResult(scalar_val=10)

        def commit(self):
            pass

    class _FakeEngine:
        def connect(self):
            return _FakeConn()

    # Call with default log_summary=False (matches production ETL callers)
    refresh_all_views(_FakeEngine())
    captured = capsys.readouterr().out
    assert (
        "[WARNING] biocirv_public.mv_resources dropped from 36 to 0 rows"
        in captured
    )
    assert "mv_analytical_summary dropped" not in captured
