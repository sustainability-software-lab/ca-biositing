-- ============================================================================
-- Database Reset: Phase 2 - Transfer Ownership to biocirv_user
-- ============================================================================
-- This script is executed as the 'postgres' superuser and transfers ownership
-- of all schemas and their objects to biocirv_user so the ETL pipeline can
-- manage them independently.
-- ============================================================================

DO $$
DECLARE
    r RECORD;
    s TEXT;
    schemas TEXT[] := ARRAY[{% for schema in schemas %}'{{ schema }}'{% if not loop.last %}, {% endif %}{% endfor %}];
BEGIN
    -- Transfer schema ownership
    FOREACH s IN ARRAY schemas LOOP
        EXECUTE format('ALTER SCHEMA %I OWNER TO %I', s, '{{ biocirv_user }}');
        RAISE NOTICE 'Transferred ownership of schema % to %', s, '{{ biocirv_user }}';
    END LOOP;

    -- Transfer table ownership
    FOREACH s IN ARRAY schemas LOOP
        FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = s) LOOP
            EXECUTE format('ALTER TABLE %I.%I OWNER TO %I', s, r.tablename, '{{ biocirv_user }}');
        END LOOP;
        RAISE NOTICE 'Transferred ownership of all tables in schema %', s;
    END LOOP;

    -- Transfer sequence ownership
    FOREACH s IN ARRAY schemas LOOP
        FOR r IN (SELECT sequence_name FROM information_schema.sequences WHERE sequence_schema = s) LOOP
            EXECUTE format('ALTER SEQUENCE %I.%I OWNER TO %I', s, r.sequence_name, '{{ biocirv_user }}');
        END LOOP;
        RAISE NOTICE 'Transferred ownership of all sequences in schema %', s;
    END LOOP;

    -- Transfer view ownership
    FOREACH s IN ARRAY schemas LOOP
        FOR r IN (SELECT viewname FROM pg_views WHERE schemaname = s) LOOP
            EXECUTE format('ALTER VIEW %I.%I OWNER TO %I', s, r.viewname, '{{ biocirv_user }}');
        END LOOP;
        RAISE NOTICE 'Transferred ownership of all views in schema %', s;
    END LOOP;

    -- Transfer materialized view ownership
    FOREACH s IN ARRAY schemas LOOP
        FOR r IN (SELECT matviewname FROM pg_matviews WHERE schemaname = s) LOOP
            EXECUTE format('ALTER MATERIALIZED VIEW %I.%I OWNER TO %I', s, r.matviewname, '{{ biocirv_user }}');
        END LOOP;
        RAISE NOTICE 'Transferred ownership of all materialized views in schema %', s;
    END LOOP;

    RAISE NOTICE 'Phase 2 Complete: Ownership transferred to %', '{{ biocirv_user }}';
END $$;
