"""Tests for `biocirv_public` materialized view definitions.

Covers:
1. PostgreSQL dialect compilation (`literal_binds=True`) for all 5 views.
2. Strict privacy & Stage 1 scope assertions on compiled SQL (no PII/fine-location/note
   columns, no Stage 2 analysis tables).
3. Functional SQLite query execution verifying:
   - All `common.py` QC & privacy filters (`get_resource_filter`, `get_provider_filter`,
     `get_qc_status_filter` including `qc_pass IS NULL` exclusion, `get_icp_filter`, and
     `get_sum_constraints_subquery`).
   - NULL-safe `coalesce(experiment_id, -1)` sum-constraint join for records with
     `experiment_id IS NULL`.
   - Collision-safe compound-predicate polymorphic outerjoin on `(record_id, record_type)`.
   - `FieldSampleCondition` pre-aggregation preventing `(prepared_sample_id, field_sample_id)`
     row fan-out in `mv_samples` and deterministic `ORDER BY` in `string_agg`.
   - `COUNT(DISTINCT ...)` entity counts in `mv_resources` (including `replicate_record_count`).
   - Technical replicate `mean_value` and `std_dev` in `mv_sample_summary` and
     `mv_analytical_summary`.
4. Alembic migration `0027` isolation (never drops pre-existing `data_portal` or `ca_biositing` views).
"""

from __future__ import annotations

import math
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Session

from ca_biositing.datamodels.biocirv_public_views import (
    BIOCIRV_PUBLIC_VIEW_NAMES,
    mv_analytical_observations,
    mv_analytical_summary,
    mv_resources,
    mv_sample_summary,
    mv_samples,
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
    "mv_analytical_observations": mv_analytical_observations,
    "mv_samples": mv_samples,
    "mv_resources": mv_resources,
    "mv_sample_summary": mv_sample_summary,
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
    """Verify explicit dependency ordering places mv_analytical_observations first."""
    assert BIOCIRV_PUBLIC_VIEW_NAMES[0] == "mv_analytical_observations"
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
        "ultimate_record",
        "xrd_record",
        "ftnir_record",
        "fermentation_record",
        "gasification_record",
        "pretreatment_record",
    ]
    for token in forbidden_tokens:
        assert token not in sql, f"Forbidden token {token!r} found in {view_name} SQL"


def test_mv_samples_compiles_deterministic_ordered_string_agg_on_postgres():
    """Verify mv_samples compiles string_agg with explicit ORDER BY on PostgreSQL."""
    sql = compile_pg(mv_samples).lower()
    assert (
        "string_agg(distinct_ag_treatments.ag_treatment_name, '; ' order by distinct_ag_treatments.ag_treatment_name asc)"
        in sql
    )
    assert (
        "string_agg(distinct_processing_methods.processing_method_name, '; ' order by distinct_processing_methods.processing_method_name asc)"
        in sql
    )


def test_migration_0027_is_scoped_exclusively_to_biocirv_public():
    """Verify migration 0027 does not drop or recreate pre-existing data_portal/ca_biositing views."""
    repo_root = Path(__file__).resolve().parents[4]
    migration_path = (
        repo_root
        / "alembic"
        / "versions"
        / "0027_create_biocirv_public_schema_and_views.py"
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
            f"Migration 0027 must not touch unrelated view {view_name}"
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
        # Stage 1 XrfRecord with colliding record_id "PROX-REP-1" and qc_pass="fail"
        # Verifies that compound join on (record_id, record_type) prevents cross-type collision
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

        # --- Assert View 1: mv_analytical_observations ---
        obs_rows = session.execute(mv_analytical_observations).mappings().all()
        obs_ids = [r["observation_id"] for r in obs_rows]
        assert obs_ids == [1, 2, 3, 4, 5, 6, 16, 17, 18]
        assert all(r["provider_codename"] == "PROVIDER_ALPHA" for r in obs_rows)
        assert all(r["county_name"] == "San Joaquin" for r in obs_rows)
        assert all(r["geoid"] == "06077" for r in obs_rows)

        # --- Assert View 2: mv_samples (no fan-out on FieldSampleCondition) ---
        sample_rows = session.execute(mv_samples).mappings().all()
        assert len(sample_rows) == 1
        s_row = sample_rows[0]
        assert s_row["prepared_sample_id"] == 100
        assert s_row["field_sample_id"] == 10
        assert s_row["ag_treatment_name"] == "irrigated; organic"
        assert s_row["processing_method_name"] == "hulled; screened"
        # 5 distinct replicate records (PROX-REP-1, PROX-REP-2, COMP-REP-1, CAL-REP-1, ICP-REP-1)
        # vs 9 distinct parameter observations
        assert s_row["replicate_record_count"] == 5
        assert s_row["observation_count"] == 9

        # --- Assert View 3: mv_resources (COUNT(DISTINCT ...)) ---
        res_rows = session.execute(mv_resources).mappings().all()
        assert len(res_rows) == 1
        r_row = res_rows[0]
        assert r_row["resource_id"] == 1
        assert r_row["resource_name"] == "almond_hulls"
        assert r_row["field_sample_count"] == 1
        assert r_row["prepared_sample_count"] == 1
        assert r_row["provider_count"] == 1
        assert r_row["county_count"] == 1
        assert r_row["replicate_record_count"] == 5
        assert r_row["observation_count"] == 9
        assert r_row["has_proximate"] is True
        assert r_row["has_compositional"] is True
        assert r_row["has_calorimetry"] is True
        assert r_row["has_icp"] is True
        assert r_row["has_xrf"] is False

        # --- Assert View 4: mv_sample_summary (replicate averaging & stddev) ---
        ss_rows = session.execute(mv_sample_summary).mappings().all()
        by_param = {r["parameter_name"]: r for r in ss_rows}
        assert set(by_param.keys()) == {
            "moisture",
            "ash solids",
            "volatile solids",
            "glucan",
            "xylan",
            "lignin",
            "higher_heating_value",
            "calcium",
        }
        moisture_row = by_param["moisture"]
        assert moisture_row["replicate_count"] == 2
        assert float(moisture_row["mean_value"]) == pytest.approx(9.0)
        assert float(moisture_row["std_dev"]) == pytest.approx(math.sqrt(2.0))
        assert float(moisture_row["min_value"]) == pytest.approx(8.0)
        assert float(moisture_row["max_value"]) == pytest.approx(10.0)
        assert moisture_row["drying_step"] is True

        # Single-replicate parameter has std_dev = None
        assert by_param["glucan"]["replicate_count"] == 1
        assert by_param["glucan"]["std_dev"] is None

        # --- Assert View 5: mv_analytical_summary ---
        as_rows = session.execute(mv_analytical_summary).mappings().all()
        as_by_param = {r["parameter_name"]: r for r in as_rows}
        assert float(as_by_param["moisture"]["mean_value"]) == pytest.approx(9.0)
        assert float(as_by_param["moisture"]["std_dev"]) == pytest.approx(math.sqrt(2.0))
        assert as_by_param["moisture"]["observation_count"] == 2
        assert as_by_param["moisture"]["prepared_sample_count"] == 1
        assert as_by_param["moisture"]["field_sample_count"] == 1
        assert as_by_param["moisture"]["provider_count"] == 1
