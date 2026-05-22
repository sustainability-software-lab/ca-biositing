#!/bin/bash
# scripts/cloud-backup.sh
# Performs a manual SQL export of a Cloud SQL instance to its corresponding GCS backup bucket.
# Usage: DEPLOY_ENV=staging bash scripts/cloud-backup.sh

set -e

# Default to staging if DEPLOY_ENV is not set
ENV=${DEPLOY_ENV:-staging}
PROJECT_ID="biocirv-470318"
INSTANCE_NAME="biocirv-$ENV"
DATABASE_NAME="biocirv-$ENV"
BUCKET_NAME="biocirv-$ENV-backups"
DATE_PREFIX=$(date +%Y%m%d)
TIME_SUFFIX=$(date +%H%M%S)
BACKUP_FILENAME="${DATE_PREFIX}-biocirv-${ENV}-backup-${TIME_SUFFIX}.sql"
BACKUP_PATH="gs://$BUCKET_NAME/$BACKUP_FILENAME"

echo "=== BioCirV Database Backup ==="
echo "Environment: $ENV"
echo "Project:     $PROJECT_ID"
echo "Instance:    $INSTANCE_NAME"
echo "Database:    $DATABASE_NAME"
echo "Destination: $BACKUP_PATH"
echo "==============================="

# Verify bucket existence
if ! gcloud storage buckets describe "gs://$BUCKET_NAME" --project="$PROJECT_ID" > /dev/null 2>&1; then
    echo "Error: Bucket gs://$BUCKET_NAME does not exist."
    echo "Please ensure infrastructure is deployed for environment: $ENV"
    exit 1
fi

# Verify instance existence
if ! gcloud sql instances describe "$INSTANCE_NAME" --project="$PROJECT_ID" > /dev/null 2>&1; then
    echo "Error: Cloud SQL instance $INSTANCE_NAME does not exist."
    exit 1
fi

# Perform export
echo "Starting SQL export (this may take a few minutes)..."
gcloud sql export sql "$INSTANCE_NAME" "$BACKUP_PATH" \
    --project="$PROJECT_ID" \
    --database="$DATABASE_NAME" \
    --offload

echo "Success! Backup saved to: $BACKUP_PATH"
