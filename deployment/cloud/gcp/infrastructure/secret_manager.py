"""Secret Manager resources, database users, and password management."""

from dataclasses import dataclass, field
from typing import Sequence

import pulumi
import pulumi_gcp as gcp
import pulumi_random as random

from cloud_sql import CloudSQLResources
from config import (
    DB_USER,
    GCP_PROJECT,
    READONLY_USERS,
    SA_DASHBOARDS_PUBLISHER,
    SECRET_DB_PASSWORD,
    SECRET_GSHEETS,
    SECRET_USDA_API_KEY,
    SECRET_GOOGLE_MAPS_API_KEY,
    SECRET_PREFECT_AUTH,
    SECRET_POSTGRES_PASSWORD,
    SECRET_JWT_KEY,
    SECRET_ADMIN_PASSWORD,
    SECRET_RO_PREFIX,
    SECRET_OAUTH2_CLIENT_ID,
    SECRET_OAUTH2_CLIENT_SECRET,
    SECRET_OAUTH2_COOKIE_SECRET,
    STACK_NAME,
)


@dataclass
class SecretResources:
    db_password: random.RandomPassword
    db_user: gcp.sql.User
    db_password_secret: gcp.secretmanager.Secret
    gsheets_secret: gcp.secretmanager.Secret
    usda_api_key_secret: gcp.secretmanager.Secret = None
    google_maps_api_key_secret: gcp.secretmanager.Secret = None
    prefect_auth_password: random.RandomPassword = None
    prefect_auth_secret: gcp.secretmanager.Secret = None
    readonly_users: dict = field(default_factory=dict)
    readonly_passwords: dict = field(default_factory=dict)
    readonly_secrets: dict = field(default_factory=dict)
    readonly_secret_iam_members: dict = field(default_factory=dict)
    postgres_password: random.RandomPassword = None
    postgres_user: gcp.sql.User = None
    postgres_password_secret: gcp.secretmanager.Secret = None
    jwt_secret: random.RandomPassword = None
    jwt_secret_sm: gcp.secretmanager.Secret = None
    admin_password: random.RandomPassword = None
    admin_password_sm: gcp.secretmanager.Secret = None
    oauth2_client_id_secret: gcp.secretmanager.Secret = None
    oauth2_client_secret_secret: gcp.secretmanager.Secret = None
    oauth2_cookie_secret: random.RandomPassword = None
    oauth2_cookie_secret_sm: gcp.secretmanager.Secret = None


def grant_dashboards_publisher_readonly_secret_access(
    secrets: SecretResources,
    publisher_sa: gcp.serviceaccount.Account | None = None,
    service_accounts: dict[str, gcp.serviceaccount.Account] | None = None,
) -> dict[str, gcp.secretmanager.SecretIamMember]:
    """Grant dashboards-publisher secretAccessor exclusively on biocirv_readonly.

    Enforces single-stack Pulumi ownership:
    - On staging: binds biocirv-staging-dash-pub to biocirv-staging-ro-biocirv_readonly.
    - On production: binds biocirv-prod-dash-pub AND biocirv-staging-dash-pub to
      biocirv-production-ro-biocirv_readonly so the staging dashboard workflow can
      read the production read-only secret without cross-stack resource contention.
    """
    if secrets.readonly_secret_iam_members:
        return secrets.readonly_secret_iam_members

    ro_biocirv_secret = secrets.readonly_secrets.get("biocirv_readonly")
    if ro_biocirv_secret is None:
        return {}

    target_sa = publisher_sa or (
        service_accounts.get("dashboards-publisher") if service_accounts else None
    )
    publisher_member = (
        target_sa.email.apply(lambda email: f"serviceAccount:{email}")
        if target_sa is not None
        else f"serviceAccount:{SA_DASHBOARDS_PUBLISHER}@{GCP_PROJECT}.iam.gserviceaccount.com"
    )

    deps: list[pulumi.Resource] = [ro_biocirv_secret]
    if target_sa is not None:
        deps.append(target_sa)

    iam_members: dict[str, gcp.secretmanager.SecretIamMember] = {}
    iam_members["dashboards-publisher"] = gcp.secretmanager.SecretIamMember(
        "ro-biocirv-readonly-dashboards-publisher-accessor",
        project=GCP_PROJECT,
        secret_id=ro_biocirv_secret.secret_id,
        role="roles/secretmanager.secretAccessor",
        member=publisher_member,
        opts=pulumi.ResourceOptions(depends_on=deps),
    )

    if STACK_NAME == "production":
        iam_members["staging-dashboards-publisher"] = gcp.secretmanager.SecretIamMember(
            "ro-biocirv-readonly-staging-dashboards-publisher-accessor",
            project=GCP_PROJECT,
            secret_id=ro_biocirv_secret.secret_id,
            role="roles/secretmanager.secretAccessor",
            member=f"serviceAccount:biocirv-staging-dash-pub@{GCP_PROJECT}.iam.gserviceaccount.com",
            opts=pulumi.ResourceOptions(depends_on=[ro_biocirv_secret]),
        )

    secrets.readonly_secret_iam_members = iam_members
    return iam_members


