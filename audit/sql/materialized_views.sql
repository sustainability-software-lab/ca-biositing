-- Materialized View Schema Audit
-- This module audits the columns and indexes of the data_portal materialized views
-- against the MVP specification.

-- 1. Check columns for all data_portal materialized views
SELECT
    c.relname AS view_name,
    a.attname AS column_name,
    format_type(a.atttypid, a.atttypmod) AS data_type,
    NOT a.attnotnull AS is_nullable
FROM pg_attribute a
JOIN pg_class c ON a.attrelid = c.oid
JOIN pg_namespace n ON c.relnamespace = n.oid
WHERE n.nspname = 'data_portal'
  AND c.relkind = 'm'  -- 'm' for materialized view
  AND a.attnum > 0
  AND NOT a.attisdropped
ORDER BY c.relname, a.attnum;

-- 2. Check indexes for all data_portal materialized views
SELECT
    schemaname,
    tablename AS view_name,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'data_portal'
ORDER BY tablename, indexname;
