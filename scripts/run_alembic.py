#!/usr/bin/env python
"""
Wrapper that loads credentials from resources/docker/.env (without copying
them into any source file), adjusts POSTGRES_HOST to localhost for running
alembic from the host machine, then exec's alembic with the provided args.

Usage (called by pixi tasks):
    python scripts/run_alembic.py upgrade head
    python scripts/run_alembic.py revision --autogenerate -m "msg"
"""

import os
import sys
import subprocess
from pathlib import Path
from dotenv import dotenv_values

PROJECT_ROOT = Path(__file__).parent.parent.resolve()

# Load variables from resources/docker/.env with shell-style interpolation.
# This file is git-ignored and is the single source of truth for credentials.
docker_env_path = PROJECT_ROOT / "resources" / "docker" / ".env"
if not docker_env_path.exists():
    print(
        f"ERROR: {docker_env_path} not found. "
        "Copy resources/docker/.env.example to resources/docker/.env and fill in your credentials.",
        file=sys.stderr,
    )
    sys.exit(1)

env_vars = dotenv_values(docker_env_path, interpolate=True)

# Merge into process environment (process env takes precedence so that
# DATABASE_URL set externally is always honoured).
for key, value in env_vars.items():
    if key not in os.environ:
        os.environ[key] = value or ""

# For local development (running alembic from the host machine rather than
# inside Docker) the database host must be 'localhost', not 'db'.
database_url = os.environ.get("DATABASE_URL", "")
if "@db:" in database_url:
    os.environ["DATABASE_URL"] = database_url.replace("@db:", "@localhost:")

# Exec alembic with the forwarded arguments.
result = subprocess.run(["alembic"] + sys.argv[1:])
sys.exit(result.returncode)
