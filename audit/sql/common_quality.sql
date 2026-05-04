-- ============================================================================
-- Common Quality & Placeholder Audit
-- ============================================================================

-- 1. PLACEHOLDER DETECTION
-- Counts occurrences of common "null-like" strings stored in numeric/text fields.
SELECT
    record_type,
    COUNT(*) AS placeholder_count,
    COUNT(*) FILTER (WHERE value::text ILIKE 'nd' OR value::text ILIKE 'ND') AS nd_count,
    COUNT(*) FILTER (WHERE value::text ILIKE 'blank' OR value::text ILIKE 'BLANK') AS blank_count,
    COUNT(*) FILTER (WHERE value::text = '') AS empty_string_count
FROM observation
WHERE value::text ILIKE 'nd'
   OR value::text ILIKE 'ND'
   OR value::text ILIKE 'blank'
   OR value::text = ''
GROUP BY record_type;

-- 2. DUPLICATE DETECTION (Record + Parameter)
-- Identifies records that have multiple observations for the same parameter.
SELECT
    record_type,
    record_id,
    p.name AS parameter,
    COUNT(*) AS observation_count
FROM observation o
JOIN parameter p ON o.parameter_id = p.id
GROUP BY record_type, record_id, p.name
HAVING COUNT(*) > 1
LIMIT 50;

-- 3. UNIT VARIATIONS BY PARAMETER
-- Identifies parameters reported in multiple different units across the database.
SELECT
    p.name AS parameter,
    COUNT(DISTINCT u.name) AS unique_units,
    STRING_AGG(DISTINCT u.name, ', ') AS units
FROM observation o
JOIN parameter p ON o.parameter_id = p.id
JOIN unit u ON o.unit_id = u.id
GROUP BY p.name
HAVING COUNT(DISTINCT u.name) > 1;

-- 4. QC FAIL OVERVIEW
-- Summary of records flagged as 'fail' across all major analytical types.
SELECT 'proximate' AS type, COUNT(*) FILTER (WHERE qc_pass = 'fail') AS fail_count FROM proximate_record
UNION ALL
SELECT 'ultimate', COUNT(*) FILTER (WHERE qc_pass = 'fail') FROM ultimate_record
UNION ALL
SELECT 'compositional', COUNT(*) FILTER (WHERE qc_pass = 'fail') FROM compositional_record
UNION ALL
SELECT 'icp', COUNT(*) FILTER (WHERE qc_pass = 'fail') FROM icp_record
UNION ALL
SELECT 'fermentation', COUNT(*) FILTER (WHERE qc_pass = 'fail') FROM fermentation_record;
