---
type: Bug
title: "#491: IMAGE_TAG defaults to ’latest’ and Pulumi GCP provider drift causes spurious cloud diffs"
description: IMAGE_TAG default of ’latest’ can deploy unpinned images; Pulumi provider drift creates spurious diffs.
tags: [bug, infra-deploy]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:29:21Z" }
status: stable
code_refs: ["deployment/cloud/gcp/infrastructure/config.py", "deployment/README.md"]
sources: ["https://github.com/sustainability-software-lab/ca-biositing/issues/491"]
governance: context
stale_after: "2026-11-15"
---

**Purpose.** Open defect tracked as #491 (https://github.com/sustainability-software-lab/ca-biositing/issues/491). Symptom: IMAGE_TAG silently defaults to ’latest’. Running cloud-plan against staging shows spurious diffs from the Pulumi GCP provider version drift.

**Status.** Open on GitHub (created 2026-10-05; assignee unassigned). Part of theme `facts/issues-infra-deploy`.

**Suspected code location.**

| Path:line | Role |
|---|---|
| `deployment/cloud/gcp/infrastructure/config.py:81` | (IMAGE_TAG = os.environ.get(’IMAGE_TAG’, ’latest’)) |
| `deployment/cloud/gcp/infrastructure/config.py:83-86` | (WEBSERVICE_IMAGE / PIPELINE_IMAGE built from IMAGE_TAG) |
| `deployment/README.md:689` | (documents the latest default) |

**How it works.** Verified in code and docs. Provider drift cause is from the issue (not re-run here).

**Interfaces.** Inputs: data rows or UI state named in the issue. Outputs: portal views or ETL tables named above.

**Gotchas.** The issue body may be truncated or contain images; the symptom above is the issue text, not a reproduction.

**History.** Opened 2026-10-05 as #491. Related issues are listed in the theme concept.

**Open questions.** Root cause confirmed in code? Reproduce against the staging DB before fixing.

# Related Concepts
- [Issues: deployment, cloud infrastructure and environments](../facts/issues-infra-deploy.md): Theme inventory that lists #491
- [Current state snapshot (2026-10-16)](../facts/current-state.md): Open-bug snapshot as of 2026-10-16
