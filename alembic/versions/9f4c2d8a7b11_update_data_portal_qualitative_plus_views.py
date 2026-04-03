"""Update data portal qualitative-plus materialized views

Revision ID: 9f4c2d8a7b11
Revises: 607a6a005a3b
Create Date: 2026-04-02 14:05:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from ca_biositing.datamodels.data_portal_views import (
    mv_biomass_end_uses,
    mv_biomass_pricing,
    mv_biomass_search,
    mv_usda_county_production,
)

# revision identifiers, used by Alembic.
revision: str = "9f4c2d8a7b11"
down_revision: Union[str, Sequence[str], None] = "607a6a005a3b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


DATA_PORTAL_SCHEMA = "data_portal"


def _create_mv(name: str, stmt) -> None:
    compiled = stmt.compile(
        dialect=sa.dialects.postgresql.dialect(),
        compile_kwargs={"literal_binds": True},
    )
    op.execute(f"CREATE MATERIALIZED VIEW {DATA_PORTAL_SCHEMA}.{name} AS {compiled}")


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(f"CREATE SCHEMA IF NOT EXISTS {DATA_PORTAL_SCHEMA}")

    op.execute(
        f"DROP MATERIALIZED VIEW IF EXISTS {DATA_PORTAL_SCHEMA}.mv_biomass_county_production CASCADE"
    )

    # Existing views to replace with updated definitions
    op.execute(
        f"DROP MATERIALIZED VIEW IF EXISTS {DATA_PORTAL_SCHEMA}.mv_biomass_search CASCADE"
    )
    # Pricing may already exist from prior migrations; we recreate from contract definition
    op.execute(
        f"DROP MATERIALIZED VIEW IF EXISTS {DATA_PORTAL_SCHEMA}.mv_biomass_pricing CASCADE"
    )

    # End uses is newly introduced for the frontend contract
    op.execute(
        f"DROP MATERIALIZED VIEW IF EXISTS {DATA_PORTAL_SCHEMA}.mv_biomass_end_uses CASCADE"
    )
    op.execute(
        f"DROP MATERIALIZED VIEW IF EXISTS {DATA_PORTAL_SCHEMA}.mv_usda_county_production CASCADE"
    )

    _create_mv("mv_biomass_search", mv_biomass_search)
    _create_mv("mv_biomass_pricing", mv_biomass_pricing)
    _create_mv("mv_biomass_end_uses", mv_biomass_end_uses)
    _create_mv("mv_usda_county_production", mv_usda_county_production)

    op.execute(
        f"CREATE UNIQUE INDEX idx_mv_biomass_search_id "
        f"ON {DATA_PORTAL_SCHEMA}.mv_biomass_search (id)"
    )
    op.execute(
        f"CREATE UNIQUE INDEX idx_mv_biomass_pricing_key "
        f"ON {DATA_PORTAL_SCHEMA}.mv_biomass_pricing (commodity_name, county, geoid, report_date)"
    )
    op.execute(
        f"CREATE UNIQUE INDEX idx_mv_biomass_end_uses_key "
        f"ON {DATA_PORTAL_SCHEMA}.mv_biomass_end_uses (resource_id, use_case)"
    )
    op.execute(
        f"CREATE UNIQUE INDEX idx_mv_usda_county_production_id "
        f"ON {DATA_PORTAL_SCHEMA}.mv_usda_county_production (id)"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        f"DROP MATERIALIZED VIEW IF EXISTS {DATA_PORTAL_SCHEMA}.mv_biomass_end_uses CASCADE"
    )
    op.execute(
        f"DROP MATERIALIZED VIEW IF EXISTS {DATA_PORTAL_SCHEMA}.mv_biomass_pricing CASCADE"
    )
    op.execute(
        f"DROP MATERIALIZED VIEW IF EXISTS {DATA_PORTAL_SCHEMA}.mv_biomass_search CASCADE"
    )
    op.execute(
        f"DROP MATERIALIZED VIEW IF EXISTS {DATA_PORTAL_SCHEMA}.mv_usda_county_production CASCADE"
    )
