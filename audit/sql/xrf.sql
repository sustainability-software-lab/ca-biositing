-- ============================================================================
-- XRF Analysis Comprehensive Audit
-- ============================================================================

-- 1. RECORD COUNTS & QC GOVERNANCE
SELECT
    'xrf' AS record_type,
    COUNT(*) AS total_records,
    COUNT(*) FILTER (WHERE qc_pass = 'pass') AS qc_pass_count,
    COUNT(*) FILTER (WHERE qc_pass = 'fail') AS qc_fail_count,
    COUNT(*) FILTER (WHERE qc_pass IS NULL) AS qc_null_count
FROM xrf_record;

-- 2. METADATA COMPLETENESS (QC-PASS/NULL ONLY)
SELECT
    'xrf' AS record_type,
    COUNT(*) AS total_qc_non_fail,
    COUNT(analyst_id) AS analyst_filled,
    COUNT(method_id) AS method_filled,
    COUNT(raw_data_id) AS raw_data_filled,
    COUNT(experiment_id) AS experiment_filled,
    COUNT(dataset_id) AS dataset_filled
FROM xrf_record
WHERE qc_pass != 'fail';

-- 3. SAMPLE & RESOURCE CONNECTIVITY (QC-PASS/NULL ONLY)
SELECT
    'xrf' AS record_type,
    COUNT(DISTINCT xr.prepared_sample_id) AS unique_prepared_samples,
    COUNT(DISTINCT xr.resource_id) AS unique_resources,
    COUNT(DISTINCT fs.id) AS unique_field_samples,
    COUNT(DISTINCT pap.id) AS unique_primary_ag_products,
    ROUND(100.0 * COUNT(DISTINCT pap.id) / NULLIF(COUNT(DISTINCT xr.prepared_sample_id), 0), 1) AS lineage_integrity_pct
FROM xrf_record xr
LEFT JOIN prepared_sample ps ON xr.prepared_sample_id = ps.id
LEFT JOIN field_sample fs ON ps.field_sample_id = fs.id
LEFT JOIN resource r ON fs.resource_id = r.id
LEFT JOIN primary_ag_product pap ON r.primary_ag_product_id = pap.id
WHERE xr.qc_pass != 'fail';

-- 4. PARAMETER COVERAGE & UNIT CONSISTENCY (QC-PASS/NULL ONLY)
SELECT
    p.name AS parameter,
    COUNT(*) AS obs_count,
    COUNT(DISTINCT u.name) AS unit_count,
    STRING_AGG(DISTINCT u.name, ', ') AS units_used,
    COUNT(DISTINCT o.record_id) AS records_with_param,
    ROUND(100.0 * COUNT(DISTINCT o.record_id) / NULLIF((SELECT COUNT(*) FROM xrf_record WHERE qc_pass != 'fail'), 0), 1) AS record_coverage_pct
FROM observation o
JOIN parameter p ON o.parameter_id = p.id
LEFT JOIN unit u ON o.unit_id = u.id
JOIN xrf_record r ON o.record_id = r.record_id
WHERE o.record_type = 'xrf analysis' AND r.qc_pass != 'fail'
GROUP BY p.name
ORDER BY obs_count DESC;
