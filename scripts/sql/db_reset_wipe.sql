-- ============================================================================
-- Database Reset: Phase 1 - Wipe Schemas and Restore Core Infrastructure
-- ============================================================================
-- This script is executed as the 'postgres' superuser and performs:
--   1. Drop all application schemas (ca_biositing, data_portal, public)
--   2. Recreate the public schema
--   3. Grant basic permissions to admin and public
--   4. Enable required PostGIS and utility extensions
-- ============================================================================

-- Drop schemas (this will cascade-delete all contained objects)
{% for schema in schemas %}
DROP SCHEMA IF EXISTS {{ schema }} CASCADE;
{% endfor %}

-- Recreate schemas
{% for schema in schemas %}
CREATE SCHEMA {{ schema }};
{% endfor %}

-- Restore basic permissions on public schema
GRANT ALL ON SCHEMA public TO {{ admin_role }};
GRANT ALL ON SCHEMA public TO public;
GRANT ALL ON SCHEMA public TO {{ biocirv_user }};
GRANT USAGE ON SCHEMA public TO {{ biocirv_readonly }};

-- Enable required extensions
{% for ext in extensions %}
CREATE EXTENSION IF NOT EXISTS {{ ext }};
{% endfor %}

-- Confirmation message
SELECT 'Phase 1 Complete: Schemas wiped and extensions restored' AS reset_status;
