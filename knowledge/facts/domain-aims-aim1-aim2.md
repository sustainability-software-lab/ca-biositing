---
type: Fact
title: "Research aims: Aim 1 feedstock characterization vs Aim 2 conversion experiments"
description: "Aim 1 = feedstock collection and lab characterization (proximate, ultimate, XRF, ICP, etc.); Aim 2 = pretreatment, fermentation and gasification conversion experiments."
tags: [domain, aim1, aim2, research, biocirv]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-16T22:27:18Z" }
status: stable
code_refs: ["src/ca_biositing/pipeline/ca_biositing/pipeline/etl/extract/basic_sample_info.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/extract/thermochem_data.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/flows/aim2_bioconversion.py", "src/ca_biositing/datamodels/ca_biositing/datamodels/models/aim1_records/", "src/ca_biositing/datamodels/ca_biositing/datamodels/models/aim2_records/"]
sources: ["README.md", "docs/pipeline/USDA/ANALYTICS_HANDOFF.md", "docs/api/datamodels.md", "commit 543adde", "commit a4e6fc9"]
governance: context
---

## What the code and docs say
- Aim 1: the Google Sheet is named ’Aim 1-Feedstock Collection and Processing Data-BioCirV’ (pipeline etl/extract/basic_sample_info.py:7). Its analytical records are proximate, ultimate, compositional, ICP, XRF, XRD, calorimetry, FTNIR and RGB (datamodels models/aim1_records/). docs/pipeline/USDA/ANALYTICS_HANDOFF.md says the focus is Aim 1 lab analyses, which ’represent the core experimental data’, and relates crops, preprocessing methods and analytical techniques.
- Aim 2: the Google Sheet is named ’Aim 2-Thermochem Conversion Data-BioCirV’ (pipeline etl/extract/thermochem_data.py:7). It covers thermochemical conversion (gasification, autoclave) and bioconversion (pretreatment, enzymatic hydrolysis, fermentation with strains). Models live in models/aim2_records/. The Aim 2 sheet pulls Aim 1 material types and preprocessing reference sheets (thermochem_data.py:19-21), which shows the two aims share a sample vocabulary.
- The README describes the project as biomass feedstock siting for California (Cal BioScape, San Joaquin Valley). Its ’Data Domains’ table calls Aim 1 records lab analyses and Aim 2 records fermentation and pretreatment experiment results.

## Summary
| | Aim 1 | Aim 2 |
|---|---|---|
| Question | What is the feedstock made of and how much is there | How does the feedstock convert to fuels or products |
| Unit of work | Field sample, then prepared sample, then lab analysis | Experiment run in a reactor, vessel or fermenter |
| Key tables | proximate_record, ultimate_record, icp_record, xrf_record, calorimetry_record, ... | fermentation_record, pretreatment_record, gasification_record, bioconversion_method, strain |
| Measurements | observation rows (parameter, unit) | observation rows, plus gasification timeseries archived in GCS |
| Supply side | resource, resource_availability, residue_factor | feeds back through resource and prepared_sample |

## Caveats
- The exact aim statements (research questions and deliverables) are not in this repo. The split above is inferred from sheet names, ETL flow names and model names. Confirm the official aim text with the project lead.
- The docs say Aim 2 ’bioconversion/thermochemical’ work, but the code also treats gasification and autoclave as Aim 2.

# Related Concepts
- [Aim 1 analytical record tables (proximate, ultimate, XRF, ICP, etc.)](../architecture/datamodels-aim1-records.md): Aim 1 record tables described here
- [Aim 2 processing and conversion tables (pretreatment, fermentation, gasification)](../architecture/datamodels-aim2-records.md): Aim 2 record tables described here
- [Domain terms as used in the datamodels: resource, field sample, prepared sample, analysis record, observation, parameter, unit, method, dataset](domain-core-terms.md): Defines the terms used by both aims
- [Glossary](glossary.md): Project-wide glossary hub
- [System overview (start here)](../architecture/system-overview.md): Hub for the overall system
