# Deployment Directory

This directory contains deployment resources, specifically cloud deployment
resources, for getting the ca-biositing project up and running on Google Cloud
Platform (GCP) using Pulumi (Python).

# Directory Structure

```text
deployment
├── cloud/gcp/infrastructure/    # Pulumi infrastructure-as-code (Python)
│   ├── apis.py                  # GCP API enablement
│   ├── artifact_registry.py     # GHCR and Quay.io remote repos
│   ├── cloud_run.py             # Cloud Run services and jobs
│   ├── cloud_sql.py             # Cloud SQL instance and databases
│   ├── config.py                # Constants and stack configuration
│   ├── deploy.py                # Pulumi Automation API entry point
│   ├── iam.py                   # Service accounts and IAM bindings
│   ├── networking.py            # Cloud Router and Cloud NAT
│   ├── secret_manager.py        # Secret Manager secrets
│   ├── storage.py               # GCS buckets
│   └── wif.py                   # Workload Identity Federation
```

## Quick Start

### Prerequisites

- Access to the BioCirV project in GCP
- `gcloud` CLI:
  https://docs.cloud.google.com/sdk/docs/install-sdk#latest-version
- Pulumi CLI (installed automatically via pixi):

  ```bash
  pixi run -e deployment install-pulumi
  ```

  Verify installation:

  ```bash
  pixi run -e deployment pulumi version
  ```

### Sign into gcloud CLI

Run both commands to authenticate fully. The first authenticates the gcloud CLI
itself; the second creates Application Default Credentials (ADC) used by Pulumi
and other tools.

```bash
# 1. Authenticate the gcloud CLI (required for gcloud commands)
gcloud auth login

# 2. Create Application Default Credentials (required for Pulumi and SDKs)
gcloud auth application-default login
```

Make sure to configure the project property correctly. You can see it with the
following command

```bash
gcloud config get project
```

And set it correctly with

```bash
gcloud config set project <PROJECT_ID>
```

### First-Time Setup

#### 0. Build the Pulumi Docker image (one-time)

All `cloud-*` pixi tasks run Pulumi inside a Docker container. Build the image
before running any other setup steps:

```bash
docker build -t ca-biositing-pulumi deployment/cloud/gcp/infrastructure/
```

This only needs to be re-run if `deployment/cloud/gcp/infrastructure/Dockerfile`
changes.

> **Version alignment:** The `PULUMI_GCP_VERSION` in the Dockerfile and the
> `pulumi-gcp` pin in `pixi.toml` (`[feature.cloud.pypi-dependencies]`) must
> stay in sync. The Dockerfile controls the version used by Docker-wrapped tasks
> (`cloud-deploy`, `cloud-plan`, etc.) while `pixi.toml` controls the version
> used by direct tasks (`cloud-deploy-direct`, `cloud-plan-direct`) and CI. If
> they diverge, Pulumi state schema mismatches can occur.

#### 1. Create the Pulumi state bucket (one-time)

This creates a GCS bucket to store Pulumi state files. Only needs to be run once
per project.

```bash
pixi run -e deployment cloud-bootstrap
```

#### 2. Login to the Pulumi backend

```bash
pixi run -e deployment cloud-init
```

#### 3. Initialize the staging stack (one-time)

```bash
cd deployment/cloud/gcp/infrastructure
pixi run -e deployment pulumi stack init staging
```

#### 4. Import existing resources (one-time)

If GCP resources already exist and need to be imported into Pulumi state:

```bash
# Import the Cloud SQL instance
pixi run -e deployment pulumi import \
  gcp:sql/databaseInstance:DatabaseInstance staging-db-instance \
  projects/biocirv-470318/instances/biocirv-staging \
  --stack staging --yes

# Import the Cloud SQL database
pixi run -e deployment pulumi import \
  gcp:sql/database:Database staging-db \
  biocirv-470318/biocirv-staging/biocirv-staging \
  --stack staging --yes
```

### Deploying Changes

From the project root directory:

```bash
# Preview pending changes
pixi run -e deployment cloud-plan

# Deploy pending changes
pixi run -e deployment cloud-deploy
```

### DANGEROUS: Destroy All GCP Resources

From the project root directory:

```bash
pixi run -e deployment cloud-destroy
```

Certain pieces of infrastructure with deletion retention policies may fail to
delete when this is run. If you really want to delete them, change that
infrastructure's configuration in `__main__.py`, deploy these changes with
`pixi run -e deployment cloud-plan` and `pixi run -e deployment cloud-deploy`,
and then retry running the above command.

