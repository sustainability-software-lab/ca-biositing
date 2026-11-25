# Runbook: Move Auth Tables to the `auth` Schema (Migration 0029)

Step-by-step procedure for upgrading an existing database that already holds
`api_user` and `api_key` rows (staging, production, or a long-lived local DB)
from revision `0028` to `0029`. See #580 and PR #582.

Migration `0029` runs `ALTER TABLE ... SET SCHEMA auth` on both tables. This is
a catalog-only change: rows, primary keys, the `api_key -> api_user` foreign
key, indexes, and the `id` sequences move with the tables, so user ids, API
keys, and password hashes are unchanged. Nobody needs a new key or password.

**Plan for a short maintenance window.** Between the moment the new webservice
image is live and the moment `0029` has run, login (`/v1/auth/token`), API-key
requests, and admin user/key endpoints fail with HTTP 500 because the old schema
and the new code disagree. Public endpoints are unaffected. With the normal
deploy pipeline this window is a few minutes.

---

## Why there is a window

The deploy workflows (`deploy-staging.yml`, `deploy-production.yml`) run in this
order:

1. **Deploy Infrastructure (Pulumi)** with `IMAGE_TAG` set: the webservice
   service and the migration job are updated to the new image.
2. **Run Database Migrations**: `cloud-migrate-ci` executes the
   `biocirv-<env>-migrate` Cloud Run job (`alembic upgrade head`).
3. **Force Cloud Run Revision Updates** and **Validate Deployment Health**.

After step 1 the new code queries `auth.api_user`; until step 2 finishes the
tables are still in `public`. The reverse also holds: old code cannot read the
tables once `0029` has run. Neither order is safe without a window.

---

## Prerequisites

- PR #582 is merged and the "Build and Push Docker Images" workflow has produced
  images for the merge commit.
- `gcloud` is authenticated to project `biocirv-470318` with permission to run
  Cloud Run jobs and read the DB password secret.
- The Cloud SQL Auth Proxy is available locally, using the project's port
  convention: `5434` for staging, `5435` for production (see
  [DB_RESET.md](DB_RESET.md)).
- Migrations run as `biocirv_user`, the owner of `api_user` and `api_key`.
  `SET SCHEMA` requires table ownership; step 1 checks it.
- Announce the window to API-key holders and admins.

Shell variables used below (production shown; use `staging`/`5434` for staging):

```bash
export DEPLOY_ENV=production
export PGPORT=5435
export PGHOST=localhost
export PGUSER=biocirv_user
export PGDATABASE=biocirv-production
export PGPASSWORD="$(gcloud secrets versions access latest --secret="biocirv-${DEPLOY_ENV}-db-password")"
```

`biocirv-<env>-db-password` is the `biocirv_user` password secret created by
Pulumi (`SECRET_DB_PASSWORD` in
`deployment/cloud/gcp/infrastructure/config.py`).

---

## Step 1: Pre-flight checks (no changes)

Start the Cloud SQL Auth Proxy on `$PGPORT`, then record the current state:

```sql
SELECT (SELECT version_num FROM alembic_version)         AS alembic_head,
       (SELECT count(*) FROM public.api_user)            AS users,
       (SELECT count(*) FROM public.api_key)             AS keys,
       (SELECT max(id) FROM public.api_user)             AS max_user_id,
       pg_get_userbyid(c.relowner)                       AS api_user_owner,
       to_regnamespace('auth') IS NOT NULL               AS auth_schema_exists
FROM pg_class c
WHERE c.oid = 'public.api_user'::regclass;
```

Continue only if:

| Column               | Expected                      |
| -------------------- | ----------------------------- |
| `alembic_head`       | `0028`                        |
| `api_user_owner`     | `biocirv_user`                |
| `auth_schema_exists` | `f`                           |
| `users`, `keys`      | non-zero; note them for later |

If `alembic_head` is older than `0028`, that's fine: `upgrade head` applies
`0028` and `0029` in order. If `auth_schema_exists` is `t`, stop and inspect;
someone has created the schema by hand.

## Step 2: Back up

Take an on-demand Cloud SQL backup, and a logical dump of the two tables as a
fast restore path:

```bash
gcloud sql backups create --instance="biocirv-${DEPLOY_ENV}" \
  --description="pre-0029 auth schema move"

pg_dump --data-only --table=public.api_user --table=public.api_key \
  --file="auth_tables_pre_0029_${DEPLOY_ENV}.sql"
```

