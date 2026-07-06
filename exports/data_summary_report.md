# Data Summary Report

Generated on: 2026-06-26

## Aim 1: Analytical Records

| Analysis Type | Record Count |
| :------------ | :----------- |
| Compositional | 1,043        |
| Calorimetry   | 6            |
| FTNIR         | 0            |
| ICP           | 1,066        |
| Proximate     | 1,339        |

## Aim 2: Processing Records

| Analysis Type | Record Count |
| :------------ | :----------- |
| Fermentation  | 4,021        |
| Gasification  | 801          |

## USDA & External Data

- **USDA Survey Records**: 7,338
- **USDA Census Records**: 3,188
- **Distinct Commodities**: 15

## Records by Dataset Type

| Dataset Type               | Count |
| :------------------------- | :---- |
| county_ag_report_record    | 7     |
| usda_survey_record         | 107   |
| usda_census_record         | 107   |
| resource_price_record      | 1     |
| resource_production_record | 1     |
| other (compositional/aim)  | 1     |

## Filter Quality Assessment (QC Assessment)

This section compares the raw data in base tables vs the filtered data available
in the Data Portal materialized views (which exclude failed QC records and
outliers).

| Domain                         | Raw Records        | QC'd Portal Records         |
| :----------------------------- | :----------------- | :-------------------------- |
| **Composition** (Observations) | 50,294 (Total Obs) | 5,209 (represented in view) |
| **Fermentation** (Records)     | 4,021              | 410                         |
| **Gasification** (Records)     | 801                | 269                         |

**Notes on Composition View:** The `mv_biomass_composition` view aggregates
observations. The "represented" count refers to the sum of `observation_count`
within the view. The view itself contains 1,087 aggregated rows.