## Troubleshooting

### Pulumi CLI not found

Install Pulumi into the pixi environment:

```bash
pixi run -e deployment install-pulumi
```

### Authentication errors

Make sure you are logged into gcloud (both commands are required):

```bash
gcloud auth login
gcloud auth application-default login
```

### State backend errors

If you see errors about the state backend, make sure you've run:

```bash
pixi run -e deployment cloud-init
```

### Resources already exist errors during `pulumi up`

If you run `pulumi up` before importing existing resources, Pulumi will try to
create resources that already exist in GCP. Follow the import steps in the
"First-Time Setup" section above.

## Multi-Environment Deployment

The infrastructure supports multiple environments (staging, production) within
the same GCP project (`biocirv-470318`). The `DEPLOY_ENV` environment variable
drives stack selection and resource naming.

### How It Works

- `config.py` reads `DEPLOY_ENV` (default: `staging`) and derives all GCP
  resource names as `biocirv-{env}-{resource}`
- Each environment has its own Pulumi stack, Cloud SQL instance, Cloud Run
  services, secrets, service accounts, and WIF pool
- Shell scripts and pixi tasks also use `DEPLOY_ENV` to target the correct
  resources

### Targeting an Environment

```bash
# Staging (default)
pixi run -e deployment cloud-plan          # Docker-wrapped (macOS)
pixi run -e deployment cloud-plan-direct   # Direct (Linux/CI)

# Production
DEPLOY_ENV=production pixi run -e deployment cloud-plan
DEPLOY_ENV=production pixi run -e deployment cloud-plan-direct
```

### CI/CD Pipelines

| Environment | Trigger                           | Workflow                |
| ----------- | --------------------------------- | ----------------------- |
| Staging     | Push to `main` (via docker-build) | `deploy-staging.yml`    |
| Production  | GitHub Release published          | `deploy-production.yml` |

Both workflows set `DEPLOY_ENV` explicitly in their top-level `env:` block.

### Bootstrapping a New Environment

1. `DEPLOY_ENV=<env> pixi run -e deployment cloud-deploy-direct` — create all
   resources
2. Enable Private Google Access on the default subnet (required for VPC egress
   to reach Cloud Run internal services):
   ```bash
   gcloud compute networks subnets update default --region=us-west1 --enable-private-ip-google-access
   ```
3. Run `cloud-outputs-direct` to get WIF provider and deployer SA email
4. Update the corresponding `deploy-<env>.yml` workflow with WIF values
5. Upload manual secrets (GSheets credentials, USDA API key, OAuth2 creds):
   ```bash
   gcloud secrets versions add biocirv-<env>-gsheets-credentials --data-file=credentials.json
   echo -n "KEY" | gcloud secrets versions add biocirv-<env>-usda-nass-api-key --data-file=-
   printf 'CLIENT_ID' | gcloud secrets versions add biocirv-<env>-oauth2-client-id --data-file=-
   printf 'CLIENT_SECRET' | gcloud secrets versions add biocirv-<env>-oauth2-client-secret --data-file=-
   ```
6. Redeploy to pick up OAuth2 secrets:
   `DEPLOY_ENV=<env> pixi run -e deployment cloud-deploy`
7. Update Google OAuth client redirect URI to the prefect-auth's
   `/oauth2/callback` URL (from `cloud-outputs-direct`). Also update the **OAuth
   consent screen branding** (APIs & Services → OAuth consent screen → Branding)
   — the app name shown on the Google login page is set there, not in the OAuth
   client itself. For example, set it to "CA Biositing Prefect Server" (without
   an environment suffix) or a per-environment name if separate OAuth clients
   are used.
8. Run migrations:
   `DEPLOY_ENV=<env> IMAGE_TAG=<tag> pixi run -e deployment cloud-migrate-ci`
9. Seed admin user (manual, idempotent):
   `DEPLOY_ENV=<env> pixi run -e deployment cloud-seed-admin`

---

## Local Development: OAuth2-Proxy for Prefect UI

The local Docker Compose environment includes a `prefect-auth` service
(oauth2-proxy) that puts Google OAuth authentication in front of the Prefect UI.
This mirrors the cloud architecture and lets developers test auth routing
locally.

### How It Works

- `http://localhost:4180` — Prefect UI through prefect-auth proxy (redirects
  directly to Google OAuth)
- `http://localhost:4200` — Prefect UI direct access (no auth, for debugging and
  host-side pixi tasks)
