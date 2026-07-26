# audit/targets/views/mv_biomass_composition.py
from audit.targets.registry import AuditTarget, register

register(AuditTarget(
    name="mv_biomass_composition",
    source_type="view",
    description="Compositional analysis aggregated by resource and parameter. "
                "Covers all AIM1 analysis types: compositional, proximate, ultimate, "
                "xrf, icp, calorimetry, xrd, ftnir, pretreatment.",

    # Layer 1: population stats already computed by the view
    population_sql="""
        SELECT resource_name, analysis_type, parameter_name, unit,
               avg_value, std_dev, min_value, max_value, observation_count
        FROM data_portal.mv_biomass_composition
        WHERE observation_count >= 3
    """,

    # Layer 2: individual observations with record_id and analyst attribution
    observation_sql="""
        SELECT
            cr.record_id,
            cr.experiment_id,
            exp.exper_start_date AS experiment_date,
            cr.prepared_sample_id,
            fs.id AS field_sample_id,
            fs.collection_timestamp,
            prov.codename AS provider_codename,
            r.name AS resource_name,
            pap.name AS primary_product,
            p.name AS parameter_name,
            u.name AS unit,
            o.value AS observed_value,
            cr.technical_replicate_no AS repl_no,
            cr.qc_pass,
            o.note AS note,
            c.email AS analyst_email,
            'compositional' AS analysis_type
        FROM public.compositional_record cr
        JOIN public.resource r ON cr.resource_id = r.id
        JOIN public.observation o ON lower(o.record_id) = lower(cr.record_id)
        JOIN public.parameter p ON o.parameter_id = p.id
        LEFT JOIN public.unit u ON o.unit_id = u.id
        LEFT JOIN public.contact c ON cr.analyst_id = c.id
        LEFT JOIN public.prepared_sample ps ON cr.prepared_sample_id = ps.id
        LEFT JOIN public.field_sample fs    ON ps.field_sample_id = fs.id
        LEFT JOIN public.provider prov      ON fs.provider_id = prov.id
        LEFT JOIN public.experiment exp     ON cr.experiment_id = exp.id
        LEFT JOIN public.primary_ag_product pap ON r.primary_ag_product_id = pap.id
        WHERE cr.qc_pass != 'fail'

        UNION ALL

        SELECT
            pr.record_id,
            pr.experiment_id,
            exp.exper_start_date AS experiment_date,
            pr.prepared_sample_id,
            fs.id AS field_sample_id,
            fs.collection_timestamp,
            prov.codename AS provider_codename,
            r.name AS resource_name,
            pap.name AS primary_product,
            p.name AS parameter_name,
            u.name AS unit,
            o.value AS observed_value,
            pr.technical_replicate_no AS repl_no,
            pr.qc_pass,
            o.note AS note,
            c.email AS analyst_email,
            'proximate' AS analysis_type
        FROM public.proximate_record pr
        JOIN public.resource r ON pr.resource_id = r.id
        JOIN public.observation o ON lower(o.record_id) = lower(pr.record_id)
        JOIN public.parameter p ON o.parameter_id = p.id
        LEFT JOIN public.unit u ON o.unit_id = u.id
        LEFT JOIN public.contact c ON pr.analyst_id = c.id
        LEFT JOIN public.prepared_sample ps ON pr.prepared_sample_id = ps.id
        LEFT JOIN public.field_sample fs    ON ps.field_sample_id = fs.id
        LEFT JOIN public.provider prov      ON fs.provider_id = prov.id
        LEFT JOIN public.experiment exp     ON pr.experiment_id = exp.id
        LEFT JOIN public.primary_ag_product pap ON r.primary_ag_product_id = pap.id
        WHERE pr.qc_pass != 'fail'

        UNION ALL

        SELECT
            ur.record_id,
            ur.experiment_id,
            exp.exper_start_date AS experiment_date,
            ur.prepared_sample_id,
            fs.id AS field_sample_id,
            fs.collection_timestamp,
            prov.codename AS provider_codename,
            r.name AS resource_name,
            pap.name AS primary_product,
            p.name AS parameter_name,
            u.name AS unit,
            o.value AS observed_value,
            ur.technical_replicate_no AS repl_no,
            ur.qc_pass,
            o.note AS note,
            c.email AS analyst_email,
            'ultimate' AS analysis_type
        FROM public.ultimate_record ur
        JOIN public.resource r ON ur.resource_id = r.id
        JOIN public.observation o ON lower(o.record_id) = lower(ur.record_id)
        JOIN public.parameter p ON o.parameter_id = p.id
        LEFT JOIN public.unit u ON o.unit_id = u.id
        LEFT JOIN public.contact c ON ur.analyst_id = c.id
        LEFT JOIN public.prepared_sample ps ON ur.prepared_sample_id = ps.id
        LEFT JOIN public.field_sample fs    ON ps.field_sample_id = fs.id
        LEFT JOIN public.provider prov      ON fs.provider_id = prov.id
        LEFT JOIN public.experiment exp     ON ur.experiment_id = exp.id
        LEFT JOIN public.primary_ag_product pap ON r.primary_ag_product_id = pap.id
        WHERE ur.qc_pass != 'fail'

        UNION ALL

        SELECT
            xr.record_id,
            xr.experiment_id,
            exp.exper_start_date AS experiment_date,
            xr.prepared_sample_id,
            fs.id AS field_sample_id,
            fs.collection_timestamp,
            prov.codename AS provider_codename,
            r.name AS resource_name,
            pap.name AS primary_product,
            p.name AS parameter_name,
            u.name AS unit,
            o.value AS observed_value,
            xr.technical_replicate_no AS repl_no,
            xr.qc_pass,
            o.note AS note,
            c.email AS analyst_email,
            'xrf' AS analysis_type
        FROM public.xrf_record xr
        JOIN public.resource r ON xr.resource_id = r.id
        JOIN public.observation o ON lower(o.record_id) = lower(xr.record_id)
        JOIN public.parameter p ON o.parameter_id = p.id
        LEFT JOIN public.unit u ON o.unit_id = u.id
        LEFT JOIN public.contact c ON xr.analyst_id = c.id
        LEFT JOIN public.prepared_sample ps ON xr.prepared_sample_id = ps.id
        LEFT JOIN public.field_sample fs    ON ps.field_sample_id = fs.id
        LEFT JOIN public.provider prov      ON fs.provider_id = prov.id
        LEFT JOIN public.experiment exp     ON xr.experiment_id = exp.id
        LEFT JOIN public.primary_ag_product pap ON r.primary_ag_product_id = pap.id
        WHERE xr.qc_pass != 'fail'

        UNION ALL

        SELECT
            ir.record_id,
            ir.experiment_id,
            exp.exper_start_date AS experiment_date,
            ir.prepared_sample_id,
            fs.id AS field_sample_id,
            fs.collection_timestamp,
            prov.codename AS provider_codename,
            r.name AS resource_name,
            pap.name AS primary_product,
            p.name AS parameter_name,
            u.name AS unit,
            o.value AS observed_value,
            ir.technical_replicate_no AS repl_no,
            ir.qc_pass,
            o.note AS note,
            c.email AS analyst_email,
            'icp' AS analysis_type
        FROM public.icp_record ir
        JOIN public.resource r ON ir.resource_id = r.id
        JOIN public.observation o ON lower(o.record_id) = lower(ir.record_id)
        JOIN public.parameter p ON o.parameter_id = p.id
        LEFT JOIN public.unit u ON o.unit_id = u.id
        LEFT JOIN public.contact c ON ir.analyst_id = c.id
        LEFT JOIN public.prepared_sample ps ON ir.prepared_sample_id = ps.id
        LEFT JOIN public.field_sample fs    ON ps.field_sample_id = fs.id
        LEFT JOIN public.provider prov      ON fs.provider_id = prov.id
        LEFT JOIN public.experiment exp     ON ir.experiment_id = exp.id
        LEFT JOIN public.primary_ag_product pap ON r.primary_ag_product_id = pap.id
        WHERE ir.qc_pass != 'fail'

        UNION ALL

        SELECT
            cr.record_id,
            cr.experiment_id,
            exp.exper_start_date AS experiment_date,
            cr.prepared_sample_id,
            fs.id AS field_sample_id,
            fs.collection_timestamp,
            prov.codename AS provider_codename,
            r.name AS resource_name,
            pap.name AS primary_product,
            p.name AS parameter_name,
            u.name AS unit,
            o.value AS observed_value,
            cr.technical_replicate_no AS repl_no,
            cr.qc_pass,
            o.note AS note,
            c.email AS analyst_email,
            'calorimetry' AS analysis_type
        FROM public.calorimetry_record cr
        JOIN public.resource r ON cr.resource_id = r.id
        JOIN public.observation o ON lower(o.record_id) = lower(cr.record_id)
        JOIN public.parameter p ON o.parameter_id = p.id
        LEFT JOIN public.unit u ON o.unit_id = u.id
        LEFT JOIN public.contact c ON cr.analyst_id = c.id
        LEFT JOIN public.prepared_sample ps ON cr.prepared_sample_id = ps.id
        LEFT JOIN public.field_sample fs    ON ps.field_sample_id = fs.id
        LEFT JOIN public.provider prov      ON fs.provider_id = prov.id
        LEFT JOIN public.experiment exp     ON cr.experiment_id = exp.id
        LEFT JOIN public.primary_ag_product pap ON r.primary_ag_product_id = pap.id
        WHERE cr.qc_pass != 'fail'

        UNION ALL

        SELECT
            xr.record_id,
            xr.experiment_id,
            exp.exper_start_date AS experiment_date,
            xr.prepared_sample_id,
            fs.id AS field_sample_id,
            fs.collection_timestamp,
            prov.codename AS provider_codename,
            r.name AS resource_name,
            pap.name AS primary_product,
            p.name AS parameter_name,
            u.name AS unit,
            o.value AS observed_value,
            xr.technical_replicate_no AS repl_no,
            xr.qc_pass,
            o.note AS note,
            c.email AS analyst_email,
            'xrd' AS analysis_type
        FROM public.xrd_record xr
        JOIN public.resource r ON xr.resource_id = r.id
        JOIN public.observation o ON lower(o.record_id) = lower(xr.record_id)
        JOIN public.parameter p ON o.parameter_id = p.id
        LEFT JOIN public.unit u ON o.unit_id = u.id
        LEFT JOIN public.contact c ON xr.analyst_id = c.id
        LEFT JOIN public.prepared_sample ps ON xr.prepared_sample_id = ps.id
        LEFT JOIN public.field_sample fs    ON ps.field_sample_id = fs.id
        LEFT JOIN public.provider prov      ON fs.provider_id = prov.id
        LEFT JOIN public.experiment exp     ON xr.experiment_id = exp.id
        LEFT JOIN public.primary_ag_product pap ON r.primary_ag_product_id = pap.id
        WHERE xr.qc_pass != 'fail'

        UNION ALL

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
            p.name AS parameter_name,
            u.name AS unit,
            o.value AS observed_value,
            fr.technical_replicate_no AS repl_no,
            fr.qc_pass,
            o.note AS note,
            c.email AS analyst_email,
            'ftnir' AS analysis_type
        FROM public.ftnir_record fr
        JOIN public.resource r ON fr.resource_id = r.id
        JOIN public.observation o ON lower(o.record_id) = lower(fr.record_id)
        JOIN public.parameter p ON o.parameter_id = p.id
        LEFT JOIN public.unit u ON o.unit_id = u.id
        LEFT JOIN public.contact c ON fr.analyst_id = c.id
        LEFT JOIN public.prepared_sample ps ON fr.prepared_sample_id = ps.id
        LEFT JOIN public.field_sample fs    ON ps.field_sample_id = fs.id
        LEFT JOIN public.provider prov      ON fs.provider_id = prov.id
        LEFT JOIN public.experiment exp     ON fr.experiment_id = exp.id
        LEFT JOIN public.primary_ag_product pap ON r.primary_ag_product_id = pap.id
        WHERE fr.qc_pass != 'fail'

        UNION ALL

        SELECT
            pr.record_id,
            pr.experiment_id,
            exp.exper_start_date AS experiment_date,
            pr.prepared_sample_id,
            fs.id AS field_sample_id,
            fs.collection_timestamp,
            prov.codename AS provider_codename,
            r.name AS resource_name,
            pap.name AS primary_product,
            p.name AS parameter_name,
            u.name AS unit,
            o.value AS observed_value,
            pr.technical_replicate_no AS repl_no,
            pr.qc_pass,
            o.note AS note,
            c.email AS analyst_email,
            'pretreatment' AS analysis_type
        FROM public.pretreatment_record pr
        JOIN public.resource r ON pr.resource_id = r.id
        JOIN public.observation o ON lower(o.record_id) = lower(pr.record_id)
        JOIN public.parameter p ON o.parameter_id = p.id
        LEFT JOIN public.unit u ON o.unit_id = u.id
        LEFT JOIN public.contact c ON pr.analyst_id = c.id
        LEFT JOIN public.prepared_sample ps ON pr.prepared_sample_id = ps.id
        LEFT JOIN public.field_sample fs    ON ps.field_sample_id = fs.id
        LEFT JOIN public.provider prov      ON fs.provider_id = prov.id
        LEFT JOIN public.experiment exp     ON pr.experiment_id = exp.id
        LEFT JOIN public.primary_ag_product pap ON r.primary_ag_product_id = pap.id
        WHERE pr.qc_pass != 'fail'
    """,

    group_by_cols=["resource_name", "analysis_type", "parameter_name", "unit"],
    numeric_cols=["observed_value"],
    id_cols=["record_id", "resource_name", "parameter_name"],
    analyst_col="analyst_email",
    gx_suite_path="audit/expectations/mv_biomass_composition.json",
    use_isolation_forest=False,
))
