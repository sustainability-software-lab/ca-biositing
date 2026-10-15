# CA Biositing Analytics - Agent Handoff for Laboratory Data Visualization

## CRITICAL: Read This First

**ALWAYS start by reading these files for codebase best practices:**

- [`AGENTS.md`](../../../AGENTS.md) - Repository overview, build system,
  pathing, common pitfalls
- [`.agents/rules/namespace-packages.md`](../../../.agents/rules/namespace-packages.md) -
  PEP 420 structure and import patterns
- [`.agents/rules/docker-workflow.md`](../../../.agents/rules/docker-workflow.md) -
  Docker/Pixi service commands
- [`.agents/rules/troubleshooting.md`](../../../.agents/rules/troubleshooting.md) -
  Common pitfalls and solutions

**Build System:** This project uses **Pixi** for environment management. ALWAYS
use `pixi run` commands, never conda/pip directly.

## Project Context

### Analytics Goal

Create visualizations to understand the relationships between:

- **Crops** (biomass resources/primary agricultural products)
- **Preprocessing Methods** (sample preparation techniques)
- **Analytical Techniques** (laboratory analysis methods)

Focus on **AIM 1** laboratory analyses which represent the core experimental
data.

### Current Branch

`usda_etl_feat` - Contains analytical data and database infrastructure

## Database Schema Overview

### Key Tables & Relationships

#### 1. Crops/Biomass Resources

- **`resource`** - Primary biomass resource definitions
- **`primary_ag_product`** - Agricultural product classifications
- **`resource_usda_commodity_map`** - Links resources to USDA commodity
  classifications

#### 2. Sample Preparation

- **`preparation_method`** - Methods like drying, grinding, sieving
- **`prepared_sample`** - Samples that have undergone preparation
- **Key Fields:** `name`, `description`, `prep_temp_c`, `drying_step`

#### 3. Analytical Techniques

- **`analysis_type`** - Categories of analytical techniques
- **`experiment_analysis`** - Links experiments to analysis types
- **AIM 1 Analysis Tables:**
  - `proximate_record` - Proximate analysis (moisture, ash, volatiles)
  - `ultimate_record` - Ultimate analysis (C, H, N, S, O)
  - `compositional_record` - Compositional analysis
  - `icp_record` - ICP-OES elemental analysis
  - `xrf_record` - X-ray fluorescence
  - `xrd_record` - X-ray diffraction
  - `calorimetry_record` - Heat content analysis
  - `ftnir_record` - FTIR spectroscopy
  - `rgb_record` - Color analysis

#### 4. Core Relationships

```
resource -> prepared_sample -> aim1_record_base -> [specific_analysis_record]
         \-> analysis_type -> experiment_analysis
```

## Database Access Patterns

### Essential Setup Commands

```bash
# Environment setup
pixi install

# Start database services
pixi run start-services

# Check service health
pixi run service-status

# Apply migrations if needed
pixi run migrate
```

### Database Connection

```python
from ca_biositing.datamodels.database import get_session_local
from ca_biositing.datamodels.schemas.generated.ca_biositing import (
    Resource, PrimaryAgProduct, PreparationMethod, AnalysisType,
    Aim1RecordBase, ProximateRecord, UltimateRecord, CompositionalRecord
)

# Get database session
SessionLocal = get_session_local()
session = SessionLocal()

# Example queries (always close session!)
try:
    resources = session.query(Resource).all()
    analysis_types = session.query(AnalysisType).all()
finally:
    session.close()
```

### Database URL Configuration

- **Local Development:**
  `postgresql://biocirv_user:biocirv_dev_password@localhost:5432/biocirv_db`
- **Docker:** Services run on `localhost:5432` when accessed from host

## Key Analysis Queries

### 1. Crops and Preprocessing Methods

```sql
SELECT
    r.name as crop_name,
    pm.name as prep_method,
    pm.prep_temp_c,
    pm.drying_step,
    COUNT(*) as sample_count
FROM resource r
JOIN prepared_sample ps ON r.id = ps.resource_id
JOIN preparation_method pm ON ps.prep_method_id = pm.id
GROUP BY r.name, pm.name, pm.prep_temp_c, pm.drying_step;
```

