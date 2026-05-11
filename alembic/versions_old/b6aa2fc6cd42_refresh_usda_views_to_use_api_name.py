"""refresh_usda_views_to_use_api_name

Revision ID: b6aa2fc6cd42
Revises: eacbc6544a10
Create Date: 2026-02-27 11:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
from sqlalchemy.dialects.postgresql import dialect as pg_dialect

from ca_biositing.datamodels.views import VIEW_SCHEMA, USDA_CENSUS_VIEW, USDA_SURVEY_VIEW

# revision identifiers, used by Alembic.
revision: str = "b6aa2fc6cd42"
down_revision: Union[str, Sequence[str], None] = "eacbc6544a10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _create_view(view_name: str, view_query) -> None:
    compiled = view_query.compile(
        dialect=pg_dialect(), compile_kwargs={"literal_binds": True}
    )
    op.execute(f"CREATE MATERIALIZED VIEW {VIEW_SCHEMA}.{view_name} AS {compiled}")


def upgrade() -> None:
    """Upgrade schema."""
    # We are changing view definitions (name -> lower(api_name)), so a refresh
    # alone is insufficient; drop/create is required for definition changes.
    op.execute(f"DROP MATERIALIZED VIEW IF EXISTS {VIEW_SCHEMA}.usda_census_view CASCADE")
    op.execute(f"DROP MATERIALIZED VIEW IF EXISTS {VIEW_SCHEMA}.usda_survey_view CASCADE")

    _create_view("usda_census_view", USDA_CENSUS_VIEW)
    _create_view("usda_survey_view", USDA_SURVEY_VIEW)


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(f"DROP MATERIALIZED VIEW IF EXISTS {VIEW_SCHEMA}.usda_census_view CASCADE")
    op.execute(f"DROP MATERIALIZED VIEW IF EXISTS {VIEW_SCHEMA}.usda_survey_view CASCADE")

    # Downgrade must recreate the previous definitions (usda_crop from uc.name).
    # REFRESH MATERIALIZED VIEW cannot revert a view definition.
    op.execute(
        f"""
        CREATE MATERIALIZED VIEW {VIEW_SCHEMA}.usda_census_view AS
        SELECT
          obs.id,
          uc.name AS usda_crop,
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
          uc.name AS usda_crop,
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
