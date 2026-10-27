"""
Tests for infrastructure ETL pipeline scripts.

These tests verify:
1. Extract modules are importable and have the correct `extract` task signature.
2. Transform modules are importable and have the correct `transform` task signature.
3. Load modules are importable and have the correct `load` task signature.
4. Flow modules are importable and have the correct flow function name.
5. Transform returns an empty DataFrame (not None) when given an empty data source.
6. Load returns True immediately when given an empty DataFrame.
"""

import pytest
import pandas as pd


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

INFRASTRUCTURE_DATASETS = [
    "petroleum_pipelines",
    "biosolids_facilities",
    "cafo_manure_locations",
    "combustion_plants",
    "district_energy_systems",
    "ethanol_biorefineries",
    "food_processing_facilities",
    "landfills",
    "livestock_anaerobic_digesters",
    "msw_to_energy_anaerobic_digesters",
    "saf_and_renewable_diesel_plants",
    "wastewater_treatment_plants",
    "crude_oil_pipelines",
    "railways",
    "biodiesel_plants",
    "tomato_processors",
    "food_manufacturers_epa",
    "food_manufacturers_carb",
]

# petroleum_pipelines load is in infrastructure/ subdir; all others too
LOAD_MODULE_PATH = "ca_biositing.pipeline.etl.load.infrastructure.{name}"
EXTRACT_MODULE_PATH = "ca_biositing.pipeline.etl.extract.{name}"
TRANSFORM_MODULE_PATH = "ca_biositing.pipeline.etl.transform.infrastructure.{name}"
FLOW_MODULE_PATH = "ca_biositing.pipeline.flows.{name}"
FLOW_FUNC_SUFFIX = "_flow"


# ---------------------------------------------------------------------------
# Extract import tests
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name", INFRASTRUCTURE_DATASETS)
def test_extract_importable(name):
    """Each infrastructure extract module must be importable with an `extract` task."""
    import importlib
    mod = importlib.import_module(EXTRACT_MODULE_PATH.format(name=name))
    assert hasattr(mod, "extract"), f"extract module '{name}' missing 'extract' function"


# ---------------------------------------------------------------------------
# Transform import tests
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name", INFRASTRUCTURE_DATASETS)
def test_transform_importable(name):
    """Each infrastructure transform module must be importable with a `transform` task."""
    import importlib
    mod = importlib.import_module(TRANSFORM_MODULE_PATH.format(name=name))
    assert hasattr(mod, "transform"), f"transform module '{name}' missing 'transform' function"


# ---------------------------------------------------------------------------
# Load import tests
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name", INFRASTRUCTURE_DATASETS)
def test_load_importable(name):
    """Each infrastructure load module must be importable with a `load` task."""
    import importlib
    mod = importlib.import_module(LOAD_MODULE_PATH.format(name=name))
    assert hasattr(mod, "load"), f"load module '{name}' missing 'load' function"


# ---------------------------------------------------------------------------
# Flow import tests
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name", INFRASTRUCTURE_DATASETS)
def test_flow_importable(name):
    """Each infrastructure flow module must be importable with the correct flow function."""
    import importlib
    mod = importlib.import_module(FLOW_MODULE_PATH.format(name=name))
    expected_func = name + FLOW_FUNC_SUFFIX
    assert hasattr(mod, expected_func), (
        f"flow module '{name}' missing flow function '{expected_func}'"
    )


# ---------------------------------------------------------------------------
# Transform behaviour: empty input → empty DataFrame (not None)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name", INFRASTRUCTURE_DATASETS)
def test_transform_empty_input_returns_empty_dataframe(name):
    """
    When the data source contains an empty DataFrame, transform should return
    an empty DataFrame (not None), so the downstream load step can handle it.
    """
    import importlib
    mod = importlib.import_module(TRANSFORM_MODULE_PATH.format(name=name))
    transform_fn = mod.transform.fn  # unwrap Prefect task wrapper

    result = transform_fn(data_sources={name: pd.DataFrame()})
    assert result is not None, f"transform '{name}' returned None for empty input"
    assert isinstance(result, pd.DataFrame), (
        f"transform '{name}' did not return a DataFrame for empty input"
    )
    assert result.empty, f"transform '{name}' returned non-empty DataFrame for empty input"


# ---------------------------------------------------------------------------
# Load behaviour: None or empty DataFrame → returns True immediately
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name", INFRASTRUCTURE_DATASETS)
def test_load_empty_dataframe_returns_true(name):
    """
    load() must return True (not raise) when passed None or an empty DataFrame,
    so flows can handle missing data gracefully.
    """
    import importlib
    mod = importlib.import_module(LOAD_MODULE_PATH.format(name=name))
    load_fn = mod.load.fn  # unwrap Prefect task wrapper

    # Test with None
    result_none = load_fn(None)
    assert result_none is True, f"load '{name}' did not return True for None input"

    # Test with empty DataFrame
    result_empty = load_fn(pd.DataFrame())
    assert result_empty is True, f"load '{name}' did not return True for empty DataFrame"