### 2. Analysis Types by Crop

```sql
SELECT
    r.name as crop_name,
    at.name as analysis_type,
    COUNT(*) as analysis_count
FROM resource r
JOIN prepared_sample ps ON r.id = ps.resource_id
JOIN aim1_record_base arb ON ps.id = arb.prepared_sample_id
JOIN experiment_analysis ea ON arb.experiment_id = ea.experiment_id
JOIN analysis_type at ON ea.analysis_type_id = at.id
GROUP BY r.name, at.name;
```

### 3. Preprocessing → Analysis Pipeline

```sql
SELECT
    r.name as crop_name,
    pm.name as prep_method,
    at.name as analysis_type,
    COUNT(*) as pipeline_count
FROM resource r
JOIN prepared_sample ps ON r.id = ps.resource_id
JOIN preparation_method pm ON ps.prep_method_id = pm.id
JOIN aim1_record_base arb ON ps.id = arb.prepared_sample_id
JOIN experiment_analysis ea ON arb.experiment_id = ea.experiment_id
JOIN analysis_type at ON ea.analysis_type_id = at.id
GROUP BY r.name, pm.name, at.name
ORDER BY crop_name, prep_method, analysis_type;
```

## Data Access via Python

### Using SQLAlchemy Models

```python
from ca_biositing.datamodels.database import get_session_local
from ca_biositing.datamodels.schemas.generated.ca_biositing import *
import pandas as pd

SessionLocal = get_session_local()

def get_crop_analysis_pipeline():
    """Get crop → preprocessing → analysis pipeline data."""
    session = SessionLocal()
    try:
        query = session.query(
            Resource.name.label('crop_name'),
            PreparationMethod.name.label('prep_method'),
            AnalysisType.name.label('analysis_type')
        ).select_from(Resource)\
         .join(PreparedSample, Resource.id == PreparedSample.resource_id)\
         .join(PreparationMethod, PreparedSample.prep_method_id == PreparationMethod.id)\
         .join(Aim1RecordBase, PreparedSample.id == Aim1RecordBase.prepared_sample_id)\
         .join(ExperimentAnalysis, Aim1RecordBase.experiment_id == ExperimentAnalysis.experiment_id)\
         .join(AnalysisType, ExperimentAnalysis.analysis_type_id == AnalysisType.id)

        return pd.read_sql(query.statement, session.bind)
    finally:
        session.close()
```

### Using Direct SQL with pandas

```python
import pandas as pd
from ca_biositing.datamodels.database import get_engine

def get_analytical_data_summary():
    """Get summary of analytical data for visualization."""
    engine = get_engine()

    query = """
    SELECT
        r.name as crop_name,
        pm.name as prep_method,
        pm.prep_temp_c,
        pm.drying_step,
        at.name as analysis_type,
        COUNT(*) as record_count
    FROM resource r
    JOIN prepared_sample ps ON r.id = ps.resource_id
    JOIN preparation_method pm ON ps.prep_method_id = pm.id
    JOIN aim1_record_base arb ON ps.id = arb.prepared_sample_id
    JOIN experiment_analysis ea ON arb.experiment_id = ea.experiment_id
    JOIN analysis_type at ON ea.analysis_type_id = at.id
    GROUP BY r.name, pm.name, pm.prep_temp_c, pm.drying_step, at.name
    ORDER BY crop_name, prep_method, analysis_type;
    """

    return pd.read_sql(query, engine)
```

## API Access (Alternative to Direct Database)

### REST API Endpoints

```python
import requests

# Check available endpoints
api_base = "http://localhost:8000/v1"

# Get resources (crops)
resources = requests.get(f"{api_base}/resources").json()

# Get analysis types
analysis_types = requests.get(f"{api_base}/analysis_types").json()

# Get experiments with analysis data
experiments = requests.get(f"{api_base}/experiments").json()
```

### Start API Server

```bash
pixi run start-webservice
# API available at http://localhost:8000
# Interactive docs at http://localhost:8000/docs
```

