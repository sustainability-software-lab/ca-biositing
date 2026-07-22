from audit.targets.registry import AuditTarget, register

# Build a target to check variance in forest residue moisture
# Template for dynamic ad-hoc target discovery

target = AuditTarget(
    name="adhoc_forest_residue_moisture",
    source_type="view",
    description="Check variance in forest residue moisture",
    population_sql="""
        SELECT
            resource_name,
            parameter_name,
            unit,
            AVG(value) as avg_value,
            STDDEV(value) as stddev_value
        FROM analytics.mv_biomass_composition
        WHERE resource_name LIKE '%Forest Residue%'
          AND parameter_name = 'Moisture'
        GROUP BY 1, 2, 3
    """,
    observation_sql="""
        SELECT
            record_id,
            resource_name,
            parameter_name,
            unit,
            value,
            analyst_email
        FROM analytics.mv_biomass_composition
        WHERE resource_name LIKE '%Forest Residue%'
          AND parameter_name = 'Moisture'
    """,
    group_by_cols=["resource_name", "parameter_name", "unit"],
    numeric_cols=["value"],
    id_cols=["record_id"],
    analyst_col="analyst_email"
)

register(target)
