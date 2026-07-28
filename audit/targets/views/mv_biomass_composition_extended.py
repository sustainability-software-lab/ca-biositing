# audit/targets/views/mv_biomass_composition_extended.py
from audit.targets.registry import AuditTarget, register

register(AuditTarget(
    name="mv_biomass_composition_extended",
    source_type="view",
    description="Extended composition audit including provider and collection date context.",

    # Layer 1: stats by resource, parameter, unit, and provider
    population_sql="""
        SELECT
            r.name AS resource_name,
            p.name AS parameter_name,
            u.name AS unit,
            prov.codename AS provider_codename,
            AVG(o.value) AS avg_value,
            STDDEV(o.value) AS std_dev,
            COUNT(o.value) AS observation_count
        FROM public.observation o
        JOIN public.parameter p ON o.parameter_id = p.id
        LEFT JOIN public.unit u ON o.unit_id = u.id
        JOIN public.compositional_record cr ON lower(o.record_id) = lower(cr.record_id)
        JOIN public.resource r ON cr.resource_id = r.id
        JOIN public.prepared_sample ps ON cr.prepared_sample_id = ps.id
        JOIN public.field_sample fs ON ps.field_sample_id = fs.id
        JOIN public.provider prov ON fs.provider_id = prov.id
        WHERE cr.qc_pass != 'fail'
        GROUP BY r.name, p.name, u.name, prov.codename
        HAVING COUNT(o.value) >= 3
    """,

    # Layer 2: individual observations with provider and collection date
    observation_sql="""
        SELECT
            r.name          AS resource_name,
            p.name          AS parameter_name,
            u.name          AS unit,
            o.value         AS observed_value,
            cr.record_id,
            cr.qc_pass,
            prov.codename   AS provider_codename,
            fs.collection_timestamp,
            fs.harvest_date,
            cr.created_at,
            cr.created_at    AS sample_date  -- fallback: no dedicated sample_date column on this record type
        FROM public.compositional_record cr
        JOIN public.resource r ON cr.resource_id = r.id
        JOIN public.observation o ON lower(o.record_id) = lower(cr.record_id)
        JOIN public.parameter p ON o.parameter_id = p.id
        LEFT JOIN public.unit u ON o.unit_id = u.id
        JOIN public.prepared_sample ps ON cr.prepared_sample_id = ps.id
        JOIN public.field_sample fs ON ps.field_sample_id = fs.id
        JOIN public.provider prov ON fs.provider_id = prov.id
        WHERE cr.qc_pass != 'fail'
    """,

    group_by_cols=["resource_name", "parameter_name", "unit", "provider_codename"],
    numeric_cols=["observed_value"],
    id_cols=["record_id", "resource_name", "parameter_name"],
    analyst_col=None,
    gx_suite_path="audit/expectations/mv_biomass_composition_extended.json",
    use_isolation_forest=False,
))
