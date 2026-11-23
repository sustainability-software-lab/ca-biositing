---
type: Decision
title: "Decision: oauth2-proxy with Google login in front of the Prefect UI and API"
description: "Why oauth2-proxy with Google login fronts Prefect locally and in GCP, why the cloud server is internal-only, and how local and cloud auth differ."
tags: [decision, auth, prefect, oauth2-proxy, google-oauth]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:28:34Z" }
status: stable
code_refs: ["resources/docker/docker-compose.yml", "deployment/cloud/gcp/infrastructure/cloud_run.py", "scripts/validate-deployment.sh"]
sources: ["resources/docker/docker-compose.yml", "deployment/cloud/gcp/infrastructure/cloud_run.py", "commit 72439c5", "commit f3ca6dd", "commit 09787cd", "commit 79f9344", "https://github.com/sustainability-software-lab/ca-biositing/pull/221", "https://github.com/sustainability-software-lab/ca-biositing/pull/222"]
governance: context
---

## Decision
Prefect 3 server has no built-in login for this deployment. Access to its UI and API is gated by oauth2-proxy with the Google provider. In GCP the Prefect server itself is `INGRESS_TRAFFIC_INTERNAL_ONLY`, so only the proxy (public) and internal workloads reach it.

## Context and reasoning
- 72439c5 (PR #221, 2026-03-27): oauth2-proxy added to local compose "for Prefect UI auth", with the Prefect server kept on host port 4200 for backward compatibility.
- f3ca6dd (PR #222): cloud oauth2-proxy service, with Cloud Router + NAT so the proxy can reach Google’s OAuth endpoints.
- 09787cd (PR #223): renamed to `prefect-auth`, skip-auth for `/api/health`, skip provider button.
- 79f9344 (PR #226): secrets volume-mounted rather than env value_source, because of the Cloud Run env var serialization bug.
- Upstream headers: oauth2-proxy forwards `X-Auth-Request-Email` and `X-Auth-Request-User` (deployment/README "Key design decisions").

## Alternatives considered
- Prefect Cloud or Prefect’s own auth: not in the repo. resources/README.md lists Prefect Cloud as a production option; no decision record found.
- Cloud IAP or service-to-service identity tokens: deployment/README states the VPC-internal ingress approach avoids identity-token injection. Not evaluated further in the repo.

## Trade-offs
- Gain: no auth code in Prefect; single domain-restricted login in cloud (`lbl.gov`, cloud_run.py oauth2 command).
- Cost: local and cloud auth differ. Local allows any Google account (`OAUTH2_PROXY_EMAIL_DOMAINS=*`, compose line 118) and the Prefect server is also directly exposed on localhost:4200. Cloud restricts to `lbl.gov`.
- Cost: the Prefect worker and the trigger job talk to the server directly (internal path), bypassing the proxy by design.

## Open questions
- Whether the local `EMAIL_DOMAINS=*` setting is acceptable on shared developer laptops (confirm with the owner).
- Whether the oauth2 client is shared between staging and production (deployment/README bootstrap step 7 suggests per-env OAuth consent branding; confirm).

# Related Concepts
- [Prefect on Cloud Run: server, always-on worker, auth proxy, and ETL trigger job](../architecture/infra-prefect-cloud-run.md): Services that this decision shapes.
- [Local Docker Compose topology (db, setup-db, Prefect server/worker, oauth2-proxy)](../architecture/infra-local-topology.md): Local oauth2-proxy and its differences.
- [System overview (start here)](../architecture/system-overview.md): Auth boundary for the orchestration UI.
