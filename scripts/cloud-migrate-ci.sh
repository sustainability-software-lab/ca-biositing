#!/usr/bin/env bash
set -euo pipefail

# Update migration job image with IMAGE_TAG and execute.
# IMAGE_TAG defaults to "latest" if not set in the environment.
# DEPLOY_ENV defaults to "staging" if not set.

DEPLOY_ENV="${DEPLOY_ENV:-staging}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
JOB_NAME="biocirv-${DEPLOY_ENV}-migrate"
GCP_REGION="${GCP_REGION:-us-west1}"
GCP_PROJECT="${GCP_PROJECT:-biocirv-470318}"

echo "Updating migration job: ${JOB_NAME}"
echo "Environment: ${DEPLOY_ENV}"
echo "Image tag: ${IMAGE_TAG}"
echo "Region: ${GCP_REGION}"

IMAGE_URL="us-west1-docker.pkg.dev/${GCP_PROJECT}/ghcr-proxy/sustainability-software-lab/ca-biositing/pipeline:${IMAGE_TAG}"
echo "Image URL: ${IMAGE_URL}"

gcloud run jobs update "${JOB_NAME}" \
  --image="${IMAGE_URL}" \
  --region="${GCP_REGION}"

echo "Executing migration job..."
gcloud run jobs execute "${JOB_NAME}" \
  --region="${GCP_REGION}" \
  --wait

echo "Migration job completed successfully."
