"""Workload Identity Federation for GitHub Actions deployment."""

from dataclasses import dataclass
from typing import Sequence

import pulumi
import pulumi_gcp as gcp

from config import GCP_PROJECT, GITHUB_REPO, WIF_POOL_ID, WIF_PROVIDER_ID, SA_DEPLOYER, STACK_NAME


@dataclass
class WIFResources:
    pool: gcp.iam.WorkloadIdentityPool
    provider: gcp.iam.WorkloadIdentityPoolProvider
    deployer_sa: gcp.serviceaccount.Account
    provider_name: pulumi.Output
    deployer_iam_members: dict[str, gcp.projects.IAMMember] = None


def create_wif(
    depends_on: Sequence[pulumi.Resource] | None = None,
    service_accounts: dict[str, gcp.serviceaccount.Account] | None = None,
) -> WIFResources:
    """Create Workload Identity Federation resources for GitHub Actions.

    This sets up keyless authentication so GitHub Actions can deploy
    to GCP without long-lived service account keys.
    """
    opts = pulumi.ResourceOptions(depends_on=depends_on or [])

    # Look up the project number dynamically
    project = gcp.organizations.get_project(project_id=GCP_PROJECT)
    project_number = project.number

    # --- WIF Pool & Provider ---
    pool = gcp.iam.WorkloadIdentityPool(
        "github-actions-pool",
        workload_identity_pool_id=WIF_POOL_ID,
        display_name=f"GitHub Actions ({STACK_NAME.capitalize()})",
        description=f"WIF pool for GitHub Actions CI/CD ({STACK_NAME})",
        opts=opts,
    )

    provider = gcp.iam.WorkloadIdentityPoolProvider(
        "github-oidc-provider",
        workload_identity_pool_id=pool.workload_identity_pool_id,
        workload_identity_pool_provider_id=WIF_PROVIDER_ID,
        display_name=f"GitHub OIDC ({STACK_NAME.capitalize()})",
        description=f"GitHub Actions OIDC provider ({STACK_NAME})",
        attribute_mapping={
            "google.subject": "assertion.sub",
            "attribute.repository": "assertion.repository",
            "attribute.workflow_ref": "assertion.workflow_ref",
        },
        attribute_condition=f'assertion.repository == "{GITHUB_REPO}"',
        oidc=gcp.iam.WorkloadIdentityPoolProviderOidcArgs(
            issuer_uri="https://token.actions.githubusercontent.com",
        ),
        opts=pulumi.ResourceOptions(depends_on=[pool]),
    )

    # Full provider resource name for google-github-actions/auth
    provider_name = pulumi.Output.all(
        pool.name, provider.workload_identity_pool_provider_id
    ).apply(lambda args: f"{args[0]}/providers/{args[1]}")

    # --- Deployer Service Account ---
    deployer_sa = gcp.serviceaccount.Account(
        "gh-deploy-sa",
        account_id=SA_DEPLOYER,
        display_name=f"GitHub Actions Deployer ({STACK_NAME.capitalize()})",
        opts=opts,
    )

    # IAM roles for the deployer SA
    deployer_roles = [
        "roles/cloudbuild.builds.editor",
        "roles/iam.serviceAccountUser",  # actAs Cloud Build default SA
        "roles/run.admin",
        "roles/viewer",
        "roles/cloudsql.admin",
        "roles/iam.serviceAccountAdmin",
        "roles/secretmanager.admin",
        "roles/resourcemanager.projectIamAdmin",
        "roles/artifactregistry.admin",  # create/manage AR remote repos
        "roles/storage.admin",  # create/manage GCS buckets
    ]

    deployer_iam_members = {}
    for role in deployer_roles:
        role_short = role.split("/")[-1]
        deployer_iam_members[role_short] = gcp.projects.IAMMember(
            f"gh-deploy-{role_short}",
            project=GCP_PROJECT,
            role=role,
            member=deployer_sa.email.apply(
                lambda email: f"serviceAccount:{email}"
            ),
        )

    # Storage admin on the Pulumi state bucket
    # (needs storage.admin, not just objectAdmin, so Pulumi can read
    # bucket IAM policies during `refresh`)
    gcp.storage.BucketIAMMember(
        "gh-deploy-pulumi-state",
        bucket="biocirv-470318-pulumi-state",
        role="roles/storage.admin",
        member=deployer_sa.email.apply(
            lambda email: f"serviceAccount:{email}"
        ),
    )

    # Storage admin on the Cloud Build staging bucket
    # (Cloud Build uploads source tarballs here before building)
    gcp.storage.BucketIAMMember(
        "gh-deploy-cloudbuild-staging",
        bucket="biocirv-470318_cloudbuild",
        role="roles/storage.admin",
        member=deployer_sa.email.apply(
            lambda email: f"serviceAccount:{email}"
        ),
    )

    wif_principal_set = pulumi.Output.concat(
        "principalSet://iam.googleapis.com/projects/",
        project_number,
        "/locations/global/workloadIdentityPools/",
        pool.workload_identity_pool_id,
        f"/attribute.repository/{GITHUB_REPO}",
    )

    # Allow WIF pool to impersonate the deployer SA
    gcp.serviceaccount.IAMBinding(
        "gh-deploy-wif-binding",
        service_account_id=deployer_sa.name,
        role="roles/iam.workloadIdentityUser",
        members=[wif_principal_set],
    )

    # Allow WIF pool to impersonate the scoped dashboards publisher and reader SAs
    scoped_workflow_refs = {
        "dashboards-publisher": f"{GITHUB_REPO}/.github/workflows/dashboard-artifacts.yml@refs/heads/main",
        "dashboards-reader": f"{GITHUB_REPO}/.github/workflows/gh-pages.yml@refs/heads/main",
    }
    for sa_key, wf_ref in scoped_workflow_refs.items():
        if service_accounts and sa_key in service_accounts:
            scoped_principal_set = pulumi.Output.concat(
                "principalSet://iam.googleapis.com/projects/",
                project_number,
                "/locations/global/workloadIdentityPools/",
                pool.workload_identity_pool_id,
                f"/attribute.workflow_ref/{wf_ref}",
            )
            gcp.serviceaccount.IAMBinding(
                f"{sa_key}-wif-binding",
                service_account_id=service_accounts[sa_key].name,
                role="roles/iam.workloadIdentityUser",
                members=[scoped_principal_set],
                opts=pulumi.ResourceOptions(depends_on=[service_accounts[sa_key]]),
            )

    return WIFResources(
        pool=pool,
        provider=provider,
        deployer_sa=deployer_sa,
        provider_name=provider_name,
        deployer_iam_members=deployer_iam_members,
    )
