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
            gr.record_id,
            gr.experiment_id,
            exp.exper_start_date AS experiment_date,
            gr.prepared_sample_id,
            fs.id AS field_sample_id,
            fs.collection_timestamp,
            prov.codename AS provider_codename,
            r.name AS resource_name,
            NULL AS primary_product,
            p.name AS parameter_name,
            u.name AS unit,
            o.value AS observed_value,
            gr.technical_replicate_no AS repl_no,
            gr.qc_pass,
            o.note AS note,
            c.email AS analyst_email,
            dv.name AS reactor_type
        FROM public.gasification_record gr
        JOIN public.resource r ON gr.resource_id = r.id
        JOIN public.observation o ON lower(o.record_id) = lower(gr.record_id)
        JOIN public.parameter p ON o.parameter_id = p.id
        LEFT JOIN public.unit u ON o.unit_id = u.id
        LEFT JOIN public.decon_vessel dv ON gr.reactor_type_id = dv.id
        LEFT JOIN public.prepared_sample ps ON gr.prepared_sample_id = ps.id
        LEFT JOIN public.field_sample fs    ON ps.field_sample_id = fs.id
        LEFT JOIN public.provider prov      ON fs.provider_id = prov.id
        LEFT JOIN public.experiment exp     ON gr.experiment_id = exp.id
        LEFT JOIN public.contact c          ON gr.analyst_id = c.id
        WHERE gr.qc_pass != 'fail'
    """,
    group_by_cols=["resource_name", "reactor_type", "parameter_name", "unit"],
    numeric_cols=["observed_value"],
    id_cols=["record_id"],
    gx_suite_path="audit/expectations/mv_biomass_gasification.json",
    use_isolation_forest=True,
))
