"""Update views with lowercase normalization

Revision ID: 90304bbf8365
Revises: ee768a98ae28
Create Date: 2026-03-17 13:16:37.271094

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '90304bbf8365'
down_revision: Union[str, Sequence[str], None] = 'ee768a98ae28'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

from sqlalchemy.dialects.postgresql import dialect as pg_dialect
from ca_biositing.datamodels.views import (
    VIEW_SCHEMA,
    ANALYSIS_DATA_VIEW,
    ANALYSIS_AVERAGE_VIEW_SQL,
    USDA_CENSUS_VIEW,
    USDA_SURVEY_VIEW,
    BILLION_TON_TILESET_VIEW
)

def upgrade() -> None:
    """Upgrade schema."""
    # Drop dependent views first
    op.execute(f"DROP MATERIALIZED VIEW IF EXISTS {VIEW_SCHEMA}.analysis_average_view CASCADE")
    op.execute(f"DROP MATERIALIZED VIEW IF EXISTS {VIEW_SCHEMA}.analysis_data_view CASCADE")
    op.execute(f"DROP MATERIALIZED VIEW IF EXISTS {VIEW_SCHEMA}.usda_census_view CASCADE")
    op.execute(f"DROP MATERIALIZED VIEW IF EXISTS {VIEW_SCHEMA}.usda_survey_view CASCADE")
    op.execute(f"DROP MATERIALIZED VIEW IF EXISTS {VIEW_SCHEMA}.billion_ton_tileset_view CASCADE")

    # Recreate views with new definitions
    for view_name, definition in [
        ("analysis_data_view", ANALYSIS_DATA_VIEW),
        ("usda_census_view", USDA_CENSUS_VIEW),
        ("usda_survey_view", USDA_SURVEY_VIEW),
        ("billion_ton_tileset_view", BILLION_TON_TILESET_VIEW),
    ]:
        compiled = definition.compile(
            dialect=pg_dialect(), compile_kwargs={"literal_binds": True}
        )
        op.execute(f"CREATE MATERIALIZED VIEW {VIEW_SCHEMA}.{view_name} AS {compiled}")

    # Recreate analysis_average_view
    op.execute(
        f"CREATE MATERIALIZED VIEW {VIEW_SCHEMA}.analysis_average_view AS "
        f"{ANALYSIS_AVERAGE_VIEW_SQL}"
    )

    # Recreate indexes for analysis_data_view
    op.execute(f"CREATE INDEX IF NOT EXISTS idx_analysis_data_view_resource ON {VIEW_SCHEMA}.analysis_data_view (resource)")
    op.execute(f"CREATE INDEX IF NOT EXISTS idx_analysis_data_view_geoid ON {VIEW_SCHEMA}.analysis_data_view (geoid)")


def downgrade() -> None:
    """Downgrade schema."""
    # Since this is a specialized cleanup/fix migration,
    # downgrade just drops and lets the previous revision recreate if needed,
    # but practically we don't need complex downgrade logic for view column casing.
    op.execute(f"DROP MATERIALIZED VIEW IF EXISTS {VIEW_SCHEMA}.analysis_average_view CASCADE")
    op.execute(f"DROP MATERIALIZED VIEW IF EXISTS {VIEW_SCHEMA}.analysis_data_view CASCADE")
    op.execute(f"DROP MATERIALIZED VIEW IF EXISTS {VIEW_SCHEMA}.usda_census_view CASCADE")
    op.execute(f"DROP MATERIALIZED VIEW IF EXISTS {VIEW_SCHEMA}.usda_survey_view CASCADE")
    op.execute(f"DROP MATERIALIZED VIEW IF EXISTS {VIEW_SCHEMA}.billion_ton_tileset_view CASCADE")
