# AGENTS.md - Resources Directory

This file provides guidance to AI assistants when working with the `resources/`
directory of the ca-biositing repository.

## Directory Overview

The `resources/` directory contains deployment resources for running the
ca-biositing ETL pipeline in a containerized, orchestrated environment. This
directory is separate from the source code and provides the infrastructure layer
for development and deployment.

**Key Purpose**: Container orchestration and workflow management configuration

**Technologies**:

- Docker & Docker Compose for containerization
- Prefect for workflow orchestration
- PostgreSQL for data and metadata storage
- Pixi for Python environment management (within containers)

## Cross-Cutting Documentation

This directory uses project-wide patterns documented in:

| Topic           | Document                                                  | When to Reference                   |
| --------------- | --------------------------------------------------------- | ----------------------------------- |
| Docker Workflow | [docker-workflow.md](../.agents/rules/docker-workflow.md) | Docker commands, service management |
| Troubleshooting | [troubleshooting.md](../.agents/rules/troubleshooting.md) | Common errors and solutions         |

## Directory Structure

```text
resources/
├── docker/                          # Docker orchestration
│   ├── .dockerignore                # Docker build exclusions
│   ├── .env                         # Local environment config (git-ignored)
│   ├── .env.example                 # Environment template
│   ├── create_prefect_db.sql        # Prefect DB initialization
│   ├── docker-compose.yml           # Service orchestration
│   └── pipeline.dockerfile          # Multi-stage production Dockerfile
└── prefect/                         # Prefect configuration
    ├── deploy.py                    # Deployment automation script
    ├── prefect.yaml                 # Flow deployment definitions
    └── run_prefect_flow.py          # Master flow orchestration
```

## Docker Resources (`resources/docker/`)

### Key Files

**docker-compose.yml**

- **Purpose**: Orchestrates all services (database, Prefect server, worker,
  setup)
- **Services**:
  - `db`: PostgreSQL 13 container
  - `setup-db`: One-time Alembic migration runner
  - `prefect-server`: Prefect orchestration server
  - `prefect-worker`: Prefect worker for executing flows
- **Networks**: `prefect-network` bridge for inter-container communication
- **Volumes**: `pgdata` (PostgreSQL), `prefectdata` (Prefect metadata)
- **Key Feature**: Health checks ensure services start in correct order

**pipeline.dockerfile**

- **Purpose**: Multi-stage build for production-ready containers
- **Stage 1 (build)**: Uses Pixi to install dependencies in `etl` environment
- **Stage 2 (production)**: Minimal Ubuntu image with only runtime dependencies
- **Key Feature**: Creates shell-hook script for environment activation
- **Optimization**: No Pixi binary needed in production container

**create_prefect_db.sql**

- **Purpose**: Initializes `prefect_db` database for Prefect server
- **Behavior**: Idempotent (safe to run multiple times)
- **Execution**: Auto-runs on first container start via
  `/docker-entrypoint-initdb.d/`

**.env.example**

- **Purpose**: Template for environment configuration
- **Critical Variables**:
  - `POSTGRES_*`: Database connection parameters
  - `DATABASE_URL`: Application database connection string
  - `PREFECT_API_DATABASE_CONNECTION_URL`: Prefect metadata DB
  - `PREFECT_API_URL`: Prefect server endpoint

### Docker Workflow Commands

**ALWAYS use Pixi tasks from the project root directory:**

```bash
# Start all services
pixi run start-services

# Stop services
pixi run teardown-services

# Stop and remove volumes (CAUTION: deletes all data)
pixi run teardown-services-volumes

# View logs
pixi run service-logs

# Rebuild after code/dependency changes
pixi run rebuild-services

# Restart all services
pixi run restart-services

# Check service status
pixi run service-status

# Execute command in Prefect worker container
pixi run exec-prefect-worker <command>

# Execute command in database container
pixi run exec-db <command>
```

### Common Docker Operations

**Running Alembic Migrations (locally, not in container):**

```bash
# Apply migrations
pixi run migrate

# Auto-generate new migration from model changes
pixi run migrate-autogenerate -m "description"

# Refresh materialized views
pixi run refresh-views
```

**Accessing Database:**

```bash
# PostgreSQL application database
pixi run access-db

# Prefect metadata database
pixi run access-prefect-db
```

**Inspecting Services:**

```bash
# Check service status
pixi run service-status

# Check database health
pixi run check-db-health

# Check container health with docker inspect
docker inspect BioCirV_ETL_db | grep -A 5 Health
```

## Prefect Resources (`resources/prefect/`)

### Key Files

**prefect.yaml**

- **Purpose**: Declares Prefect deployments for version control
- **Structure**:
  - `name`: Project identifier (ca-biositing-pipeline)
  - `prefect-version`: Compatibility tracking (3.4.23)
  - `pull`: Working directory setup for workers
  - `deployments`: List of flow deployment configurations
- **Current Deployments**:
  - `master-etl-deployment`: Orchestrates all ETL flows
- **Workflow**: Commit this file to git, deploy via `prefect deploy`

**deploy.py**

- **Purpose**: Automated deployment script with retry logic
- **Features**:
  - Loads environment from `.env` file
  - Retries failed deployments (e.g., if server not ready)
  - Uses `prefect --no-prompt deploy` for non-interactive deployment
- **Usage**: `python deploy.py <deployment-name>`
- **Exit Codes**: 0 on success, 1 on .env file not found

**run_prefect_flow.py**