- The Prefect worker connects directly to `http://prefect-server:4200/api` via
  Docker DNS, bypassing the proxy

### Prerequisites: Create a Google OAuth Client

1. Go to
   [GCP Console → APIs & Services → Credentials](https://console.cloud.google.com/apis/credentials)
2. Click **Create Credentials → OAuth 2.0 Client ID**
3. Application type: **Web application**
4. Add authorized redirect URI: `http://localhost:4180/oauth2/callback`
5. Copy the **Client ID** and **Client Secret**

> **Note:** The app name shown on the Google login page (e.g. "CA Biositing
> Prefect Server Staging") is configured in the **OAuth consent screen
> branding** (APIs & Services → OAuth consent screen → Branding), not in the
> individual OAuth client. If sharing one OAuth client across environments, keep
> this in mind — all environments will show the same branding name.

### Configure Local Env

Add the following to `resources/docker/.env` (the file is gitignored — do not
commit it):

```bash
# Generate a 32-byte base64 cookie secret:
python -c 'import os,base64; print(base64.urlsafe_b64encode(os.urandom(32)).decode())'

# Then set these values in resources/docker/.env:
OAUTH2_PROXY_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
OAUTH2_PROXY_CLIENT_SECRET=your-google-client-secret
OAUTH2_PROXY_COOKIE_SECRET=<output from the command above>
```

### Start Services

```bash
pixi run start-services
```

This brings up all five services: `db`, `setup-db`, `prefect-server`,
`prefect-worker`, and `prefect-auth`.

### Access the Prefect UI

- **Via proxy (with auth):** `http://localhost:4180` — redirects directly to
  Google OAuth (skip-provider-button enabled)
- **Direct (no auth):** `http://localhost:4200` — backward compatible, for
  debugging

### Notes

- `OAUTH2_PROXY_EMAIL_DOMAINS=*` allows any Google account. Change to your
  domain (e.g. `lbl.gov`) to restrict access.
- If `OAUTH2_PROXY_*` variables are missing from `.env`, the prefect-auth
  container will fail to start. The other services (db, prefect-server, worker)
  are unaffected since they do not depend on prefect-auth.
- The health check endpoint (`/api/health`) is accessible without authentication
  for monitoring.

---

## Staging Environment

### Architecture Overview

The staging environment runs on GCP with the following components:

| Component                         | Service                                                                      |
| --------------------------------- | ---------------------------------------------------------------------------- |
| **Webservice** (FastAPI)          | Cloud Run Service (public, JWT auth)                                         |
| **Prefect Auth** (oauth2-proxy)   | Cloud Run Service (public, Google OAuth for Prefect UI, VPC egress)          |
| **Prefect Server** (UI + API)     | Cloud Run Service (internal-only ingress, minScale=1)                        |
| **Prefect Worker** (process type) | Cloud Run Service (internal, VPC egress, polls server, runs subprocesses)    |
| **Database**                      | Cloud SQL (PostgreSQL + PostGIS)                                             |
| **Backups**                       | GCS (versioned bucket for SQL exports)                                       |
| **Secrets**                       | Secret Manager (DB password, GSheets creds, OAuth2 creds, etc.)              |
| **Artifact Registry**             | Remote repos proxying GHCR and Quay.io for container images                  |
| **Cloud Router + NAT**            | Internet egress for VPC-routed traffic (OAuth APIs, external data downloads) |

```text
                    ┌──────────────────────┐
                    │      Internet        │
                    └──────┬───────────────┘
                           │
              ┌────────────┼──────────────────┐
              │            │                  │
              ▼            ▼                  ▼
     ┌────────────┐ ┌────────────┐    ┌──────────────┐
     │ Webservice │ │Prefect Auth│    │Prefect Server│
     │  :8080     │ │  :4180     │    │  :4200       │
     │  public    │ │  public    │    │ internal-only│
     │  JWT auth  │ │ Google OAuth│    │ minScale=1   │
     └────────────┘ └─────┬──────┘    └──────▲───────┘
                          │                  │
                   Direct VPC Egress         │ VPC internal traffic
                   (egress=ALL_TRAFFIC)      │
                          │                  │
                    ┌─────┴──────────────────┘
                    │     Default VPC
                    │  (Private Google Access enabled)
                    ├─────────────────────────────┐
                    │                             │
              ┌─────┴──────┐              ┌──────┴───────┐
              │ Cloud NAT  │              │Prefect Worker│
              │ (internet  │              │ VPC egress   │
              │  egress)   │              │ polls server │
              └────────────┘              └──────────────┘
                    │
              ┌─────┴──────────────────────────────┐
              │  External endpoints:               │
              │  - Google OAuth (googleapis.com)   │
              │  - USDA API (quickstats.nass.usda) │
              │  - LandIQ (data.cnra.ca.gov)       │
              └────────────────────────────────────┘
```

**Key design decisions:**

- The Prefect server uses `INGRESS_TRAFFIC_INTERNAL_ONLY` so it cannot be
  accessed directly from the internet. Direct requests return HTTP 404.
- The prefect-auth (oauth2-proxy) and Prefect worker both use **Direct VPC
  egress** (`egress=ALL_TRAFFIC`), routing all outbound traffic through the
  default VPC. This satisfies the Prefect server's internal ingress requirement
  without needing identity token injection or IAM service-to-service auth.
- **Private Google Access** is enabled on the default subnet, allowing
  VPC-routed traffic to reach Google APIs (Cloud Run `.run.app` URLs, OAuth
  token endpoints) through Google's internal network.
- **Cloud NAT** on the default VPC provides internet egress for non-Google
  external endpoints (USDA API, LandIQ data downloads).
- The Prefect server runs with `minScale=1` to avoid cold-start timeouts when
  proxied through the prefect-auth.
- Once a user authenticates through Google OAuth, the prefect-auth forwards
  requests to the Prefect server with `X-Auth-Request-Email` and
  `X-Auth-Request-User` headers, allowing the backend to identify the user
  without managing authentication itself.

Infrastructure is managed by Pulumi (Python Automation API) with state stored in
GCS.

To retrieve service URLs:

```bash
gcloud run services list --region=us-west1 --format="table(name,status.url)"
```

### Deploy / Update Infrastructure

```bash
# Preview changes
pixi run -e deployment cloud-plan

# Apply changes
pixi run -e deployment cloud-deploy
```

### Run Database Migrations

Refresh the Cloud Run job's image digest and apply Alembic migrations:

```bash
pixi run cloud-migrate
```

### Database Backups

While Cloud SQL performs automated daily backups, you can trigger a manual SQL
export to the environment's versioned backup bucket using:

```bash
# Staging (default)
pixi run cloud-backup

# Production
DEPLOY_ENV=production pixi run cloud-backup
```

Backups are saved to `gs://biocirv-{env}-backups/` using the naming convention
`YYYYMMDD-biocirv-{env}-backup-HHMMSS.sql`.

This runs two steps in order:

1. `gcloud run jobs update ... --image=...` — re-pins the Cloud Run job to the
   latest GHCR image (required because Pulumi pins the digest at deploy time and
   does not detect `:latest` tag updates).
2. `gcloud run jobs execute biocirv-alembic-migrate --region=us-west1 --wait` —
   runs the migration job and waits for it to complete.

Verify the execution completed:

```bash
gcloud run jobs executions list --job=biocirv-alembic-migrate --region=us-west1 --limit=1
```

### Prefect Server Access

The Prefect server uses `INGRESS_TRAFFIC_INTERNAL_ONLY` and is fronted by an
**prefect-auth** (oauth2-proxy) service that requires Google OAuth
authentication. Only `@lbl.gov` Google accounts can access the Prefect UI.

**Access the Prefect UI (browser):**

```bash
# Get the prefect-auth URL (this is the public entry point)
gcloud run services describe biocirv-staging-prefect-auth --region=us-west1 --format="value(status.url)"
```

Open the returned URL in a browser. You will be redirected to Google OAuth
login. After authenticating with an `@lbl.gov` account, the Prefect UI loads.

> **Note:** The Prefect server's direct `.run.app` URL is **not accessible**
> from the internet (returns HTTP 404). Always use the prefect-auth URL for
> browser access.

**Prefect CLI access:**

The Prefect CLI cannot reach the internal-only Prefect server from outside GCP.
Use the Prefect UI through the browser for monitoring and triggering flow runs.

### Trigger ETL Flows

Trigger flow runs through the Prefect UI (via the prefect-auth URL) or monitor
via the worker's Cloud Run logs:

```bash
gcloud run services logs read biocirv-prefect-worker --region=us-west1 --limit=50
```

### Read-Only Database Users

The `biocirv_readonly` Cloud SQL user is created by Pulumi (password stored in
Secret Manager as `biocirv-staging-ro-biocirv_readonly`). Read-only privileges
are granted automatically by the `0002_grant_readonly_permissions` Alembic
migration, which runs as part of `pixi run cloud-migrate`.

Retrieve the read-only password from Secret Manager (requires appropriate IAM
permissions):

```bash
gcloud secrets versions access latest --secret=biocirv-staging-ro-biocirv_readonly
```

### Connecting to the Database (DBeaver / GUI Client)

Use the Cloud SQL Auth Proxy to create a local tunnel, then connect your client
to `localhost`:

#### 1. Install and start the proxy

Install the Cloud SQL Auth Proxy via gcloud or by downloading the binary:

```bash
gcloud components install cloud-sql-proxy
```

> **Note:** When prompted during `gcloud components install`, decline the Python
> 3.13 installation to avoid conflicting with the Pixi-managed Python 3.12
> environment.

Then start the proxy (leave it running in a separate terminal):

**Cloud SQL Auth Proxy v2 (installed by `gcloud components install`):**

```bash
cloud-sql-proxy biocirv-470318:us-west1:biocirv-staging --port 5434
```

**Cloud SQL Auth Proxy v1 (if you installed the older binary directly):**

```bash
cloud_sql_proxy -instances=biocirv-470318:us-west1:biocirv-staging=tcp:5434
```

Alternatively, download the binary directly from
https://cloud.google.com/sql/docs/mysql/sql-proxy.

#### 2. Get the password

```bash
# Primary user
gcloud secrets versions access latest --secret=biocirv-staging-db-password

# Read-only user
gcloud secrets versions access latest --secret=biocirv-staging-ro-biocirv_readonly
```

#### 3. Connection settings

| Field    | Value                                                |
| -------- | ---------------------------------------------------- |
| Host     | `127.0.0.1`                                          |
| Port     | `5434`                                               |
| Database | `biocirv-staging`                                    |
| Username | `biocirv_user` (or `biocirv_readonly` for read-only) |
| Password | (from step 2)                                        |
| SSL      | off (the proxy handles encryption to Cloud SQL)      |

### Staging Troubleshooting

#### Auth proxy returns 403 or 500 on login

1. Verify the Google OAuth redirect URI matches the prefect-auth URL:
   `https://biocirv-staging-prefect-auth-xy45yfiqaq-uw.a.run.app/oauth2/callback`
2. Check for stale cookies — clear cookies for
   `biocirv-staging-prefect-auth-xy45yfiqaq-uw.a.run.app` or use incognito
3. Check prefect-auth logs:
   `gcloud run services logs read biocirv-staging-prefect-auth --region=us-west1 --limit=20`
4. Verify OAuth secrets have no trailing newline:
   ```bash
   pixi run -e deployment gcloud secrets versions access latest \
     --secret=biocirv-staging-oauth2-client-id | xxd | tail -3
   ```
   If the last byte is `0a` (newline), re-upload with `printf` instead of `echo`

#### Auth proxy returns 502 (upstream timeout)

The prefect-auth cannot reach the Prefect server. Check:

1. Prefect server is running:
   `gcloud run services describe biocirv-staging-prefect-server --region=us-west1 --format="yaml(status.conditions)"`
2. Auth-proxy has VPC egress:
   `gcloud run services describe biocirv-staging-prefect-auth --region=us-west1 --format="yaml(spec.template.metadata.annotations)" | grep vpc`
3. Private Google Access is enabled on the subnet:
   `gcloud compute networks subnets describe default --region=us-west1 --format="value(privateIpGoogleAccess)"`

#### Prefect worker not connecting

Check worker logs:

```bash
gcloud run services logs read biocirv-prefect-worker --region=us-west1 --limit=20
```

The worker needs VPC egress to reach the internal-only Prefect server. Verify
VPC egress is configured:

```bash
gcloud run services describe biocirv-staging-prefect-worker --region=us-west1 \
  --format="yaml(spec.template.metadata.annotations)" | grep vpc
```

#### Flow runs stuck in "Pending"

1. Verify the work pool (`biocirv-staging-pool`, type `process`) is online in
   the Prefect UI (via prefect-auth URL)
2. Check the worker logs for errors:
   `gcloud run services logs read biocirv-prefect-worker --region=us-west1 --limit=20`
3. Verify the worker container has `DATABASE_URL` and `PREFECT_API_URL` set

#### Credential rotation

1. Update the secret version in Secret Manager
2. Redeploy to pick up the new secret:
   ```bash
   pixi run -e deployment cloud-deploy
   ```

#### PostgreSQL extensions not enabled

Connect to the database and enable the extensions. Note that `psql` is **not**
bundled in the pixi environment — install it separately:

- macOS: `brew install libpq` (adds `psql` to PATH)
- Linux: `sudo apt install postgresql-client`

```bash
gcloud sql connect biocirv-staging --user=postgres --database=biocirv-staging
```

```sql
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;
CREATE EXTENSION IF NOT EXISTS btree_gin;
SELECT PostGIS_Version();
SELECT extname FROM pg_extension WHERE extname IN ('pg_trgm', 'unaccent', 'btree_gin');
```

---

## CI/CD (GitHub Actions)

Staging deployment is automated via a GitHub Actions workflow that triggers on
every push to `main`.

### What Happens on Merge to Main

The `deploy-staging.yml` workflow runs these steps sequentially:

1. **Build images** — submits a Cloud Build that tags images with both `:latest`
   and the short commit SHA (e.g., `:abc1234`)
2. **Deploy infrastructure** — runs Pulumi to update Cloud Run services, Cloud
   SQL, and other GCP resources with the SHA-tagged images
3. **Run migrations** — updates the migration Cloud Run job to the new image and
   executes `alembic upgrade head`
4. **Update services** — forces new Cloud Run revisions for the worker and
   webservice to pick up the latest images

### Authentication

The workflow uses **Workload Identity Federation (WIF)** — keyless
authentication from GitHub Actions to GCP. No service account keys are stored in
GitHub secrets. The WIF pool is scoped to the
`sustainability-software-lab/ca-biositing` repository only.

### CI vs Local Tasks

| Purpose         | Local (macOS, Docker) | CI / Linux (direct)     |
| --------------- | --------------------- | ----------------------- |
| Deploy infra    | `cloud-deploy`        | `cloud-deploy-direct`   |
| Preview infra   | `cloud-plan`          | `cloud-plan-direct`     |
| Refresh state   | `cloud-refresh`       | `cloud-refresh-direct`  |
| Show outputs    | `cloud-outputs`       | `cloud-outputs-direct`  |
| Run migrations  | `cloud-migrate`       | `cloud-migrate-ci`      |
| Update services | (manual gcloud)       | `cloud-update-services` |

All CI tasks read `IMAGE_TAG` from the environment (defaults to `latest`).

### Manual Trigger

You can manually trigger the workflow from the GitHub Actions UI: **Actions →
Deploy Staging → Run workflow**.

### Monitoring

View workflow runs at:
`https://github.com/sustainability-software-lab/ca-biositing/actions/workflows/deploy-staging.yml`

### What Is NOT Managed by CI

- Frontend deployment (has its own Cloud Build triggers)
- Prefect deployment registration (one-time manual step per flow)
- Manual secrets: GSheets credentials, USDA API key, and OAuth2 client
  credentials (see Secret Management section)

### Debugging Failed Deployments

1. Check the workflow run logs in GitHub Actions
2. For Cloud Build failures: check
   [Cloud Build History](https://console.cloud.google.com/cloud-build/builds?project=biocirv-470318)
3. For Pulumi state issues: run `pixi run -e deployment cloud-refresh` locally
   to clear pending operations, then re-trigger the workflow
4. Manual deployment via existing `pixi run cloud-*` tasks (Docker-wrapped)
   remains available as a fallback

---

## Full Staging Deployment Runbook

> **Note:** Staging deployment is now automated via CI/CD (see above). The
> manual runbook below is still useful for initial setup, debugging, and
> one-time operations.

Follow these steps in order for a complete staging deployment — from building
images through database migration, Prefect deployment registration, and ETL
execution.

### Prerequisites

- `gcloud` CLI authenticated: `gcloud auth login` and
  `gcloud auth application-default login`
- Docker daemon running (for local builds)
- `pixi` installed
- Access to the BioCirV GCP project (`biocirv-470318`)
- `credentials.json` service account file for Google Sheets/Drive access

### Step 1: Deploy / Update Infrastructure

```bash
pixi run cloud-deploy
```

This creates or updates all GCP resources: Cloud SQL instance, Secret Manager
secrets, Cloud Run services (webservice, prefect-server, prefect-worker,
prefect-auth), Artifact Registry remote repos, Cloud Router/NAT, and Cloud Run
jobs (migration, seed-admin).

### Step 2: Upload Secrets (post-deploy, manual)

These secrets must be populated manually after `cloud-deploy` creates the secret
shells:

```bash
# 1. GSheets / Google Drive service account credentials
gcloud secrets versions add biocirv-staging-gsheets-credentials \
  --data-file=credentials.json \
  --project=biocirv-470318

# 2. USDA NASS API key (replace with actual key value)
echo -n "YOUR_USDA_NASS_API_KEY" | \
  gcloud secrets versions add biocirv-staging-usda-nass-api-key \
  --data-file=- \
  --project=biocirv-470318

# 3. OAuth2 proxy client ID and secret (from GCP OAuth consent screen)
#    Use printf to avoid trailing newline — Google OAuth rejects IDs with \n
printf 'YOUR_GOOGLE_CLIENT_ID' | \
  gcloud secrets versions add biocirv-staging-oauth2-client-id \
  --data-file=- \
  --project=biocirv-470318

printf 'YOUR_GOOGLE_CLIENT_SECRET' | \
  gcloud secrets versions add biocirv-staging-oauth2-client-secret \
  --data-file=- \
  --project=biocirv-470318
```

After populating the OAuth2 secrets, redeploy to pick up the new secret
versions:

```bash
pixi run -e deployment cloud-deploy
```

Verify the secret versions were created:

```bash
gcloud secrets versions list biocirv-staging-gsheets-credentials --project=biocirv-470318
gcloud secrets versions list biocirv-staging-usda-nass-api-key --project=biocirv-470318
gcloud secrets versions list biocirv-staging-oauth2-client-id --project=biocirv-470318
gcloud secrets versions list biocirv-staging-oauth2-client-secret --project=biocirv-470318
```

### Step 3: Run Database Migrations

```bash
pixi run cloud-migrate
```

This rebuilds the pipeline image, updates the migration job's image digest, and
runs `alembic upgrade head` in Cloud Run.

Verify migration succeeded:

```bash
gcloud run jobs executions list --job=biocirv-alembic-migrate --region=us-west1 --limit=1
```

Expected: `SUCCEEDED` status.

### Step 4: Seed Admin User (manual, one-time per environment)

After migrations have run, seed the initial admin user by executing the Cloud
Run seed-admin job:

```bash
# Staging
pixi run -e deployment cloud-seed-admin

# Production
DEPLOY_ENV=production pixi run -e deployment cloud-seed-admin
```

Or directly via gcloud:

```bash
gcloud run jobs execute biocirv-staging-seed-admin --region=us-west1 --wait
```

This is **idempotent** — if the admin user already exists, the script exits
successfully without changes. The admin password is read from Secret Manager
(`biocirv-<env>-admin-password`).

> **Note:** Admin seeding is intentionally a manual process for both staging and
> production. It is not part of the CI/CD pipeline.

### Step 5: Force New Cloud Run Revision for Worker

After uploading secrets, force a new revision to pick up the latest image and
mounted secret:

```bash
gcloud run services update biocirv-prefect-worker \
  --image=us-west1-docker.pkg.dev/biocirv-470318/ghcr-proxy/sustainability-software-lab/ca-biositing/pipeline:latest \
  --region=us-west1
```

### Step 6: Access Prefect UI and Trigger Flows

The Prefect server is internal-only and accessed through the prefect-auth:

```bash
# Get the prefect-auth URL
gcloud run services describe biocirv-staging-prefect-auth \
  --region=us-west1 --format="value(status.url)"
```

Open the URL in a browser, authenticate with your `@lbl.gov` Google account,
then use the Prefect UI to register deployments and trigger flow runs.

Monitor flow runs via the worker's Cloud Run logs:

```bash
gcloud run services logs read biocirv-prefect-worker --region=us-west1 --limit=100
```

### Step 9: Verify Data in Cloud SQL

Connect via Cloud SQL Auth Proxy (see "Connecting to the Database" section),
then:

```sql
-- Resource information (Google Sheets flow)
SELECT count(*) FROM resource_information;
-- Analysis records (Google Sheets flow)
SELECT count(*) FROM analysis_record;
-- USDA data (API flow)
SELECT count(*) FROM usda_census_survey;
-- LandIQ data (if LANDIQ_SHAPEFILE_URL was configured)
SELECT count(*) FROM landiq_record;
-- Billion Ton data (Google Drive flow)
SELECT count(*) FROM billion_ton;
```

Expected: Non-zero counts for flows that have valid data sources.

---

## Environment Variables Reference

All environment variables injected into the Prefect worker Cloud Run service:

| Variable                         | Source                                               | Description                                      |
| -------------------------------- | ---------------------------------------------------- | ------------------------------------------------ |
| `PREFECT_API_URL`                | Derived from prefect-server URI                      | Prefect API endpoint                             |
| `PREFECT_WORK_POOL_NAME`         | Plain text                                           | Work pool name (`biocirv-staging-pool`)          |
| `DB_USER`                        | Plain text                                           | Cloud SQL username                               |
| `POSTGRES_DB`                    | Plain text                                           | Database name                                    |
| `DB_PASS`                        | Secret Manager (`biocirv-staging-db-password`)       | Database password                                |
| `INSTANCE_CONNECTION_NAME`       | Plain text                                           | Cloud SQL Unix socket path                       |
| `USDA_NASS_API_KEY`              | Secret Manager (`biocirv-staging-usda-nass-api-key`) | USDA NASS QuickStats API key                     |
| `CREDENTIALS_PATH`               | Plain text                                           | Path to GSheets/Drive service account file       |
| `GOOGLE_APPLICATION_CREDENTIALS` | Plain text                                           | Path to GCP service account credentials (ADC)    |
| `LANDIQ_SHAPEFILE_URL`           | Plain text                                           | HTTP URL to download LandIQ shapefile at runtime |

---

## Secret Management

### Automatically managed by Pulumi

| Secret                                 | Description                                         |
| -------------------------------------- | --------------------------------------------------- |
| `biocirv-staging-db-password`          | Cloud SQL primary user password (auto-generated)    |
| `biocirv-staging-postgres-password`    | Postgres superuser password (auto-generated)        |
| `biocirv-staging-ro-biocirv_readonly`  | Read-only user password (auto-generated)            |
| `biocirv-staging-prefect-auth`         | Prefect HTTP Basic Auth password (auto-generated)   |
| `biocirv-staging-oauth2-cookie-secret` | OAuth2 proxy cookie encryption key (auto-generated) |

### Manually uploaded post-deploy

| Secret                                 | How to upload                                                                                              |
| -------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| `biocirv-staging-gsheets-credentials`  | `gcloud secrets versions add biocirv-staging-gsheets-credentials --data-file=credentials.json`             |
| `biocirv-staging-usda-nass-api-key`    | `echo -n "KEY" \| gcloud secrets versions add biocirv-staging-usda-nass-api-key --data-file=-`             |
| `biocirv-staging-oauth2-client-id`     | `printf 'CLIENT_ID' \| gcloud secrets versions add biocirv-staging-oauth2-client-id --data-file=-`         |
| `biocirv-staging-oauth2-client-secret` | `printf 'CLIENT_SECRET' \| gcloud secrets versions add biocirv-staging-oauth2-client-secret --data-file=-` |

> **Important:** Use `printf` (not `echo`) to avoid a trailing newline in the
> secret value. A trailing newline causes Google OAuth to reject the client ID.

---

## ETL Flow Troubleshooting

#### ETL flow fails with "USDA API key is empty"

Upload the USDA NASS API key to Secret Manager:

```bash
echo -n "YOUR_USDA_NASS_API_KEY" | \
  gcloud secrets versions add biocirv-staging-usda-nass-api-key \
  --data-file=- --project=biocirv-470318
```

Then force a new Cloud Run revision:

```bash
gcloud run services update biocirv-prefect-worker \
  --image=us-west1-docker.pkg.dev/biocirv-470318/ghcr-proxy/sustainability-software-lab/ca-biositing/pipeline:latest --region=us-west1
```

#### Google Sheets / Drive authentication fails

1. Verify the secret has a version:
   `gcloud secrets versions list biocirv-staging-gsheets-credentials`
2. Verify `CREDENTIALS_PATH` env var on the worker is
   `/app/gsheets-credentials/credentials.json`
3. Verify the service account in `credentials.json` has been shared on the
   relevant Google Sheets

#### LandIQ flow fails with "Shapefile path does not exist"

Set the `LANDIQ_SHAPEFILE_URL` env var to a valid URL pointing to a zip archive
containing the shapefile. Update via Pulumi config or override at deploy time:

```bash
# Update in cloud_run.py's LANDIQ_SHAPEFILE_URL value, then redeploy:
pixi run cloud-deploy
# Or update the running service directly:
gcloud run services update biocirv-prefect-worker \
  --update-env-vars LANDIQ_SHAPEFILE_URL=https://your-url/landiq.zip \
  --region=us-west1
```

#### Worker not picking up new code after image rebuild

Pulumi pins image digests and won't detect `:latest` tag updates automatically.
Force a new revision:

```bash
gcloud run services update biocirv-prefect-worker \
  --image=us-west1-docker.pkg.dev/biocirv-470318/ghcr-proxy/sustainability-software-lab/ca-biositing/pipeline:latest --region=us-west1
```
