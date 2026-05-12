"""add_materialized_views

Revision ID: 9c5c72c6d059
Revises: f5c8c031aef9
Create Date: 2026-02-11 21:25:31.229772

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import dialect as pg_dialect

# Import materialized view definitions
from ca_biositing.datamodels.views import (
    VIEW_SCHEMA,
    VIEW_DEFINITIONS,
    ANALYSIS_AVERAGE_VIEW_SQL,
    SPATIAL_VIEW_INDEXES,
)

# revision identifiers, used by Alembic.
revision: str = '9c5c72c6d059'
down_revision: Union[str, Sequence[str], None] = 'f5c8c031aef9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create materialized views from Core select() expressions
    for view_name, view_query in VIEW_DEFINITIONS:
        compiled = view_query.compile(
            dialect=pg_dialect(), compile_kwargs={"literal_binds": True}
        )
        op.execute(
            f"CREATE MATERIALIZED VIEW {VIEW_SCHEMA}.{view_name} AS {compiled}"
        )

    # Create analysis_average_view (depends on analysis_data_view)
    op.execute(
        f"CREATE MATERIALIZED VIEW {VIEW_SCHEMA}.analysis_average_view AS "
        f"{ANALYSIS_AVERAGE_VIEW_SQL}"
    )

    # Create spatial indexes
    for idx_name, view_name, column in SPATIAL_VIEW_INDEXES:
        op.execute(
            f"CREATE INDEX IF NOT EXISTS {idx_name} ON {VIEW_SCHEMA}.{view_name} "
            f"USING GIST ({column})"
        )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop materialized views in reverse order
    op.execute(f"DROP MATERIALIZED VIEW IF EXISTS {VIEW_SCHEMA}.analysis_average_view CASCADE")
    for view_name, _ in reversed(VIEW_DEFINITIONS):
        op.execute(f"DROP MATERIALIZED VIEW IF EXISTS {VIEW_SCHEMA}.{view_name} CASCADE")
