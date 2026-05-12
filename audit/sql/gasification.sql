-- ============================================================================
-- Gasification Comprehensive Audit
-- ============================================================================

-- 1. RECORD COUNTS & QC GOVERNANCE
SELECT
    'gasification' AS record_type,
    COUNT(*) AS total_records,
    COUNT(*) FILTER (WHERE qc_pass = 'pass') AS qc_pass_count,
    COUNT(*) FILTER (WHERE qc_pass = 'fail') AS qc_fail_count,
    COUNT(*) FILTER (WHERE qc_pass IS NULL) AS qc_null_count,
    ROUND(100.0 * COUNT(*) FILTER (WHERE qc_pass = 'pass') / NULLIF(COUNT(*), 0), 1) AS pass_pct
FROM gasification_record;

-- 2. METADATA & REACTOR COMPLETENESS (QC-PASS/NULL ONLY)
SELECT
    'gasification' AS record_type,
    COUNT(*) AS total_qc_non_fail,
    COUNT(analyst_id) AS analyst_filled,
    ROUND(100.0 * COUNT(analyst_id) / NULLIF(COUNT(*), 0), 1) AS analyst_pct,
    COUNT(method_id) AS method_filled,
    ROUND(100.0 * COUNT(method_id) / NULLIF(COUNT(*), 0), 1) AS method_pct,
    COUNT(experiment_id) AS experiment_filled,
    ROUND(100.0 * COUNT(experiment_id) / NULLIF(COUNT(*), 0), 1) AS experiment_pct,
    COUNT(reactor_type_id) AS reactor_filled,
    COUNT(dataset_id) AS dataset_filled
FROM gasification_record
WHERE qc_pass != 'fail';

-- 3. SAMPLE & RESOURCE CONNECTIVITY (QC-PASS/NULL ONLY)
SELECT
    'gasification' AS record_type,
    COUNT(DISTINCT gr.prepared_sample_id) AS unique_prepared_samples,
    COUNT(DISTINCT gr.resource_id) AS unique_resources,
    COUNT(DISTINCT gr.experiment_id) AS unique_experiments,
    COUNT(DISTINCT fs.id) AS unique_field_samples,
    COUNT(DISTINCT pap.id) AS unique_primary_ag_products,
    ROUND(100.0 * COUNT(DISTINCT pap.id) / NULLIF(COUNT(DISTINCT gr.prepared_sample_id), 0), 1) AS lineage_integrity_pct
FROM gasification_record gr
LEFT JOIN prepared_sample ps ON gr.prepared_sample_id = ps.id
LEFT JOIN field_sample fs ON ps.field_sample_id = fs.id
LEFT JOIN resource r ON fs.resource_id = r.id
LEFT JOIN primary_ag_product pap ON r.primary_ag_product_id = pap.id
WHERE gr.qc_pass != 'fail';

-- 4. PARAMETER COVERAGE & UNIT CONSISTENCY (QC-PASS/NULL ONLY)
SELECT
    p.name AS parameter,
    COUNT(*) AS obs_count,
    COUNT(DISTINCT u.name) AS unit_count,
    STRING_AGG(DISTINCT u.name, ', ') AS units_used,
    COUNT(DISTINCT o.record_id) AS records_with_param,
    ROUND(100.0 * COUNT(DISTINCT o.record_id) / NULLIF((SELECT COUNT(*) FROM gasification_record WHERE qc_pass != 'fail'), 0), 1) AS record_coverage_pct
FROM observation o
JOIN parameter p ON o.parameter_id = p.id
LEFT JOIN unit u ON o.unit_id = u.id
JOIN gasification_record r ON o.record_id = r.record_id
WHERE o.record_type = 'gasification' AND r.qc_pass != 'fail'
GROUP BY p.name
ORDER BY obs_count DESC;
