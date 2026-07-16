# audit/targets/views/mv_biomass_gasification.py
from audit.targets.registry import AuditTarget, register

register(AuditTarget(
    name="mv_biomass_gasification",
    source_type="view",
    description="Gasification syngas composition and yield data.",
    population_sql="""
        SELECT resource_name, reactor_type, parameter_name, unit,
               AVG(avg_value) AS avg_value, STDDEV(avg_value) AS std_dev,
               COUNT(*) AS observation_count
        FROM data_portal.mv_biomass_gasification
        GROUP BY resource_name, reactor_type, parameter_name, unit
        HAVING COUNT(*) >= 3
    """,
    observation_sql="""
        SELECT
            r.name AS resource_name,
            dv.name AS reactor_type,
            o.value AS observed_value,
            gr.record_id,
            gr.qc_pass,
            gr.created_at,
            p.name AS parameter_name,
            u.name AS unit
        FROM public.gasification_record gr
        JOIN public.resource r ON gr.resource_id = r.id
        JOIN public.observation o ON lower(o.record_id) = lower(gr.record_id)
        JOIN public.parameter p ON o.parameter_id = p.id
        LEFT JOIN public.unit u ON o.unit_id = u.id
        LEFT JOIN public.decon_vessel dv ON gr.reactor_type_id = dv.id
        WHERE gr.qc_pass != 'fail'
    """,
    group_by_cols=["resource_name", "reactor_type", "parameter_name", "unit"],
    numeric_cols=["observed_value"],
    id_cols=["record_id"],
    use_isolation_forest=True,
))
