"""squash_data_portal_additions

Revision ID: 63c0fedd3446
Revises: 90304bbf8365
Create Date: 2026-03-26 16:36:15.776754

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel
from ca_biositing.datamodels.data_portal_views import (
    mv_biomass_search,
    mv_biomass_composition,
    mv_biomass_county_production,
    mv_biomass_availability,
    mv_biomass_sample_stats,
    mv_biomass_fermentation,
    mv_biomass_gasification,
    mv_biomass_pricing,
    mv_usda_county_production
)

# revision identifiers, used by Alembic.
revision: str = '63c0fedd3446'
down_revision: Union[str, Sequence[str], None] = '90304bbf8365'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add uri to resource
    op.add_column('resource', sa.Column('uri', sqlmodel.sql.sqltypes.AutoString(), nullable=True))

    # Create data_portal schema
    op.execute("CREATE SCHEMA IF NOT EXISTS data_portal")

    # Helper to create MV
    def create_mv(name, stmt):
        compiled = stmt.compile(dialect=sa.dialects.postgresql.dialect(), compile_kwargs={"literal_binds": True})
        op.execute(f"CREATE MATERIALIZED VIEW data_portal.{name} AS {compiled}")

    create_mv("mv_biomass_search", mv_biomass_search)
    op.execute("CREATE UNIQUE INDEX idx_mv_biomass_search_id ON data_portal.mv_biomass_search (id)")

    create_mv("mv_biomass_composition", mv_biomass_composition)
    op.execute("CREATE UNIQUE INDEX idx_mv_biomass_composition_key ON data_portal.mv_biomass_composition (resource_id, analysis_type, parameter_name, unit)")

    create_mv("mv_biomass_county_production", mv_biomass_county_production)
    op.execute("CREATE UNIQUE INDEX idx_mv_biomass_county_production_id ON data_portal.mv_biomass_county_production (id)")

    create_mv("mv_biomass_availability", mv_biomass_availability)
    op.execute("CREATE UNIQUE INDEX idx_mv_biomass_availability_resource_id ON data_portal.mv_biomass_availability (resource_id)")

    create_mv("mv_biomass_sample_stats", mv_biomass_sample_stats)
    op.execute("CREATE UNIQUE INDEX idx_mv_biomass_sample_stats_resource_id ON data_portal.mv_biomass_sample_stats (resource_id)")

    create_mv("mv_biomass_fermentation", mv_biomass_fermentation)
    op.execute("CREATE UNIQUE INDEX idx_mv_biomass_fermentation_key ON data_portal.mv_biomass_fermentation (resource_id, strain_name, pretreatment_method, enzyme_name, product_name, unit)")

    create_mv("mv_biomass_gasification", mv_biomass_gasification)
    op.execute("CREATE UNIQUE INDEX idx_mv_biomass_gasification_key ON data_portal.mv_biomass_gasification (resource_id, parameter_name, reactor_type, unit)")

    create_mv("mv_biomass_pricing", mv_biomass_pricing)
    op.execute("CREATE UNIQUE INDEX idx_mv_biomass_pricing_id ON data_portal.mv_biomass_pricing (id)")

    create_mv("mv_usda_county_production", mv_usda_county_production)
    op.execute("CREATE UNIQUE INDEX idx_mv_usda_county_production_id ON data_portal.mv_usda_county_production (id)")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP SCHEMA IF EXISTS data_portal CASCADE")
    op.drop_column('resource', 'uri')
