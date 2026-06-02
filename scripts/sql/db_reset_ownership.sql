-- ============================================================================
-- Database Reset: Phase 2 - Grant Control to biocirv_user
-- ============================================================================
-- This script is executed as the 'postgres' superuser and grants full control
-- of all schemas and their objects to biocirv_user via GRANT and
-- ALTER DEFAULT PRIVILEGES. This circumvents Cloud SQL 'SET ROLE' limitations.
-- ============================================================================

DO $$
DECLARE
    s TEXT;
    schemas TEXT[] := ARRAY[{% for schema in schemas %}'{{ schema }}'{% if not loop.last %}, {% endif %}{% endfor %}];
BEGIN
    -- Grant schema-level control
    FOREACH s IN ARRAY schemas LOOP
        -- Transfer schema ownership to biocirv_user
        EXECUTE format('ALTER SCHEMA %I OWNER TO %I', s, '{{ biocirv_user }}');

        EXECUTE format('GRANT ALL ON SCHEMA %I TO %I', s, '{{ biocirv_user }}');

        -- Grant permissions on all existing objects (tables, sequences, functions)
        EXECUTE format('GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA %I TO %I', s, '{{ biocirv_user }}');
        EXECUTE format('GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA %I TO %I', s, '{{ biocirv_user }}');
        EXECUTE format('GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA %I TO %I', s, '{{ biocirv_user }}');
        EXECUTE format('GRANT ALL PRIVILEGES ON ALL PROCEDURES IN SCHEMA %I TO %I', s, '{{ biocirv_user }}');
        EXECUTE format('GRANT ALL PRIVILEGES ON ALL ROUTINES IN SCHEMA %I TO %I', s, '{{ biocirv_user }}');

        -- Set default privileges so biocirv_user has control over objects created by postgres (e.g. during migrations)
        -- We run this as postgres, so we can only set default privileges for the postgres role.
        EXECUTE format('ALTER DEFAULT PRIVILEGES FOR ROLE %I IN SCHEMA %I GRANT ALL ON TABLES TO %I', 'postgres', s, '{{ biocirv_user }}');
        EXECUTE format('ALTER DEFAULT PRIVILEGES FOR ROLE %I IN SCHEMA %I GRANT ALL ON SEQUENCES TO %I', 'postgres', s, '{{ biocirv_user }}');
        EXECUTE format('ALTER DEFAULT PRIVILEGES FOR ROLE %I IN SCHEMA %I GRANT ALL ON FUNCTIONS TO %I', 'postgres', s, '{{ biocirv_user }}');
        EXECUTE format('ALTER DEFAULT PRIVILEGES FOR ROLE %I IN SCHEMA %I GRANT ALL ON TYPES TO %I', 'postgres', s, '{{ biocirv_user }}');

        RAISE NOTICE 'Granted full control of schema % and future objects to %', s, '{{ biocirv_user }}';
    END LOOP;

    -- Reassign all objects owned by postgres in this database to biocirv_user
    -- This handles objects like the alembic_version table or initial views
    -- created during the reset process before ownership was transferred.
    EXECUTE format('REASSIGN OWNED BY %I TO %I', 'postgres', '{{ biocirv_user }}');

    RAISE NOTICE 'Phase 2 Complete: Control granted to %', '{{ biocirv_user }}';
END $$;