## Visualization Recommendations

### 1. Sankey Diagram

**Best for:** Showing flow from crops → preprocessing → analysis

```python
import plotly.graph_objects as go

# Create nodes: [crops, prep_methods, analysis_types]
# Create links: crop→prep, prep→analysis with thickness = count
```

### 2. Heatmap Matrix

**Best for:** Crop vs Analysis Type frequency

```python
import seaborn as sns
import matplotlib.pyplot as plt

# Pivot table: crops as rows, analysis_types as columns, count as values
pivot_data = df.pivot_table(
    index='crop_name',
    columns='analysis_type',
    values='record_count',
    fill_value=0
)
sns.heatmap(pivot_data, annot=True, cmap='YlOrRd')
```

### 3. Network Graph

**Best for:** Complex multi-way relationships

```python
import networkx as nx
import matplotlib.pyplot as plt

# Create graph: crops→prep_methods→analysis_types
G = nx.DiGraph()
# Add nodes and edges based on pipeline data
```

### 4. Interactive Dashboard

**Best for:** Exploratory analysis

```python
import plotly.dash as dash
import plotly.express as px

# Dropdown filters for crops, prep methods
# Dynamic charts updating based on selections
```

## Essential Files for Analytics

### Schema Definitions

- `resources/linkml/modules/aim1_records/` - AIM 1 analysis record schemas
- `resources/linkml/modules/sample_preparation/` - Preprocessing method schemas
- `resources/linkml/modules/resource_information/` - Crop/biomass schemas

### Generated Models

- `src/ca_biositing/datamodels/schemas/generated/ca_biositing.py` - SQLAlchemy
  models

### Database Access

- `src/ca_biositing/datamodels/database.py` - Database connection utilities
- `src/ca_biositing/webservice/` - REST API for data access

### Documentation

- `src/ca_biositing/webservice/API_DOCUMENTATION.md` - API endpoint
  documentation

## Common Pitfalls ⚠️

### Database Issues

- **Empty tables:** Run full ETL to populate data:
  `cd resources/prefect && pixi run python -c "from run_prefect_flow import master_flow; master_flow()"`
- **Connection errors:** Ensure services running with `pixi run service-status`
- **Schema changes:** Use `pixi run migrate` for database updates

### Import Issues

- **Module not found:** Always use `pixi run python script.py` instead of direct
  Python
- **Namespace packages:** Follow absolute import patterns from AGENTS.md
- **SQLAlchemy imports:** Import models from
  `ca_biositing.datamodels.schemas.generated.ca_biositing`

### Data Access Patterns

- **Always close sessions:** Use try/finally or context managers
- **Large queries:** Consider pagination for large datasets
- **Performance:** Use joins instead of multiple queries when possible

## Environment Setup Checklist

```bash
# 1. Install environment
pixi install

# 2. Start database services
pixi run start-services

# 3. Check data availability
pixi run python -c "
from ca_biositing.datamodels.database import get_session_local
from ca_biositing.datamodels.schemas.generated.ca_biositing import Resource, AnalysisType
session = get_session_local()()
print(f'Resources: {session.query(Resource).count()}')
print(f'Analysis Types: {session.query(AnalysisType).count()}')
session.close()
"

# 4. Start API (optional)
pixi run start-webservice
```

## Success Criteria

1. **Data Access:** Successfully query crop, preprocessing, and analysis data
2. **Visualization:** Create informative charts showing analytical pipelines
3. **Insights:** Identify patterns in crop → preprocessing → analysis workflows
4. **Performance:** Handle database queries efficiently without memory issues

## Data Exploration Starting Points

1. **Count records by table:** Understand data volume and completeness
2. **Explore unique values:** See what crops, prep methods, analyses are
   available
3. **Check relationships:** Validate foreign key connections work as expected
4. **Identify patterns:** Look for common analytical workflows per crop type

---

**Last Updated:** February 9, 2026 **Context:** Database contains AIM 1
laboratory analysis data with crop, preprocessing, and analytical technique
relationships **Next Agent:** Focus on exploratory data analysis and creating
meaningful visualizations of analytical workflows
