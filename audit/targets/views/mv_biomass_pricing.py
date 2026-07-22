# audit/targets/views/mv_biomass_pricing.py
from audit.targets.registry import AuditTarget, register

register(AuditTarget(
    name="mv_biomass_pricing",
    source_type="view",
    description="Market pricing data for biomass resources.",
    population_sql="""
        SELECT resource_name, price_unit,
               AVG(price_avg) AS avg_value, STDDEV(price_avg) AS std_dev,
               COUNT(*) AS observation_count
        FROM data_portal.mv_biomass_pricing
        GROUP BY resource_name, price_unit
        HAVING COUNT(*) >= 3
    """,
    observation_sql="""
        SELECT resource_name, price_unit,
               price_avg AS observed_value,
               id AS record_id
        FROM data_portal.mv_biomass_pricing
    """,
    group_by_cols=["resource_name", "price_unit"],
    numeric_cols=["observed_value"],
    id_cols=["record_id"],
    gx_suite_path="audit/expectations/mv_biomass_pricing.json",
    use_isolation_forest=False,
))
