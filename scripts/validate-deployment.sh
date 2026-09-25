#!/usr/bin/env bash
set -euo pipefail

# Validate deployment health after service updates.
# Usage: DEPLOY_ENV=staging bash scripts/validate-deployment.sh
# Waits up to 5 minutes for services to become healthy.

DEPLOY_ENV="${DEPLOY_ENV:-staging}"
GCP_REGION="${GCP_REGION:-us-west1}"
TIMEOUT=300
INTERVAL=10
ELAPSED=0

echo "Validating deployment for environment: ${DEPLOY_ENV}"

# Check if jq is installed (required for JSON parsing)
if ! command -v jq &> /dev/null; then
    echo "ERROR: jq is required but not installed. Installing..."
    # Try to install jq if not available
    if command -v apt-get &> /dev/null; then
        sudo apt-get update && sudo apt-get install -y jq
    elif command -v yum &> /dev/null; then
        sudo yum install -y jq
    elif command -v brew &> /dev/null; then
        brew install jq
    else
        echo "ERROR: Cannot install jq automatically. Please install it manually."
        exit 1
    fi
fi

check_webservice_health() {
    local url
    url=$(gcloud run services describe "biocirv-${DEPLOY_ENV}-webservice" \
        --region="${GCP_REGION}" --format="value(status.url)" 2>/dev/null) || return 1
    [ -n "$url" ] || return 1
    local status
    status=$(curl -s -o /dev/null -w "%{http_code}" "${url}/health" 2>/dev/null) || return 1
    [ "$status" = "200" ]
}

check_prefect_server() {
    # Prefect server uses INGRESS_TRAFFIC_INTERNAL_ONLY, so we check via
    # the prefect-auth proxy. /api/health is in skip-auth routes.
    local url
    url=$(gcloud run services describe "biocirv-${DEPLOY_ENV}-prefect-auth" \
        --region="${GCP_REGION}" --format="value(status.url)" 2>/dev/null) || return 1
    [ -n "$url" ] || return 1
    local status
    status=$(curl -s -o /dev/null -w "%{http_code}" "${url}/api/health" 2>/dev/null) || return 1
    [ "$status" = "200" ]
}

check_worker_ready() {
    # Worker is internal-only (no external HTTP access).
    # Check Cloud Run service conditions instead.
    local ready
    ready=$(gcloud run services describe "biocirv-${DEPLOY_ENV}-prefect-worker" \
        --region="${GCP_REGION}" --format=json 2>/dev/null \
        | jq -r '.status.conditions[]? | select(.type=="Ready") | .status' 2>/dev/null) || return 1
    [ "$ready" = "True" ]
}

while [ "$ELAPSED" -lt "$TIMEOUT" ]; do
    echo "[${ELAPSED}/${TIMEOUT}s] Checking service health..."

    webservice_ok=false
    prefect_ok=false
    worker_ok=false

    if check_webservice_health; then
        echo "  OK  Webservice is healthy"
        webservice_ok=true
    else
        echo "  --  Webservice not ready yet"
    fi

    if check_prefect_server; then
        echo "  OK  Prefect server is healthy"
        prefect_ok=true
    else
        echo "  --  Prefect server not ready yet"
    fi

    if check_worker_ready; then
        echo "  OK  Worker is ready"
        worker_ok=true
    else
        echo "  --  Worker not ready yet"
    fi

    if [ "$webservice_ok" = true ] && [ "$prefect_ok" = true ] && [ "$worker_ok" = true ]; then
        echo ""
        echo "All services are healthy. Deployment validated."
        exit 0
    fi

    sleep "$INTERVAL"
    ELAPSED=$((ELAPSED + INTERVAL))
done

echo ""
echo "Deployment validation FAILED — services did not become healthy within ${TIMEOUT}s"
exit 1
