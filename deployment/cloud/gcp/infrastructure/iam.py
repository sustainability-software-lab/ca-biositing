"""Service accounts and IAM role bindings."""

from dataclasses import dataclass
from typing import Sequence

import pulumi
import pulumi_gcp as gcp

from config import (
    GCP_PROJECT,
    STACK_NAME,
    SA_WEBSERVICE,
    SA_PREFECT_SERVER,
    SA_PREFECT_WORKER,
    SA_MIGRATE,
    SA_OAUTH2_PROXY,
    SA_FRONTEND,
    SA_DASHBOARDS_PUBLISHER,
    SA_DASHBOARDS_READER,
)


@dataclass
class IAMResources:
    service_accounts: dict


# Service account definitions: (logical_name, account_id, display_name, roles)
SA_DEFINITIONS = [
    (
        "webservice",
        SA_WEBSERVICE,
        "Webservice Cloud Run SA",
        [
            "roles/cloudsql.client",
            "roles/secretmanager.secretAccessor",
        ],
    ),
    (
        "prefect-server",
        SA_PREFECT_SERVER,
        "Prefect Server Cloud Run SA",
        [
            "roles/cloudsql.client",
            "roles/secretmanager.secretAccessor",
        ],
    ),
    (
        "prefect-worker",
        SA_PREFECT_WORKER,
        "Prefect Worker Cloud Run SA",
        [
            "roles/cloudsql.client",
            "roles/secretmanager.secretAccessor",
            "roles/storage.objectAdmin",
        ],
    ),
    (
        "migrate",
        SA_MIGRATE,
        "Migration Cloud Run SA",
        [
            "roles/cloudsql.client",
            "roles/secretmanager.secretAccessor",
        ],
    ),
    (
        "oauth2-proxy",
        SA_OAUTH2_PROXY,
        "OAuth2-Proxy Cloud Run SA",
        [
            "roles/secretmanager.secretAccessor",
        ],
    ),
    (
        "frontend",
        SA_FRONTEND,
        "Cal BioScape Frontend Cloud Run SA",
        [
            "roles/secretmanager.secretAccessor",
        ],
    ),
    (
        "dashboards-publisher",
        SA_DASHBOARDS_PUBLISHER,
        f"BioCirV Dashboards Publisher ({STACK_NAME})",
        [],
    ),
    (
        "dashboards-reader",
        SA_DASHBOARDS_READER,
        f"BioCirV Dashboards Reader ({STACK_NAME})",
        [],
    ),
]


def create_service_accounts(
    depends_on: Sequence[pulumi.Resource] | None = None,
) -> IAMResources:
    """Create service accounts and IAM role bindings."""
    service_accounts = {}
    opts = pulumi.ResourceOptions(depends_on=depends_on or [])

    for logical_name, account_id, display_name, roles in SA_DEFINITIONS:
        sa = gcp.serviceaccount.Account(
            f"sa-{logical_name}",
            account_id=account_id,
            display_name=display_name,
            opts=opts,
        )
        service_accounts[logical_name] = sa

        for role in roles:
            role_short = role.split("/")[-1]
            gcp.projects.IAMMember(
                f"sa-{logical_name}-{role_short}",
                project=GCP_PROJECT,
                role=role,
                member=sa.email.apply(lambda email: f"serviceAccount:{email}"),
            )

    return IAMResources(service_accounts=service_accounts)
