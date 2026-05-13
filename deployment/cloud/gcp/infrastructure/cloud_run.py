"""Cloud Run Services and Jobs."""

from dataclasses import dataclass
from typing import Sequence

import pulumi
import pulumi_gcp as gcp

from config import (
    GCP_REGION,
    WEBSERVICE_IMAGE,
    PIPELINE_IMAGE,
    PREFECT_SERVER_IMAGE,
    OAUTH2_PROXY_IMAGE,
    PREFECT_WORK_POOL_NAME,
    DB_USER,
    DB_NAME,
    PREFECT_DB_NAME,
    LANDIQ_SHAPEFILE_URL,
    CORS_ORIGINS,
    CR_WEBSERVICE_NAME,
    CR_MIGRATION_JOB_NAME,
    CR_SEED_ADMIN_JOB_NAME,
    CR_PREFECT_SERVER_NAME,
    CR_PREFECT_WORKER_NAME,
    CR_OAUTH2_PROXY_NAME,
    OAUTH2_PROXY_EMAIL_DOMAIN,
)
from cloud_sql import CloudSQLResources
from secret_manager import SecretResources
from iam import IAMResources


@dataclass
class CloudRunResources:
    webservice: gcp.cloudrunv2.Service
    migration_job: gcp.cloudrunv2.Job
    seed_admin_job: gcp.cloudrunv2.Job
    prefect_server: gcp.cloudrunv2.Service
    prefect_worker: gcp.cloudrunv2.Service
    oauth2_proxy: gcp.cloudrunv2.Service


