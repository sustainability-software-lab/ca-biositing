"""Stack configuration and project constants."""

import os

from pulumi import automation as auto

# Project and stack settings
PROJECT_NAME = "ca-biositing-infrastructure"
STACK_NAME = os.environ.get("DEPLOY_ENV", "staging")
BACKEND_URL = "gs://biocirv-470318-pulumi-state"

# GCP settings
GCP_PROJECT = "biocirv-470318"
GCP_REGION = "us-west1"

# GitHub repository (org/repo) for Workload Identity Federation
GITHUB_REPO = "sustainability-software-lab/ca-biositing"

# Cloud SQL
DB_INSTANCE_NAME = f"biocirv-{STACK_NAME}"
DB_NAME = f"biocirv-{STACK_NAME}"
PREFECT_DB_NAME = "prefect"
PREFECT_WORK_POOL_NAME = f"biocirv-{STACK_NAME}-pool"
DB_USER = "biocirv_user"

# Storage
IMAGE_BUCKET_NAME = f"biocirv-{STACK_NAME}-bucket"
BACKUP_BUCKET_NAME = f"biocirv-{STACK_NAME}-backups"
GASIFICATION_BUCKET_NAME = f"biocirv-{STACK_NAME}-gasification-data"

# Read-only users
READONLY_USERS = ["biocirv_readonly"]

# Cloud Run service/job names
CR_WEBSERVICE_NAME = f"biocirv-{STACK_NAME}-webservice"
CR_MIGRATION_JOB_NAME = f"biocirv-{STACK_NAME}-migrate"
CR_SEED_ADMIN_JOB_NAME = f"biocirv-{STACK_NAME}-seed-admin"
CR_PREFECT_SERVER_NAME = f"biocirv-{STACK_NAME}-prefect-server"
CR_PREFECT_WORKER_NAME = f"biocirv-{STACK_NAME}-prefect-worker"
CR_OAUTH2_PROXY_NAME = f"biocirv-{STACK_NAME}-prefect-auth"
OAUTH2_PROXY_EMAIL_DOMAIN = "lbl.gov"

# Secret Manager secret IDs
SECRET_DB_PASSWORD = f"biocirv-{STACK_NAME}-db-password"
SECRET_GSHEETS = f"biocirv-{STACK_NAME}-gsheets-credentials"
SECRET_USDA_API_KEY = f"biocirv-{STACK_NAME}-usda-nass-api-key"
SECRET_PREFECT_AUTH = f"biocirv-{STACK_NAME}-prefect-auth"
SECRET_POSTGRES_PASSWORD = f"biocirv-{STACK_NAME}-postgres-password"
SECRET_JWT_KEY = f"biocirv-{STACK_NAME}-jwt-secret-key"
SECRET_ADMIN_PASSWORD = f"biocirv-{STACK_NAME}-admin-password"
SECRET_RO_PREFIX = f"biocirv-{STACK_NAME}-ro"
SECRET_OAUTH2_CLIENT_ID = f"biocirv-{STACK_NAME}-oauth2-client-id"
SECRET_OAUTH2_CLIENT_SECRET = f"biocirv-{STACK_NAME}-oauth2-client-secret"
SECRET_OAUTH2_COOKIE_SECRET = f"biocirv-{STACK_NAME}-oauth2-cookie-secret"
SECRET_GOOGLE_MAPS_API_KEY = f"biocirv-{STACK_NAME}-google-maps-api-key"

# Service account IDs (GCP limit: 30 chars)
# "production" is abbreviated to "prod" to stay within the limit.
_sa_env = "prod" if STACK_NAME == "production" else STACK_NAME
SA_WEBSERVICE = f"biocirv-{_sa_env}-cr-websvc"
SA_PREFECT_SERVER = f"biocirv-{_sa_env}-cr-prefect"
SA_PREFECT_WORKER = f"biocirv-{_sa_env}-cr-worker"
SA_MIGRATE = f"biocirv-{_sa_env}-cr-migrate"
SA_DEPLOYER = f"biocirv-{_sa_env}-gh-deploy"
SA_OAUTH2_PROXY = f"biocirv-{_sa_env}-cr-pfct-auth"
SA_FRONTEND = f"biocirv-{_sa_env}-cr-frontend"

# Workload Identity Federation IDs
WIF_POOL_ID = f"github-actions-{STACK_NAME}"
WIF_PROVIDER_ID = f"github-oidc-{STACK_NAME}"

# CORS origins for webservice (JSON array string for Cloud Run env var)
CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "")

# Container images — override with env vars to use digest/commit-based tags
# instead of :latest (which Pulumi cannot detect changes for).
# Images are pulled via an Artifact Registry remote repo that proxies GHCR.
AR_GHCR_BASE = f"us-west1-docker.pkg.dev/{GCP_PROJECT}/ghcr-proxy/sustainability-software-lab/ca-biositing"
AR_QUAYIO_BASE = f"us-west1-docker.pkg.dev/{GCP_PROJECT}/quayio-proxy"
OAUTH2_PROXY_IMAGE = f"{AR_QUAYIO_BASE}/oauth2-proxy/oauth2-proxy:v7.7.1-alpine"
IMAGE_TAG = os.environ.get("IMAGE_TAG", "latest")
WEBSERVICE_IMAGE = os.environ.get(
    "WEBSERVICE_IMAGE", f"{AR_GHCR_BASE}/webservice:{IMAGE_TAG}"
)
PIPELINE_IMAGE = os.environ.get(
    "PIPELINE_IMAGE", f"{AR_GHCR_BASE}/pipeline:{IMAGE_TAG}"
)
PREFECT_SERVER_IMAGE = os.environ.get(
    "PREFECT_SERVER_IMAGE", "prefecthq/prefect:3-python3.12"
)

# LandIQ shapefile URL for Cloud Run (2023 provisional crop mapping dataset)
LANDIQ_SHAPEFILE_URL = os.environ.get(
    "LANDIQ_SHAPEFILE_URL",
    "https://data.cnra.ca.gov/dataset/6c3d65e3-35bb-49e1-a51e-49d5a2cf09a9/resource/25d0f174-4bec-4987-a402-602cd1372786/download/i15_crop_mapping_2023_provisional.zip",
)


def configure_stack(stack: auto.Stack) -> None:
    """Set all stack configuration programmatically."""
    stack.set_config("gcp:project", auto.ConfigValue(GCP_PROJECT))
    stack.set_config("gcp:region", auto.ConfigValue(GCP_REGION))
