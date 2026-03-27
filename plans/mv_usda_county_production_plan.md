# Plan: Revision of `mv_usda_county_production` (Revised)

This document outlines the implementation plan for fixing the logic in the
`mv_usda_county_production` materialized view.

## 1. Goal

The primary objective is to align the view with the required grain: **one
resource/primary_ag_product combo per geoid**, using 2022 USDA Census data as
the primary source.

## 2. Technical Specification

### 2.1 Grain & Aggregation

- **Grain**: `resource_id`, `primary_ag_product`, `geoid`, `dataset_year`.
- **Aggregation Strategy**:
  - `primary_product_volume`: `AVG(value)` where `parameter` = 'production'.
  - `production_acres`: `AVG(value)` where `parameter` in ('area bearing', 'area
    harvested', 'area in production').
  - `calculated_estimate_volume`:
    `AVG(production_acres) * residue_factor_dry_tons_acre`.
- **Unit Preference (Constraint)**: To enforce the one-row-per-geoid grain, we
  will prioritize records with unit 'TONS'. If multiple units exist for a single
  record, only the preferred unit will be selected to avoid duplicate rows.

### 2.2 Join Logic

The view will be constructed using the following joins:

1.  **Anchor**: `UsdaCensusRecord`
2.  **Filtering**: Filter `UsdaCensusRecord` where `year = 2022`.
3.  **Commodity Mapping**: Join `ResourceUsdaCommodityMap` on
    `UsdaCensusRecord.commodity_code == ResourceUsdaCommodityMap.usda_commodity_id`.
4.  **Resource Info**: Join `Resource` and `PrimaryAgProduct` via the mapping
    table.
5.  **Geography**: Join `Place` on `UsdaCensusRecord.geoid == Place.geoid`.
6.  **Observations**: Join `Observation` (denormalized via subquery) on
    `record_id`.
    - Subquery filters for `record_type = 'usda_census_record'`.
    - Subquery extracts `production` and `acres` parameters into columns.
    - **Unit Filtering**: The subquery will rank units (e.g., 'tons' >
      'bushels' > others) and pick the top one for each `record_id` to ensure
      grain.
7.  **Availability/Factors**: Outer join `ResourceAvailability` on `resource_id`
    and `geoid`.

### 2.3 Column Mapping

| Column                       | Source / Logic                                                              |
| :--------------------------- | :-------------------------------------------------------------------------- |
| `id`                         | `func.row_number().over()`                                                  |
| `resource_id`                | `Resource.id`                                                               |
| `resource_name`              | `Resource.name`                                                             |
| `primary_ag_product`         | `PrimaryAgProduct.name`                                                     |
| `geoid`                      | `Place.geoid`                                                               |
| `county`                     | `Place.county_name`                                                         |
| `state`                      | `Place.state_name`                                                          |
| `dataset_year`               | `UsdaCensusRecord.year` (Filtered to 2022)                                  |
| `primary_product_volume`     | `AVG(census_obs.production)`                                                |
| `volume_unit`                | `census_obs.volume_unit`                                                    |
| `production_acres`           | `AVG(census_obs.acres)`                                                     |
| `known_biomass_volume`       | `NULL` (For now)                                                            |
| `calculated_estimate_volume` | `AVG(census_obs.acres) * ResourceAvailability.residue_factor_dry_tons_acre` |
| `biomass_unit`               | `'dry_tons_acre'`                                                           |

## 3. Implementation Steps

1.  **Update Subquery**: Modify the `census_obs` subquery in
    `data_portal_views.py` to:
    - Correctly identify the three acre-related parameters.
    - Implement a case statement or ranking to prioritize 'TONS' for the volume
      unit.
2.  **Top-level Selection**: Rewrite the `mv_usda_county_production` selection
    to include `GROUP BY` on the grain columns (`resource_id`, `geoid`,
    `dataset_year`).
3.  **Refactor Joins**: Ensure all joins are correctly typed and handle
    potential nulls in `ResourceAvailability`.
4.  **Migration**: Generate and apply a new Alembic migration to update the
    materialized view definition in the database.

## 4. Known Limitations

- **Residue Factor Mismatch**: The `residue_factor_dry_tons_acre` represents the
  total amount of residues (hulls, shells, sticks, etc.) for a crop and does not
  distinguish between individual resource amounts (e.g. hulls only).
- **Unit Exclusion**: By enforcing a single row per grain, records reported in
  non-preferred units (if a preferred unit exists for the same record) will be
  filtered out.
- **2022 Focus**: This view currently only processes the 2022 Census year.

## 5. Summary of Implementation Strategy

We will use a subquery to aggregate observations at the `record_id` level first,
handling the unit prioritization there. Then, we will join this with the
`resource` and `geography` tables and aggregate again to the `resource_id` /
`geoid` grain to ensure a clean, unique dataset for the frontend.
