"""Fix case-sensitivity in analysis_data_view joins

Revision ID: ee768a98ae28
Revises: 64de60aff03d
Create Date: 2026-03-11 15:42:40.838857

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
revision: str = 'ee768a98ae28'
down_revision: Union[str, Sequence[str], None] = '64de60aff03d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Snapshotted previous version SQL for downgrade (without LOWER() calls)
PREVIOUS_ANALYSIS_DATA_VIEW_SQL = """
SELECT
    obs.id,
    obs.record_id,
    obs.record_type,
    res.id AS resource_id,
    res.name AS resource,
    la.geography_id AS geoid,
    param.name AS parameter,
    obs.value,
    u.name AS unit,
    dt.name AS dimension,
    obs.dimension_value,
    du.name AS dimension_unit
FROM observation obs
JOIN parameter param ON obs.parameter_id = param.id
JOIN unit u ON obs.unit_id = u.id
LEFT JOIN dimension_type dt ON obs.dimension_type_id = dt.id
LEFT JOIN unit du ON obs.dimension_unit_id = du.id
LEFT JOIN proximate_record pr ON obs.record_id = pr.record_id AND obs.record_type = 'proximate analysis'
LEFT JOIN ultimate_record ur ON obs.record_id = ur.record_id AND obs.record_type = 'ultimate analysis'
LEFT JOIN compositional_record cr ON obs.record_id = cr.record_id AND obs.record_type = 'compositional analysis'
LEFT JOIN icp_record ir ON obs.record_id = ir.record_id AND (obs.record_type = 'icp analysis' OR obs.record_type = 'icp-oes' OR obs.record_type = 'icp-ms')
LEFT JOIN xrf_record xr ON obs.record_id = xr.record_id AND obs.record_type = 'xrf analysis'
LEFT JOIN calorimetry_record calr ON obs.record_id = calr.record_id AND obs.record_type = 'calorimetry analysis'
LEFT JOIN xrd_record xrr ON obs.record_id = xrr.record_id AND obs.record_type = 'xrd analysis'
LEFT JOIN fermentation_record fr ON obs.record_id = fr.record_id AND obs.record_type = 'fermentation'
LEFT JOIN pretreatment_record ptr ON obs.record_id = ptr.record_id AND obs.record_type = 'pretreatment'
LEFT JOIN prepared_sample ps ON ps.id = COALESCE(
    pr.prepared_sample_id, ur.prepared_sample_id, cr.prepared_sample_id, ir.prepared_sample_id,
    xr.prepared_sample_id, calr.prepared_sample_id, xrr.prepared_sample_id, fr.prepared_sample_id,
    ptr.prepared_sample_id
)
LEFT JOIN field_sample fs ON fs.id = ps.field_sample_id
LEFT JOIN resource res ON res.id = COALESCE(
    pr.resource_id, ur.resource_id, cr.resource_id, ir.resource_id,
    xr.resource_id, calr.resource_id, xrr.resource_id, fr.resource_id, ptr.resource_id,
    fs.resource_id
)
LEFT JOIN location_address la ON fs.sampling_location_id = la.id
WHERE obs.record_type NOT IN ('usda_census_record', 'usda_survey_record')
"""

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

    # Recreate indexes for analysis_data_view
    op.execute(f"CREATE INDEX IF NOT EXISTS idx_analysis_data_view_resource ON {VIEW_SCHEMA}.analysis_data_view (resource)")
    op.execute(f"CREATE INDEX IF NOT EXISTS idx_analysis_data_view_geoid ON {VIEW_SCHEMA}.analysis_data_view (geoid)")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(f"DROP MATERIALIZED VIEW IF EXISTS {VIEW_SCHEMA}.analysis_average_view CASCADE")
    op.execute(f"DROP MATERIALIZED VIEW IF EXISTS {VIEW_SCHEMA}.analysis_data_view CASCADE")

    # Restore previous analysis_data_view definition
    op.execute(
        f"CREATE MATERIALIZED VIEW {VIEW_SCHEMA}.analysis_data_view AS {PREVIOUS_ANALYSIS_DATA_VIEW_SQL}"
    )

    # Recreate analysis_average_view
    op.execute(
        f"CREATE MATERIALIZED VIEW {VIEW_SCHEMA}.analysis_average_view AS "
        f"{ANALYSIS_AVERAGE_VIEW_SQL}"
    )

    # Restore indexes for the downgraded view
    op.execute(f"CREATE INDEX IF NOT EXISTS idx_analysis_data_view_resource ON {VIEW_SCHEMA}.analysis_data_view (resource)")
    op.execute(f"CREATE INDEX IF NOT EXISTS idx_analysis_data_view_geoid ON {VIEW_SCHEMA}.analysis_data_view (geoid)")
