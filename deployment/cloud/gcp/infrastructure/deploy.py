"""Pulumi Automation API entry point for GCP infrastructure."""

import json
import sys

import pulumi
from pulumi import automation as auto

from config import (
    BACKEND_URL,
    PROJECT_NAME,
    STACK_NAME,
    configure_stack,
)

# Import module functions (each creates a group of resources)
from apis import enable_apis
from cloud_sql import create_cloud_sql
from iam import create_service_accounts
from secret_manager import create_secrets
from storage import create_storage_resources

from artifact_registry import create_artifact_registry, create_quayio_registry
from cloud_run import create_cloud_run_resources
from networking import create_cloud_nat
from wif import create_wif


def pulumi_program():
    """Inline Pulumi program defining all GCP infrastructure."""
    # 1. Enable required GCP APIs — downstream resources depend on these.
    api_services = enable_apis()

    # 1.5. Workload Identity Federation for GitHub Actions CI/CD
    # (must be created before AR so the deployer SA has artifactregistry.admin)
    wif = create_wif(depends_on=[api_services["iam"]])

    # 1.6. Artifact Registry: remote repo proxying GHCR for Cloud Run
    # Depends on the deployer SA's AR admin grant (CI runs as this SA)
    ghcr_proxy = create_artifact_registry(
        depends_on=[
            api_services["artifactregistry"],
            wif.deployer_iam_members["artifactregistry.admin"],
        ]
    )

    # 1.7. Artifact Registry: remote repo proxying Quay.io for oauth2-proxy image
    quayio_proxy = create_quayio_registry(
        depends_on=[
            api_services["artifactregistry"],
        ]
    )

    # 2. Cloud SQL: instance, databases, users
    sql = create_cloud_sql(depends_on=[api_services["sqladmin"]])

    # 3. Secrets: DB password, GSheets credentials, read-only user passwords
    secret_resources = create_secrets(
        sql, depends_on=[api_services["secretmanager"]]
    )

    # 4. IAM: service accounts and role bindings
    iam = create_service_accounts(
        depends_on=[api_services["iam"], api_services["cloudresourcemanager"]]
    )

    # 4.5. Storage: GCS buckets
    storage = create_storage_resources(
        service_accounts=iam.service_accounts,
        sql_instance=sql.instance,
        depends_on=[api_services["storage"]],
    )

    # 4.7. Cloud NAT: enables VPC egress for Cloud Run (oauth2-proxy needs
    #       internet access for Google OAuth while routing via VPC for internal traffic)
    cloud_nat = create_cloud_nat(depends_on=[api_services["compute"]])

    # 5. Cloud Run: Services and Jobs (images pulled via AR remote repos)
    cr = create_cloud_run_resources(
        sql, secret_resources, iam,
        depends_on=[api_services["run"], ghcr_proxy, quayio_proxy, cloud_nat.nat],
    )

    # --- All exports centralized here ---
    # Cloud SQL
    pulumi.export("db_instance_name", sql.instance.name)
    pulumi.export("db_instance_connection_name", sql.instance.connection_name)
    pulumi.export("database_name", sql.database.name)
    pulumi.export("prefect_database_name", sql.prefect_database.name)

    # Secrets
    pulumi.export("db_password_secret_name", secret_resources.db_password_secret.name)
    pulumi.export("gsheets_secret_name", secret_resources.gsheets_secret.name)
    pulumi.export("usda_api_key_secret_name", secret_resources.usda_api_key_secret.name)
    pulumi.export(
        "prefect_auth_secret_name", secret_resources.prefect_auth_secret.name
    )
    for username, secret in secret_resources.readonly_secrets.items():
        pulumi.export(f"ro_{username}_password_secret", secret.name)
    pulumi.export(
        "postgres_password_secret_name",
        secret_resources.postgres_password_secret.name,
    )

    pulumi.export(
        "admin_password_secret_name",
        secret_resources.admin_password_sm.name,
    )

    # IAM
    for sa_name, sa in iam.service_accounts.items():
        pulumi.export(f"sa_{sa_name}_email", sa.email)

    # Workload Identity Federation
    pulumi.export("wif_provider_name", wif.provider_name)
    pulumi.export("deployer_sa_email", wif.deployer_sa.email)

    # Cloud Run
    pulumi.export("webservice_url", cr.webservice.uri)
    pulumi.export("prefect_server_url", cr.prefect_server.uri)
    pulumi.export("oauth2_proxy_url", cr.oauth2_proxy.uri)
    pulumi.export("migration_job_name", cr.migration_job.name)
    pulumi.export("seed_admin_job_name", cr.seed_admin_job.name)

    # Storage
    pulumi.export("image_bucket_name", storage.bucket.name)
    pulumi.export("backup_bucket_name", storage.backup_bucket.name)
    pulumi.export("gasification_bucket_name", storage.gasification_bucket.name)


def get_stack() -> auto.Stack:
    """Create or select the Pulumi stack with programmatic config."""
    stack = auto.create_or_select_stack(
        stack_name=STACK_NAME,
        project_name=PROJECT_NAME,
        program=pulumi_program,
        opts=auto.LocalWorkspaceOptions(
            project_settings=auto.ProjectSettings(
                name=PROJECT_NAME,
                runtime="python",
                backend=auto.ProjectBackend(url=BACKEND_URL),
            ),
        ),
    )
    configure_stack(stack)
    return stack


def main():
    args = sys.argv[1:]
    command = args[0] if args else "preview"

    stack = get_stack()

    if command == "preview":
        result = stack.preview(on_output=print)
        print(f"\nPreview summary: {json.dumps(result.change_summary, indent=2)}")

    elif command == "up":
        # Refresh first to clear any pending operations from interrupted deploys
        print("Running refresh to reconcile state...")
        try:
            stack.refresh(on_output=print)
            print("Refresh complete. Starting update...\n")
        except auto.errors.CommandError as e:
            print(f"\nRefresh failed (non-fatal): {e}")
            print("Continuing with update...\n")
        result = stack.up(on_output=print)
        if result.summary:
            print(
                f"\nUpdate summary: {json.dumps(result.summary.resource_changes, indent=2)}"
            )
        else:
            print("\nUpdate completed (no summary available).")

    elif command == "destroy":
        stack.destroy(on_output=print)
        print("Destroy complete.")

    elif command == "refresh":
        stack.refresh(on_output=print)
        print("Refresh complete.")

    elif command == "outputs":
        outputs = stack.outputs()
        for key, val in outputs.items():
            print(f"{key}: {val.value}")

    else:
        print(f"Unknown command: {command}")
        print("Usage: python deploy.py [preview|up|destroy|refresh|outputs]")
        sys.exit(1)


if __name__ == "__main__":
    main()
