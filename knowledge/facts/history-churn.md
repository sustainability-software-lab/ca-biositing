---
type: Fact
title: Most-churned files and what the churn implies (snapshot at e41d00d)
description: "Top 40 files by number of commits touching them, with the interpretation that config, deploy, and view files are the real volatility hot spots."
tags: [churn, hotspots, history]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:29:04Z" }
status: stable
code_refs: ["pixi.toml", "deployment/cloud/gcp/infrastructure/config.py", "deployment/cloud/gcp/infrastructure/deploy.py", ".github/workflows/ci.yml", "src/ca_biositing/datamodels/ca_biositing/datamodels/models/__init__.py"]
sources: ["git log --format= --name-only, HEAD e41d00d"]
governance: context
stale_after: "2026-12-31"
---

## Purpose
Shows where change concentrates so a reader knows which files need extra care or are unstable.

## Key files
Top files by commit count (`git log --format= --name-only | sort | uniq -c | sort -rn | head -40`):
| Commits | Path | Role |
|---|---|---|
| 49 | pixi.toml | environments and tasks |
| 27 | README.md | project overview (overhauled for Zenodo in 4ff6700) |
| 27 | .gitignore | ignore rules |
| 25 | pixi.lock | lockfile (removed in 09120d1 and restored by later commits) |
| 21 | .pre-commit-config.yaml | hook config (mostly bot updates) |
| 20 | resources/prefect/run_prefect_flow.py | Prefect runner |
| 17 | deployment/cloud/gcp/infrastructure/config.py | stack config |
| 14 | deployment/cloud/gcp/infrastructure/deploy.py | Pulumi deploy |
| 14 | .github/workflows/ci.yml | CI |
| 12 | src/ca_biositing/datamodels/ca_biositing/datamodels/views.py | view registry |
| 12 | src/ca_biositing/datamodels/ca_biositing/datamodels/models/__init__.py | model registry |
| 12 | deployment/cloud/gcp/infrastructure/cloud_run.py | Cloud Run |
| 11 | tests/webservice/v1/conftest.py | webservice test fixtures |
| 11 | .github/workflows/deploy-staging.yml | staging deploy |
| 10 | resources/docker/docker-compose.yml | local services |
| 10 | .github/workflows/copilot-setup-steps.yml | agent setup workflow |
| 9 | src/ca_biositing/pipeline/.../utils/name_id_swap.py | ETL helper |
| 9 | src/ca_biositing/datamodels/.../data_portal_views/mv_biomass_volume_estimate.py | volume view |

Total history (sum of `git log --shortstat`, approximate because merges may double count): about 3,146 file changes, +482,613 / -144,898 lines.

## How it works
Churn clusters in three places:
1. Build and environment config (pixi.toml, pixi.lock, .gitignore, pre-commit): the environment is the most-touched surface.
2. Deployment and CI (deployment/, .github/workflows/): reflects the 2026 GCP burst.
3. Data portal views and model registries: reflects the ongoing ETL and MV work.

## Interfaces
Not applicable.

## Gotchas
- High churn in pixi.lock is mostly dependency updates and is not a design signal.
- Do not infer quality from churn alone; many commits are "fix:" chains.

## History
Snapshot at e41d00d; the top list will shift as work continues.

## Open questions
- Whether the 49-commit pixi.toml churn includes many dependabot-driven edits (not verified; check with `git log --author` filters).

# Related Concepts
- [Contributors by commit count and area (snapshot at e41d00d)](history-contributors.md): who edits the hot files
- [System overview (start here)](../architecture/system-overview.md): hub for the components these files belong to
- [History: GCP staging and production deployment automation (Feb to Apr 2026)](history-gcp-staging-deployment.md): explains deployment churn
