"""expand_feedstock_view_columns_for_api_queries

Revision ID: cfe7ab7b7a20
Revises: b6aa2fc6cd42
Create Date: 2026-02-28 18:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
from sqlalchemy.dialects.postgresql import dialect as pg_dialect

from ca_biositing.datamodels.views import (
    ANALYSIS_AVERAGE_VIEW_SQL,
    ANALYSIS_DATA_VIEW,
    USDA_CENSUS_VIEW,
    USDA_SURVEY_VIEW,
    VIEW_SCHEMA,
)

# revision identifiers, used by Alembic.
revision: str = "cfe7ab7b7a20"
down_revision: Union[str, Sequence[str], None] = "b6aa2fc6cd42"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _create_view(view_name: str, view_query) -> None:
    compiled = view_query.compile(
        dialect=pg_dialect(), compile_kwargs={"literal_binds": True}
    )
    op.execute(f"CREATE MATERIALIZED VIEW {VIEW_SCHEMA}.{view_name} AS {compiled}")


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        f"DROP MATERIALIZED VIEW IF EXISTS {VIEW_SCHEMA}.analysis_average_view CASCADE"
    )
    op.execute(f"DROP MATERIALIZED VIEW IF EXISTS {VIEW_SCHEMA}.analysis_data_view CASCADE")
    op.execute(f"DROP MATERIALIZED VIEW IF EXISTS {VIEW_SCHEMA}.usda_census_view CASCADE")
    op.execute(f"DROP MATERIALIZED VIEW IF EXISTS {VIEW_SCHEMA}.usda_survey_view CASCADE")

    _create_view("analysis_data_view", ANALYSIS_DATA_VIEW)
    _create_view("usda_census_view", USDA_CENSUS_VIEW)
    _create_view("usda_survey_view", USDA_SURVEY_VIEW)
    op.execute(
        f"CREATE MATERIALIZED VIEW {VIEW_SCHEMA}.analysis_average_view AS "
        f"{ANALYSIS_AVERAGE_VIEW_SQL}"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        f"DROP MATERIALIZED VIEW IF EXISTS {VIEW_SCHEMA}.analysis_average_view CASCADE"
    )
    op.execute(f"DROP MATERIALIZED VIEW IF EXISTS {VIEW_SCHEMA}.analysis_data_view CASCADE")
    op.execute(f"DROP MATERIALIZED VIEW IF EXISTS {VIEW_SCHEMA}.usda_census_view CASCADE")
    op.execute(f"DROP MATERIALIZED VIEW IF EXISTS {VIEW_SCHEMA}.usda_survey_view CASCADE")

    # Previous analysis view shape used a synthetic geoid and no dimension fields.
    op.execute(
        f"""
        CREATE MATERIALIZED VIEW {VIEW_SCHEMA}.analysis_data_view AS
        SELECT
          obs.id,
          res.name AS resource,
          '06000'::text AS geoid,
          param.name AS parameter,
          obs.value,
          u.name AS unit
        FROM public.observation obs
        JOIN public.parameter param ON obs.parameter_id = param.id
        JOIN public.unit u ON obs.unit_id = u.id
        LEFT JOIN public.proximate_record pr
          ON obs.record_id = pr.record_id
         AND obs.record_type = 'proximate analysis'
        LEFT JOIN public.ultimate_record ur
          ON obs.record_id = ur.record_id
         AND obs.record_type = 'ultimate analysis'
        LEFT JOIN public.compositional_record cr
          ON obs.record_id = cr.record_id
         AND obs.record_type = 'compositional analysis'
        LEFT JOIN public.icp_record ir
          ON obs.record_id = ir.record_id
         AND obs.record_type = 'icp analysis'
        LEFT JOIN public.prepared_sample ps
          ON ps.id = COALESCE(
            pr.prepared_sample_id,
            ur.prepared_sample_id,
            cr.prepared_sample_id,
            ir.prepared_sample_id
          )
        LEFT JOIN public.field_sample fs ON fs.id = ps.field_sample_id
        LEFT JOIN public.resource res ON res.id = fs.resource_id
        """
    )

    # Previous USDA views exposed the core observation fields only.
    op.execute(
        f"""
        CREATE MATERIALIZED VIEW {VIEW_SCHEMA}.usda_census_view AS
        SELECT
          obs.id,
          LOWER(uc.api_name) AS usda_crop,
          p.geoid,
          param.name AS parameter,
          obs.value,
          u.name AS unit,
          dt.name AS dimension,
          obs.dimension_value,
          du.name AS dimension_unit
        FROM public.observation obs
        JOIN public.usda_census_record ucr
          ON obs.record_id = ucr.id::text
         AND obs.record_type = 'usda_census_record'
        JOIN public.usda_commodity uc ON ucr.commodity_code = uc.id
        JOIN public.place p ON ucr.geoid = p.geoid
        JOIN public.parameter param ON obs.parameter_id = param.id
        JOIN public.unit u ON obs.unit_id = u.id
        LEFT JOIN public.dimension_type dt ON obs.dimension_type_id = dt.id
        LEFT JOIN public.unit du ON obs.dimension_unit_id = du.id
        """
    )
    op.execute(
        f"""
        CREATE MATERIALIZED VIEW {VIEW_SCHEMA}.usda_survey_view AS
        SELECT
          obs.id,
          LOWER(uc.api_name) AS usda_crop,
          p.geoid,
          param.name AS parameter,
          obs.value,
          u.name AS unit,
          dt.name AS dimension,
          obs.dimension_value,
          du.name AS dimension_unit
        FROM public.observation obs
        JOIN public.usda_survey_record usr
          ON obs.record_id = usr.id::text
         AND obs.record_type = 'usda_survey_record'
        JOIN public.usda_commodity uc ON usr.commodity_code = uc.id
        JOIN public.place p ON usr.geoid = p.geoid
        JOIN public.parameter param ON obs.parameter_id = param.id
        JOIN public.unit u ON obs.unit_id = u.id
        LEFT JOIN public.dimension_type dt ON obs.dimension_type_id = dt.id
        LEFT JOIN public.unit du ON obs.dimension_unit_id = du.id
        """
    )
    op.execute(
        f"CREATE MATERIALIZED VIEW {VIEW_SCHEMA}.analysis_average_view AS "
        f"{ANALYSIS_AVERAGE_VIEW_SQL}"
    )
