"""Almond ETL materialized view edits.

Revision ID: 0009_almond_etl_mv_edits
Revises: 9e8f7a6b5c52
Create Date: 2026-05-04 00:00:00.000000
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "0009_almond_etl_mv_edits"
down_revision = "9e8f7a6b5c52"
branch_labels = None
depends_on = None


MV_BIOMASS_COUNTY_PRODUCTION_UPGRADE_SQL = """
CREATE MATERIALIZED VIEW data_portal.mv_biomass_county_production AS
SELECT row_number() OVER (ORDER BY anon_1.resource_id, anon_1.geoid, anon_1.scenario, anon_1.year) AS id, anon_1.resource_id, anon_1.resource_name, anon_1.resource_class, anon_1.geoid, anon_1.county, anon_1.state, anon_1.scenario, anon_1.price_offered_usd, anon_1.production, anon_1.production_unit, anon_1.energy_content, anon_1.energy_unit, anon_1.density_dt_per_sqmi, anon_1.county_square_miles, anon_1.year
FROM (
    SELECT billion_ton2023_record.resource_id AS resource_id, resource.name AS resource_name, resource_class.name AS resource_class, place.geoid AS geoid, place.county_name AS county, place.state_name AS state, billion_ton2023_record.scenario_name AS scenario, billion_ton2023_record.price_offered_usd AS price_offered_usd, billion_ton2023_record.production AS production, unit.name AS production_unit, billion_ton2023_record.production_energy_content AS energy_content, eu.name AS energy_unit, billion_ton2023_record.product_density_dtpersqmi AS density_dt_per_sqmi, billion_ton2023_record.county_square_miles AS county_square_miles, 2023 AS year
    FROM billion_ton2023_record
    JOIN resource ON billion_ton2023_record.resource_id = resource.id
    LEFT OUTER JOIN resource_class ON resource.resource_class_id = resource_class.id
    JOIN place ON billion_ton2023_record.geoid = place.geoid
    LEFT OUTER JOIN unit ON billion_ton2023_record.production_unit_id = unit.id
    LEFT OUTER JOIN unit AS eu ON billion_ton2023_record.energy_content_unit_id = eu.id
    UNION ALL
    SELECT resource_production_record.resource_id AS resource_id, resource.name AS resource_name, resource_class.name AS resource_class, place.geoid AS geoid, place.county_name AS county, place.state_name AS state, COALESCE(resource_production_record.scenario, 'almond_nsjv') AS scenario, NULL AS price_offered_usd, anon_2.production AS production, anon_2.production_unit AS production_unit, NULL AS energy_content, NULL AS energy_unit, NULL AS density_dt_per_sqmi, NULL AS county_square_miles, CAST(EXTRACT(YEAR FROM resource_production_record.report_date) AS INTEGER) AS year
    FROM resource_production_record
    JOIN resource ON resource_production_record.resource_id = resource.id
    LEFT OUTER JOIN resource_class ON resource.resource_class_id = resource_class.id
    JOIN place ON resource_production_record.geoid = place.geoid
    JOIN (
        SELECT observation.record_id AS record_id, avg(observation.value) AS production, unit.name AS production_unit
        FROM observation
        JOIN parameter ON observation.parameter_id = parameter.id
        LEFT OUTER JOIN unit ON observation.unit_id = unit.id
        WHERE observation.record_type = 'resource_production_record' AND lower(parameter.name) = 'production'
        GROUP BY observation.record_id, unit.name
    ) AS anon_2 ON CAST(resource_production_record.id AS VARCHAR) = anon_2.record_id
) AS anon_1
"""


MV_BIOMASS_COUNTY_PRODUCTION_DOWNGRADE_SQL = """
CREATE MATERIALIZED VIEW data_portal.mv_biomass_county_production AS
SELECT row_number() OVER (ORDER BY billion_ton2023_record.resource_id, place.geoid, billion_ton2023_record.scenario_name, billion_ton2023_record.price_offered_usd) AS id, billion_ton2023_record.resource_id, resource.name AS resource_name, resource_class.name AS resource_class, place.geoid, place.county_name AS county, place.state_name AS state, billion_ton2023_record.scenario_name AS scenario, billion_ton2023_record.price_offered_usd, billion_ton2023_record.production, unit.name AS production_unit, billion_ton2023_record.production_energy_content AS energy_content, eu.name AS energy_unit, billion_ton2023_record.product_density_dtpersqmi AS density_dt_per_sqmi, billion_ton2023_record.county_square_miles, 2023 AS year
FROM billion_ton2023_record
JOIN resource ON billion_ton2023_record.resource_id = resource.id
LEFT OUTER JOIN resource_class ON resource.resource_class_id = resource_class.id
JOIN place ON billion_ton2023_record.geoid = place.geoid
LEFT OUTER JOIN unit ON billion_ton2023_record.production_unit_id = unit.id
LEFT OUTER JOIN unit AS eu ON billion_ton2023_record.energy_content_unit_id = eu.id
"""


MV_BIOMASS_PRICING_UPGRADE_SQL = """
CREATE MATERIALIZED VIEW data_portal.mv_biomass_pricing AS
SELECT row_number() OVER (ORDER BY anon_1.commodity_name, anon_1.geoid, anon_1.report_date) AS id, anon_1.commodity_name, anon_1.geoid, anon_1.county, anon_1.state, anon_1.report_date, anon_1.market_type_category, anon_1.sale_type, anon_1.price_min, anon_1.price_max, anon_1.price_avg, anon_1.price_unit
FROM (
    SELECT usda_commodity.name AS commodity_name, place.geoid AS geoid, place.county_name AS county, place.state_name AS state, usda_market_record.report_date AS report_date, usda_market_record.market_type_category AS market_type_category, usda_market_record.sale_type AS sale_type, anon_2.price_min AS price_min, anon_2.price_max AS price_max, anon_2.price_avg AS price_avg, anon_2.price_unit AS price_unit
    FROM usda_market_record
    JOIN usda_market_report ON usda_market_record.report_id = usda_market_report.id
    JOIN usda_commodity ON usda_market_record.commodity_id = usda_commodity.id
    LEFT OUTER JOIN location_address ON usda_market_report.office_city_id = location_address.id
    LEFT OUTER JOIN place ON location_address.geography_id = place.geoid
    JOIN (
        SELECT observation.record_id AS record_id, avg(observation.value) AS price_avg, min(observation.value) AS price_min, max(observation.value) AS price_max, unit.name AS price_unit
        FROM observation
        JOIN parameter ON observation.parameter_id = parameter.id
        LEFT OUTER JOIN unit ON observation.unit_id = unit.id
        WHERE observation.record_type = 'usda_market_record' AND lower(parameter.name) = 'price received'
        GROUP BY observation.record_id, unit.name
    ) AS anon_2 ON CAST(usda_market_record.id AS VARCHAR) = anon_2.record_id
    UNION ALL
    SELECT resource.name AS commodity_name, place.geoid AS geoid, place.county_name AS county, place.state_name AS state, resource_price_record.report_start_date AS report_date, NULL AS market_type_category, NULL AS sale_type, anon_3.price_min AS price_min, anon_3.price_max AS price_max, anon_3.price_avg AS price_avg, anon_3.price_unit AS price_unit
    FROM resource_price_record
    JOIN resource ON resource_price_record.resource_id = resource.id
    JOIN place ON resource_price_record.geoid = place.geoid
    JOIN (
        SELECT observation.record_id AS record_id, avg(observation.value) AS price_avg, min(observation.value) AS price_min, max(observation.value) AS price_max, unit.name AS price_unit
        FROM observation
        JOIN parameter ON observation.parameter_id = parameter.id
        LEFT OUTER JOIN unit ON observation.unit_id = unit.id
        WHERE observation.record_type = 'resource_price_record' AND lower(parameter.name) IN ('price', 'price received', 'price_avg', 'weighted average price', 'price production weighted average')
        GROUP BY observation.record_id, unit.name
    ) AS anon_3 ON CAST(resource_price_record.id AS VARCHAR) = anon_3.record_id
) AS anon_1
"""


MV_BIOMASS_PRICING_DOWNGRADE_SQL = """
CREATE MATERIALIZED VIEW data_portal.mv_biomass_pricing AS
SELECT row_number() OVER (ORDER BY usda_market_record.id) AS id, usda_commodity.name AS commodity_name, place.geoid, place.county_name AS county, place.state_name AS state, usda_market_record.report_date, usda_market_record.market_type_category, usda_market_record.sale_type, anon_1.price_min, anon_1.price_max, anon_1.price_avg, anon_1.price_unit
FROM usda_market_record
JOIN usda_market_report ON usda_market_record.report_id = usda_market_report.id
JOIN usda_commodity ON usda_market_record.commodity_id = usda_commodity.id
LEFT OUTER JOIN location_address ON usda_market_report.office_city_id = location_address.id
LEFT OUTER JOIN place ON location_address.geography_id = place.geoid
JOIN (
    SELECT observation.record_id AS record_id, avg(observation.value) AS price_avg, min(observation.value) AS price_min, max(observation.value) AS price_max, unit.name AS price_unit
    FROM observation
    JOIN parameter ON observation.parameter_id = parameter.id
    LEFT OUTER JOIN unit ON observation.unit_id = unit.id
    WHERE observation.record_type = 'usda_market_record' AND lower(parameter.name) = 'price received'
    GROUP BY observation.record_id, unit.name
) AS anon_1 ON CAST(usda_market_record.id AS VARCHAR) = anon_1.record_id
"""


def upgrade() -> None:
    """Recreate the almond ETL materialized views with raw SQL snapshots."""

    op.execute("DROP MATERIALIZED VIEW IF EXISTS data_portal.mv_biomass_pricing CASCADE")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS data_portal.mv_biomass_county_production CASCADE")

    op.execute(MV_BIOMASS_PRICING_UPGRADE_SQL)
    op.execute("CREATE UNIQUE INDEX idx_mv_biomass_pricing_id ON data_portal.mv_biomass_pricing (id)")
    op.execute("CREATE INDEX idx_mv_biomass_pricing_commodity_name ON data_portal.mv_biomass_pricing (commodity_name)")
    op.execute("CREATE INDEX idx_mv_biomass_pricing_county ON data_portal.mv_biomass_pricing (county)")

    op.execute(MV_BIOMASS_COUNTY_PRODUCTION_UPGRADE_SQL)
    op.execute("CREATE UNIQUE INDEX idx_mv_biomass_county_production_id ON data_portal.mv_biomass_county_production (id)")

    op.execute("GRANT SELECT ON data_portal.mv_biomass_pricing TO biocirv_readonly")
    op.execute("GRANT SELECT ON data_portal.mv_biomass_county_production TO biocirv_readonly")


def downgrade() -> None:
    """Restore the pre-almond materialized views."""

    op.execute("DROP MATERIALIZED VIEW IF EXISTS data_portal.mv_biomass_pricing CASCADE")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS data_portal.mv_biomass_county_production CASCADE")

    op.execute(MV_BIOMASS_PRICING_DOWNGRADE_SQL)
    op.execute("CREATE UNIQUE INDEX idx_mv_biomass_pricing_id ON data_portal.mv_biomass_pricing (id)")
    op.execute("CREATE INDEX idx_mv_biomass_pricing_commodity_name ON data_portal.mv_biomass_pricing (commodity_name)")
    op.execute("CREATE INDEX idx_mv_biomass_pricing_county ON data_portal.mv_biomass_pricing (county)")

    op.execute(MV_BIOMASS_COUNTY_PRODUCTION_DOWNGRADE_SQL)
    op.execute("CREATE UNIQUE INDEX idx_mv_biomass_county_production_id ON data_portal.mv_biomass_county_production (id)")

    op.execute("GRANT SELECT ON data_portal.mv_biomass_pricing TO biocirv_readonly")
    op.execute("GRANT SELECT ON data_portal.mv_biomass_county_production TO biocirv_readonly")
