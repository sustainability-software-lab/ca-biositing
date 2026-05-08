"""add_usda_resource_commodity_view

Revision ID: d3f1e2a4b5c6
Revises: cfe7ab7b7a20
Create Date: 2026-03-07 00:00:00.000000

Adds usda_resource_commodity_view, a lightweight materialized view that maps
each resource name to its USDA commodity ID via ResourceUsdaCommodityMap.

This enables discovery endpoints (GET /v1/feedstocks/usda/census/resources and
GET /v1/feedstocks/usda/survey/resources) to resolve queryable resource names
from view columns only, preserving the view-as-source-of-truth principle
established in PR #159 / issue #158.
"""

from typing import Sequence, Union

from alembic import op
from sqlalchemy.dialects.postgresql import dialect as pg_dialect

from ca_biositing.datamodels.views import (
    USDA_RESOURCE_COMMODITY_VIEW,
    VIEW_SCHEMA,
)

# revision identifiers, used by Alembic.
revision: str = "d3f1e2a4b5c6"
down_revision: Union[str, Sequence[str], None] = "cfe7ab7b7a20"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_VIEW_NAME = "usda_resource_commodity_view"


def upgrade() -> None:
    """Create usda_resource_commodity_view."""
    compiled = USDA_RESOURCE_COMMODITY_VIEW.compile(
        dialect=pg_dialect(), compile_kwargs={"literal_binds": True}
    )
    op.execute(
        f"CREATE MATERIALIZED VIEW {VIEW_SCHEMA}.{_VIEW_NAME} AS {compiled}"
    )


def downgrade() -> None:
    """Drop usda_resource_commodity_view."""
    op.execute(
        f"DROP MATERIALIZED VIEW IF EXISTS {VIEW_SCHEMA}.{_VIEW_NAME} CASCADE"
    )
