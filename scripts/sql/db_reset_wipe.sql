-- ============================================================================
-- Database Reset: Phase 1 - Wipe Schemas and Restore Core Infrastructure
-- ============================================================================
-- This script is executed as the 'postgres' superuser and performs:
--   1. Drop all application schemas (ca_biositing, data_portal, public)
--   2. Recreate the public schema
--   3. Grant basic permissions to postgres and public
--   4. Enable required PostGIS and utility extensions
-- ============================================================================

-- Drop schemas (this will cascade-delete all contained objects)
DROP SCHEMA IF EXISTS ca_biositing CASCADE;
DROP SCHEMA IF EXISTS data_portal CASCADE;
DROP SCHEMA IF EXISTS public CASCADE;

-- Recreate the public schema
CREATE SCHEMA public;

-- Restore basic permissions on public schema
GRANT ALL ON SCHEMA public TO postgres;
GRANT ALL ON SCHEMA public TO public;
GRANT ALL ON SCHEMA public TO {{ biocirv_user }};
GRANT USAGE ON SCHEMA public TO {{ biocirv_readonly }};

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;
CREATE EXTENSION IF NOT EXISTS btree_gin;

-- Confirmation message
SELECT 'Phase 1 Complete: Schemas wiped and extensions restored' AS reset_status;
