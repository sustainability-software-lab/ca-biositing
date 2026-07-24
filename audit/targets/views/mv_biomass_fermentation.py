# audit/targets/views/mv_biomass_fermentation.py
from audit.targets.registry import AuditTarget, register

register(AuditTarget(
    name="mv_biomass_fermentation",
    source_type="view",
    description="Fermentation yield data: organism, substrate, product.",
    population_sql="""
        SELECT resource_name, strain_name, pretreatment_method, bioconversion_method, product_name, unit,
               AVG(avg_value) AS avg_value, STDDEV(avg_value) AS std_dev,
               COUNT(*) AS observation_count
        FROM data_portal.mv_biomass_fermentation
        GROUP BY resource_name, strain_name, pretreatment_method, bioconversion_method, product_name, unit
        HAVING COUNT(*) >= 3
    """,
    observation_sql="""
        SELECT
            fr.record_id,
            fr.experiment_id,
            exp.exper_start_date AS experiment_date,
            fr.prepared_sample_id,
            fs.id AS field_sample_id,
            fs.collection_timestamp,
            prov.codename AS provider_codename,
            r.name AS resource_name,
            pap.name AS primary_product,
            p.name AS product_name,
            u.name AS unit,
            o.value AS observed_value,
            fr.technical_replicate_no AS repl_no,
            fr.qc_pass,
            o.note AS note,
            c.email AS analyst_email,
            dv.name AS reactor_vessel,
            s.name AS strain_name
        FROM public.fermentation_record fr
        JOIN public.resource r ON fr.resource_id = r.id
        JOIN public.observation o ON lower(o.record_id) = lower(fr.record_id)
        JOIN public.parameter p ON o.parameter_id = p.id
        LEFT JOIN public.unit u ON o.unit_id = u.id
        LEFT JOIN public.strain s ON fr.strain_id = s.id
        LEFT JOIN public.prepared_sample ps ON fr.prepared_sample_id = ps.id
        LEFT JOIN public.field_sample fs ON ps.field_sample_id = fs.id
        LEFT JOIN public.provider prov ON fs.provider_id = prov.id
        LEFT JOIN public.experiment exp ON fr.experiment_id = exp.id
        LEFT JOIN public.contact c ON exp.analyst_id = c.id
        LEFT JOIN public.primary_ag_product pap ON r.primary_ag_product_id = pap.id
        LEFT JOIN public.decon_vessel dv ON fr.vessel_id = dv.id
        WHERE fr.qc_pass != 'fail'
    """,
    group_by_cols=["resource_name", "strain_name", "product_name", "unit"],
    numeric_cols=["observed_value"],
    id_cols=["record_id"],
    gx_suite_path="audit/expectations/mv_biomass_fermentation.json",
    use_isolation_forest=True,  # multivariate
))
