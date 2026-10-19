# CA Biositing Web Service

FastAPI REST API for the
[CA Biositing](https://github.com/sustainability-software-lab/ca-biositing)
project — serving biomass feedstock data including USDA Census/Survey statistics
and laboratory analysis results.

Shares database models with the companion
[`ca-biositing-datamodels`](https://pypi.org/project/ca-biositing-datamodels/)
package.

## Installation

```bash
pip install ca-biositing-webservice
```

## Quick Start

```bash
uvicorn ca_biositing.webservice.main:app --reload
```

Interactive docs at `http://localhost:8000/docs`.

## API Overview

| Endpoint Family | Base Path                     | Description                                |
| --------------- | ----------------------------- | ------------------------------------------ |
| Auth            | `/v1/auth/token`              | JWT access tokens                          |
| Analysis        | `/v1/feedstocks/analysis/`    | Lab analysis data by resource and location |
| USDA Census     | `/v1/feedstocks/usda/census/` | USDA Census data by crop or resource       |
| USDA Survey     | `/v1/feedstocks/usda/survey/` | USDA Survey data by crop or resource       |

Each family includes discovery endpoints returning available crops, resources,
geoids, and parameters. All lookups are case-insensitive.

### Authentication

The `/v1/auth/token` endpoint uses **POST** (not GET) because credentials are
sent in the request body — keeping them out of URLs, server logs, and browser
history.

It returns a **JWT (JSON Web Token)**: a compact, cryptographically signed
string that encodes your identity. Once issued, include it on every subsequent
request in the `Authorization` header:

```
Authorization: Bearer <your_token>
```

The token is time-limited. When it expires, call `/v1/auth/token` again to get a
new one. No session state is stored server-side — each request is validated by
verifying the token signature.

## BioCirV Portal Authentication, Dashboard Serving & Two-Stage QC API

In addition to the public feedstock endpoints, the webservice hosts the internal
**BioCirV Analytical Dashboard Suite** (`/v1/dashboards/*`) and **Two-Stage QC
Review API** (`/v1/qc/*`).

### Isolated Portal Authentication (`portal_auth.py`)

To prevent cookie or session collisions with the CalBioScape React frontend
(which uses `access_token` against `/v1/auth/*`), internal dashboards and QC
endpoints use a completely separate cookie and authentication module
(`ca_biositing.webservice.services.portal_auth`):

- **Cookie Name:** `biocirv_portal_token` (`HttpOnly`, `SameSite=Lax`, path `/`,
  `Secure` on HTTPS).
- **Supported Credentials:**
  1. Google OIDC ID token (`POST /v1/dashboards/auth/google` or
     `Authorization: Bearer <google_id_token>`), verified via
     `google.oauth2.id_token.verify_oauth2_token` when `GOOGLE_OAUTH_CLIENT_ID`
     is configured.
  2. Portal HMAC-SHA256 JWT stored in `biocirv_portal_token` or passed via
     `Authorization: Bearer <portal_jwt>`.
  3. Local development login (`POST /v1/dashboards/auth/dev-login`) when
     `ENVIRONMENT=local` or `DASHBOARD_DEV_AUTH_BYPASS=true`.

### Domain & Email Allowlist Configuration

Access to `/v1/dashboards/*` and `/v1/qc/*` is governed by environment settings
in `ca_biositing.webservice.config.Settings`:

| Setting                     | Default                               | Description                                                                              |
| :-------------------------- | :------------------------------------ | :--------------------------------------------------------------------------------------- |
| `GOOGLE_OAUTH_CLIENT_ID`    | `""`                                  | Google OAuth 2.0 Web Client ID for verifying Google ID tokens.                           |
| `DASHBOARD_SESSION_SECRET`  | `""` (falls back to `JWT_SECRET_KEY`) | HMAC-SHA256 secret used to sign `biocirv_portal_token` session cookies.                  |
| `DASHBOARD_ALLOWED_DOMAINS` | `"lbl.gov,berkeley.edu"`              | Comma-separated email domains automatically granted `analyst` access.                    |
| `DASHBOARD_ALLOWED_EMAILS`  | `""`                                  | Comma-separated external collaborator emails granted `analyst` access.                   |
| `DASHBOARD_ADMIN_EMAILS`    | `""`                                  | Comma-separated administrator emails promoted to the `admin` role.                       |
| `DASHBOARD_GCS_BUCKET`      | `""`                                  | Optional GCS bucket name (e.g., `biocirv-staging-dashboards`) for fallback HTML loading. |
| `DASHBOARD_GCS_PREFIX`      | `"dashboards/staging/latest"`         | Object prefix inside `DASHBOARD_GCS_BUCKET`.                                             |
| `QC_AUDIT_GSHEET_NAME`      | `""`                                  | Target Google Sheet name for Stage 2 QC writeback.                                       |

### Two-Role RBAC Matrix (`analyst` vs. `admin`)

| Capability / Endpoint                                                                                 | `analyst` (`@lbl.gov`, `@berkeley.edu`, or allowlisted email) | `admin` (`DASHBOARD_ADMIN_EMAILS` or `User.is_admin=True`) |
| :---------------------------------------------------------------------------------------------------- | :-----------------------------------------------------------: | :--------------------------------------------------------: |
| View internal dashboards (`GET /v1/dashboards/{subpath:path}`)                                        |                              Yes                              |                            Yes                             |
| Export collaborator `.html` / `.csv` slices                                                           |                              Yes                              |                            Yes                             |
| List Stage 1 QC decisions & summary (`GET /v1/qc/decisions`, `GET /v1/qc/summary`)                    |                              Yes                              |                            Yes                             |
| Flag records from Selection Tray to Workbench (`POST /v1/qc/tray-to-workbench`)                       |                              Yes                              |                            Yes                             |
| Submit Stage 1 QC decisions (`POST /v1/qc/decisions`, `POST /v1/qc/decisions/approve`)                |                              Yes                              |                            Yes                             |
| Revert Stage 1 QC decisions (`POST /v1/qc/decisions/{id}/revert`)                                     |                              Yes                              |                            Yes                             |
| Assign QC review tasks (`PATCH /v1/qc/decisions/{id}/assign`)                                         |                              Yes                              |                            Yes                             |
| Export/import deterministic QC seed CSV (`GET /v1/qc/export-seed-csv`, `POST /v1/qc/import-seed-csv`) |                              Yes                              |                            Yes                             |
| Trigger Stage 2 Google Sheets writeback & MV refresh (`POST /v1/qc/sync-gsheet`)                      |                   **No (`403 Forbidden`)**                    |                          **Yes**                           |

### Local-or-GCS Dashboard Loader (`dashboard_loader.py`)

`GET /v1/dashboards/{subpath:path}` serves the 5-product suite (`index.html`,
`login.html`, `db_environment_drift_dashboard.html`, and `metadata/*.html`):

1. **Path Traversal Protection:** Rejects `..`, leading slashes, non-`.html`
   suffixes, and any relative path not in the explicit 6-file allowlist.
2. **Local-First Resolution:** Serves from `DASHBOARD_LOCAL_DIR`
   (`exports/plots/` by default) when files exist locally.
3. **GCS Fallback with TTL Cache:** When local files are absent (such as on
   Cloud Run), fetches
   `gs://{DASHBOARD_GCS_BUCKET}/{DASHBOARD_GCS_PREFIX}/{subpath}` with an
   in-memory TTL cache (`DASHBOARD_CACHE_TTL_SECONDS`, default 300 seconds).
4. **Unauthenticated Browser Redirect:** Unauthenticated browser navigation
   (`Accept: text/html`) redirects (`302 Found`) to
   `/v1/dashboards/login?next=...`, whereas programmatic/API requests receive
   `401 Unauthorized`.

### Two-Stage QC Review API (`/v1/qc/*`)

| Method & Path                        | Role Required | Description                                                                                                                                                                                                           |
| :----------------------------------- | :------------ | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `GET /v1/qc/decisions`               | `analyst`     | Returns Stage 1 QC decisions from `qc_review_decision` (filterable by `resource_name`, `analysis_type`, `decision_status`, `assigned_to_email`, `unsynced_only`).                                                     |
| `GET /v1/qc/summary`                 | `analyst`     | Returns aggregate counts (`total`, `unsynced_count`, `synced_count`, `by_status`, `by_flag_type`).                                                                                                                    |
| `POST /v1/qc/decisions`              | `analyst`     | Records a single-record or replicate-group Stage 1 QC decision in `qc_review_decision`, immediately updates `qc_pass` on the target `*_record` rows in PostgreSQL, and sets `synced_to_gsheet = False`.               |
| `POST /v1/qc/decisions/approve`      | `analyst`     | Batch-submits multiple Stage 1 QC decisions in a single transaction.                                                                                                                                                  |
| `POST /v1/qc/tray-to-workbench`      | `analyst`     | Persists flagged records or replicate groups from the Page 2 / Page 3 Selection Tray into `qc_review_decision` and returns `workbench_url` (`/v1/dashboards/metadata/resource_audit_workbench.html?decision_id=...`). |
| `POST /v1/qc/decisions/{id}/revert`  | `analyst`     | Reverts a previous QC decision back to `qc_pass = "pass"` and marks `synced_to_gsheet = False`.                                                                                                                       |
| `PATCH /v1/qc/decisions/{id}/assign` | `analyst`     | Updates `assigned_to_email` and optional review note on an existing decision.                                                                                                                                         |
| `POST /v1/qc/sync-gsheet`            | `admin`       | Executes Stage 2 Google Sheets writeback for unsynced decisions, marks synced rows `synced_to_gsheet = True`, and optionally refreshes materialized views.                                                            |
| `GET /v1/qc/export-seed-csv`         | `analyst`     | Exports the `qc_review_decision` ledger as a deterministic CSV seed file.                                                                                                                                             |
| `POST /v1/qc/import-seed-csv`        | `analyst`     | Upserts QC decisions from a CSV seed payload and applies their `new_qc_pass` values to the target PostgreSQL record tables.                                                                                           |

## Key Dependencies

- [`ca-biositing-datamodels`](https://pypi.org/project/ca-biositing-datamodels/)
  — shared database models
- [FastAPI](https://fastapi.tiangolo.com/) — web framework
- [Uvicorn](https://www.uvicorn.org/) — ASGI server
- [PyJWT](https://pyjwt.readthedocs.io/) — JWT authentication

## Links

- [Repository](https://github.com/sustainability-software-lab/ca-biositing)
- [Issue Tracker](https://github.com/sustainability-software-lab/ca-biositing/issues)

## Contributors

[![Contributors](https://contrib.rocks/image?repo=sustainability-software-lab/ca-biositing)](https://github.com/sustainability-software-lab/ca-biositing/graphs/contributors)

## Acknowledgement

We acknowledge software engineering support from the University of Washington
[Scientific Software Engineering Center (SSEC)](https://escience.washington.edu/software-engineering/ssec/),
as part of the Schmidt Sciences
[Virtual Institute for Scientific Software (VISS)](https://www.schmidtsciences.org/).

## License

CA Biositing Web Service is licensed under the open source
[BSD 3-Clause License](https://opensource.org/license/bsd-3-clause).