Store the dump outside the repository and delete it after the change is
verified; it contains password and key hashes.

## Step 3: Run the deploy (opens the window)

**Production:** run the "Deploy Production" workflow (release-triggered or
`workflow_dispatch`).

**Staging:** the "Deploy Staging" workflow runs automatically after the image
build on `main`; you can also trigger it with `workflow_dispatch`.

Watch the "Run Database Migrations" job. Its log ends with:

```
Running upgrade 0028 -> 0029, Move auth tables into a dedicated auth schema (#580)
```

The window closes when that job succeeds.

### Manual alternative

If you need to apply the migration outside the workflow (for example, the
workflow failed after Pulumi), run the same job directly. Use the image tag the
workflow deployed:

```bash
DEPLOY_ENV=$DEPLOY_ENV IMAGE_TAG=<short-sha> pixi run -e deployment cloud-migrate-ci
```

Or from your machine through the proxy:

```bash
POSTGRES_HOST=localhost POSTGRES_PORT=$PGPORT pixi run migrate
```

## Step 4: Verify

```sql
SELECT (SELECT version_num FROM alembic_version)                    AS alembic_head,
       (SELECT count(*) FROM auth.api_user)                         AS users,
       (SELECT count(*) FROM auth.api_key)                          AS keys,
       to_regclass('public.api_user') IS NULL
         AND to_regclass('public.api_key') IS NULL                  AS public_empty,
       has_schema_privilege('biocirv_readonly', 'auth', 'USAGE')    AS readonly_usage,
       pg_get_serial_sequence('auth.api_user', 'id')                AS user_seq;
```

Expected: `alembic_head = 0029`; `users` and `keys` match step 1;
`public_empty = t`; `readonly_usage = f`; `user_seq = auth.api_user_id_seq`.

Then run the grant check against the same database:

```bash
DATABASE_URL="postgresql+psycopg2://biocirv_user:${PGPASSWORD}@localhost:${PGPORT}/${PGDATABASE}" \
  pixi run python scripts/check_readonly_auth_grants.py
# OK: biocirv_readonly cannot read auth tables: auth.api_key, auth.api_user
```

Smoke-test the service:

1. `GET /health` returns 200 (the workflow's "Validate Deployment Health" job
   also checks this).
2. Log in as an existing admin via `POST /v1/auth/token`.
3. Call a protected endpoint with an existing API key.
4. `GET /v1/auth/api-keys` as admin returns the expected keys.

Announce the end of the window.

---

## Rollback

`0029` is reversible and keeps data. Roll back the database and the webservice
image together, because each version of the code works with only one schema
layout.

1. Downgrade the database (through the proxy):

   ```bash
   DATABASE_URL="postgresql+psycopg2://biocirv_user:${PGPASSWORD}@localhost:${PGPORT}/${PGDATABASE}" \
     pixi run alembic downgrade 0028
   ```

   Both tables move back to `public` with their rows, index names are restored,
   and the `auth` schema is dropped. The `0028` revokes stay in place, so
   `biocirv_readonly` still cannot read them.

2. Redeploy the previous webservice image:

   ```bash
   DEPLOY_ENV=$DEPLOY_ENV IMAGE_TAG=<previous-short-sha> pixi run -e deployment cloud-update-services
   ```

3. Re-run the step 1 query and confirm the counts and `alembic_head = 0028`.

If the database is damaged, restore from the step 2 backup instead
(`gcloud sql backups restore`), which replaces the whole instance's data.

---

## Notes

- **Local databases:** `pixi run migrate` applies `0029` to the Docker DB. To
  start fresh instead, `pixi run db-reset-local` now also wipes and recreates
  the `auth` schema (it is listed under `private_schemas` in
  `resources/config/db_reset.yaml`).
- **Read-only consumers:** anything connecting as `biocirv_readonly` (for
  example the dashboards publisher) could not read the auth tables after `0028`
  and still cannot. No change is needed.
- **Scripts that write raw SQL** against `api_user`/`api_key` must use
  `auth.api_user`/`auth.api_key`. `scripts/create_admin.py` uses the ORM model
  and needs no change.

## Verification of this runbook

Tested on a throwaway `postgis/postgis:17-3.5` database migrated to `0028` and
seeded with two users and one API key: the pre-flight query, `upgrade head`, the
verification query, `check_readonly_auth_grants.py`, a new `INSERT` (which got
the next id from the moved sequence), the FK join, `downgrade 0028`, and a
re-upgrade all behaved as described. It has not yet been run against Cloud SQL.
