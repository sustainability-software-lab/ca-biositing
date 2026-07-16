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
            r.name          AS resource_name,
            'compositional' AS analysis_type,
            p.name          AS parameter_name,
            u.name          AS unit,
            o.value         AS observed_value,
            cr.record_id,
            cr.qc_pass,
            cr.note,
            c.name          AS analyst_name,
            c.email         AS analyst_email,
            cr.created_at
        FROM public.compositional_record cr
        JOIN public.resource r ON cr.resource_id = r.id
        JOIN public.observation o ON lower(o.record_id) = lower(cr.record_id)
        JOIN public.parameter p ON o.parameter_id = p.id
        LEFT JOIN public.unit u ON o.unit_id = u.id
        LEFT JOIN public.contact c ON cr.analyst_id = c.id
        WHERE cr.qc_pass != 'fail'

        UNION ALL

        SELECT
            r.name          AS resource_name,
            'proximate'     AS analysis_type,
            p.name          AS parameter_name,
            u.name          AS unit,
            o.value         AS observed_value,
            pr.record_id,
            pr.qc_pass,
            pr.note,
            c.name          AS analyst_name,
            c.email         AS analyst_email,
            pr.created_at
        FROM public.proximate_record pr
        JOIN public.resource r ON pr.resource_id = r.id
        JOIN public.observation o ON lower(o.record_id) = lower(pr.record_id)
        JOIN public.parameter p ON o.parameter_id = p.id
        LEFT JOIN public.unit u ON o.unit_id = u.id
        LEFT JOIN public.contact c ON pr.analyst_id = c.id
        WHERE pr.qc_pass != 'fail'

        UNION ALL

        SELECT
            r.name          AS resource_name,
            'ultimate'      AS analysis_type,
            p.name          AS parameter_name,
            u.name          AS unit,
            o.value         AS observed_value,
            ur.record_id,
            ur.qc_pass,
            ur.note,
            c.name          AS analyst_name,
            c.email         AS analyst_email,
            ur.created_at
        FROM public.ultimate_record ur
        JOIN public.resource r ON ur.resource_id = r.id
        JOIN public.observation o ON lower(o.record_id) = lower(ur.record_id)
        JOIN public.parameter p ON o.parameter_id = p.id
        LEFT JOIN public.unit u ON o.unit_id = u.id
        LEFT JOIN public.contact c ON ur.analyst_id = c.id
        WHERE ur.qc_pass != 'fail'
        UNION ALL

        SELECT
            r.name          AS resource_name,
            'xrf'           AS analysis_type,
            p.name          AS parameter_name,
            u.name          AS unit,
            o.value         AS observed_value,
            xr.record_id,
            xr.qc_pass,
            xr.note,
            c.name          AS analyst_name,
            c.email         AS analyst_email,
            xr.created_at
        FROM public.xrf_record xr
        JOIN public.resource r ON xr.resource_id = r.id
        JOIN public.observation o ON lower(o.record_id) = lower(xr.record_id)
        JOIN public.parameter p ON o.parameter_id = p.id
        LEFT JOIN public.unit u ON o.unit_id = u.id
        LEFT JOIN public.contact c ON xr.analyst_id = c.id
        WHERE xr.qc_pass != 'fail'

        UNION ALL

        SELECT
            r.name          AS resource_name,
            'icp'           AS analysis_type,
            p.name          AS parameter_name,
            u.name          AS unit,
            o.value         AS observed_value,
            ir.record_id,
            ir.qc_pass,
            ir.note,
            c.name          AS analyst_name,
            c.email         AS analyst_email,
            ir.created_at
        FROM public.icp_record ir
        JOIN public.resource r ON ir.resource_id = r.id
        JOIN public.observation o ON lower(o.record_id) = lower(ir.record_id)
        JOIN public.parameter p ON o.parameter_id = p.id
        LEFT JOIN public.unit u ON o.unit_id = u.id
        LEFT JOIN public.contact c ON ir.analyst_id = c.id
        WHERE ir.qc_pass != 'fail'

        UNION ALL

        SELECT
            r.name          AS resource_name,
            'calorimetry'   AS analysis_type,
            p.name          AS parameter_name,
            u.name          AS unit,
            o.value         AS observed_value,
            cr.record_id,
            cr.qc_pass,
            cr.note,
            c.name          AS analyst_name,
            c.email         AS analyst_email,
            cr.created_at
        FROM public.calorimetry_record cr
        JOIN public.resource r ON cr.resource_id = r.id
        JOIN public.observation o ON lower(o.record_id) = lower(cr.record_id)
        JOIN public.parameter p ON o.parameter_id = p.id
        LEFT JOIN public.unit u ON o.unit_id = u.id
        LEFT JOIN public.contact c ON cr.analyst_id = c.id
        WHERE cr.qc_pass != 'fail'

        UNION ALL

        SELECT
            r.name          AS resource_name,
            'xrd'           AS analysis_type,
            p.name          AS parameter_name,
            u.name          AS unit,
            o.value         AS observed_value,
            xr.record_id,
            xr.qc_pass,
            xr.note,
            c.name          AS analyst_name,
            c.email         AS analyst_email,
            xr.created_at
        FROM public.xrd_record xr
        JOIN public.resource r ON xr.resource_id = r.id
        JOIN public.observation o ON lower(o.record_id) = lower(xr.record_id)
        JOIN public.parameter p ON o.parameter_id = p.id
        LEFT JOIN public.unit u ON o.unit_id = u.id
        LEFT JOIN public.contact c ON xr.analyst_id = c.id
        WHERE xr.qc_pass != 'fail'

        UNION ALL

        SELECT
            r.name          AS resource_name,
            'ftnir'         AS analysis_type,
            p.name          AS parameter_name,
            u.name          AS unit,
            o.value         AS observed_value,
            fr.record_id,
            fr.qc_pass,
            fr.note,
            c.name          AS analyst_name,
            c.email         AS analyst_email,
            fr.created_at
        FROM public.ftnir_record fr
        JOIN public.resource r ON fr.resource_id = r.id
        JOIN public.observation o ON lower(o.record_id) = lower(fr.record_id)
        JOIN public.parameter p ON o.parameter_id = p.id
        LEFT JOIN public.unit u ON o.unit_id = u.id
        LEFT JOIN public.contact c ON fr.analyst_id = c.id
        WHERE fr.qc_pass != 'fail'

        UNION ALL

        SELECT
            r.name          AS resource_name,
            'pretreatment'  AS analysis_type,
            p.name          AS parameter_name,
            u.name          AS unit,
            o.value         AS observed_value,
            pr.record_id,
            pr.qc_pass,
            pr.note,
            c.name          AS analyst_name,
            c.email         AS analyst_email,
            pr.created_at
        FROM public.pretreatment_record pr
        JOIN public.resource r ON pr.resource_id = r.id
        JOIN public.observation o ON lower(o.record_id) = lower(pr.record_id)
        JOIN public.parameter p ON o.parameter_id = p.id
        LEFT JOIN public.unit u ON o.unit_id = u.id
        LEFT JOIN public.contact c ON pr.analyst_id = c.id
        WHERE pr.qc_pass != 'fail'
    """,

    group_by_cols=["resource_name", "analysis_type", "parameter_name", "unit"],
    numeric_cols=["observed_value"],
    id_cols=["record_id", "resource_name", "parameter_name"],
    analyst_col="analyst_email",
    gx_suite_path="audit/expectations/mv_biomass_composition.json",
    use_isolation_forest=False,
))
