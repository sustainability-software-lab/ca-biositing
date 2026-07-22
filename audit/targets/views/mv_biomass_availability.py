# audit/targets/views/mv_biomass_availability.py
from audit.targets.registry import AuditTarget, register

register(AuditTarget(
    name="mv_biomass_availability",
    source_type="view",
    description="Biomass availability and residue factors.",
    population_sql="""
        SELECT resource_name,
               AVG(dry_tons_per_acre) AS avg_value, STDDEV(dry_tons_per_acre) AS std_dev,
               COUNT(*) AS observation_count
        FROM data_portal.mv_biomass_availability
        GROUP BY resource_name
        HAVING COUNT(*) >= 3
    """,
    observation_sql="""
        SELECT resource_name,
               dry_tons_per_acre AS observed_value,
               resource_id AS record_id
        FROM data_portal.mv_biomass_availability
    """,
    group_by_cols=["resource_name"],
    numeric_cols=["observed_value"],
    id_cols=["record_id"],
    gx_suite_path="audit/expectations/mv_biomass_availability.json",
    use_isolation_forest=False,
))
