# audit/targets/views/mv_biomass_end_uses.py
from audit.targets.registry import AuditTarget, register

register(AuditTarget(
    name="mv_biomass_end_uses",
    source_type="view",
    description="End-use breakdown per resource.",
    population_sql="""
        SELECT resource_name, use_case,
               AVG(percentage_high) AS avg_value, STDDEV(percentage_high) AS std_dev,
               COUNT(*) AS observation_count
        FROM data_portal.mv_biomass_end_uses
        GROUP BY resource_name, use_case
        HAVING COUNT(*) >= 3
    """,
    observation_sql="""
        SELECT resource_name, use_case,
               percentage_high AS observed_value,
               resource_id AS record_id
        FROM data_portal.mv_biomass_end_uses
    """,
    group_by_cols=["resource_name", "use_case"],
    numeric_cols=["observed_value"],
    id_cols=["record_id"],
    gx_suite_path="audit/expectations/mv_biomass_end_uses.json",
    use_isolation_forest=False,
))
