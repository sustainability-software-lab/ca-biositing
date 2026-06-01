# Database Reset Operations Guide

This guide describes the standardized database reset process for the
`ca-biositing` project.

## Overview

The database reset process is a three-phase operation that wipes application
schemas, restores core infrastructure (extensions), transfers control to the
application user, and grants read-only access.

### Why Reset?

A reset is typically required when:

1. The database schema has become inconsistent or corrupted.
2. A "Clean Slate" is needed for testing or data loading.
3. Migrating to a new environment.

**WARNING: This operation is DESTRUCTIVE. All data in the application schemas
will be PERMANENTLY DELETED.**

---

## Architecture

The reset process is orchestrated by a Python script (`scripts/db_reset.py`)
that uses Jinja2-templated SQL files.

1.  **Phase 1: Wipe (`db_reset_wipe.sql`)**: Drops `public`, `ca_biositing`, and
    `data_portal` schemas. Recreates schemas as the current user and grants
    `ALL` to `biocirv_user`. Enables extensions (`postgis`, etc.).
2.  **Phase 2: Control (`db_reset_ownership.sql`)**: Grants `ALL PRIVILEGES` to
    `biocirv_user` and sets `ALTER DEFAULT PRIVILEGES` for future objects.
3.  **Phase 3: Read-Only (`db_reset_readonly.sql`)**: Grants `SELECT` access to
    `biocirv_readonly`.

---

## Cloud SQL Permission Model (IMPORTANT)

Due to circular membership restrictions in Google Cloud SQL, we use a
**Grant-based Control Model** rather than a strict **Ownership Model**.

### Role Hierarchy

To allow the `postgres` user to manage application objects without `SET ROLE`
errors, the following role membership must be established:

1.  `postgres` must be a member of `biocirv_user`.
2.  `biocirv_user` must **NOT** be a member of `postgres`.

If you encounter `must be able to SET ROLE "biocirv_user"`, run the following
SQL as a superuser:

```sql
REVOKE postgres FROM biocirv_user;
GRANT biocirv_user TO postgres;
```

### Ownership vs. Control

- **Owner**: The `postgres` user technically owns the schemas and objects
  created during migrations.
- **Control**: The `biocirv_user` is granted `ALL PRIVILEGES` on these objects.
- **Default Privileges**: `ALTER DEFAULT PRIVILEGES` ensures that any new
  objects created by `postgres` (e.g. during migrations) automatically grant
  full control to `biocirv_user`.

---

## Prerequisites

### Local Environment

- Docker services must be running: `pixi run start-services`
- Environment variables (optional, defaults used if missing):
  `POSTGRES_PASSWORD`

### Staging/Production

- Cloud SQL Auth Proxy must be running on the expected ports:
  - **Staging**: Port `5434`
  - **Production**: Port `5433`
- Credentials must be set in environment variables:
  - `DB_PASSWORD_STAGING`
  - `DB_PASSWORD_PROD`

---

## Usage

### 1. Dry Run (Recommended)

Always perform a dry run first to see what would happen:

```bash
pixi run db-reset-local-dry-run
# or
python scripts/db_reset.py --env staging --dry-run
```

### 2. Local Reset

```bash
pixi run db-reset-local
```

### 3. Staging Reset

```bash
pixi run db-reset-staging
```

### 4. Production Reset

```bash
pixi run db-reset-prod
```

### 5. Force Reset (Non-Interactive)

To skip the confirmation prompt (useful for CI/CD):

```bash
pixi run db-reset-staging-force
```

---

## Post-Reset Steps

After a successful reset, the database is empty. You must apply migrations and
load data.

### 1. Apply Migrations

To apply migrations to a specific environment, set the `POSTGRES_HOST` and
`POSTGRES_PORT` environment variables to point to the Cloud SQL Auth Proxy.

**Local**:

```bash
pixi run migrate
```

**Staging**:

```bash
POSTGRES_HOST=localhost POSTGRES_PORT=5434 pixi run migrate
```

**Production**:

```bash
POSTGRES_HOST=localhost POSTGRES_PORT=5433 pixi run migrate
```

### 2. Trigger ETL

The ETL pipeline is typically triggered via Prefect. Ensure you are targeting
the correct environment in your Prefect configuration or by using the
appropriate deployment.

**Local**:

```bash
pixi run run-etl
```

**Cloud (Staging/Production)**: ETL for cloud environments is usually managed
through the Prefect Cloud UI or CI/CD pipelines. Refer to
[`docs/pipeline/DEPLOYMENT.md`](docs/pipeline/DEPLOYMENT.md) for more details.

---

## Troubleshooting

### Connection Errors

- Verify that the database is accessible and the correct port is being used.
- For cloud environments, ensure the Cloud SQL Auth Proxy is running.
- Check if your IP is authorized (if not using the proxy).

### Permission Denied

- The reset script must be executed as the `postgres` superuser (configured in
  `resources/config/db_reset.yaml`).
- If you encounter permission errors during ownership transfer, ensure the
  `biocirv_user` and `biocirv_readonly` roles exist.

### Logs

Detailed logs are created for every reset attempt:
`logs/db_reset/reset_{env}_{timestamp}.log`
