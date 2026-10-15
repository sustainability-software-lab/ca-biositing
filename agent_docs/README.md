# Agent Documentation Index

Cross-cutting guidance for AI assistants working on the ca-biositing project.
This folder contains consolidated documentation for topics that apply across
multiple packages, eliminating redundancy while preserving all information.

## Documents

| Document                                           | Description                                                                               | Referenced By                    |
| -------------------------------------------------- | ----------------------------------------------------------------------------------------- | -------------------------------- |
| [namespace_packages.md](namespace_packages.md)     | PEP 420 namespace package structure and import patterns                                   | datamodels, pipeline, webservice |
| [testing_patterns.md](testing_patterns.md)         | pytest fixtures, test commands, and testing patterns                                      | All packages                     |
| [code_quality.md](code_quality.md)                 | Pre-commit workflow, code style, and import conventions                                   | All packages                     |
| [troubleshooting.md](troubleshooting.md)           | Common pitfalls and solutions across all components                                       | All files                        |
| [docker_workflow.md](docker_workflow.md)           | Docker/Pixi service commands and ETL operations                                           | root, resources                  |
| [geospatial_standards.md](geospatial_standards.md) | Canonical SRID/CRS standards (`EPSG:4326`, `EPSG:3310`) and static county boundary assets | analysis, pipeline, datamodels   |

## Usage

Package-specific AGENTS.md files reference these documents using relative links.
When AI assistants encounter topics covered here, they should consult these
canonical references rather than looking for duplicated content.

## Structure

```
agent_docs/
├── README.md                 # This file - index and overview
├── namespace_packages.md     # PEP 420 namespace package guidance
├── testing_patterns.md       # Testing fixtures and patterns
├── code_quality.md           # Pre-commit, style, imports
├── troubleshooting.md        # Common issues and solutions
├── docker_workflow.md        # Docker and Pixi task commands
└── geospatial_standards.md   # SRID/CRS standards & canonical county geo assets
```

## Related Documentation

- **Main AGENTS.md**: [/AGENTS.md](../AGENTS.md) - Repository overview and
  environment setup
- **Resources AGENTS.md**: [/resources/AGENTS.md](../resources/AGENTS.md) -
  Prefect deployment specifics
- **Datamodels AGENTS.md**:
  [/src/ca_biositing/datamodels/AGENTS.md](../src/ca_biositing/datamodels/AGENTS.md) -
  SQLModel patterns
- **Pipeline AGENTS.md**:
  [/src/ca_biositing/pipeline/AGENTS.md](../src/ca_biositing/pipeline/AGENTS.md) -
  ETL task patterns
- **Webservice AGENTS.md**:
  [/src/ca_biositing/webservice/AGENTS.md](../src/ca_biositing/webservice/AGENTS.md) -
  FastAPI patterns
