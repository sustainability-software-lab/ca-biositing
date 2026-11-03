---
type: Bug
title: deployment/README.md describes a dashboard privacy gate and bucket settings the code does not implement
description: "The README GCS section claims public access prevention, an opt-in glob and a denylist that storage.py and gh-pages.yml do not implement; Product 1 is published to Pages by default."
tags: [bug, docs, drift, dashboards, github-pages, privacy]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-22T21:27:25Z" }
status: stable
code_refs: ["deployment/README.md", "deployment/cloud/gcp/infrastructure/storage.py", ".github/workflows/gh-pages.yml"]
sources: ["commit 3eba913", "commit 1fcadb4", "https://github.com/sustainability-software-lab/ca-biositing/pull/527", ".github/workflows/gh-pages.yml"]
governance: context
stale_after: "2026-12-31"
---

## Symptom
deployment/README.md:990-1052 (section added by 3eba913, PR #527) disagrees with the code at a2c8de8.

| README claim | Code at a2c8de8 |
|---|---|
| README:1000 bucket uses public_access_prevention enforced | storage.py:110-126 sets no public_access_prevention (grep finds none) |
| README:1046-1048 GH_PAGES_GALLERY_GLOB is opt-in, for example exports/slices/*_public_slice.html | gh-pages.yml:44 sets a non-empty default: index.html metadata/resource_analysis_dashboard.html |
| README:1050-1052 unconditional denylist includes resource_analysis_dashboard.html, db_snapshot*.json, env_fingerprint*.json, resource_ai_insights*.json | gh-pages.yml:107-112 denies four pages only; resource_analysis_dashboard.html is copied by default (line 44) |
| README:1046 copies gallery into the MkDocs site/ build | gh-pages.yml:88-118 copies from GCS into _site/gallery |

## Impact
Product 1 (Characterization and AI Brief, metadata/resource_analysis_dashboard.html) is published publicly by default. The gh-pages.yml comment (lines 40-43) says the public subset is intended, but the README says it is blocked. The owner needs to confirm which is correct.

## Status
Open at a2c8de8. The README text has not changed since 3eba913.

## Fix direction
Either fix the README to match gh-pages.yml, or remove resource_analysis_dashboard.html from the default glob, and set public access prevention in storage.py if the README claim is wanted.

# Related Concepts
- [gh-pages.yml: builds the public Pages gallery from the GCS latest bundle](../architecture/ci-gh-pages-gallery-consumer.md): the workflow whose behaviour the README misdescribes
- [GCS dashboards bucket, its service accounts, WIF bindings, and runtime reads](../architecture/infra-dashboards-gcs-bucket.md): the bucket settings the README misdescribes
- [Known infra documentation drift and dead config (snapshot at e41d00d)](doc-drift-infra.md): the earlier infra doc-drift snapshot
