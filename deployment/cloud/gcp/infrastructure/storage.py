"""GCS Bucket resources."""

from dataclasses import dataclass
from typing import Sequence

import pulumi
import pulumi_gcp as gcp

from config import IMAGE_BUCKET_NAME, BACKUP_BUCKET_NAME, GCP_REGION


@dataclass
class StorageResources:
    bucket: gcp.storage.Bucket
    backup_bucket: gcp.storage.Bucket


def create_storage_resources(
    sql_instance: gcp.sql.DatabaseInstance | None = None,
    depends_on: Sequence[pulumi.Resource] | None = None,
) -> StorageResources:
    """Create GCS buckets."""
    opts = pulumi.ResourceOptions(depends_on=depends_on or [])

    # Create the image bucket
    bucket = gcp.storage.Bucket(
        "image-bucket",
        name=IMAGE_BUCKET_NAME,
        location=GCP_REGION,
        uniform_bucket_level_access=True,
        force_destroy=False,  # Protect images from accidental deletion
        opts=opts,
    )

    # Make the bucket public (read-only) for the data portal
    gcp.storage.BucketIAMMember(
        "image-bucket-public-viewer",
        bucket=bucket.name,
        role="roles/storage.objectViewer",
        member="allUsers",
    )

    # Create the backup bucket (versioned, not public)
    backup_bucket = gcp.storage.Bucket(
        "backup-bucket",
        name=BACKUP_BUCKET_NAME,
        location=GCP_REGION,
        uniform_bucket_level_access=True,
        versioning=gcp.storage.BucketVersioningArgs(enabled=True),
        force_destroy=False,  # Protect backups from accidental deletion
        opts=opts,
    )

    # Grant Cloud SQL service account access to the backup bucket if provided
    if sql_instance:
        gcp.storage.BucketIAMMember(
            "backup-bucket-sql-admin",
            bucket=backup_bucket.name,
            role="roles/storage.objectAdmin",
            member=sql_instance.service_account_email_address.apply(
                lambda email: f"serviceAccount:{email}"
            ),
        )

    return StorageResources(bucket=bucket, backup_bucket=backup_bucket)
