-- ============================================================================
-- Database Reset: Phase 3 - Grant Read-Only Access
-- ============================================================================
-- This script is executed as the 'postgres' superuser and grants SELECT-only
-- permissions to biocirv_readonly for the application schemas.
-- ============================================================================

-- Grant schema-level usage
{% for schema in schemas if schema != 'public' %}
GRANT USAGE ON SCHEMA {{ schema }} TO {{ biocirv_readonly }};
{% endfor %}

-- Grant table-level select
{% for schema in schemas if schema != 'public' %}
GRANT SELECT ON ALL TABLES IN SCHEMA {{ schema }} TO {{ biocirv_readonly }};
{% endfor %}

-- Set default permissions for future objects
{% for schema in schemas if schema != 'public' %}
ALTER DEFAULT PRIVILEGES FOR USER {{ biocirv_user }} IN SCHEMA {{ schema }}
  GRANT SELECT ON TABLES TO {{ biocirv_readonly }};
{% endfor %}

SELECT 'Phase 3 Complete: Read-only access granted' AS reset_status;