def create_secrets(
    sql: CloudSQLResources,
    depends_on: Sequence[pulumi.Resource] | None = None,
    service_accounts: dict[str, gcp.serviceaccount.Account] | None = None,
) -> SecretResources:
    """Create Secret Manager secrets, database users, and passwords."""
    secret_opts = pulumi.ResourceOptions(depends_on=depends_on or [])

    # Primary database user password
    db_password = random.RandomPassword(
        "db-password",
        length=32,
        special=False,
    )

    # Create the primary database user
    db_user = gcp.sql.User(
        "db-user",
        name=DB_USER,
        instance=sql.instance.name,
        password=db_password.result,
    )

    # Store the DB password in Secret Manager
    db_password_secret = gcp.secretmanager.Secret(
        "db-password-secret",
        secret_id=SECRET_DB_PASSWORD,
        replication=gcp.secretmanager.SecretReplicationArgs(
            auto=gcp.secretmanager.SecretReplicationAutoArgs(),
        ),
        opts=secret_opts,
    )

    gcp.secretmanager.SecretVersion(
        "db-password-version",
        secret=db_password_secret.id,
        secret_data=db_password.result,
    )

    # Google Sheets credentials secret (version added manually post-deploy)
    gsheets_secret = gcp.secretmanager.Secret(
        "gsheets-credentials-secret",
        secret_id=SECRET_GSHEETS,
        replication=gcp.secretmanager.SecretReplicationArgs(
            auto=gcp.secretmanager.SecretReplicationAutoArgs(),
        ),
        opts=secret_opts,
    )

    # USDA NASS API key (version added manually post-deploy)
    usda_api_key_secret = gcp.secretmanager.Secret(
        "usda-api-key-secret",
        secret_id=SECRET_USDA_API_KEY,
        replication=gcp.secretmanager.SecretReplicationArgs(
            auto=gcp.secretmanager.SecretReplicationAutoArgs(),
        ),
        opts=secret_opts,
    )

    # Google Maps API key (version added manually post-deploy)
    google_maps_api_key_secret = gcp.secretmanager.Secret(
        "google-maps-api-key-secret",
        secret_id=SECRET_GOOGLE_MAPS_API_KEY,
        replication=gcp.secretmanager.SecretReplicationArgs(
            auto=gcp.secretmanager.SecretReplicationAutoArgs(),
        ),
        opts=secret_opts,
    )

    # Prefect server auth credential (HTTP Basic Auth)
    prefect_auth_password = random.RandomPassword(
        "prefect-auth-password",
        length=32,
        special=False,
    )

    prefect_auth_secret = gcp.secretmanager.Secret(
        "prefect-auth-secret",
        secret_id=SECRET_PREFECT_AUTH,
        replication=gcp.secretmanager.SecretReplicationArgs(
            auto=gcp.secretmanager.SecretReplicationAutoArgs(),
        ),
        opts=secret_opts,
    )

    gcp.secretmanager.SecretVersion(
        "prefect-auth-version",
        secret=prefect_auth_secret.id,
        secret_data=pulumi.Output.concat("admin:", prefect_auth_password.result),
    )

    # Read-only users
    readonly_users = {}
    readonly_passwords = {}
    readonly_secrets = {}

    for username in READONLY_USERS:
        # Generate password for read-only user
        ro_password = random.RandomPassword(
            f"ro-password-{username}",
            length=32,
            special=False,
        )
        readonly_passwords[username] = ro_password

        # Create the Cloud SQL user
        ro_user = gcp.sql.User(
            f"ro-user-{username}",
            name=username,
            instance=sql.instance.name,
            password=ro_password.result,
            deletion_policy="ABANDON",
        )
        readonly_users[username] = ro_user

        # Store password in Secret Manager
        ro_secret = gcp.secretmanager.Secret(
            f"ro-password-secret-{username}",
            secret_id=f"{SECRET_RO_PREFIX}-{username}",
            replication=gcp.secretmanager.SecretReplicationArgs(
                auto=gcp.secretmanager.SecretReplicationAutoArgs(),
            ),
            opts=secret_opts,
        )
        readonly_secrets[username] = ro_secret

        gcp.secretmanager.SecretVersion(
            f"ro-password-version-{username}",
            secret=ro_secret.id,
            secret_data=ro_password.result,
        )

    # Postgres superuser password
    postgres_password = random.RandomPassword(
        "postgres-password",
        length=32,
        special=False,
    )

    # Manage the built-in postgres user (Pulumi will adopt the existing user)
    postgres_user = gcp.sql.User(
        "postgres-user",
        name="postgres",
        instance=sql.instance.name,
        password=postgres_password.result,
        deletion_policy="ABANDON",
    )

    # Store the postgres password in Secret Manager
    postgres_password_secret = gcp.secretmanager.Secret(
        "postgres-password-secret",
        secret_id=SECRET_POSTGRES_PASSWORD,
        replication=gcp.secretmanager.SecretReplicationArgs(
            auto=gcp.secretmanager.SecretReplicationAutoArgs(),
        ),
        opts=secret_opts,
    )

    gcp.secretmanager.SecretVersion(
        "postgres-password-version",
        secret=postgres_password_secret.id,
        secret_data=postgres_password.result,
    )

    # JWT signing secret for webservice authentication
    jwt_secret = random.RandomPassword("jwt-secret-key", length=64, special=False)

    jwt_secret_sm = gcp.secretmanager.Secret(
        "jwt-secret",
        secret_id=SECRET_JWT_KEY,
        replication=gcp.secretmanager.SecretReplicationArgs(
            auto=gcp.secretmanager.SecretReplicationAutoArgs(),
        ),
        opts=secret_opts,
    )

    gcp.secretmanager.SecretVersion(
        "jwt-secret-version",
        secret=jwt_secret_sm.id,
        secret_data=jwt_secret.result,
    )

    # Admin user password for webservice API authentication
    admin_password = random.RandomPassword(
        "admin-password", length=32, special=False
    )

    admin_password_sm = gcp.secretmanager.Secret(
        "admin-password-secret",
        secret_id=SECRET_ADMIN_PASSWORD,
        replication=gcp.secretmanager.SecretReplicationArgs(
            auto=gcp.secretmanager.SecretReplicationAutoArgs(),
        ),
        opts=secret_opts,
    )

    gcp.secretmanager.SecretVersion(
        "admin-password-version",
        secret=admin_password_sm.id,
        secret_data=admin_password.result,
    )

    # OAuth2-proxy: Google OAuth client ID (version added manually post-deploy)
    oauth2_client_id_secret = gcp.secretmanager.Secret(
        "oauth2-client-id-secret",
        secret_id=SECRET_OAUTH2_CLIENT_ID,
        replication=gcp.secretmanager.SecretReplicationArgs(
            auto=gcp.secretmanager.SecretReplicationAutoArgs(),
        ),
        opts=secret_opts,
    )

    # OAuth2-proxy: Google OAuth client secret (version added manually post-deploy)
    oauth2_client_secret_secret = gcp.secretmanager.Secret(
        "oauth2-client-secret-secret",
        secret_id=SECRET_OAUTH2_CLIENT_SECRET,
        replication=gcp.secretmanager.SecretReplicationArgs(
            auto=gcp.secretmanager.SecretReplicationAutoArgs(),
        ),
        opts=secret_opts,
    )

    # OAuth2-proxy: cookie encryption secret (auto-generated)
    oauth2_cookie_secret = random.RandomPassword(
        "oauth2-cookie-secret",
        length=32,
        special=False,
    )

    oauth2_cookie_secret_sm = gcp.secretmanager.Secret(
        "oauth2-cookie-secret-sm",
        secret_id=SECRET_OAUTH2_COOKIE_SECRET,
        replication=gcp.secretmanager.SecretReplicationArgs(
            auto=gcp.secretmanager.SecretReplicationAutoArgs(),
        ),
        opts=secret_opts,
    )

    gcp.secretmanager.SecretVersion(
        "oauth2-cookie-secret-version",
        secret=oauth2_cookie_secret_sm.id,
        secret_data=oauth2_cookie_secret.result,
    )

    resources = SecretResources(
        db_password=db_password,
        db_user=db_user,
        db_password_secret=db_password_secret,
        gsheets_secret=gsheets_secret,
        usda_api_key_secret=usda_api_key_secret,
        google_maps_api_key_secret=google_maps_api_key_secret,
        prefect_auth_password=prefect_auth_password,
        prefect_auth_secret=prefect_auth_secret,
        readonly_users=readonly_users,
        readonly_passwords=readonly_passwords,
        readonly_secrets=readonly_secrets,
        postgres_password=postgres_password,
        postgres_user=postgres_user,
        postgres_password_secret=postgres_password_secret,
        jwt_secret=jwt_secret,
        jwt_secret_sm=jwt_secret_sm,
        admin_password=admin_password,
        admin_password_sm=admin_password_sm,
        oauth2_client_id_secret=oauth2_client_id_secret,
        oauth2_client_secret_secret=oauth2_client_secret_secret,
        oauth2_cookie_secret=oauth2_cookie_secret,
        oauth2_cookie_secret_sm=oauth2_cookie_secret_sm,
    )
    grant_dashboards_publisher_readonly_secret_access(
        resources,
        service_accounts=service_accounts,
    )
    return resources
