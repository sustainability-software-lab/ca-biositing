"""Update analysis_data_view to filter USDA records and fix NameError

Revision ID: 3b255400a04e
Revises: 2605c6e2b9da
Create Date: 2026-02-26 16:29:59.500796

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import dialect as pg_dialect

# Import materialized view definitions
from ca_biositing.datamodels.views import (
    VIEW_SCHEMA,
    ANALYSIS_DATA_VIEW,
    ANALYSIS_AVERAGE_VIEW_SQL
)


# revision identifiers, used by Alembic.
revision: str = '3b255400a04e'
down_revision: Union[str, Sequence[str], None] = '2605c6e2b9da'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Drop dependent view first
    op.execute(f"DROP MATERIALIZED VIEW IF EXISTS {VIEW_SCHEMA}.analysis_average_view CASCADE")

    # Drop and recreate analysis_data_view
    op.execute(f"DROP MATERIALIZED VIEW IF EXISTS {VIEW_SCHEMA}.analysis_data_view CASCADE")

    compiled = ANALYSIS_DATA_VIEW.compile(
        dialect=pg_dialect(), compile_kwargs={"literal_binds": True}
    )
    op.execute(
        f"CREATE MATERIALIZED VIEW {VIEW_SCHEMA}.analysis_data_view AS {compiled}"
    )

    # Recreate analysis_average_view
    op.execute(
        f"CREATE MATERIALIZED VIEW {VIEW_SCHEMA}.analysis_average_view AS "
        f"{ANALYSIS_AVERAGE_VIEW_SQL}"
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Since we don't store the old view definition here, we just drop.
    # In a real scenario, we might want to revert the filter.
    op.execute(f"DROP MATERIALIZED VIEW IF EXISTS {VIEW_SCHEMA}.analysis_average_view CASCADE")
    op.execute(f"DROP MATERIALIZED VIEW IF EXISTS {VIEW_SCHEMA}.analysis_data_view CASCADE")
