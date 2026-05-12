-- Sample Lineage Audit
-- Chain: Prepared -> Field -> Resource -> AgProduct

-- 1. Linkage Integrity
SELECT
    (SELECT COUNT(*) FROM prepared_sample) AS total_prepared,
    COUNT(ps.id) AS linked_to_ag_product,
    ROUND(100.0 * COUNT(pap.id) / NULLIF((SELECT COUNT(*) FROM prepared_sample), 0), 2) AS integrity_pct
FROM prepared_sample ps
LEFT JOIN field_sample fs ON ps.field_sample_id = fs.id
LEFT JOIN resource r ON fs.resource_id = r.id
LEFT JOIN primary_ag_product pap ON r.primary_ag_product_id = pap.id;

-- 2. Orphaned Prepared Samples
SELECT id, name
FROM prepared_sample
WHERE field_sample_id IS NULL
LIMIT 10;
