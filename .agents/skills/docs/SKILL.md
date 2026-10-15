---
name: docs
description:
  Use when work completed in this session needs writing up in the MkDocs site
  under docs/ — new pipelines, schema or API changes, deployment changes, or
  gotchas that readers of the site need to know.
---

# Docs

Write or update the MkDocs documentation in `docs/` for recent work in this
session.

## Arguments

Optional: a topic, a section, or "all" to cover everything from this session.

## Instructions

1. **Gather context** — run these in parallel to understand what changed:

   - `git log --oneline -20` (recent commits)
   - `git diff main...HEAD --stat` (if on a feature branch)
   - `git log --oneline --since="8 hours ago"` (today's work)
   - Read `mkdocs.yml`, whose `nav:` is explicit, and `docs/README.md`, a
     symlink to the repository `README.md` that serves as the site's home page

2. **Determine scope** — based on the argument and recent changes, decide which
   docs need writing or updating:

   - If the argument is a specific topic (e.g., "landiq", "auth", "materialized
     views"), focus there
   - If the argument is a section (e.g., "pipeline", "datamodels",
     "deployment"), update that section
   - If the argument is "all" or empty, document everything from the current
     session
   - Always check existing docs first — update rather than duplicate

3. **Write documentation** covering these categories as relevant:

   ### Technical Details
   - What was built, changed, or fixed
   - Schema changes (SQLModel models, Alembic migrations, materialized views),
     API endpoints, and ETL flows
   - Configuration changes, environment variables, Pixi tasks, or dependencies
     added

   ### Technical Architecture
   - System design and component relationships
   - Data flow diagrams (use Mermaid syntax)
   - Integration points: Google Sheets and external sources → Prefect ETL →
     PostgreSQL → materialized views → FastAPI → frontend
   - Infrastructure decisions (Docker Compose locally; GCP and Pulumi for
     deployment)

   ### Decisions and Learnings
   - Record decisions, rejected alternatives, and non-obvious gotchas in project
     memory with the `okf-memory` skill, not in `docs/`. Link the concept to the
     relevant docs page when that helps.

4. **Place documentation correctly** — follow the existing layout:

   - System architecture → `docs/architecture.md`
   - ETL pipeline and flows → `docs/pipeline/`
   - Data models, schema, and the SQL-first workflow → `docs/datamodels/`
   - Web service and API → `docs/webservice/` and `docs/api/`
   - Docker and Prefect resources → `docs/resources/`
   - Cloud deployment → `docs/deployment/`
   - Operational runbooks → `docs/operations/`
   - Implementation plans are not docs: keep them in the gitignored `plans/`
     directory

5. **Update mkdocs.yml nav** — if you created a new file, add it to the `nav:`
   section in `mkdocs.yml` under the correct heading. Match existing indentation
   and naming style.

6. **Verify** — run `pixi run -e docs docs-build` to confirm MkDocs builds
   without errors.

7. **Report** — show the user:
   - Files created or updated (with paths)
   - New nav entries added
   - Build status (pass/fail)

## Documentation Style

- Use MkDocs Material features: admonitions (`!!! note`, `!!! warning`,
  `!!! tip`), tabs, Mermaid diagrams, code blocks with language tags
- Start every doc with a level-1 heading and a 1-2 sentence summary
- Use tables for structured data (configs, env vars, field mappings)
- Keep headings hierarchical (h1 → h2 → h3, never skip levels)
- Use imperative voice for guides ("Run the migration", not "You should run the
  migration")
- Architecture decisions follow the pattern:

```markdown
### YYYY-MM-DD: Decision Title (Status)

- **Decision:** What was decided
- **Why:** The reasoning and constraints
- **Result:** What was implemented and any notable outcomes
```

## Mermaid Diagram Conventions

- Use `graph TD` for top-down architecture diagrams
- Use `sequenceDiagram` for request/response flows
- Use `erDiagram` for database relationships
- Keep diagrams focused — split complex systems into multiple diagrams
- Label edges with the protocol or mechanism (e.g., `-->|JWT|`, `-->|REST|`,
  `-->|Queue|`)

## Rules

- Never delete existing documentation — update or extend it
- Always read existing docs before writing to avoid duplication
- Every new doc must appear in `mkdocs.yml` nav
- Date-stamp architecture decisions
- Use relative links between docs (e.g., `../pipeline/ETL_WORKFLOW.md`)
- Build must pass before considering the task done
- If `pixi run -e docs docs-build` fails, fix the issue (usually a nav mismatch
  or broken link)
- NEVER include sensitive information in documentation (credentials, internal
  processes, etc.)
