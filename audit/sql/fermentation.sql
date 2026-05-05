-- ============================================================================
-- Fermentation Comprehensive Audit
-- ============================================================================

-- 1. RECORD COUNTS & QC GOVERNANCE
SELECT
    'fermentation' AS record_type,
    COUNT(*) AS total_records,
    COUNT(*) FILTER (WHERE qc_pass = 'pass') AS qc_pass_count,
    COUNT(*) FILTER (WHERE qc_pass = 'fail') AS qc_fail_count,
    COUNT(*) FILTER (WHERE qc_pass IS NULL) AS qc_null_count,
    ROUND(100.0 * COUNT(*) FILTER (WHERE qc_pass = 'pass') / NULLIF(COUNT(*), 0), 1) AS pass_pct
FROM fermentation_record;

-- 2. METADATA & PROCESSING METHOD COMPLETENESS (QC-PASS/NULL ONLY)
SELECT
    'fermentation' AS record_type,
    COUNT(*) AS total_qc_non_fail,
    COUNT(analyst_id) AS analyst_filled,
    COUNT(method_id) AS method_filled,
    COUNT(raw_data_id) AS raw_data_filled,
    COUNT(experiment_id) AS experiment_filled,
    COUNT(strain_id) AS strain_filled,
    COUNT(vessel_id) AS vessel_filled,
    COUNT(pretreatment_method_id) AS pretreatment_method_filled,
    COUNT(eh_method_id) AS eh_method_filled,
    COUNT(bioconversion_method_id) AS bioconversion_method_filled,
    COUNT(well_position) AS well_position_filled
FROM fermentation_record
WHERE qc_pass != 'fail';

-- 3. PERCENT COVERAGE MATRIX
SELECT
    'fermentation' AS record_type,
    ROUND(100.0 * COUNT(analyst_id) / COUNT(*), 1) AS analyst_pct,
    ROUND(100.0 * COUNT(method_id) / COUNT(*), 1) AS method_pct,
    ROUND(100.0 * COUNT(experiment_id) / COUNT(*), 1) AS experiment_pct,
    ROUND(100.0 * COUNT(strain_id) / COUNT(*), 1) AS strain_pct,
    ROUND(100.0 * COUNT(pretreatment_method_id) / COUNT(*), 1) AS pretreatment_pct,
    ROUND(100.0 * COUNT(eh_method_id) / COUNT(*), 1) AS eh_pct,
    ROUND(100.0 * COUNT(bioconversion_method_id) / COUNT(*), 1) AS bioconversion_pct
FROM fermentation_record
WHERE qc_pass != 'fail';

-- 4. SAMPLE & RESOURCE CONNECTIVITY
SELECT
    'fermentation' AS record_type,
    COUNT(DISTINCT fr.prepared_sample_id) AS unique_prepared_samples,
    COUNT(DISTINCT fr.resource_id) AS unique_resources,
    COUNT(DISTINCT fr.experiment_id) AS unique_experiments,
    COUNT(DISTINCT fs.id) AS unique_field_samples,
    COUNT(DISTINCT pap.id) AS unique_primary_ag_products
FROM fermentation_record fr
LEFT JOIN prepared_sample ps ON fr.prepared_sample_id = ps.id
LEFT JOIN field_sample fs ON ps.field_sample_id = fs.id
LEFT JOIN resource r ON fs.resource_id = r.id
LEFT JOIN primary_ag_product pap ON r.primary_ag_product_id = pap.id
WHERE fr.qc_pass != 'fail';

-- 5. PARAMETER COVERAGE
SELECT
    p.name AS parameter,
    u.name AS unit,
    COUNT(*) AS obs_count,
    COUNT(DISTINCT o.record_id) AS records_with_param
FROM observation o
JOIN parameter p ON o.parameter_id = p.id
LEFT JOIN unit u ON o.unit_id = u.id
JOIN fermentation_record r ON o.record_id = r.record_id
WHERE o.record_type = 'fermentation' AND r.qc_pass != 'fail'
GROUP BY p.name, u.name
ORDER BY obs_count DESC;
