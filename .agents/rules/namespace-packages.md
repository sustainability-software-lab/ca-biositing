# Namespace Package Structure (PEP 420)

**Load when:** adding a module or package under `src/ca_biositing/`, fixing an
import error, or changing package structure or a `pyproject.toml`.

This project uses PEP 420 implicit namespace packages to share the
`ca_biositing` namespace across multiple independently-installable packages.

## Critical Rule

**The `ca_biositing/` directory does NOT have an `__init__.py` file.**

This allows multiple packages to share the `ca_biositing` namespace:

- `ca_biositing.datamodels`
- `ca_biositing.pipeline`
- `ca_biositing.webservice`

## Package Structure Pattern

Each namespace package follows this structure:

```text
src/ca_biositing/<package>/
├── ca_biositing/              # No __init__.py at this level (namespace)
│   └── <package>/             # Package implementation
│       ├── __init__.py        # Package initialization
│       └── *.py               # Module files
├── tests/                     # Test suite
├── pyproject.toml             # Package metadata
└── README.md                  # Documentation
```

### Datamodels Example

```text
src/ca_biositing/datamodels/
├── ca_biositing/              # No __init__.py at this level (namespace)
│   └── datamodels/            # Package implementation
│       ├── __init__.py        # Package initialization
│       ├── biomass.py         # Biomass models
│       ├── config.py          # Model configuration
│       ├── database.py        # Database setup
│       └── ...                # Other model modules
├── tests/                     # Test suite
├── pyproject.toml             # Package metadata
└── README.md                  # Documentation
```

### Pipeline Example

```text
src/ca_biositing/pipeline/
├── ca_biositing/              # No __init__.py at this level (namespace)
│   └── pipeline/              # Package implementation
│       ├── __init__.py        # Package initialization
│       ├── etl/               # ETL modules
│       ├── flows/             # Prefect flows
│       └── utils/             # Utilities
├── tests/                     # Test suite
├── pyproject.toml             # Package metadata
└── README.md                  # Documentation
```

### Webservice Example

```text
src/ca_biositing/webservice/
├── ca_biositing/              # No __init__.py at this level (namespace)
│   └── webservice/            # Package implementation
│       ├── __init__.py        # Package initialization
│       └── main.py            # FastAPI application
├── tests/                     # Test suite
├── pyproject.toml             # Package metadata
└── README.md                  # Documentation
```

## Import Patterns

```python
# Correct - imports work across namespace packages
from ca_biositing.datamodels.biomass import Biomass
from ca_biositing.pipeline.utils.lookup_utils import replace_name_with_id_df
from ca_biositing.webservice.main import app

# Cross-package imports in pipeline
from ca_biositing.datamodels.database import get_engine
from ca_biositing.datamodels.biomass import BiomassType

# Cross-package imports in webservice
from ca_biositing.datamodels.biomass import Biomass
from ca_biositing.datamodels.database import get_session
```

## Installation

For development, install all packages in editable mode:

```bash
# Using Pixi (recommended)
pixi install

# Or manually with pip
pip install -e src/ca_biositing/datamodels
pip install -e src/ca_biositing/pipeline
pip install -e src/ca_biositing/webservice
```

## Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'ca_biositing.datamodels'"

**Causes:**

1. Package not installed
2. `__init__.py` exists in `ca_biositing/` directory (breaks namespace)
3. Incorrect working directory

**Solutions:**

```bash
# Verify structure (no __init__.py in ca_biositing/)
ls -la src/ca_biositing/
# Should show: datamodels/ pipeline/ webservice/ (no __init__.py)

# If __init__.py exists, remove it
rm src/ca_biositing/datamodels/ca_biositing/__init__.py  # WRONG location
# The __init__.py should ONLY be in:
# src/ca_biositing/datamodels/ca_biositing/datamodels/__init__.py  # CORRECT

# Install in development mode
pip install -e src/ca_biositing/datamodels

# Or reinstall via Pixi
pixi install
```

### Issue: "ModuleNotFoundError: No module named 'ca_biositing.pipeline'"

Same troubleshooting as above. Verify:

1. No `__init__.py` in `src/ca_biositing/pipeline/ca_biositing/`
2. `__init__.py` exists in `src/ca_biositing/pipeline/ca_biositing/pipeline/`
3. Package is installed: `pip install -e src/ca_biositing/pipeline`

### Issue: "ModuleNotFoundError: No module named 'ca_biositing.webservice'"

Same troubleshooting as above. Verify:

1. No `__init__.py` in `src/ca_biositing/webservice/ca_biositing/`
2. `__init__.py` exists in
   `src/ca_biositing/webservice/ca_biositing/webservice/`
3. Package is installed: `pip install -e src/ca_biositing/webservice`

### Issue: Import works in one package but not another

**Cause:** Only some packages are installed.

**Solution:** Install all packages:

```bash
pixi install  # Installs all packages via Pixi

# Or manually
pip install -e src/ca_biositing/datamodels
pip install -e src/ca_biositing/pipeline
pip install -e src/ca_biositing/webservice
```

## Best Practices

1. **Never add `__init__.py` to `ca_biositing/` directory** - This breaks
   namespace package functionality

2. **Always add `__init__.py` to the actual package directory** - e.g.,
   `ca_biositing/datamodels/__init__.py`

3. **Use absolute imports** - Always use full import paths like
   `from ca_biositing.datamodels.biomass import Biomass`

4. **Install in editable mode** - Use `pip install -e` or `pixi install` for
   development

5. **Check structure after git operations** - Merge conflicts or rebases might
   accidentally create `__init__.py` files in wrong locations
