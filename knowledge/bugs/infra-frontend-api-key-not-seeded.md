---
type: Bug
title: "#428: Prod frontend X-API-Key is not auto-seeded, so a DB reset silently breaks the frontend"
description: Production frontend breaks silently if auth rows are wiped; the frontend API key is not seeded by the deploy pipeline.
tags: [bug, infra-deploy]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:29:17Z" }
status: stable
code_refs: ["src/ca_biositing/webservice/ca_biositing/webservice/dependencies.py", "src/ca_biositing/webservice/ca_biositing/webservice/services/auth_service.py", "deployment/cloud/gcp/infrastructure/secret_manager.py"]
sources: ["https://github.com/sustainability-software-lab/ca-biositing/issues/428"]
governance: context
stale_after: "2026-11-15"
---

**Purpose.** Open defect tracked as #428 (https://github.com/sustainability-software-lab/ca-biositing/issues/428). Symptom: Deploy pipeline seeds the admin user into prod but not the frontend API key. Any auth-row wipe makes the frontend X-API-Key stop matching an active ApiKey row, with no alert.

**Status.** Open on GitHub (created 2026-06-17; assignee unassigned). Part of theme `facts/issues-infra-deploy`.

**Suspected code location.**

| Path:line | Role |
|---|---|
| `src/ca_biositing/webservice/ca_biositing/webservice/dependencies.py:99-135` | (X-API-Key path: validate_api_key, 401 on no match) |
| `src/ca_biositing/webservice/ca_biositing/webservice/services/auth_service.py` | (validate_api_key) |
| `deployment/cloud/gcp/infrastructure/secret_manager.py` | and config.py (secret wiring) |

**How it works.** Verified the X-API-Key 401 path and that Secret Manager is used in deployment. Where the admin seed runs is inferred to be in deployment/ (confirm by grepping deployment/ for seed logic).

**Interfaces.** Inputs: data rows or UI state named in the issue. Outputs: portal views or ETL tables named above.

**Gotchas.** The issue body may be truncated or contain images; the symptom above is the issue text, not a reproduction.

**History.** Opened 2026-06-17 as #428. Related issues are listed in the theme concept.

**Open questions.** Root cause confirmed in code? Reproduce against the staging DB before fixing.

# Related Concepts
- [Issues: deployment, cloud infrastructure and environments](../facts/issues-infra-deploy.md): Theme inventory that lists #428
- [Current state snapshot (2026-10-16)](../facts/current-state.md): Open-bug snapshot as of 2026-10-16
