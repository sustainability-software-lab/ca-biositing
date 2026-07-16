# audit/targets/views/mv_biomass_sample_stats.py
from audit.targets.registry import AuditTarget, register

register(AuditTarget(
    name="mv_biomass_sample_stats",
    source_type="view",
    description="Sample statistics aggregated across all analytical record types.",
    population_sql="""
        SELECT resource_name,
               AVG(total_record_count) AS avg_value, STDDEV(total_record_count) AS std_dev,
               COUNT(*) AS observation_count
        FROM data_portal.mv_biomass_sample_stats
        GROUP BY resource_name
        HAVING COUNT(*) >= 3
    """,
    observation_sql="""
        SELECT resource_name,
               total_record_count AS observed_value,
               resource_id AS record_id
        FROM data_portal.mv_biomass_sample_stats
    """,
    group_by_cols=["resource_name"],
    numeric_cols=["observed_value"],
    id_cols=["record_id"],
    use_isolation_forest=False,
))
