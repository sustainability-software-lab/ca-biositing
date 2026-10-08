"""Structural regression tests for data-quality filters applied by materialized views.

These tests compile each view's SQLAlchemy select() to PostgreSQL SQL and assert
on the compiled WHERE clause text. They do not hit a live database; they pin
down what the SQL *should* contain so the filter-centralization refactor
(common.py restructuring) can be verified to be behavior-preserving at each
phase. See plans/jiggly-crafting-planet.md for the phase-by-phase plan.
"""

from sqlalchemy.dialects import postgresql

from ca_biositing.datamodels import views as ca_views
from ca_biositing.datamodels.data_portal_views import (
    mv_biomass_composition,
    mv_biomass_fermentation,
    mv_biomass_gasification,
    mv_biomass_sample_stats,
    mv_usda_county_production,
)
from ca_biositing.datamodels.data_portal_views.common import EXCLUDED_PROVIDERS, EXCLUDED_RESOURCES


def compile_sql(select_expr) -> str:
    """Compile a SQLAlchemy select() to literal PostgreSQL SQL text for inspection."""
    return str(
        select_expr.compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )


def test_excluded_resources_are_defined():
    """EXCLUDED_RESOURCES should contain the known problematic resource names."""
    assert "sargassum" in EXCLUDED_RESOURCES
    assert "almond woodchips" in EXCLUDED_RESOURCES


def test_excluded_providers_are_defined():
    """EXCLUDED_PROVIDERS should contain the known problematic provider codenames."""
    assert "jaguar" in EXCLUDED_PROVIDERS


def test_analysis_data_view_excludes_resources_and_providers():
    sql = compile_sql(ca_views.ANALYSIS_DATA_VIEW)
    assert "sargassum" in sql
    assert "jaguar" in sql


def test_analysis_data_view_has_proximate_and_compositional_sum_bounds():
    sql = compile_sql(ca_views.ANALYSIS_DATA_VIEW)
    assert "95" in sql
    assert "105" in sql
    assert "40" in sql


def test_analysis_data_view_missing_icp_ppm_cap_pre_phase2():
    """Documents the #476 drift: views.py does not apply the ICP >500,000ppm cap.

    This test is expected to need updating once Phase 2 adds the cap to
    ANALYSIS_DATA_VIEW - at that point this should assert the cap IS present,
    mirroring mv_biomass_composition's behavior.
    """
    sql = compile_sql(ca_views.ANALYSIS_DATA_VIEW)
    assert "500000" not in sql


def test_analysis_data_view_has_qc_pass_fail_check():
    sql = compile_sql(ca_views.ANALYSIS_DATA_VIEW)
    assert "qc_pass" in sql
    assert "'fail'" in sql


def test_analysis_data_view_has_ultimate_whitelist():
    sql = compile_sql(ca_views.ANALYSIS_DATA_VIEW)
    for param in ["carbon", "nitrogen", "oxygen", "sulfur", "hydrogen"]:
        assert param in sql


def test_mv_biomass_composition_excludes_resources():
    sql = compile_sql(mv_biomass_composition)
    assert "sargassum" in sql


def test_mv_biomass_composition_has_sum_bounds_and_icp_cap():
    sql = compile_sql(mv_biomass_composition)
    assert "95" in sql
    assert "105" in sql
    assert "40" in sql
    assert "500000" in sql


def test_mv_biomass_composition_has_qc_pass_fail_check():
    sql = compile_sql(mv_biomass_composition)
    assert "qc_pass" in sql
    assert "'fail'" in sql


def test_mv_biomass_fermentation_excludes_resources_and_providers():
    sql = compile_sql(mv_biomass_fermentation)
    assert "sargassum" in sql
    assert "jaguar" in sql
    assert "qc_pass" in sql
    assert "'fail'" in sql


def test_mv_biomass_gasification_excludes_resources_and_providers():
    sql = compile_sql(mv_biomass_gasification)
    assert "sargassum" in sql
    assert "jaguar" in sql
    assert "qc_pass" in sql
    assert "'fail'" in sql


def test_mv_biomass_sample_stats_excludes_resources_and_providers():
    sql = compile_sql(mv_biomass_sample_stats)
    assert "sargassum" in sql
    assert "jaguar" in sql


def test_mv_usda_county_production_has_min_year_filter():
    sql = compile_sql(mv_usda_county_production)
    assert "2017" in sql


def test_mv_usda_county_production_has_no_resource_or_qc_filter():
    """Documents the deliberate (undocumented-until-Phase-4) absence of
    resource/provider/QC filtering on raw USDA county production data."""
    sql = compile_sql(mv_usda_county_production)
    assert "sargassum" not in sql
    assert "jaguar" not in sql
