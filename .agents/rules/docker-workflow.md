# Docker Workflow

**Load when:** starting, stopping, rebuilding, or inspecting the Docker services
(PostgreSQL, Prefect server and worker), or deploying and running ETL flows.

The ETL pipeline runs in Docker containers orchestrated by Prefect. Docker is
managed through **Pixi tasks** - never use docker-compose commands directly.

## Prerequisites

Docker and Docker Compose are included as Pixi dependencies:

```bash
# Verify Docker is available through Pixi
pixi run which docker
pixi run which docker-compose
```

## Docker Services

The `docker-compose.yml` defines these services:

| Service          | Description                       | Port |
| ---------------- | --------------------------------- | ---- |
| `db`             | PostgreSQL 13 database            | 5432 |
| `setup-db`       | One-time Alembic migration runner | -    |
| `prefect-server` | Prefect orchestration server      | 4200 |
| `prefect-worker` | Prefect worker for flow execution | -    |

### Service Details

**PostgreSQL (`db`):**

- Hosts both application and Prefect databases
- Port 5432, persistent volumes
- Health checks enabled
- Volumes: `pgdata` for data persistence

**Database Setup (`setup-db`):**

- One-time Alembic migrations
- Runs on startup, waits for DB health
- Uses `alembic upgrade head`

**Prefect Server (`prefect-server`):**

- Orchestration UI/API on port 4200
- Stores workflow metadata
- Manages work pools and flow deployments
- Access at: <http://0.0.0.0:4200>

**Prefect Worker (`prefect-worker`):**

- Executes scheduled/triggered flows
- Process-based task execution
- Access to credentials and application database
- Volumes: Flow code, credentials, Alembic scripts

## Service Management

**ALWAYS use Pixi tasks for Docker operations:**

### Starting and Stopping

```bash
# Start all services (PostgreSQL, Prefect server, Prefect worker)
pixi run start-services

# Stop services (keeps volumes)
pixi run teardown-services

# Stop and remove volumes (CAUTION: deletes all data)
pixi run teardown-services-volumes

# Restart all services
pixi run restart-services
```

### Monitoring

```bash
# Check service status
pixi run service-status

# View logs from all services
pixi run service-logs

# Monitor via Prefect UI
open http://0.0.0.0:4200
```

### Database Operations

```bash
# Check database health
pixi run check-db-health

# Access application database (psql shell)
pixi run access-db

# Access Prefect metadata database (psql shell)
pixi run access-prefect-db
```

### Advanced Operations

```bash
# Rebuild Docker images (after dependency changes)
pixi run rebuild-services

# Execute commands in Prefect worker container
pixi run exec-prefect-worker <command>

# Execute commands in database container
pixi run exec-db <command>

# Restart just the Prefect worker
pixi run restart-prefect-worker
```

## ETL Operations

```bash
# Deploy Prefect flows
pixi run deploy

# Run the ETL pipeline
pixi run run-etl
```

### Deploying Flows

```bash
# Deploy using the pipeline deploy task (recommended)
pixi run deploy

# Deploy directly with prefect CLI (in container)
pixi run exec-prefect-worker prefect deploy
```

### Running Flows

```bash
# Trigger master flow via deployment (recommended)
pixi run run-etl

# Run flow directly for testing (bypasses deployment)
pixi run exec-prefect-worker python -c 'from run_prefect_flow import master_flow; master_flow()'
```

### Monitoring Flows

```bash
# Access Prefect UI
open http://0.0.0.0:4200

# Check work pools
pixi run exec-prefect-worker prefect work-pool ls

# View flow runs
pixi run exec-prefect-worker prefect flow-run ls
```

## Alembic Migrations

```bash
# Apply migrations (runs automatically via setup-db service)
pixi run exec-prefect-worker alembic upgrade head

# Generate new migration
pixi run exec-prefect-worker alembic revision --autogenerate -m "description"

# Check migration history
pixi run exec-prefect-worker alembic history

# Downgrade one migration
pixi run exec-prefect-worker alembic downgrade -1
```

## Environment Configuration

### Creating .env File

```bash
cd resources/docker
cp .env.example .env
# Edit .env with your specific values
```

**NEVER commit `.env` to git** - it contains sensitive credentials.

### Required Environment Variables

**Database Connection:**

