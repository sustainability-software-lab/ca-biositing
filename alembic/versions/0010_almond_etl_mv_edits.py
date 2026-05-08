"""Almond ETL materialized view edits.

Revision ID: 0010_almond_etl_mv_edits
Revises: 55f93e3a6237
Create Date: 2026-05-04 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
from sqlalchemy.dialects.postgresql import dialect as pg_dialect

from ca_biositing.datamodels.data_portal_views import mv_biomass_search


# revision identifiers, used by Alembic.
revision: str = "0010_almond_etl_mv_edits"
down_revision = "55f93e3a6237"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _compile_view_sql(view_query) -> str:
    compiled = view_query.compile(
        dialect=pg_dialect(), compile_kwargs={"literal_binds": True}
    )
    return str(compiled)


def upgrade() -> None:
    """Almond ETL materialized view edits - deferred for investigation."""
    # Recreate search MV so volume fields derive from resource_production_record observations.
    op.execute("DROP MATERIALIZED VIEW IF EXISTS data_portal.mv_biomass_search CASCADE")
    op.execute(
        f"CREATE MATERIALIZED VIEW data_portal.mv_biomass_search AS {_compile_view_sql(mv_biomass_search)}"
    )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_biomass_search_id ON data_portal.mv_biomass_search (id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_mv_biomass_search_search_vector ON data_portal.mv_biomass_search USING GIN (search_vector)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_mv_biomass_search_name_trgm ON data_portal.mv_biomass_search USING GIN (name gin_trgm_ops)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_mv_biomass_search_resource_class ON data_portal.mv_biomass_search (resource_class)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_mv_biomass_search_resource_subclass ON data_portal.mv_biomass_search (resource_subclass)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_mv_biomass_search_primary_product ON data_portal.mv_biomass_search (primary_product)"
    )

    op.execute("""
    DROP MATERIALIZED VIEW IF EXISTS data_portal.mv_biomass_pricing;

    CREATE MATERIALIZED VIEW data_portal.mv_biomass_pricing AS
    WITH pricing_obs AS (
        SELECT
            observation.record_id,
            avg(observation.value) AS price_avg,
            min(observation.value) AS price_min,
            max(observation.value) AS price_max,
            unit.name AS price_unit
        FROM observation
        JOIN parameter ON observation.parameter_id = parameter.id
        LEFT JOIN unit ON observation.unit_id = unit.id
        WHERE lower(parameter.name) IN (
            'price received','price paid','price avg','price production weighted average',
            'price production weighted avg','weighted_average_price','price','weighted average price'
        )
        AND observation.value IS NOT NULL
        AND observation.record_type IN ('usda_market_record','resource_price_record')
        GROUP BY observation.record_id, unit.name
    ),
    usda_sel AS (
        SELECT
            usda_commodity.name AS commodity_name,
            place.geoid,
            place.county_name AS county,
            place.state_name AS state,
            usda_market_record.report_date,
            usda_market_record.market_type_category,
            usda_market_record.sale_type,
            pricing_obs.price_min,
            pricing_obs.price_max,
            pricing_obs.price_avg,
            pricing_obs.price_unit
        FROM usda_market_record
        JOIN usda_market_report ON usda_market_record.report_id = usda_market_report.id
        JOIN usda_commodity ON usda_market_record.commodity_id = usda_commodity.id
        LEFT JOIN location_address ON usda_market_report.office_city_id = location_address.id
        LEFT JOIN place ON location_address.geography_id = place.geoid
        JOIN resource_usda_commodity_map ON usda_commodity.id = resource_usda_commodity_map.usda_commodity_id
        LEFT JOIN pricing_obs ON cast(usda_market_record.id AS text) = pricing_obs.record_id
        WHERE resource_usda_commodity_map.resource_id IS NOT NULL
    ),
    resource_sel AS (
        SELECT
            resource.name AS commodity_name,
            resource_price_record.geoid,
            place.county_name AS county,
            place.state_name AS state,
            resource_price_record.report_start_date AS report_date,
            NULL::text AS market_type_category,
            resource_price_record.freight_terms AS sale_type,
            pricing_obs.price_min,
            pricing_obs.price_max,
            pricing_obs.price_avg,
            pricing_obs.price_unit
        FROM resource_price_record
        LEFT JOIN resource ON resource_price_record.resource_id = resource.id
        LEFT JOIN place ON resource_price_record.geoid = place.geoid
        LEFT JOIN pricing_obs ON cast(resource_price_record.id AS text) = pricing_obs.record_id
    )
    SELECT row_number() OVER (ORDER BY commodity_name) AS id, * FROM (
        SELECT * FROM usda_sel
        UNION ALL
        SELECT * FROM resource_sel
    ) AS combined;

    CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_biomass_pricing_id ON data_portal.mv_biomass_pricing (id);
    """)


def downgrade() -> None:
    """Almond ETL materialized view edits - deferred for investigation."""
    op.execute("""
    DROP INDEX IF EXISTS data_portal.idx_mv_biomass_search_primary_product;
    DROP INDEX IF EXISTS data_portal.idx_mv_biomass_search_resource_subclass;
    DROP INDEX IF EXISTS data_portal.idx_mv_biomass_search_resource_class;
    DROP INDEX IF EXISTS data_portal.idx_mv_biomass_search_name_trgm;
    DROP INDEX IF EXISTS data_portal.idx_mv_biomass_search_search_vector;
    DROP INDEX IF EXISTS data_portal.idx_mv_biomass_search_id;
    DROP MATERIALIZED VIEW IF EXISTS data_portal.mv_biomass_search;
    DROP MATERIALIZED VIEW IF EXISTS data_portal.mv_biomass_pricing;
    DROP INDEX IF EXISTS data_portal.idx_mv_biomass_pricing_id;
    """)
