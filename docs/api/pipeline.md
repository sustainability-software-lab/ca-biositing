# Pipeline API Reference

Auto-generated reference for `ca_biositing.pipeline` — the ETL pipeline
components for data ingestion, transformation, and loading.

## How to use this page

This page documents the programmatic API for the ETL components — the extract,
transform, and load modules, Prefect flows, and utility functions — rendered
from source-code docstrings.

**Who this is for:** developers who want to import, extend, or integrate with
the pipeline code directly (e.g., adding a new extract step, writing a custom
transform, or calling a flow from another context).

**This is not an HTTP REST API.** The pipeline runs as a background process
orchestrated by Prefect — it has no REST endpoints. It appears here under
"API Reference" because, like the Datamodels page, it documents a callable
Python package interface rather than a user-facing workflow guide. For step-by-
step workflow instructions, see the [Pipeline guides](../pipeline/README.md).

---

## Pipeline Package

::: ca_biositing.pipeline
    options:
      show_submodules: false
      show_root_heading: false
      show_root_full_path: false

## ETL Core

::: ca_biositing.pipeline.etl
    options:
      show_submodules: false
      show_root_heading: false
      show_root_full_path: false

### Extract

::: ca_biositing.pipeline.etl.extract
    options:
      show_submodules: true
      show_root_heading: false
      show_root_full_path: false
      filters:
        - "!^_"

### Transform

::: ca_biositing.pipeline.etl.transform
    options:
      show_submodules: true
      show_root_heading: false
      show_root_full_path: false
      filters:
        - "!^_"

### Load

::: ca_biositing.pipeline.etl.load
    options:
      show_submodules: true
      show_root_heading: false
      show_root_full_path: false
      filters:
        - "!^_"

## Utilities

::: ca_biositing.pipeline.utils
    options:
      show_submodules: false
      show_root_heading: false
      show_root_full_path: false

### Cleaning Functions

::: ca_biositing.pipeline.utils.cleaning_functions
    options:
      show_submodules: false
      show_root_heading: false
      show_root_full_path: false
      filters:
        - "!^_"
