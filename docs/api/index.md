# API Reference

This section provides auto-generated reference documentation for the
`ca_biositing` Python packages, rendered from source code docstrings.

## Python Packages

- **[Datamodels](datamodels.md)** — SQLModel database models (91 models across
  15 domain subdirectories)
- **[Pipeline](pipeline.md)** — ETL flows, extract/transform/load modules, and
  utility functions

## Webservice REST API

See the **[Webservice API](webservice.md)** page for a static reference that
works without a running server.

For live interactive exploration, start the webservice and visit
[http://localhost:8000/docs](http://localhost:8000/docs):

```bash
pixi run start-webservice
```

To regenerate the static spec after API changes:

```bash
pixi run -e webservice generate-openapi
```
