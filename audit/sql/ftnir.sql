-- ============================================================================
-- FTNIR Analysis Comprehensive Audit
-- ============================================================================

-- 1. RECORD COUNTS & QC GOVERNANCE
SELECT
    'ftnir' AS record_type,
    COUNT(*) AS total_records,
    COUNT(*) FILTER (WHERE qc_pass = 'pass') AS qc_pass_count,
    COUNT(*) FILTER (WHERE qc_pass = 'fail') AS qc_fail_count,
    COUNT(*) FILTER (WHERE qc_pass IS NULL) AS qc_null_count
FROM ftnir_record;

-- 2. METADATA COMPLETENESS (QC-PASS/NULL ONLY)
SELECT
    'ftnir' AS record_type,
    COUNT(*) AS total_qc_non_fail,
    COUNT(analyst_id) AS analyst_filled,
    COUNT(method_id) AS method_filled,
    COUNT(raw_data_id) AS raw_data_filled,
    COUNT(experiment_id) AS experiment_filled,
    COUNT(dataset_id) AS dataset_filled
FROM ftnir_record
WHERE qc_pass != 'fail';

-- 3. SAMPLE & RESOURCE CONNECTIVITY (QC-PASS/NULL ONLY)
SELECT
    'ftnir' AS record_type,
    COUNT(DISTINCT fr.prepared_sample_id) AS unique_prepared_samples,
    COUNT(DISTINCT fr.resource_id) AS unique_resources,
    COUNT(DISTINCT fs.id) AS unique_field_samples,
    COUNT(DISTINCT pap.id) AS unique_primary_ag_products,
    ROUND(100.0 * COUNT(DISTINCT pap.id) / NULLIF(COUNT(DISTINCT fr.prepared_sample_id), 0), 1) AS lineage_integrity_pct
FROM ftnir_record fr
LEFT JOIN prepared_sample ps ON fr.prepared_sample_id = ps.id
LEFT JOIN field_sample fs ON ps.field_sample_id = fs.id
LEFT JOIN resource r ON fs.resource_id = r.id
LEFT JOIN primary_ag_product pap ON r.primary_ag_product_id = pap.id
WHERE fr.qc_pass != 'fail';
