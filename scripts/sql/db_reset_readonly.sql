-- ============================================================================
-- Database Reset: Phase 3 - Grant Read-Only Access
-- ============================================================================
-- This script is executed as the 'postgres' superuser and grants SELECT-only
-- permissions to biocirv_readonly for the application schemas.
-- ============================================================================

DO $$
DECLARE
    s TEXT;
    t TEXT;
    seq TEXT;
    schemas TEXT[] := ARRAY[{% for schema in schemas %}'{{ schema }}'{% if not loop.last %}, {% endif %}{% endfor %}];
BEGIN
    -- Grant read-only access to all application schemas
    FOREACH s IN ARRAY schemas LOOP
        -- Grant schema-level usage
        EXECUTE format('GRANT USAGE ON SCHEMA %I TO %I', s, '{{ biocirv_readonly }}');

        -- Grant table-level select on existing objects
        -- Note: 'ALL TABLES' includes views and materialized views in PostgreSQL
        EXECUTE format('GRANT SELECT ON ALL TABLES IN SCHEMA %I TO %I', s, '{{ biocirv_readonly }}');
        EXECUTE format('GRANT SELECT ON ALL SEQUENCES IN SCHEMA %I TO %I', s, '{{ biocirv_readonly }}');

        -- Set default permissions for future objects created by postgres (e.g. during migrations)
        -- We run this as postgres, so we can only set default privileges for the postgres role.
        EXECUTE format('ALTER DEFAULT PRIVILEGES FOR ROLE %I IN SCHEMA %I GRANT SELECT ON TABLES TO %I', 'postgres', s, '{{ biocirv_readonly }}');
        EXECUTE format('ALTER DEFAULT PRIVILEGES FOR ROLE %I IN SCHEMA %I GRANT SELECT ON SEQUENCES TO %I', 'postgres', s, '{{ biocirv_readonly }}');

        RAISE NOTICE 'Granted read-only access to schema % for %', s, '{{ biocirv_readonly }}';
    END LOOP;

    -- CBS-SEC-003: auth tables (and their sequences) must never be readable by the
    -- read-only role. No-op right after a wipe; matters when re-run on a migrated DB.
    FOR t IN SELECT c.oid::regclass::text FROM pg_class c
             WHERE c.oid IN (to_regclass('public.api_user'), to_regclass('public.api_key'))
    LOOP
        EXECUTE format('REVOKE ALL ON TABLE %s FROM %I', t, '{{ biocirv_readonly }}');
        FOR seq IN SELECT pg_get_serial_sequence(t, a.attname)
                   FROM pg_attribute a
                   WHERE a.attrelid = t::regclass AND a.attnum > 0 AND NOT a.attisdropped
                     AND pg_get_serial_sequence(t, a.attname) IS NOT NULL
        LOOP
            EXECUTE format('REVOKE ALL ON SEQUENCE %s FROM %I', seq, '{{ biocirv_readonly }}');
        END LOOP;
    END LOOP;

    RAISE NOTICE 'Phase 3 Complete: Read-only access granted to %', '{{ biocirv_readonly }}';
END $$;
