"""Run DB diagnostics for materialized views and source tables.

Usage: pixi run python scripts/view_diagnostics.py
"""
import json
from sqlalchemy import text
from ca_biositing.datamodels.database import get_engine

QUERIES = {
    "usda_market_record_count": "SELECT COUNT(*) AS count FROM usda_market_record",
    "pricing_observation_count": (
        "SELECT COUNT(*) AS count FROM observation "
        "WHERE record_type = 'usda_market_record' "
        "AND parameter_id IN (SELECT id FROM parameter WHERE lower(name) = 'price received')"
    ),
    "parameter_price_variants": "SELECT DISTINCT name FROM parameter WHERE lower(name) LIKE '%price%'",
    "mv_biomass_pricing_count": "SELECT COUNT(*) AS count FROM data_portal.mv_biomass_pricing",
    "resource_production_count": "SELECT COUNT(*) AS count FROM resource_production_record",
    "mv_biomass_search_count": "SELECT COUNT(*) AS count FROM ca_biositing.mv_biomass_search",
    "mv_biomass_search_production_terms": (
        "SELECT resource, geoid, parameter, COUNT(*) AS n "
        "FROM ca_biositing.mv_biomass_search "
        "WHERE parameter ILIKE '%production%' OR parameter ILIKE '%volume%' OR parameter ILIKE '%yield%' "
        "GROUP BY resource, geoid, parameter ORDER BY n DESC LIMIT 20"
    ),
    "sample_market_join": (
        "SELECT umr.id AS market_id, anon.record_id AS obs_record_id, anon.price_avg, anon.price_unit "
        "FROM usda_market_record umr "
        "LEFT JOIN ("
        "  SELECT observation.record_id AS record_id, avg(observation.value) AS price_avg, min(observation.value) AS price_min, max(observation.value) AS price_max, unit.name AS price_unit "
        "  FROM observation "
        "  JOIN parameter ON observation.parameter_id = parameter.id "
        "  LEFT JOIN unit ON observation.unit_id = unit.id "
        "  WHERE observation.record_type = 'usda_market_record' AND lower(parameter.name) = 'price received' "
        "  GROUP BY observation.record_id, unit.name"
        " ) AS anon ON CAST(umr.id AS VARCHAR) = anon.record_id "
        "LIMIT 50"
    ),
    "data_portal_matviews": "SELECT matviewname FROM pg_matviews WHERE schemaname = 'data_portal' ORDER BY matviewname",
}


def run():
    engine = get_engine()
    results = {}
    with engine.connect() as conn:
        for key, query in QUERIES.items():
            try:
                res = conn.execute(text(query))
                rows = [dict(r) for r in res.mappings().all()]
                # Simplify single-count results
                if len(rows) == 1 and 'count' in rows[0]:
                    results[key] = rows[0]['count']
                else:
                    results[key] = rows
            except Exception as e:
                results[key] = {"error": str(e)}
    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    run()
