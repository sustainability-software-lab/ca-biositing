# BioCirv Data Filtering Inventory Plan

## Purpose

BioCirv data passes through several systems before reaching users. Rules affecting which records appear may be distributed across analyst inputs, ETL pipelines, database logic, materialized views, APIs, and front-end code.

This makes it difficult to answer questions such as:

- Where is a category of data excluded?
- Is the same exclusion applied in multiple places?
- Do different outputs use different inclusion criteria?
- Is data removed from the pipeline or only hidden from users?

The first phase of this project will create a focused inventory of the logic that affects **record inclusion**.

## Phase 1 question

**Where and why can data be removed from, excluded from, or hidden in BioCirv outputs?**

The inventory should prioritize logic that determines whether a record:

- continues through the data pipeline
- is stored in a database table
- appears in a view or materialized view
- is returned by an API or backend query
- is displayed in the front end

The scan should follow the repository's actual structure rather than assuming in advance where filters are implemented.

## Included in Phase 1

Document meaningful rules that:

- explicitly include or exclude records
- reject records because of validation
- omit records through SQL conditions
- remove records through join behavior
- discard records during deduplication
- use analyst-provided flags to control inclusion
- exclude records from views, APIs, or other outputs
- hide records in the front end

Also include validations or flags that do not directly remove records when they clearly control a later inclusion decision.

## Not included in Phase 1

Do not exhaustively inventory:

- routine normalization or formatting
- unit conversions
- field or column renaming
- ordinary null replacement
- transformations that do not affect record inclusion
- aggregations that only summarize data
- warnings that do not affect inclusion
- test and fixture logic, unless it reveals an otherwise undocumented production rule

Potentially relevant items that fall outside the current scope may be placed in a brief **Possible Follow-Up** section.

## Level of detail

Use one inventory entry per meaningful inclusion or exclusion rule, not one entry per conditional statement or code occurrence.

When the same apparent rule is implemented in several places, document it as one entry and list each implementation location. This should make duplication visible without unnecessarily expanding the inventory.

## Inventory fields

| Field | Description |
|---|---|
| Rule | Plain-language description of what is included or excluded |
| Pipeline stage | Where the rule acts |
| Data affected | Dataset, table, field, view, endpoint, or output |
| Trigger | Condition that causes the rule to act |
| Effect | Whether records are removed, rejected, omitted, or hidden |
| Source | File, relevant function or object, and line range when possible |
| Related rules | Possible duplicate, conflict, or dependency |
| Questions | Uncertainty requiring human review |

Use `Unknown` when the repository does not provide enough evidence. Do not guess at undocumented scientific or business rationales.

## Expected outputs

### 1. Markdown Report

#### Pipeline overview markdown

A brief description of the major data stages discovered in the repository and how records move between them.

This should provide context for the inventory, not become a detailed architectural review.

#### Duplicate or conflict candidates

A short list of rules that may:

- implement the same exclusion in multiple locations
- apply different criteria to similar data
- affect the same records differently across outputs
- duplicate an earlier filter unnecessarily

Treat these as questions for human review rather than confirmed defects.

#### Discovery gaps

A short list of relevant areas the repository scan could not fully inspect, such as:

- external Google Sheets or analyst processes
- database objects not defined in the repository
- dynamically generated SQL
- environment-dependent behavior
- domain-specific logic whose intent is unclear


#### Possible follow-up

A limited list of potentially important validation or transformation logic that was encountered but falls outside the Phase 1 scope.


### 2. Priority filter inventory

A table containing the meaningful rules that affect whether records reach stored or user-facing outputs.

This can be a .xslx or csv and script to make write-back privileges to this google sheet: https://docs.google.com/spreadsheets/d/1dEp-46Jng4K6oKGA41rMyzzHLmwIfJ-6p1KRnwnUpog/edit?gid=0#gid=0

## Current agent task

Inspect the repository and produce the outputs above.

Prioritize rules that can change record inclusion in stored data or user-facing outputs. Do not exhaustively document routine transformations or every conditional statement.

Follow imports, calls, SQL definitions, configuration, and data-flow paths where needed. Do not restrict discovery to code containing terms such as `filter`, `exclude`, or `validate`.

Do not:

- modify code or configuration
- implement monitoring or instrumentation
- decide where filters should ideally live
- recommend a final architecture
- judge whether a scientific rule is correct without documented evidence

Stop after creating the first-pass inventory and noting questions for human review.

## Later phases

After the inventory has been reviewed, the team may:

1. Define which inclusion and data-quality rules are desired.
2. Decide where each rule should ideally be implemented.
3. Consolidate, relocate, remove, or document existing rules.
4. Assign stable identifiers to confirmed rules.
5. Add instrumentation to measure how many records each rule removes or retains.
6. Monitor data loss and filtering behavior over time.

These activities are not part of the initial repository scan.
