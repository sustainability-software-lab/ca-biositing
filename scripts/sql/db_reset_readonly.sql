-- ============================================================================
-- Database Reset: Phase 3 - Grant Read-Only Access
-- ============================================================================
-- This script is executed as the 'postgres' superuser and grants SELECT-only
-- permissions to biocirv_readonly for the ca_biositing and data_portal schemas.
-- ============================================================================

-- Grant schema-level usage
GRANT USAGE ON SCHEMA ca_biositing TO {{ biocirv_readonly }};
GRANT USAGE ON SCHEMA data_portal TO {{ biocirv_readonly }};

-- Grant table-level select
GRANT SELECT ON ALL TABLES IN SCHEMA ca_biositing TO {{ biocirv_readonly }};
GRANT SELECT ON ALL TABLES IN SCHEMA data_portal TO {{ biocirv_readonly }};

-- Set default permissions for future objects
ALTER DEFAULT PRIVILEGES FOR USER {{ biocirv_user }} IN SCHEMA ca_biositing
  GRANT SELECT ON TABLES TO {{ biocirv_readonly }};
ALTER DEFAULT PRIVILEGES FOR USER {{ biocirv_user }} IN SCHEMA data_portal
  GRANT SELECT ON TABLES TO {{ biocirv_readonly }};

SELECT 'Phase 3 Complete: Read-only access granted' AS reset_status;