def create_cloud_run_resources(
    sql: CloudSQLResources,
    secrets: SecretResources,
    iam: IAMResources,
    depends_on: Sequence[pulumi.Resource] | None = None,
) -> CloudRunResources:
    """Create all Cloud Run Services and Jobs."""
    run_opts = pulumi.ResourceOptions(depends_on=depends_on or [])

    # --- 5.2: FastAPI Webservice ---
    # Secrets are mounted as volumes (not value_source env vars) because the
    # GCP Cloud Run v2 API rejects the Terraform provider's serialization of
    # env vars with value_source (sends both value="" and valueSource, violating
    # the protobuf oneof).  A shell wrapper reads secret files into env vars.
    webservice = gcp.cloudrunv2.Service(
        "webservice",
        name=CR_WEBSERVICE_NAME,
        location=GCP_REGION,
        deletion_protection=False,
        ingress="INGRESS_TRAFFIC_ALL",
        template=gcp.cloudrunv2.ServiceTemplateArgs(
            service_account=iam.service_accounts["webservice"].email,
            scaling=gcp.cloudrunv2.ServiceTemplateScalingArgs(
                min_instance_count=0,
                max_instance_count=10,
            ),
            containers=[
                gcp.cloudrunv2.ServiceTemplateContainerArgs(
                    image=WEBSERVICE_IMAGE,
                    # Override default CMD to inject secret env vars from mounted files
                    args=[
                        "sh", "-c",
                        "export DB_PASS=$(cat /secrets/db-password/value) "
                        "&& export API_JWT_SECRET_KEY=$(cat /secrets/jwt-secret/value) "
                        "&& exec uvicorn ca_biositing.webservice.main:app "
                        "--host 0.0.0.0 --port 8080",
                    ],
                    ports=gcp.cloudrunv2.ServiceTemplateContainerPortsArgs(
                        container_port=8080,
                    ),
                    resources=gcp.cloudrunv2.ServiceTemplateContainerResourcesArgs(
                        limits={"cpu": "1", "memory": "512Mi"},
                        cpu_idle=False,
                        startup_cpu_boost=True,
                    ),
                    envs=[
                        gcp.cloudrunv2.ServiceTemplateContainerEnvArgs(
                            name="DB_USER",
                            value=DB_USER,
                        ),
                        # App config uses POSTGRES_DB when INSTANCE_CONNECTION_NAME is set
                        gcp.cloudrunv2.ServiceTemplateContainerEnvArgs(
                            name="POSTGRES_DB",
                            value=DB_NAME,
                        ),
                        gcp.cloudrunv2.ServiceTemplateContainerEnvArgs(
                            name="INSTANCE_CONNECTION_NAME",
                            value=sql.instance.connection_name,
                        ),
                        gcp.cloudrunv2.ServiceTemplateContainerEnvArgs(
                            name="API_JWT_COOKIE_SECURE",
                            value="true",
                        ),
                        *(
                            [gcp.cloudrunv2.ServiceTemplateContainerEnvArgs(
                                name="API_CORS_ORIGINS",
                                value=CORS_ORIGINS,
                            )]
                            if CORS_ORIGINS
                            else []
                        ),
                    ],
                    volume_mounts=[
                        gcp.cloudrunv2.ServiceTemplateContainerVolumeMountArgs(
                            name="cloudsql",
                            mount_path="/cloudsql",
                        ),
                        gcp.cloudrunv2.ServiceTemplateContainerVolumeMountArgs(
                            name="db-password",
                            mount_path="/secrets/db-password",
                        ),
                        gcp.cloudrunv2.ServiceTemplateContainerVolumeMountArgs(
                            name="jwt-secret",
                            mount_path="/secrets/jwt-secret",
                        ),
                    ],
                    # Cloud Run v2 supports startup_probe and liveness_probe only.
                    # Readiness probes are not available in the Cloud Run v2 API.
                    # The startup probe uses HTTP GET /health to gate traffic until
                    # the database is reachable (replaces the original TCP check).
                    startup_probe=gcp.cloudrunv2.ServiceTemplateContainerStartupProbeArgs(
                        http_get=gcp.cloudrunv2.ServiceTemplateContainerStartupProbeHttpGetArgs(
                            path="/health",
                            port=8080,
                        ),
                        timeout_seconds=10,
                        period_seconds=10,
                        failure_threshold=30,
                    ),
                    liveness_probe=gcp.cloudrunv2.ServiceTemplateContainerLivenessProbeArgs(
                        http_get=gcp.cloudrunv2.ServiceTemplateContainerLivenessProbeHttpGetArgs(
                            path="/",
                            port=8080,
                        ),
                        timeout_seconds=10,
                        period_seconds=30,
                        failure_threshold=3,
                    ),
                )
            ],
            volumes=[
                gcp.cloudrunv2.ServiceTemplateVolumeArgs(
                    name="cloudsql",
                    cloud_sql_instance=gcp.cloudrunv2.ServiceTemplateVolumeCloudSqlInstanceArgs(
                        instances=[sql.instance.connection_name],
                    ),
                ),
                gcp.cloudrunv2.ServiceTemplateVolumeArgs(
                    name="db-password",
                    secret=gcp.cloudrunv2.ServiceTemplateVolumeSecretArgs(
                        secret=secrets.db_password_secret.name,
                        items=[gcp.cloudrunv2.ServiceTemplateVolumeSecretItemArgs(
                            version="latest", path="value",
                        )],
                    ),
                ),
                gcp.cloudrunv2.ServiceTemplateVolumeArgs(
                    name="jwt-secret",
                    secret=gcp.cloudrunv2.ServiceTemplateVolumeSecretArgs(
                        secret=secrets.jwt_secret_sm.name,
                        items=[gcp.cloudrunv2.ServiceTemplateVolumeSecretItemArgs(
                            version="latest", path="value",
                        )],
                    ),
                ),
            ],
        ),
        traffics=[
            gcp.cloudrunv2.ServiceTrafficArgs(
                type="TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST",
                percent=100,
            )
        ],
        opts=run_opts,
    )

    gcp.cloudrunv2.ServiceIamMember(
        "webservice-public-access",
        name=webservice.name,
        location=GCP_REGION,
        role="roles/run.invoker",
        member="allUsers",
    )

    # --- 5.3: Alembic Migration Job ---
    migration_job = gcp.cloudrunv2.Job(
        "migration-job",
        name=CR_MIGRATION_JOB_NAME,
        location=GCP_REGION,
        deletion_protection=False,
        template=gcp.cloudrunv2.JobTemplateArgs(
            template=gcp.cloudrunv2.JobTemplateTemplateArgs(
                max_retries=1,
                timeout="600s",
                service_account=iam.service_accounts["migrate"].email,
                containers=[
                    gcp.cloudrunv2.JobTemplateTemplateContainerArgs(
                        image=PIPELINE_IMAGE,
                        args=[
                            "sh", "-c",
                            "export DB_PASS=$(cat /secrets/db-password/value) "
                            "&& exec alembic upgrade head",
                        ],
                        resources=gcp.cloudrunv2.JobTemplateTemplateContainerResourcesArgs(
                            limits={"cpu": "1", "memory": "512Mi"},
                        ),
                        envs=[
                            gcp.cloudrunv2.JobTemplateTemplateContainerEnvArgs(
                                name="DB_USER",
                                value=DB_USER,
                            ),
                            gcp.cloudrunv2.JobTemplateTemplateContainerEnvArgs(
                                name="POSTGRES_DB",
                                value=DB_NAME,
                            ),
                            gcp.cloudrunv2.JobTemplateTemplateContainerEnvArgs(
                                name="INSTANCE_CONNECTION_NAME",
                                value=sql.instance.connection_name,
                            ),
                        ],
                        volume_mounts=[
                            gcp.cloudrunv2.JobTemplateTemplateContainerVolumeMountArgs(
                                name="cloudsql",
                                mount_path="/cloudsql",
                            ),
                            gcp.cloudrunv2.JobTemplateTemplateContainerVolumeMountArgs(
                                name="db-password",
                                mount_path="/secrets/db-password",
                            ),
                        ],
                    )
                ],
                volumes=[
                    gcp.cloudrunv2.JobTemplateTemplateVolumeArgs(
                        name="cloudsql",
                        cloud_sql_instance=gcp.cloudrunv2.JobTemplateTemplateVolumeCloudSqlInstanceArgs(
                            instances=[sql.instance.connection_name],
                        ),
                    ),
                    gcp.cloudrunv2.JobTemplateTemplateVolumeArgs(
                        name="db-password",
                        secret=gcp.cloudrunv2.JobTemplateTemplateVolumeSecretArgs(
                            secret=secrets.db_password_secret.name,
                            items=[gcp.cloudrunv2.JobTemplateTemplateVolumeSecretItemArgs(
                                version="latest", path="value",
                            )],
                        ),
                    ),
                ],
            )
        ),
        opts=run_opts,
    )

    # --- 5.3b: Admin User Seed Job ---
    seed_admin_job = gcp.cloudrunv2.Job(
        "seed-admin-job",
        name=CR_SEED_ADMIN_JOB_NAME,
        location=GCP_REGION,
        deletion_protection=False,
        template=gcp.cloudrunv2.JobTemplateArgs(
            template=gcp.cloudrunv2.JobTemplateTemplateArgs(
                max_retries=1,
                timeout="120s",
                service_account=iam.service_accounts["migrate"].email,
                containers=[
                    gcp.cloudrunv2.JobTemplateTemplateContainerArgs(
                        image=WEBSERVICE_IMAGE,
                        args=[
                            "sh", "-c",
                            "export DB_PASS=$(cat /secrets/db-password/value) "
                            "&& export ADMIN_PASSWORD=$(cat /secrets/admin-password/value) "
                            "&& exec python scripts/create_admin.py --username admin",
                        ],
                        resources=gcp.cloudrunv2.JobTemplateTemplateContainerResourcesArgs(
                            limits={"cpu": "1", "memory": "512Mi"},
                        ),
                        envs=[
                            gcp.cloudrunv2.JobTemplateTemplateContainerEnvArgs(
                                name="DB_USER",
                                value=DB_USER,
                            ),
                            gcp.cloudrunv2.JobTemplateTemplateContainerEnvArgs(
                                name="POSTGRES_DB",
                                value=DB_NAME,
                            ),
                            gcp.cloudrunv2.JobTemplateTemplateContainerEnvArgs(
                                name="INSTANCE_CONNECTION_NAME",
                                value=sql.instance.connection_name,
                            ),
                        ],
                        volume_mounts=[
                            gcp.cloudrunv2.JobTemplateTemplateContainerVolumeMountArgs(
                                name="cloudsql",
                                mount_path="/cloudsql",
                            ),
                            gcp.cloudrunv2.JobTemplateTemplateContainerVolumeMountArgs(
                                name="db-password",
                                mount_path="/secrets/db-password",
                            ),
                            gcp.cloudrunv2.JobTemplateTemplateContainerVolumeMountArgs(
                                name="admin-password",
                                mount_path="/secrets/admin-password",
                            ),
                        ],
                    )
                ],
                volumes=[
                    gcp.cloudrunv2.JobTemplateTemplateVolumeArgs(
                        name="cloudsql",
                        cloud_sql_instance=gcp.cloudrunv2.JobTemplateTemplateVolumeCloudSqlInstanceArgs(
                            instances=[sql.instance.connection_name],
                        ),
                    ),
                    gcp.cloudrunv2.JobTemplateTemplateVolumeArgs(
                        name="db-password",
                        secret=gcp.cloudrunv2.JobTemplateTemplateVolumeSecretArgs(
                            secret=secrets.db_password_secret.name,
                            items=[gcp.cloudrunv2.JobTemplateTemplateVolumeSecretItemArgs(
                                version="latest", path="value",
                            )],
                        ),
                    ),
                    gcp.cloudrunv2.JobTemplateTemplateVolumeArgs(
                        name="admin-password",
                        secret=gcp.cloudrunv2.JobTemplateTemplateVolumeSecretArgs(
                            secret=secrets.admin_password_sm.name,
                            items=[gcp.cloudrunv2.JobTemplateTemplateVolumeSecretItemArgs(
                                version="latest", path="value",
                            )],
                        ),
                    ),
                ],
            )
        ),
        opts=run_opts,
    )

    # --- 5.4: Self-hosted Prefect Server ---
    prefect_db_url = pulumi.Output.all(
        password=secrets.db_password.result,
        connection_name=sql.instance.connection_name,
    ).apply(
        lambda args: (
            f"postgresql+asyncpg://{DB_USER}:{args['password']}"
            f"@/{PREFECT_DB_NAME}?host=/cloudsql/{args['connection_name']}"
        )
    )

    prefect_server = gcp.cloudrunv2.Service(
        "prefect-server",
        name=CR_PREFECT_SERVER_NAME,
        location=GCP_REGION,
        deletion_protection=False,
        ingress="INGRESS_TRAFFIC_INTERNAL_ONLY",
        template=gcp.cloudrunv2.ServiceTemplateArgs(
            service_account=iam.service_accounts["prefect-server"].email,
            scaling=gcp.cloudrunv2.ServiceTemplateScalingArgs(
                min_instance_count=1,
                max_instance_count=1,
            ),
            containers=[
                gcp.cloudrunv2.ServiceTemplateContainerArgs(
                    image=PREFECT_SERVER_IMAGE,
                    commands=[
                        "prefect",
                        "server",
                        "start",
                        "--host",
                        "0.0.0.0",
                        "--port",
                        "4200",
                    ],
                    ports=gcp.cloudrunv2.ServiceTemplateContainerPortsArgs(
                        container_port=4200,
                    ),
                    resources=gcp.cloudrunv2.ServiceTemplateContainerResourcesArgs(
                        limits={"cpu": "1", "memory": "1Gi"},
                    ),
                    envs=[
                        gcp.cloudrunv2.ServiceTemplateContainerEnvArgs(
                            name="PREFECT_API_DATABASE_CONNECTION_URL",
                            value=prefect_db_url,
                        ),
                        gcp.cloudrunv2.ServiceTemplateContainerEnvArgs(
                            name="PREFECT_SERVER_API_HOST",
                            value="0.0.0.0",
                        ),
                        gcp.cloudrunv2.ServiceTemplateContainerEnvArgs(
                            name="PREFECT_SERVER_API_PORT",
                            value="4200",
                        ),
                        gcp.cloudrunv2.ServiceTemplateContainerEnvArgs(
                            name="PREFECT_UI_API_URL",
                            value="/api",
                        ),
                    ],
                    volume_mounts=[
                        gcp.cloudrunv2.ServiceTemplateContainerVolumeMountArgs(
                            name="cloudsql",
                            mount_path="/cloudsql",
                        )
                    ],
                    startup_probe=gcp.cloudrunv2.ServiceTemplateContainerStartupProbeArgs(
                        http_get=gcp.cloudrunv2.ServiceTemplateContainerStartupProbeHttpGetArgs(
                            path="/api/health",
                            port=4200,
                        ),
                        initial_delay_seconds=30,
                        period_seconds=10,
                        failure_threshold=10,
                    ),
                    liveness_probe=gcp.cloudrunv2.ServiceTemplateContainerLivenessProbeArgs(
                        http_get=gcp.cloudrunv2.ServiceTemplateContainerLivenessProbeHttpGetArgs(
                            path="/api/health",
                            port=4200,
                        ),
                    ),
                )
            ],
            volumes=[
                gcp.cloudrunv2.ServiceTemplateVolumeArgs(
                    name="cloudsql",
                    cloud_sql_instance=gcp.cloudrunv2.ServiceTemplateVolumeCloudSqlInstanceArgs(
                        instances=[sql.instance.connection_name],
                    ),
                )
            ],
        ),
        traffics=[
            gcp.cloudrunv2.ServiceTrafficArgs(
                type="TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST",
                percent=100,
            )
        ],
        opts=run_opts,
    )

    gcp.cloudrunv2.ServiceIamMember(
        "prefect-server-public-access",
        name=prefect_server.name,
        location=GCP_REGION,
        role="roles/run.invoker",
        member="allUsers",
    )

    # --- 5.5: Prefect Worker (process type) ---
    # Uses the pipeline image so flows run as subprocesses with all ETL deps.
    prefect_api_url = prefect_server.uri.apply(lambda uri: f"{uri}/api")

    prefect_worker = gcp.cloudrunv2.Service(
        "prefect-worker",
        name=CR_PREFECT_WORKER_NAME,
        location=GCP_REGION,
        deletion_protection=False,
        ingress="INGRESS_TRAFFIC_INTERNAL_ONLY",
        template=gcp.cloudrunv2.ServiceTemplateArgs(
            service_account=iam.service_accounts["prefect-worker"].email,
            scaling=gcp.cloudrunv2.ServiceTemplateScalingArgs(
                min_instance_count=1,  # Must stay at 1: worker polls for jobs
                max_instance_count=1,
            ),
            vpc_access=gcp.cloudrunv2.ServiceTemplateVpcAccessArgs(
                egress="ALL_TRAFFIC",
                network_interfaces=[
                    gcp.cloudrunv2.ServiceTemplateVpcAccessNetworkInterfaceArgs(
                        network="default",
                        subnetwork="default",
                    )
                ],
            ),
            containers=[
                gcp.cloudrunv2.ServiceTemplateContainerArgs(
                    image=PIPELINE_IMAGE,
                    # No commands= — use Dockerfile ENTRYPOINT (/bin/bash /shell-hook.sh)
                    args=[
                        "sh", "-c",
                        "export DB_PASS=$(cat /secrets/db-password/value) "
                        "&& export USDA_NASS_API_KEY=$(cat /secrets/usda-api-key/value) "
                        "&& export GOOGLE_MAPS_API_KEY=$(cat /secrets/google-maps-api-key/value) "
                        f"&& exec prefect worker start "
                        f"--pool {PREFECT_WORK_POOL_NAME} "
                        f"--type process --limit 3 --with-healthcheck",
                    ],
                    ports=gcp.cloudrunv2.ServiceTemplateContainerPortsArgs(
                        container_port=8080,
                    ),
                    resources=gcp.cloudrunv2.ServiceTemplateContainerResourcesArgs(
                        limits={"cpu": "2", "memory": "2Gi"},
                    ),
                    envs=[
                        gcp.cloudrunv2.ServiceTemplateContainerEnvArgs(
                            name="PREFECT_API_URL",
                            value=prefect_api_url,
                        ),
                        gcp.cloudrunv2.ServiceTemplateContainerEnvArgs(
                            name="PREFECT_WORK_POOL_NAME",
                            value=PREFECT_WORK_POOL_NAME,
                        ),
                        gcp.cloudrunv2.ServiceTemplateContainerEnvArgs(
                            name="DB_USER",
                            value=DB_USER,
                        ),
                        gcp.cloudrunv2.ServiceTemplateContainerEnvArgs(
                            name="POSTGRES_DB",
                            value=DB_NAME,
                        ),
                        gcp.cloudrunv2.ServiceTemplateContainerEnvArgs(
                            name="INSTANCE_CONNECTION_NAME",
                            value=sql.instance.connection_name,
                        ),
                        # Path to GSheets service account credentials file (mounted via Secret Manager volume)
                        gcp.cloudrunv2.ServiceTemplateContainerEnvArgs(
                            name="CREDENTIALS_PATH",
                            value="/app/gsheets-credentials/credentials.json",
                        ),
                        # Standard GCP ADC env var; also used by gspread/pydrive2 libraries
                        gcp.cloudrunv2.ServiceTemplateContainerEnvArgs(
                            name="GOOGLE_APPLICATION_CREDENTIALS",
                            value="/app/gsheets-credentials/credentials.json",
                        ),
                        # HTTP URL to download LandIQ shapefile at runtime
                        gcp.cloudrunv2.ServiceTemplateContainerEnvArgs(
                            name="LANDIQ_SHAPEFILE_URL",
                            value=LANDIQ_SHAPEFILE_URL,
                        ),
                    ],
                    volume_mounts=[
                        gcp.cloudrunv2.ServiceTemplateContainerVolumeMountArgs(
                            name="cloudsql",
                            mount_path="/cloudsql",
                        ),
                        # GSheets credentials file mounted from Secret Manager
                        gcp.cloudrunv2.ServiceTemplateContainerVolumeMountArgs(
                            name="gsheets-credentials",
                            mount_path="/app/gsheets-credentials",
                        ),
                        gcp.cloudrunv2.ServiceTemplateContainerVolumeMountArgs(
                            name="db-password",
                            mount_path="/secrets/db-password",
                        ),
                        gcp.cloudrunv2.ServiceTemplateContainerVolumeMountArgs(
                            name="usda-api-key",
                            mount_path="/secrets/usda-api-key",
                        ),
                        gcp.cloudrunv2.ServiceTemplateContainerVolumeMountArgs(
                            name="google-maps-api-key",
                            mount_path="/secrets/google-maps-api-key",
                        ),
                    ],
                    startup_probe=gcp.cloudrunv2.ServiceTemplateContainerStartupProbeArgs(
                        tcp_socket=gcp.cloudrunv2.ServiceTemplateContainerStartupProbeTcpSocketArgs(
                            port=8080,
                        ),
                        initial_delay_seconds=15,
                        period_seconds=10,
                        failure_threshold=30,
                    ),
                )
            ],
            volumes=[
                gcp.cloudrunv2.ServiceTemplateVolumeArgs(
                    name="cloudsql",
                    cloud_sql_instance=gcp.cloudrunv2.ServiceTemplateVolumeCloudSqlInstanceArgs(
                        instances=[sql.instance.connection_name],
                    ),
                ),
                # Secret Manager volume for GSheets service account credentials
                gcp.cloudrunv2.ServiceTemplateVolumeArgs(
                    name="gsheets-credentials",
                    secret=gcp.cloudrunv2.ServiceTemplateVolumeSecretArgs(
                        secret=secrets.gsheets_secret.name,
                        items=[
                            gcp.cloudrunv2.ServiceTemplateVolumeSecretItemArgs(
                                version="latest",
                                path="credentials.json",
                            )
                        ],
                    ),
                ),
                gcp.cloudrunv2.ServiceTemplateVolumeArgs(
                    name="db-password",
                    secret=gcp.cloudrunv2.ServiceTemplateVolumeSecretArgs(
                        secret=secrets.db_password_secret.name,
                        items=[gcp.cloudrunv2.ServiceTemplateVolumeSecretItemArgs(
                            version="latest", path="value",
                        )],
                    ),
                ),
                gcp.cloudrunv2.ServiceTemplateVolumeArgs(
                    name="usda-api-key",
                    secret=gcp.cloudrunv2.ServiceTemplateVolumeSecretArgs(
                        secret=secrets.usda_api_key_secret.name,
                        items=[gcp.cloudrunv2.ServiceTemplateVolumeSecretItemArgs(
                            version="latest", path="value",
                        )],
                    ),
                ),
                gcp.cloudrunv2.ServiceTemplateVolumeArgs(
                    name="google-maps-api-key",
                    secret=gcp.cloudrunv2.ServiceTemplateVolumeSecretArgs(
                        secret=secrets.google_maps_api_key_secret.name,
                        items=[gcp.cloudrunv2.ServiceTemplateVolumeSecretItemArgs(
                            version="latest", path="value",
                        )],
                    ),
                ),
            ],
        ),
        traffics=[
            gcp.cloudrunv2.ServiceTrafficArgs(
                type="TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST",
                percent=100,
            )
        ],
        opts=run_opts,
    )

    # --- 5.6: OAuth2-Proxy (fronts Prefect Server for browser auth) ---
    # Authenticates browser users via Google OAuth before forwarding to Prefect server.
    # The Prefect worker connects directly to the server (internal traffic), bypassing this proxy.
    # Secrets are mounted as volumes (not value_source env vars) because the
    # GCP Cloud Run v2 API rejects the Terraform provider's serialization of
    # env vars with value_source (sends both value="" and valueSource, violating
    # the protobuf oneof).  A shell wrapper reads secret files into env vars.
    # Uses the Alpine image (not distroless) so we have a shell for the wrapper.
    oauth2_proxy_command = prefect_server.uri.apply(
        lambda uri: [
            "sh", "-c",
            "export OAUTH2_PROXY_CLIENT_ID=$(cat /secrets/oauth2-client-id/value) "
            "&& export OAUTH2_PROXY_CLIENT_SECRET=$(cat /secrets/oauth2-client-secret/value) "
            "&& export OAUTH2_PROXY_COOKIE_SECRET=$(cat /secrets/oauth2-cookie-secret/value) "
            "&& exec oauth2-proxy"
            " --provider=google"
            f" --email-domain={OAUTH2_PROXY_EMAIL_DOMAIN}"
            " --reverse-proxy=true"
            " --cookie-secure=true"
            " --cookie-refresh=1h"
            " --skip-auth-route=GET=^/api/health$"
            " --http-address=0.0.0.0:4180"
            " --upstream-timeout=120s"
            f" --upstream={uri}"
            " --skip-provider-button=true",
        ]
    )

    oauth2_proxy = gcp.cloudrunv2.Service(
        "oauth2-proxy",
        name=CR_OAUTH2_PROXY_NAME,
        location=GCP_REGION,
        deletion_protection=False,
        ingress="INGRESS_TRAFFIC_ALL",
        template=gcp.cloudrunv2.ServiceTemplateArgs(
            service_account=iam.service_accounts["oauth2-proxy"].email,
            scaling=gcp.cloudrunv2.ServiceTemplateScalingArgs(
                min_instance_count=0,
                max_instance_count=2,
            ),
            vpc_access=gcp.cloudrunv2.ServiceTemplateVpcAccessArgs(
                egress="ALL_TRAFFIC",
                network_interfaces=[
                    gcp.cloudrunv2.ServiceTemplateVpcAccessNetworkInterfaceArgs(
                        network="default",
                        subnetwork="default",
                    )
                ],
            ),
            containers=[
                gcp.cloudrunv2.ServiceTemplateContainerArgs(
                    image=OAUTH2_PROXY_IMAGE,
                    commands=oauth2_proxy_command,
                    ports=gcp.cloudrunv2.ServiceTemplateContainerPortsArgs(
                        container_port=4180,
                    ),
                    resources=gcp.cloudrunv2.ServiceTemplateContainerResourcesArgs(
                        limits={"cpu": "1", "memory": "512Mi"},
                        startup_cpu_boost=True,
                    ),
                    envs=[
                        gcp.cloudrunv2.ServiceTemplateContainerEnvArgs(
                            name="OAUTH2_PROXY_PASS_HOST_HEADER",
                            value="false",
                        ),
                        gcp.cloudrunv2.ServiceTemplateContainerEnvArgs(
                            name="OAUTH2_PROXY_SET_XAUTHREQUEST",
                            value="true",
                        ),
                    ],
                    volume_mounts=[
                        gcp.cloudrunv2.ServiceTemplateContainerVolumeMountArgs(
                            name="oauth2-client-id",
                            mount_path="/secrets/oauth2-client-id",
                        ),
                        gcp.cloudrunv2.ServiceTemplateContainerVolumeMountArgs(
                            name="oauth2-client-secret",
                            mount_path="/secrets/oauth2-client-secret",
                        ),
                        gcp.cloudrunv2.ServiceTemplateContainerVolumeMountArgs(
                            name="oauth2-cookie-secret",
                            mount_path="/secrets/oauth2-cookie-secret",
                        ),
                    ],
                    startup_probe=gcp.cloudrunv2.ServiceTemplateContainerStartupProbeArgs(
                        http_get=gcp.cloudrunv2.ServiceTemplateContainerStartupProbeHttpGetArgs(
                            path="/ping",
                            port=4180,
                        ),
                        period_seconds=10,
                        failure_threshold=10,
                    ),
                    liveness_probe=gcp.cloudrunv2.ServiceTemplateContainerLivenessProbeArgs(
                        http_get=gcp.cloudrunv2.ServiceTemplateContainerLivenessProbeHttpGetArgs(
                            path="/ping",
                            port=4180,
                        ),
                    ),
                )
            ],
            volumes=[
                gcp.cloudrunv2.ServiceTemplateVolumeArgs(
                    name="oauth2-client-id",
                    secret=gcp.cloudrunv2.ServiceTemplateVolumeSecretArgs(
                        secret=secrets.oauth2_client_id_secret.name,
                        items=[gcp.cloudrunv2.ServiceTemplateVolumeSecretItemArgs(
                            version="latest", path="value",
                        )],
                    ),
                ),
                gcp.cloudrunv2.ServiceTemplateVolumeArgs(
                    name="oauth2-client-secret",
                    secret=gcp.cloudrunv2.ServiceTemplateVolumeSecretArgs(
                        secret=secrets.oauth2_client_secret_secret.name,
                        items=[gcp.cloudrunv2.ServiceTemplateVolumeSecretItemArgs(
                            version="latest", path="value",
                        )],
                    ),
                ),
                gcp.cloudrunv2.ServiceTemplateVolumeArgs(
                    name="oauth2-cookie-secret",
                    secret=gcp.cloudrunv2.ServiceTemplateVolumeSecretArgs(
                        secret=secrets.oauth2_cookie_secret_sm.name,
                        items=[gcp.cloudrunv2.ServiceTemplateVolumeSecretItemArgs(
                            version="latest", path="value",
                        )],
                    ),
                ),
            ],
        ),
        traffics=[
            gcp.cloudrunv2.ServiceTrafficArgs(
                type="TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST",
                percent=100,
            )
        ],
        opts=run_opts,
    )

    gcp.cloudrunv2.ServiceIamMember(
        "oauth2-proxy-public-access",
        name=oauth2_proxy.name,
        location=GCP_REGION,
        role="roles/run.invoker",
        member="allUsers",
    )

    return CloudRunResources(
        webservice=webservice,
        migration_job=migration_job,
        seed_admin_job=seed_admin_job,
        prefect_server=prefect_server,
        prefect_worker=prefect_worker,
        oauth2_proxy=oauth2_proxy,
    )
