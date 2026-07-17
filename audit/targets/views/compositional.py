# audit/targets/views/compositional.py
#
# Granular audit target for compositional analysis records only.
#
# Filter parity with mv_biomass_composition / ANALYSIS_DATA_VIEW:
#   - qc_pass != 'fail'
#   - compositional_sum between 40 and 105 (or sum == 0 meaning no key params present)
#   - resource exclusions: sargassum, #n/a, lab media, alfalfa,
#     almond hulls and shells mix, almond shells and hulls mix, almond woodchips
#
from audit.targets.registry import AuditTarget, register

register(AuditTarget(
    name="compositional",
    source_type="view",
    description=(
        "Compositional (lignocellulosic) analysis records: glucan, xylan, lignin, "
        "arabinan, mannan, galactan, acetyl, ash, moisture, etc. "
        "Filtered to qc_pass != 'fail' and compositional sum in [40, 105] "
        "(glucan + xylan + lignin). Excludes problematic resources."
    ),

    # Layer 1: population-level stats per resource / parameter / unit
    population_sql="""
        WITH qc_sums AS (
            SELECT
                cr.resource_id,
                cr.experiment_id,
                COALESCE(AVG(CASE WHEN LOWER(p.name) = 'glucan'   THEN o.value END), 0)
                + COALESCE(AVG(CASE WHEN LOWER(p.name) = 'xylan'  THEN o.value END), 0)
                + COALESCE(
                    AVG(CASE WHEN LOWER(p.name) = 'lignin'  THEN o.value END),
                    AVG(CASE WHEN LOWER(p.name) = 'lignin+' THEN o.value END)
                  ) AS compositional_sum
            FROM public.compositional_record cr
            JOIN public.observation o
                ON LOWER(o.record_id) = LOWER(cr.record_id)
                AND o.record_type IN ('compositional analysis', 'compositional_analysis')
            JOIN public.parameter p ON o.parameter_id = p.id
            WHERE cr.qc_pass != 'fail'
            GROUP BY cr.resource_id, cr.experiment_id
        )
        SELECT
            r.name                  AS resource_name,
            CASE WHEN p.name = 'ash' THEN 'ash solids' ELSE LOWER(p.name) END AS parameter_name,
            LOWER(u.name)           AS unit,
            AVG(o.value)            AS avg_value,
            STDDEV(o.value)         AS std_dev,
            MIN(o.value)            AS min_value,
            MAX(o.value)            AS max_value,
            COUNT(o.value)          AS observation_count
        FROM public.compositional_record cr
        JOIN public.resource r ON cr.resource_id = r.id
        JOIN public.observation o
            ON LOWER(o.record_id) = LOWER(cr.record_id)
            AND o.record_type IN ('compositional analysis', 'compositional_analysis')
        JOIN public.parameter p ON o.parameter_id = p.id
        LEFT JOIN public.unit u ON o.unit_id = u.id
        JOIN qc_sums qs
            ON qs.resource_id = cr.resource_id
            AND COALESCE(qs.experiment_id, -1) = COALESCE(cr.experiment_id, -1)
        WHERE
            cr.qc_pass != 'fail'
            AND LOWER(r.name) NOT IN (
                'sargassum', '#n/a', 'lab media', 'alfalfa',
                'almond hulls and shells mix',
                'almond shells and hulls mix',
                'almond woodchips'
            )
            AND (
                qs.compositional_sum = 0
                OR (qs.compositional_sum >= 40 AND qs.compositional_sum <= 105)
            )
        GROUP BY r.name, p.name, u.name
        HAVING COUNT(o.value) >= 3
    """,

    # Layer 2: individual observations with analyst attribution and QC context
    observation_sql="""
        WITH qc_sums AS (
            SELECT
                cr.resource_id,
                cr.experiment_id,
                COALESCE(AVG(CASE WHEN LOWER(p.name) = 'glucan'   THEN o.value END), 0)
                + COALESCE(AVG(CASE WHEN LOWER(p.name) = 'xylan'  THEN o.value END), 0)
                + COALESCE(
                    AVG(CASE WHEN LOWER(p.name) = 'lignin'  THEN o.value END),
                    AVG(CASE WHEN LOWER(p.name) = 'lignin+' THEN o.value END)
                  ) AS compositional_sum
            FROM public.compositional_record cr
            JOIN public.observation o
                ON LOWER(o.record_id) = LOWER(cr.record_id)
                AND o.record_type IN ('compositional analysis', 'compositional_analysis')
            JOIN public.parameter p ON o.parameter_id = p.id
            WHERE cr.qc_pass != 'fail'
            GROUP BY cr.resource_id, cr.experiment_id
        )
        SELECT
            r.name          AS resource_name,
            CASE WHEN p.name = 'ash' THEN 'ash solids' ELSE LOWER(p.name) END AS parameter_name,
            LOWER(u.name)   AS unit,
            o.value         AS observed_value,
            cr.record_id,
            cr.qc_pass,
            cr.note,
            c.name          AS analyst_name,
            c.email         AS analyst_email,
            cr.created_at,
            prov.codename    AS provider_codename,
            cr.created_at    AS sample_date  -- fallback: no dedicated sample_date column on this record type
        FROM public.compositional_record cr
        JOIN public.resource r ON cr.resource_id = r.id
        JOIN public.observation o
            ON LOWER(o.record_id) = LOWER(cr.record_id)
            AND o.record_type IN ('compositional analysis', 'compositional_analysis')
        JOIN public.parameter p ON o.parameter_id = p.id
        LEFT JOIN public.unit u ON o.unit_id = u.id
        LEFT JOIN public.contact c ON cr.analyst_id = c.id
        LEFT JOIN public.prepared_sample ps ON cr.prepared_sample_id = ps.id
        LEFT JOIN public.field_sample fs    ON ps.field_sample_id = fs.id
        LEFT JOIN public.provider prov      ON fs.provider_id = prov.id
        JOIN qc_sums qs
            ON qs.resource_id = cr.resource_id
            AND COALESCE(qs.experiment_id, -1) = COALESCE(cr.experiment_id, -1)
        WHERE
            cr.qc_pass != 'fail'
            AND LOWER(r.name) NOT IN (
                'sargassum', '#n/a', 'lab media', 'alfalfa',
                'almond hulls and shells mix',
                'almond shells and hulls mix',
                'almond woodchips'
            )
            AND (
                qs.compositional_sum = 0
                OR (qs.compositional_sum >= 40 AND qs.compositional_sum <= 105)
            )
    """,

    group_by_cols=["resource_name", "parameter_name", "unit"],
    numeric_cols=["observed_value"],
    id_cols=["record_id", "resource_name", "parameter_name"],
    analyst_col="analyst_email",
    gx_suite_path="audit/expectations/compositional.json",
    use_isolation_forest=False,
))
