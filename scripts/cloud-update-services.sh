#!/usr/bin/env bash
set -euo pipefail

# Force new Cloud Run revisions with IMAGE_TAG.
# IMAGE_TAG defaults to "latest" if not set in the environment.
# DEPLOY_ENV defaults to "staging" if not set.

DEPLOY_ENV="${DEPLOY_ENV:-staging}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
GCP_REGION="${GCP_REGION:-us-west1}"
GCP_PROJECT="${GCP_PROJECT:-biocirv-470318}"

echo "Updating Cloud Run services for environment: ${DEPLOY_ENV}"
echo "Image tag: ${IMAGE_TAG}"
echo "Region: ${GCP_REGION}"

PIPELINE_IMAGE="us-west1-docker.pkg.dev/${GCP_PROJECT}/ghcr-proxy/sustainability-software-lab/ca-biositing/pipeline:${IMAGE_TAG}"
WEBSERVICE_IMAGE="us-west1-docker.pkg.dev/${GCP_PROJECT}/ghcr-proxy/sustainability-software-lab/ca-biositing/webservice:${IMAGE_TAG}"

echo ""
echo "Updating prefect-worker service..."
echo "Image: ${PIPELINE_IMAGE}"
gcloud run services update "biocirv-${DEPLOY_ENV}-prefect-worker" \
  --image="${PIPELINE_IMAGE}" \
  --region="${GCP_REGION}"

echo ""
echo "Updating webservice..."
echo "Image: ${WEBSERVICE_IMAGE}"
gcloud run services update "biocirv-${DEPLOY_ENV}-webservice" \
  --image="${WEBSERVICE_IMAGE}" \
  --region="${GCP_REGION}"

echo ""
echo "All services updated successfully."