- `POSTGRES_HOST`: Database host (use `db` for Docker)
- `POSTGRES_USER`: Database username
- `POSTGRES_DB`: Application database name
- `POSTGRES_PASSWORD`: Database password
- `POSTGRES_PORT`: Database port (5432 default)
- `DATABASE_URL`: Full SQLAlchemy connection string

**Prefect Configuration:**

- `PREFECT_API_URL`: Prefect server endpoint
- `PREFECT_SERVER_API_HOST`: Server bind address
- `PREFECT_UI_API_URL`: UI API endpoint
- `PREFECT_API_DATABASE_CONNECTION_URL`: Prefect metadata DB connection

## When to Rebuild

**Rebuild required:**

- Adding/removing Python dependencies (`pixi add/remove`)
- Changing Dockerfile
- Updating base images
- Modifying build-time configurations

```bash
pixi run rebuild-services
pixi run start-services
```

**Rebuild NOT required:**

- Changing flow code (with volume mounts)
- Updating `.env` file (restart instead)
- Modifying `prefect.yaml` (redeploy instead)

```bash
# For .env changes
pixi run restart-services

# For prefect.yaml changes
pixi run deploy
```

## Volume Management

**Persistent volumes** retain data across container restarts:

- `pgdata`: PostgreSQL data files
- `prefectdata`: Prefect metadata and artifacts

**To reset state** (CAUTION: deletes all data):

```bash
pixi run teardown-services-volumes
pixi run start-services
```

## Inspecting Container State

```bash
# List files in container
pixi run exec-prefect-worker ls -la /app

# Check Python environment
pixi run exec-prefect-worker /bin/bash -c "source /shell-hook.sh && python --version"

# Interactive shell
pixi run exec-prefect-worker /bin/bash

# Check installed packages
pixi run exec-prefect-worker pip list
```

## Adding Dependencies

**For ETL Pipeline (Docker):**

Pipeline dependencies are managed via Pixi's `etl` environment feature. When you
add dependencies, they are automatically included in Docker builds:

```bash
# Add PyPI package to pipeline feature
pixi add --feature pipeline --pypi <package-name>

# Rebuild Docker images
pixi run rebuild-services

# Restart services
pixi run start-services
```

## Service Health Checks

**Database not ready:**

```bash
# Check PostgreSQL health
pixi run check-db-health
# Expected output: "accepting connections"
```

**Prefect server not responding:**

```bash
# Check server health endpoint
curl -f http://0.0.0.0:4200/api/health
# Expected output: HTTP 200 OK
```

**Check container health with docker inspect:**

```bash
docker inspect BioCirV_ETL_db | grep -A 5 Health
```

## Common Workflows

### Full Reset (Development)

```bash
# Stop everything and remove data
pixi run teardown-services-volumes

# Rebuild images
pixi run rebuild-services

# Start fresh
pixi run start-services

# Deploy flows
pixi run deploy

# Run ETL
pixi run run-etl
```

### After Code Changes

```bash
# If only flow code changed (volume mounted)
# No action needed - changes picked up automatically

# If dependencies changed
pixi run rebuild-services
pixi run restart-services
pixi run deploy
```

### After .env Changes

```bash
pixi run restart-services
```

### Debugging Flow Issues

```bash
# View all logs
pixi run service-logs

# Check worker specifically
docker logs BioCirV_ETL_prefect-worker

# Interactive debugging
pixi run exec-prefect-worker /bin/bash
# Then run Python commands manually
```

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Docker Network                            │
│                   (prefect-network)                          │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │     db       │  │prefect-server│  │prefect-worker│       │
│  │ PostgreSQL   │  │   Port 4200  │  │  Flow Exec   │       │
│  │              │  │              │  │              │       │
│  │ - biocirv_db │◄─┤   Prefect    │◄─┤   Prefect    │       │
│  │ - prefect_db │  │     API      │  │    Agent     │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
│         ▲                                    │               │
│         │                                    │               │
│         └────────────────────────────────────┘               │
│                    Database Connections                      │
└─────────────────────────────────────────────────────────────┘
```

## Related Documentation

- **Resources AGENTS.md**: [/resources/AGENTS.md](../../resources/AGENTS.md) -
  Prefect deployment specifics
- **Docker Workflow Guide**: `docs/pipeline/DOCKER_WORKFLOW.md`
- **Prefect Workflow Guide**: `docs/pipeline/PREFECT_WORKFLOW.md`
- **Alembic Workflow Guide**: `docs/pipeline/ALEMBIC_WORKFLOW.md`
