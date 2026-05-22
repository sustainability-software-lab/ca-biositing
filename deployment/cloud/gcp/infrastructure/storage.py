"""GCS Bucket resources."""

from dataclasses import dataclass
from typing import Sequence

import pulumi
import pulumi_gcp as gcp

from config import IMAGE_BUCKET_NAME, BACKUP_BUCKET_NAME, GASIFICATION_BUCKET_NAME, GCP_REGION


@dataclass
class StorageResources:
    bucket: gcp.storage.Bucket
    backup_bucket: gcp.storage.Bucket
    gasification_bucket: gcp.storage.Bucket


def create_storage_resources(
    service_accounts: dict[str, gcp.serviceaccount.Account],
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
        opts=opts,
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

    # Create the gasification data bucket (not public)
    gasification_bucket = gcp.storage.Bucket(
        "gasification-bucket",
        name=GASIFICATION_BUCKET_NAME,
        location=GCP_REGION,
        uniform_bucket_level_access=True,
        force_destroy=False,
        opts=opts,
    )

    # Grant frontend and webservice read access to the gasification bucket
    for sa_key in ["frontend", "webservice"]:
        if sa_key in service_accounts:
            gcp.storage.BucketIAMMember(
                f"gasification-bucket-{sa_key}-viewer",
                bucket=gasification_bucket.name,
                role="roles/storage.objectViewer",
                member=service_accounts[sa_key].email.apply(
                    lambda email: f"serviceAccount:{email}"
                ),
                opts=opts,
            )

    # Grant manual access to the data portal service account
    gcp.storage.BucketIAMMember(
        "gasification-bucket-data-portal-viewer",
        bucket=gasification_bucket.name,
        role="roles/storage.objectViewer",
        member="serviceAccount:biocirv-data-portal@biocirv-470318.iam.gserviceaccount.com",
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
            opts=opts,
        )

    return StorageResources(
        bucket=bucket, backup_bucket=backup_bucket, gasification_bucket=gasification_bucket
    )
