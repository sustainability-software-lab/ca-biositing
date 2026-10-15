# AGENTS.md

Guidance for AI assistants (Claude Code, Codex, Cursor, Copilot, Gemini CLI, and
any other agent harness) working with **ca-biositing**: ETL pipelines that load
Google Sheets and public data into PostgreSQL, a FastAPI service, and geospatial
analysis for bioeconomy siting in California.

**This file is the entry point and is deliberately short.** It carries only what
every agent needs before doing anything. Detailed rules and conventions live as
separate files under [`.agents/rules/`](.agents/rules/) and are loaded on demand
— read the one whose trigger matches your current task, not all of them. Package
directories carry their own `AGENTS.md`; read it before changing code there (see
[Package Guides](#package-guides)).

## Non-negotiables

These apply to every task, in every session:

1. **Pixi is the only package manager.** Never invoke `pip`, `conda`, or `venv`
   directly. Run `pixi install` before any other Pixi command, and never let a
   newer pixi rewrite `pixi.lock` (see
   [pixi-environments.md](.agents/rules/pixi-environments.md)).
2. **Verify before you claim.** Never report work as complete, fixed, or passing
   without having run the check and read its output. The minimum gate here is
   `pixi run pre-commit-all` plus the tests for every package you changed.
3. **Change surgically.** Every changed line must trace directly to the request.
   Don't refactor, reformat, or "improve" adjacent code you weren't asked to
   touch.
4. **Ask instead of assuming.** If the request has multiple readings or
   something is unclear, stop and name it — before implementing, not after.
5. **Change the schema only through SQLModel models and Alembic migrations.**
   Never alter tables or views by hand; follow
   [schema-and-migrations.md](.agents/rules/schema-and-migrations.md).
6. **Never open a PR** without working through
   [`.agents/rules/contribution-discipline.md`](.agents/rules/contribution-discipline.md)
   in full, including human review of the complete diff.

## Rule Index

Load the rule file whose trigger matches what you are about to do.

| Rule file                                                                      | Load when                                                                                           |
| ------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------- |
| [working-agreement.md](.agents/rules/working-agreement.md)                     | Starting any implementation, refactor, or bugfix — the behavioral baseline                          |
| [contribution-discipline.md](.agents/rules/contribution-discipline.md)         | About to commit, open a PR, or asked to "contribute" / "fix some issues"                            |
| [pixi-environments.md](.agents/rules/pixi-environments.md)                     | Running any command, adding a dependency, editing `pixi.toml`, or touching `pixi.lock`              |
| [code-quality.md](.agents/rules/code-quality.md)                               | Writing Python, committing, preparing a PR, or claiming checks pass                                 |
| [testing-patterns.md](.agents/rules/testing-patterns.md)                       | Writing, fixing, or running tests                                                                   |
| [repository-map.md](.agents/rules/repository-map.md)                           | You need to know what this repo is, where a file lives, or what CI runs                             |
| [namespace-packages.md](.agents/rules/namespace-packages.md)                   | Adding modules under `src/ca_biositing/` or fixing import errors                                    |
| [schema-and-migrations.md](.agents/rules/schema-and-migrations.md)             | Changing SQLModel models, Alembic migrations, or materialized views                                 |
| [docker-workflow.md](.agents/rules/docker-workflow.md)                         | Starting, inspecting, or rebuilding the Docker services, or running ETL flows                       |
| [agent-skills.md](.agents/rules/agent-skills.md)                               | Adding, editing, or syncing an agent skill, or editing `skills.json`                                |
| [troubleshooting.md](.agents/rules/troubleshooting.md)                         | A documented command fails or behaves unexpectedly                                                  |
| [mkdocs-okf-knowledge-bundle.md](.agents/rules/mkdocs-okf-knowledge-bundle.md) | Rendering `knowledge/` with mkdocs (optional pattern), or debugging wikilink or frontmatter clashes |

## Package Guides

| Directory                      | Guide                                              | Covers                                                 |
| ------------------------------ | -------------------------------------------------- | ------------------------------------------------------ |
| `src/ca_biositing/datamodels/` | [AGENTS.md](src/ca_biositing/datamodels/AGENTS.md) | SQLModel models, views, and database sessions          |
| `src/ca_biositing/pipeline/`   | [AGENTS.md](src/ca_biositing/pipeline/AGENTS.md)   | Prefect ETL tasks and flows                            |
| `src/ca_biositing/webservice/` | [AGENTS.md](src/ca_biositing/webservice/AGENTS.md) | The FastAPI application and endpoints                  |
| `alembic/`                     | [AGENTS.md](alembic/AGENTS.md)                     | Migration patterns and materialized-view SQL snapshots |
| `resources/`                   | [AGENTS.md](resources/AGENTS.md)                   | Docker Compose services and Prefect deployments        |
| `audit/`                       | [AGENTS.md](audit/AGENTS.md)                       | Running and interpreting the database audit            |

## Provenance

This harness — the short entry point, the on-demand rules under
`.agents/rules/`, and the `CLAUDE.md` imports — is adapted from the UW SSEC
[project template](https://github.com/uw-ssec/project-template) at commit
`fc00b39`. Its behavioral rules in turn adapt two upstream sources:

- [obra/superpowers](https://github.com/obra/superpowers) `CLAUDE.md` — agent
  contribution discipline (`contribution-discipline.md`).
- [multica-ai/andrej-karpathy-skills](https://github.com/multica-ai/andrej-karpathy-skills)
  `CLAUDE.md` — behavioral guidelines that reduce common LLM coding mistakes
  (`working-agreement.md`).

## Trust These Instructions

These instructions were generated through comprehensive exploration and testing
of the repository. Commands have been validated to work correctly. **Only
perform additional searches if:**

- You need information not covered by `AGENTS.md` or `.agents/rules/`
- Instructions appear outdated or produce errors
- You're implementing functionality that changes the build system

For routine tasks (adding files, making code changes, running checks), follow
these instructions directly without additional exploration.
