---
type: Architecture
title: "People tables: contact and provider"
description: "contact (person) and provider (codename only) are BaseEntity tables referenced as analyst, collector, preparer and provider on sampling and experiment records."
tags: [datamodels, people, contact, provider]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:26:57Z" }
status: stable
code_refs: ["src/ca_biositing/datamodels/ca_biositing/datamodels/models/people/contact.py", "src/ca_biositing/datamodels/ca_biositing/datamodels/models/people/provider.py"]
sources: ["commit 7a41e0e", "https://github.com/sustainability-software-lab/ca-biositing/pull/112", "alembic/versions/0022_exclude_jaguar_provider.py"]
governance: context
---

## Purpose
Who collected, prepared, or analysed a sample, and which provider supplied it.

## Key files
| Path:line | Role |
|---|---|
| `models/people/contact.py:7` | `Contact(BaseEntity)` table `contact`: `name`, `first_name`, `last_name`, `email`, `affiliation` |
| `models/people/provider.py:7` | `Provider(BaseEntity)` table `provider`: `codename` only |

## Interfaces
- `contact.id` referenced by: `field_sampling/field_sample.py:15` (`collector_id`), `sample_preparation/prepared_sample.py:15` (`preparer_id`), `experiment_equipment/experiment.py:13` (`analyst_id`), and the Aim mixins’ `analyst_id` (`models/base.py:53,73`).
- `provider.id` referenced by: `field_sampling/field_sample.py:14` (`provider_id`).
- Relationships exposed: `FieldSample.provider`, `FieldSample.collector`, `Experiment.analyst`, `PreparedSample.preparer`.

## Gotchas
- `Provider` holds only a codename; organisation details live elsewhere or nowhere (inferred from fields).
- No uniqueness constraint on `contact.email` or `provider.codename` in the model.
- Both tables carry `etl_run_id` and `lineage_group_id` through `BaseEntity`.
- A migration named `0022_exclude_jaguar_provider.py` exists under `alembic/versions/`; provider-level exclusion is handled in views, not in these models (not inspected).

## History
- `7a41e0e` (PR #112): SQLModel versions of these tables.

## Open questions
- Whether provider identity should be deduplicated against `contact`.

# Related Concepts
- [Datamodels base mixins (BaseEntity, LookupBase, Aim1/Aim2RecordBase)](datamodels-base.md): both inherit BaseEntity
- [ER diagram: core, places, people, auth and infrastructure tables with verified FKs](datamodels-er-diagram.md): where these FKs appear in the diagram
- [System overview (start here)](system-overview.md): hub: sample provenance people
