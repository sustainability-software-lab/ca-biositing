---
type: Requirement
title: "Generated dashboards, fingerprints, drift reports and insights are never committed to git"
description: "Must never commit or force-add exports/plots/**, audit/output/env_fingerprints/*.json, audit/output/drift_report.md or data/insights/resource_ai_insights.json; a pre-commit guard enforces it."
tags: [requirements, generated-artifacts, git, pre-commit, gcs]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-22T21:27:23Z" }
status: stable
code_refs: ["scripts/check_no_generated_artifacts.py", ".agents/rules/generated-artifacts.md", ".pre-commit-config.yaml", ".gitignore", "tests/fixtures/minimal_dashboard_snapshot.json", "tests/fixtures/minimal_env_fingerprint.json", "data/qc/qc_review_decisions_seed.csv"]
sources: ["https://github.com/sustainability-software-lab/ca-biositing/issues/519", "https://github.com/sustainability-software-lab/ca-biositing/pull/522", "commit ae147f6", ".agents/rules/generated-artifacts.md"]
governance: constraint
stale_after: "2027-04-22"
---

## Requirement
A change must keep these properties. Source: .agents/rules/generated-artifacts.md (the rule file, indexed in AGENTS.md).

1. **Never commit the forbidden paths.** exports/plots/**, audit/output/env_fingerprints/*.json, audit/output/drift_report.md, and data/insights/resource_ai_insights.json are build or publish outputs. Do not commit them and do not bypass with git add -f.
2. **Publish through CI, not git.** Dashboards and the snapshot cache are published to gs://biocirv-{env}-dashboards/ by .github/workflows/dashboard-artifacts.yml (see architecture/ci-dashboard-artifacts-publisher).
3. **Keep the allowed exception.** Small human-curated seed CSVs are allowed: data/qc/qc_review_decisions_seed.csv is re-included by .gitignore:57-58.
4. **Keep the committed fixtures small.** tests/fixtures/minimal_dashboard_snapshot.json and minimal_env_fingerprint.json are the only stand-ins used by CI. The rule states limits of under 35 KB and under 15 KB. Current sizes are about 15.8 KB and 9.5 KB.
5. **Leave local outputs untracked.** A local exports/plots/ is allowed and is served first by the webservice (dashboard_loader.py:305).

## Enforcement
| Guard | Where | What it checks |
|---|---|---|
| forbid-generated-artifacts | .pre-commit-config.yaml:42-46 | runs python3 scripts/check_no_generated_artifacts.py with the passed filenames |
| forbidden pattern table | scripts/check_no_generated_artifacts.py:27-43 | exports/plots/**, the insights JSON, env_fingerprints/*.json, drift_report.md |
| tracked-file scan | scripts/check_no_generated_artifacts.py:46-57, 71-74 | git ls-files, so an already tracked file also fails |
| .gitignore | .gitignore:142, 149-154 | exports/plots/, audit/output env_fingerprints, drift_report.md, insights JSON |
| check-added-large-files | .pre-commit-config.yaml:9-10 | new files over 500 KB, no exports/plots exclusion |

Verified at a2c8de8: the guard exits 0 on the current tree. Given exports/plots/index.html, audit/output/env_fingerprints/staging_fingerprint.json, or data/insights/resource_ai_insights.json as arguments, it prints the forbidden pattern and exits 1.

## Gotchas
- No test covers the guard. grep of tests/ finds no reference to check_no_generated_artifacts.
- The guard fails open if git ls-files errors (check script returns an empty list, lines 55-56). The filename check still runs.
- It runs through pre-commit (local hook or the pre-commit.ci service named in the ci: block of the config). No GitHub Actions job runs pre-commit (grep of .github/workflows).
- The guard is a tracked-state check, stricter than the diff-only check that issue #519 proposed.
- Historical blobs remain in .git (about 1.2 GB of raw history over 1 MB, per issue #519). Removing them needs a separate history rewrite that was not authorized.

## Open questions
- Should a guard unit test be added that covers each forbidden pattern and the allowlisted seed CSV? (inferred need)

# Related Concepts
- [Pre-commit configuration: hooks, exclusions and the mandatory pre-PR check](../architecture/tooling-pre-commit-hooks.md): the pre-commit config that hosts the guard hook
- [Decision: store generated dashboards in a GCS bucket instead of committing them to git (#519)](../decisions/dashboards-gcs-over-committed-exports.md): the decision that makes this rule necessary
- [exports/ directory: committed SQL, reports, and plot outputs](../architecture/analysis-exports-artifacts.md): the exports/ tree this rule governs
- [PRs need pre-commit passing, the full PR template, AI disclosure and human diff review](tooling-pr-ai-disclosure-and-preflight.md): the PR preflight that runs the pre-commit gate
