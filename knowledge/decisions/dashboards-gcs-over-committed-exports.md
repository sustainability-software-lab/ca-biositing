---
type: Decision
title: "Decision: store generated dashboards in a GCS bucket instead of committing them to git (#519)"
description: "Generated HTML dashboards, fingerprints and insights moved from committed exports/ files to CI-published GCS objects, with GitHub Pages as a consumer; landed Oct 19 to 21, 2026."
tags: [decision, dashboards, gcs, git-size, github-pages]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-22T21:27:24Z" }
status: stable
code_refs: ["deployment/cloud/gcp/infrastructure/storage.py", ".github/workflows/dashboard-artifacts.yml", ".github/workflows/gh-pages.yml", "scripts/check_no_generated_artifacts.py", ".gitignore"]
sources: ["https://github.com/sustainability-software-lab/ca-biositing/issues/519", "https://github.com/sustainability-software-lab/ca-biositing/pull/520", "https://github.com/sustainability-software-lab/ca-biositing/pull/521", "https://github.com/sustainability-software-lab/ca-biositing/pull/522", "https://github.com/sustainability-software-lab/ca-biositing/pull/533", "commit 752a80d", "commit 1fcadb4", "commit ae147f6", "commit bd72222"]
governance: context
stale_after: "2027-04-22"
---

## Decision
Generated dashboards, DB fingerprints, drift reports and the AI insights sidecar are no longer committed. CI builds them and publishes them to a per-environment GCS bucket (architecture/infra-dashboards-gcs-bucket, architecture/ci-dashboard-artifacts-publisher). GitHub Pages and the FastAPI portal read from that bucket (architecture/ci-gh-pages-gallery-consumer).

## Context
Issue #519 (closed 2026-10-19) recorded that:
- .git was 477 MB and two PRs (#517, #518) added about 16.5 MB more.
- CI already regenerated every committed file on each relevant push, so committing the outputs had no remaining reason.
- Historical blobs over 1 MB total about 1.2 GB of raw content.

## Alternatives considered (from the issue)
- Pages-only regeneration inside gh-pages.yml: rejected, duplicates the build logic.
- Bucket-only, dropping Pages: rejected, gives up the free public channel.
- Hybrid (chosen): bucket as the versioned store, Pages as consumer.

## What landed
- Phase 1 (infra): 752a80d (PR #520), bucket and SAs.
- Phase 2 (producer): 1fcadb4 (PR #521), publisher workflow.
- Phase 3 (consumer): 1fcadb4 (PR #521), gh-pages reads latest/.
- Phase 4 (stop committing): ae147f6 (PR #522), 34 files removed (43k lines), guard added, .agents/rules/generated-artifacts.md added.
- Safeguard: bd72222 (PR #533) blocks publishing seed fixtures to latest/.
- Phase 5 (rewrite .git history): not started, and the issue says it needs separate owner sign-off.

## Divergences from the issue
- The bucket is private. The issue asked for public read (no allUsers binding in storage.py).
- Staging only. The issue left staging or production open; the code hard-codes staging (dashboard-artifacts.yml:68, gh-pages.yml:37).
- The guard checks tracked state, not only the diff.
- The issue wanted audit/output/env_fingerprints/baseline_records_snapshot.json kept tracked. It is not tracked now, and it was not tracked at e41d00d either (git ls-tree check). The guard pattern covers it.

## Consequences
- Local exports/plots/ is now a developer cache, and the webservice serves it first when present.
- Historical links to committed HTML in exports/gallery.md are dead (see bugs/analysis-gallery-stale-entries).
- Production has no publish path yet (see bugs/dashboards-production-latest-unpublished).

## Open questions
- Which environment should the public gallery show? Code says staging; the issue asked the owner to confirm.
- When will the Phase 5 history rewrite be decided?

# Related Concepts
- [Generated dashboards, fingerprints, drift reports and insights are never committed to git](../requirements/generated-artifacts-never-committed.md): the rule this decision created
- [Publish analysis as committed static HTML instead of a live dashboard](analysis-static-html-gallery.md): the earlier committed-HTML decision this supersedes
- [GCS dashboards bucket, its service accounts, WIF bindings, and runtime reads](../architecture/infra-dashboards-gcs-bucket.md): the storage this decision chose
- [exports/ directory: committed SQL, reports, and plot outputs](../architecture/analysis-exports-artifacts.md): the exports tree that stopped being committed
