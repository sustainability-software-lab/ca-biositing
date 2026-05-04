-- ============================================================================
-- Compositional Analysis Comprehensive Audit
-- ============================================================================

-- 1. RECORD COUNTS & QC GOVERNANCE
SELECT
    'compositional' AS record_type,
    COUNT(*) AS total_records,
    COUNT(*) FILTER (WHERE qc_pass = 'pass') AS qc_pass_count,
    COUNT(*) FILTER (WHERE qc_pass = 'fail') AS qc_fail_count,
    COUNT(*) FILTER (WHERE qc_pass IS NULL) AS qc_null_count
FROM compositional_record;

-- 2. METADATA COMPLETENESS (QC-PASS/NULL ONLY)
SELECT
    'compositional' AS record_type,
    COUNT(*) AS total_qc_non_fail,
    COUNT(analyst_id) AS analyst_filled,
    ROUND(100.0 * COUNT(analyst_id) / NULLIF(COUNT(*), 0), 1) AS analyst_pct,
    COUNT(method_id) AS method_filled,
    ROUND(100.0 * COUNT(method_id) / NULLIF(COUNT(*), 0), 1) AS method_pct,
    COUNT(raw_data_id) AS raw_data_filled,
    ROUND(100.0 * COUNT(raw_data_id) / NULLIF(COUNT(*), 0), 1) AS raw_data_pct,
    COUNT(experiment_id) AS experiment_filled,
    ROUND(100.0 * COUNT(experiment_id) / NULLIF(COUNT(*), 0), 1) AS experiment_pct,
    COUNT(dataset_id) AS dataset_filled,
    ROUND(100.0 * COUNT(dataset_id) / NULLIF(COUNT(*), 0), 1) AS dataset_pct
FROM compositional_record
WHERE qc_pass != 'fail';

-- 3. SAMPLE & RESOURCE CONNECTIVITY (QC-PASS/NULL ONLY)
SELECT
    'compositional' AS record_type,
    COUNT(DISTINCT cr.prepared_sample_id) AS unique_prepared_samples,
    COUNT(DISTINCT cr.resource_id) AS unique_resources,
    COUNT(DISTINCT cr.experiment_id) AS unique_experiments,
    COUNT(DISTINCT fs.id) AS unique_field_samples,
    COUNT(DISTINCT pap.id) AS unique_primary_ag_products,
    ROUND(100.0 * COUNT(DISTINCT pap.id) / NULLIF(COUNT(DISTINCT cr.prepared_sample_id), 0), 1) AS lineage_integrity_pct
FROM compositional_record cr
LEFT JOIN prepared_sample ps ON cr.prepared_sample_id = ps.id
LEFT JOIN field_sample fs ON ps.field_sample_id = fs.id
LEFT JOIN resource r ON fs.resource_id = r.id
LEFT JOIN primary_ag_product pap ON r.primary_ag_product_id = pap.id
WHERE cr.qc_pass != 'fail';

-- 4. PARAMETER COVERAGE & UNIT CONSISTENCY (QC-PASS/NULL ONLY)
SELECT
    p.name AS parameter,
    COUNT(*) AS obs_count,
    COUNT(DISTINCT u.name) AS unit_count,
    STRING_AGG(DISTINCT u.name, ', ') AS units_used,
    COUNT(DISTINCT o.record_id) AS records_with_param,
    ROUND(100.0 * COUNT(DISTINCT o.record_id) / NULLIF((SELECT COUNT(*) FROM compositional_record WHERE qc_pass != 'fail'), 0), 1) AS record_coverage_pct
FROM observation o
JOIN parameter p ON o.parameter_id = p.id
LEFT JOIN unit u ON o.unit_id = u.id
JOIN compositional_record r ON o.record_id = r.record_id
WHERE o.record_type = 'compositional analysis' AND r.qc_pass != 'fail'
GROUP BY p.name
ORDER BY obs_count DESC;

-- 5. VALUE RANGES & STATS (QC-PASS/NULL ONLY)
SELECT
    p.name AS parameter,
    MIN(o.value) AS min_val,
    MAX(o.value) AS max_val,
    ROUND(AVG(o.value)::numeric, 4) AS avg_val,
    COUNT(*) FILTER (WHERE o.value < 0) AS negative_values_count
FROM observation o
JOIN parameter p ON o.parameter_id = p.id
JOIN compositional_record r ON o.record_id = r.record_id
WHERE o.record_type = 'compositional analysis' AND r.qc_pass != 'fail' AND o.value IS NOT NULL
GROUP BY p.name;