- **Purpose**: Master flow that orchestrates all ETL sub-flows
- **Structure**:
  - `AVAILABLE_FLOWS`: Dictionary mapping flow names to functions
  - `master_flow()`: Prefect flow that runs all sub-flows sequentially
- **Key Feature**: Single entry point for all ETL pipelines
- **Extensibility**: Add new flows by importing and registering in
  `AVAILABLE_FLOWS`

## Adding New ETL Flows

**Step-by-Step Process:**

1. **Create flow module**: `src/ca_biositing/pipeline/flows/new_flow.py`

2. **Import in master flow**: Edit `resources/prefect/run_prefect_flow.py`

   ```python
   from ca_biositing.pipeline.flows.new_flow import new_flow

   AVAILABLE_FLOWS = {
       "primary_product": primary_product_flow,
       "analysis_type": analysis_type_flow,
       "new_flow": new_flow,  # Add here
   }
   ```

3. **Define deployment** (optional): Edit `resources/prefect/prefect.yaml`

   ```yaml
   deployments:
     - name: new-flow-deployment
       tags: ["etl", "new"]
       description: Description of new flow
       entrypoint: run_prefect_flow.py:new_flow
       work_pool:
         name: biocirv_dev_work_pool
   ```

4. **Deploy**:
   ```bash
   pixi run deploy
   ```

## Environment Configuration

### Creating .env File

**ALWAYS create from template:**

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

## Development Patterns

### Testing Flow Changes

**Recommended approach:**

1. **Make changes** to flow code in `src/ca_biositing/pipeline/flows/`
2. **Rebuild container** (if dependencies changed):
   ```bash
   pixi run rebuild-services
   ```
3. **Restart services**:
   ```bash
   pixi run restart-services
   ```
4. **Test directly** (skip deployment):
   ```bash
   pixi run exec-prefect-worker python -c 'from ca_biositing.pipeline.flows.your_flow import your_flow; your_flow()'
   ```
5. **Deploy when ready**:
   ```bash
   pixi run deploy
   ```

### Inspecting Container State

```bash
# List files in container
pixi run exec-prefect-worker ls -la /app

# Check Python environment
pixi run exec-prefect-worker /bin/bash -c "source /shell-hook.sh && python --version"

# Interactive shell
pixi run exec-prefect-worker /bin/bash
```

## Architecture Decisions

### Why Multi-Stage Dockerfile?

- **Build stage**: Full Pixi toolchain for dependency resolution
- **Production stage**: Minimal runtime (only Python + dependencies)
- **Benefits**: Smaller images, faster deployments, better security

### Why Separate Prefect Server and Worker?

- **Server**: Manages orchestration, API, UI
- **Worker**: Executes flow code
- **Benefits**: Scalability (multiple workers), isolation, failure resilience

### Why Docker Compose for Development?

- **Simplicity**: Single command to start all services
- **Consistency**: Same environment across team members
- **Completeness**: Database + orchestration + workers

**For production**, consider:

- Kubernetes for orchestration
- Managed PostgreSQL (RDS, Cloud SQL)
- Prefect Cloud for hosted server

## Integration with Main Project

### Relationship to Source Code

- **Source code**: Lives in `src/ca_biositing/`
- **Docker resources**: Lives in `resources/docker/`
- **Prefect resources**: Lives in `resources/prefect/`

**Dockerfile build context**: Project root (allows access to all source code)

**Volume mounts** (development):

- Flow code: Mounted for hot-reloading
- Alembic scripts: Mounted for migrations
- Credentials: Mounted from project root

### Pixi Environment Integration

**Within containers**, Pixi manages Python environment:

1. **Build stage**: `pixi install -e etl` installs dependencies
2. **Production stage**: Copies installed environment
3. **Runtime**: Shell-hook script activates environment

**Outside containers** (local development):

- Use Pixi directly: `pixi run <task>`
- See main [/AGENTS.md](../AGENTS.md) for Pixi workflows

## Best Practices

### When to Rebuild Containers

**Rebuild required**:

- Adding/removing Python dependencies (`pixi add/remove`)
- Changing Dockerfile
- Updating base images
- Modifying build-time configurations

**Rebuild NOT required**:

- Changing flow code (with volume mounts)
- Updating `.env` file
- Modifying `prefect.yaml`

### Logging and Debugging

**View all logs**:

```bash
pixi run service-logs
```

**Increase Prefect logging**: Set in `.env`:

```bash
PREFECT_LOGGING_LEVEL=DEBUG
```

Then restart services:

```bash
pixi run restart-services
```

### Security Considerations

**Development** (current setup):

- Uses `.env` file for secrets
- Credentials mounted as volumes
- Services exposed on localhost only

**Production recommendations**:

- Use secrets management (AWS Secrets Manager, HashiCorp Vault)
- Implement TLS/SSL for all connections
- Use service accounts with minimal permissions
- Don't expose ports publicly
- Enable audit logging

## Related Documentation

**Pipeline Documentation** (`src/ca_biositing/pipeline/docs/`):

- `PREFECT_WORKFLOW.md`: Detailed Prefect usage guide
- `DOCKER_WORKFLOW.md`: Docker development workflows
- `ETL_WORKFLOW.md`: ETL development patterns
- `ALEMBIC_WORKFLOW.md`: Database migration guide
- `GCP_SETUP.md`: Google Cloud credentials setup

**Main Project Documentation**:

- [/AGENTS.md](../AGENTS.md): Main AI assistant guidance
- [/.agents/rules/](../.agents/rules/): Cross-cutting documentation
- `src/ca_biositing/pipeline/AGENTS.md`: Pipeline-specific guidance
