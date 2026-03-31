# CA Biositing Web Service

FastAPI REST API for the
[CA Biositing](https://github.com/sustainability-software-lab/ca-biositing)
project — serving biomass feedstock data including USDA Census/Survey statistics
and laboratory analysis results.

Shares database models with the companion
[`ca-biositing-datamodels`](https://pypi.org/project/ca-biositing-datamodels/)
package.

## Installation

```bash
pip install ca-biositing-webservice
```

## Quick Start

```bash
uvicorn ca_biositing.webservice.main:app --reload
```

Interactive docs at `http://localhost:8000/docs`.

## API Overview

| Endpoint Family | Base Path                     | Description                                |
| --------------- | ----------------------------- | ------------------------------------------ |
| Auth            | `/v1/auth/token`              | JWT access tokens                          |
| Analysis        | `/v1/feedstocks/analysis/`    | Lab analysis data by resource and location |
| USDA Census     | `/v1/feedstocks/usda/census/` | USDA Census data by crop or resource       |
| USDA Survey     | `/v1/feedstocks/usda/survey/` | USDA Survey data by crop or resource       |

Each family includes discovery endpoints returning available crops, resources,
geoids, and parameters. All lookups are case-insensitive.

### Authentication

The `/v1/auth/token` endpoint uses **POST** (not GET) because credentials are
sent in the request body — keeping them out of URLs, server logs, and browser
history.

It returns a **JWT (JSON Web Token)**: a compact, cryptographically signed
string that encodes your identity. Once issued, include it on every subsequent
request in the `Authorization` header:

```
Authorization: Bearer <your_token>
```

The token is time-limited. When it expires, call `/v1/auth/token` again to get a
new one. No session state is stored server-side — each request is validated by
verifying the token signature.

## Key Dependencies

- [`ca-biositing-datamodels`](https://pypi.org/project/ca-biositing-datamodels/)
  — shared database models
- [FastAPI](https://fastapi.tiangolo.com/) — web framework
- [Uvicorn](https://www.uvicorn.org/) — ASGI server
- [PyJWT](https://pyjwt.readthedocs.io/) — JWT authentication

## Links

- [Repository](https://github.com/sustainability-software-lab/ca-biositing)
- [Issue Tracker](https://github.com/sustainability-software-lab/ca-biositing/issues)

## Contributors

[![Contributors](https://contrib.rocks/image?repo=sustainability-software-lab/ca-biositing)](https://github.com/sustainability-software-lab/ca-biositing/graphs/contributors)

## Acknowledgement

We acknowledge software engineering support from the University of Washington
[Scientific Software Engineering Center (SSEC)](https://escience.washington.edu/software-engineering/ssec/),
as part of the Schmidt Sciences
[Virtual Institute for Scientific Software (VISS)](https://www.schmidtsciences.org/).

## License

CA Biositing Web Service is licensed under the open source
[BSD 3-Clause License](https://opensource.org/license/bsd-3-clause).
