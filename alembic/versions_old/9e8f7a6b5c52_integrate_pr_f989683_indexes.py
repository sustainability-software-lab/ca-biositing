"""
Integrate PR f989683 indexes - Phase C/D Part 2: Index creation

Creates 30 indexes across 10 materialized views per PDF specification:
- mv_biomass_search (6 indexes including UNIQUE)
- mv_biomass_composition (8 indexes including UNIQUE)
- mv_usda_county_production (3 indexes)
- mv_biomass_availability (1 UNIQUE index)
- mv_biomass_sample_stats (1 UNIQUE index)
- mv_biomass_fermentation (7 indexes with UNIQUE)
- mv_biomass_gasification (5 indexes with UNIQUE)
- mv_biomass_pricing (3 indexes)
- mv_biomass_end_uses (2 indexes including UNIQUE composite)
- mv_biomass_county_production (1 UNIQUE index)

Supports REFRESH MATERIALIZED VIEW CONCURRENTLY for views with UNIQUE indexes.

Revision ID: 9e8f7a6b5c52
Revises: 9e8f7a6b5c54
Create Date: 2026-04-07 04:25:00.000000
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9e8f7a6b5c52'
down_revision = '9e8f7a6b5c54'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ========== mv_biomass_search (6 indexes) ==========
    op.execute("""CREATE UNIQUE INDEX idx_mv_biomass_search_id ON data_portal.mv_biomass_search (id)""")
    op.execute("""CREATE INDEX idx_mv_biomass_search_search_vector ON data_portal.mv_biomass_search USING GIN (search_vector)""")
    op.execute("""CREATE INDEX idx_mv_biomass_search_name_trgm ON data_portal.mv_biomass_search USING GIN (name gin_trgm_ops)""")
    op.execute("""CREATE INDEX idx_mv_biomass_search_resource_class ON data_portal.mv_biomass_search (resource_class)""")
    op.execute("""CREATE INDEX idx_mv_biomass_search_resource_subclass ON data_portal.mv_biomass_search (resource_subclass)""")
    op.execute("""CREATE INDEX idx_mv_biomass_search_primary_product ON data_portal.mv_biomass_search (primary_product)""")

    # ========== mv_biomass_composition (8 indexes) ==========
    op.execute("""CREATE UNIQUE INDEX idx_mv_biomass_composition_id ON data_portal.mv_biomass_composition (id)""")
    op.execute("""CREATE INDEX idx_mv_biomass_composition_resource_id ON data_portal.mv_biomass_composition (resource_id)""")
    op.execute("""CREATE INDEX idx_mv_biomass_composition_geoid ON data_portal.mv_biomass_composition (geoid)""")
    op.execute("""CREATE INDEX idx_mv_biomass_composition_county ON data_portal.mv_biomass_composition (county)""")
    op.execute("""CREATE INDEX idx_mv_biomass_composition_analysis_type ON data_portal.mv_biomass_composition (analysis_type)""")
    op.execute("""CREATE INDEX idx_mv_biomass_composition_parameter_name ON data_portal.mv_biomass_composition (parameter_name)""")
    op.execute("""CREATE INDEX idx_mv_biomass_composition_resource_analysis ON data_portal.mv_biomass_composition (resource_id, analysis_type)""")
    op.execute("""CREATE INDEX idx_mv_biomass_composition_resource_geoid_analysis ON data_portal.mv_biomass_composition (resource_id, geoid, analysis_type)""")

    # ========== mv_usda_county_production (3 indexes) ==========
    op.execute("""CREATE UNIQUE INDEX idx_mv_usda_county_production_id ON data_portal.mv_usda_county_production (id)""")
    op.execute("""CREATE INDEX idx_mv_usda_county_production_resource_id ON data_portal.mv_usda_county_production (resource_id)""")
    op.execute("""CREATE INDEX idx_mv_usda_county_production_geoid ON data_portal.mv_usda_county_production (geoid)""")

    # ========== mv_biomass_availability (1 index) ==========
    op.execute("""CREATE UNIQUE INDEX idx_mv_biomass_availability_resource_id ON data_portal.mv_biomass_availability (resource_id)""")

    # ========== mv_biomass_sample_stats (1 index) ==========
    op.execute("""CREATE UNIQUE INDEX idx_mv_biomass_sample_stats_resource_id ON data_portal.mv_biomass_sample_stats (resource_id)""")

    # ========== mv_biomass_fermentation (7 indexes) ==========
    op.execute("""CREATE UNIQUE INDEX idx_mv_biomass_fermentation_id ON data_portal.mv_biomass_fermentation (id)""")
    op.execute("""CREATE INDEX idx_mv_biomass_fermentation_resource_id ON data_portal.mv_biomass_fermentation (resource_id)""")
    op.execute("""CREATE INDEX idx_mv_biomass_fermentation_geoid ON data_portal.mv_biomass_fermentation (geoid)""")
    op.execute("""CREATE INDEX idx_mv_biomass_fermentation_county ON data_portal.mv_biomass_fermentation (county)""")
    op.execute("""CREATE INDEX idx_mv_biomass_fermentation_strain_name ON data_portal.mv_biomass_fermentation (strain_name)""")
    op.execute("""CREATE INDEX idx_mv_biomass_fermentation_product_name ON data_portal.mv_biomass_fermentation (product_name)""")
    op.execute("""CREATE INDEX idx_mv_biomass_fermentation_resource_strain ON data_portal.mv_biomass_fermentation (resource_id, strain_name)""")

    # ========== mv_biomass_gasification (5 indexes) ==========
    op.execute("""CREATE UNIQUE INDEX idx_mv_biomass_gasification_id ON data_portal.mv_biomass_gasification (id)""")
    op.execute("""CREATE INDEX idx_mv_biomass_gasification_resource_id ON data_portal.mv_biomass_gasification (resource_id)""")
    op.execute("""CREATE INDEX idx_mv_biomass_gasification_reactor_type ON data_portal.mv_biomass_gasification (reactor_type)""")
    op.execute("""CREATE INDEX idx_mv_biomass_gasification_parameter_name ON data_portal.mv_biomass_gasification (parameter_name)""")
    op.execute("""CREATE INDEX idx_mv_biomass_gasification_resource_reactor_param ON data_portal.mv_biomass_gasification (resource_id, reactor_type, parameter_name)""")

    # ========== mv_biomass_pricing (3 indexes) ==========
    op.execute("""CREATE UNIQUE INDEX idx_mv_biomass_pricing_id ON data_portal.mv_biomass_pricing (id)""")
    op.execute("""CREATE INDEX idx_mv_biomass_pricing_commodity_name ON data_portal.mv_biomass_pricing (commodity_name)""")
    op.execute("""CREATE INDEX idx_mv_biomass_pricing_county ON data_portal.mv_biomass_pricing (county)""")

    # ========== mv_biomass_end_uses (2 indexes) ==========
    op.execute("""CREATE UNIQUE INDEX idx_mv_biomass_end_uses_resource_use_case ON data_portal.mv_biomass_end_uses (resource_id, use_case)""")
    op.execute("""CREATE INDEX idx_mv_biomass_end_uses_resource_id ON data_portal.mv_biomass_end_uses (resource_id)""")

    # ========== mv_biomass_county_production (1 index) ==========
    op.execute("""CREATE UNIQUE INDEX idx_mv_biomass_county_production_id ON data_portal.mv_biomass_county_production (id)""")


def downgrade() -> None:
    # Drop all 27 indexes in reverse order
    op.execute("DROP INDEX IF EXISTS data_portal.idx_mv_biomass_county_production_id")

    op.execute("DROP INDEX IF EXISTS data_portal.idx_mv_biomass_end_uses_resource_id")
    op.execute("DROP INDEX IF EXISTS data_portal.idx_mv_biomass_end_uses_resource_use_case")

    op.execute("DROP INDEX IF EXISTS data_portal.idx_mv_biomass_pricing_county")
    op.execute("DROP INDEX IF EXISTS data_portal.idx_mv_biomass_pricing_commodity_name")
    op.execute("DROP INDEX IF EXISTS data_portal.idx_mv_biomass_pricing_id")

    op.execute("DROP INDEX IF EXISTS data_portal.idx_mv_biomass_gasification_resource_reactor_param")
    op.execute("DROP INDEX IF EXISTS data_portal.idx_mv_biomass_gasification_parameter_name")
    op.execute("DROP INDEX IF EXISTS data_portal.idx_mv_biomass_gasification_reactor_type")
    op.execute("DROP INDEX IF EXISTS data_portal.idx_mv_biomass_gasification_resource_id")
    op.execute("DROP INDEX IF EXISTS data_portal.idx_mv_biomass_gasification_id")

    op.execute("DROP INDEX IF EXISTS data_portal.idx_mv_biomass_fermentation_resource_strain")
    op.execute("DROP INDEX IF EXISTS data_portal.idx_mv_biomass_fermentation_product_name")
    op.execute("DROP INDEX IF EXISTS data_portal.idx_mv_biomass_fermentation_strain_name")
    op.execute("DROP INDEX IF EXISTS data_portal.idx_mv_biomass_fermentation_county")
    op.execute("DROP INDEX IF EXISTS data_portal.idx_mv_biomass_fermentation_geoid")
    op.execute("DROP INDEX IF EXISTS data_portal.idx_mv_biomass_fermentation_resource_id")
    op.execute("DROP INDEX IF EXISTS data_portal.idx_mv_biomass_fermentation_id")

    op.execute("DROP INDEX IF EXISTS data_portal.idx_mv_biomass_sample_stats_resource_id")

    op.execute("DROP INDEX IF EXISTS data_portal.idx_mv_biomass_availability_resource_id")

    op.execute("DROP INDEX IF EXISTS data_portal.idx_mv_usda_county_production_geoid")
    op.execute("DROP INDEX IF EXISTS data_portal.idx_mv_usda_county_production_resource_id")
    op.execute("DROP INDEX IF EXISTS data_portal.idx_mv_usda_county_production_id")

    op.execute("DROP INDEX IF EXISTS data_portal.idx_mv_biomass_composition_resource_geoid_analysis")
    op.execute("DROP INDEX IF EXISTS data_portal.idx_mv_biomass_composition_resource_analysis")
    op.execute("DROP INDEX IF EXISTS data_portal.idx_mv_biomass_composition_parameter_name")
    op.execute("DROP INDEX IF EXISTS data_portal.idx_mv_biomass_composition_analysis_type")
    op.execute("DROP INDEX IF EXISTS data_portal.idx_mv_biomass_composition_county")
    op.execute("DROP INDEX IF EXISTS data_portal.idx_mv_biomass_composition_geoid")
    op.execute("DROP INDEX IF EXISTS data_portal.idx_mv_biomass_composition_resource_id")
    op.execute("DROP INDEX IF EXISTS data_portal.idx_mv_biomass_composition_id")

    op.execute("DROP INDEX IF EXISTS data_portal.idx_mv_biomass_search_primary_product")
    op.execute("DROP INDEX IF EXISTS data_portal.idx_mv_biomass_search_resource_subclass")
    op.execute("DROP INDEX IF EXISTS data_portal.idx_mv_biomass_search_resource_class")
    op.execute("DROP INDEX IF EXISTS data_portal.idx_mv_biomass_search_name_trgm")
    op.execute("DROP INDEX IF EXISTS data_portal.idx_mv_biomass_search_search_vector")
    op.execute("DROP INDEX IF EXISTS data_portal.idx_mv_biomass_search_id")
