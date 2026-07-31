# Visualization Gallery

## Aim 1: Analytical Record Counts

![Aim 1 Record Counts](plots/metadata/aim1_record_counts.png) _Distribution of
analytical records in the database across different analysis types
(Compositional, ICP, Proximate, etc.)._

> **Source:**
> [`analysis/metadata/data_summary_viz.py`](analysis/metadata/data_summary_viz.py)
> | **Generated:** 2026-06-26 20:10 UTC

## Aim 2: Processing Record Counts

![Aim 2 Record Counts](plots/metadata/aim2_record_counts.png) _Counts of
processing records for Fermentation and Gasification experiments._

> **Source:**
> [`analysis/metadata/data_summary_viz.py`](analysis/metadata/data_summary_viz.py)
> | **Generated:** 2026-06-26 20:10 UTC

## Filter Quality Assessment

![Filter Quality Assessment](plots/metadata/filter_quality_assessment.png)
_Comparison between raw data entries and those that successfully passed Quality
Control (QC) filters for the data portal views._

> **Source:**
> [`analysis/metadata/data_summary_viz.py`](analysis/metadata/data_summary_viz.py)
> | **Generated:** 2026-06-26 20:10 UTC

## Biomass Composition: Xylan vs Glucan

[Interactive Visualization](plots/composition/biomass_xylan_glucan.html) _A
scatter plot showing the relationship between Xylan and Glucan content across
various biomass resources. Almond-based resources are highlighted in gold._

> **Source:**
> [`analysis/composition/biomass_xylan_glucan_viz.py`](analysis/composition/biomass_xylan_glucan_viz.py)
> | **Generated:** 2026-06-26 20:10 UTC

## Aim 1: XRF Data Distribution

[Interactive Visualization](plots/composition/xrf_distribution_viz.html) _Violin
plot showing the distribution and variance of elemental concentrations from XRF
analysis across various biomass resources._

> **Source:**
> [`analysis/composition/xrf_distribution_viz.py`](analysis/composition/xrf_distribution_viz.py)
> | **Generated:** 2026-06-26 20:30 UTC

## Aim 1: XRF Si and K Distribution

[Interactive Visualization](plots/composition/xrf_si_k_distribution_viz.html)
_Detailed distribution of Silicon (Si) and Potassium (K) concentrations from XRF
analysis. Rice hulls and wheat straw are highlighted in neon green to showcase
their significantly higher silica content._

> **Source:**
> [`analysis/composition/xrf_si_k_distribution_viz.py`](analysis/composition/xrf_si_k_distribution_viz.py)
> | **Generated:** 2026-06-26 20:43 UTC

## Biomass Composition: 3D Representation

![Biomass Composition 3D](plots/composition/biomass_composition_3d.png)
[Interactive Visualization](plots/composition/biomass_composition_3d.html) _A 3D
scatter plot of Glucan vs Xylan vs Lignin content for various biomass resources.
Sweet potato culls are highlighted in orange._

> **Source:**
> [`analysis/composition/biomass_composition_3d_viz.py`](analysis/composition/biomass_composition_3d_viz.py)
> | **Generated:** 2026-06-26 20:51 UTC

## California Strawberry Acreage (2022)

[Interactive Visualization](plots/geospatial/strawberry_acreage_heatmap.html) _A
choropleth heatmap showing strawberry acreage (bearing and non-bearing) by
California county, based on USDA Census 2022 data._

> **Source:**
> [`analysis/geospatial/strawberry_acreage_heatmap.py`](analysis/geospatial/strawberry_acreage_heatmap.py)
> | **Generated:** 2026-06-26 21:07 UTC

## Biomass Composition Distribution

![Biomass Composition Distribution](plots/composition/biomass_composition_distribution.png)
[Interactive Visualization](plots/composition/biomass_composition_distribution.html)
_Violin plot showing the distribution of key biomass composition parameters
(Xylan, Glucan, Arabinan, Lignin, Moisture, Ash Solids, Volatile Solids) across
all resources._

> **Source:**
> [`analysis/composition/biomass_composition_distribution.py`](analysis/composition/biomass_composition_distribution.py)
> | **Generated:** 2026-06-27 02:46 UTC

## Data Portal: Biomass Composition Distribution

![Portal Biomass Composition Distribution](plots/composition/portal_biomass_composition_distribution.png)
[Interactive Visualization](plots/composition/portal_biomass_composition_distribution.html)
_Violin plot showing the distribution of aggregated biomass composition averages
from the `data_portal` schema. Includes Xylan, Glucan, Arabinan, Lignin,
Moisture, Ash Solids, and Volatile Solids._

> **Source:**
> [`analysis/composition/portal_biomass_composition_distribution.py`](analysis/composition/portal_biomass_composition_distribution.py)
> | **Generated:** 2026-06-27 03:28 UTC

## Proximate Analysis Distribution

![Aim Record Distribution Proximate](plots/composition/proximate_distribution.png)
[Interactive Visualization](plots/composition/proximate_distribution.html)
_Multi-dimensional interactive dashboard of individual proximate analysis data
points. Features cross-filtering by Resource, Ag Product, Provider, QC Status,
and **Data Status** (Raw vs. Portal Compliant) using sidebar selectors._

> **Source:**
> [`analysis/composition/proximate_distribution_viz.py`](analysis/composition/proximate_distribution_viz.py)
> | **Generated:** 2026-06-27 17:20 UTC

## Compositional Analysis Distribution

[Interactive Visualization](plots/composition/compositional_distribution.html)
_Interactive dashboard for compositional analysis data points, including glucan,
xylan, and lignin. Features portal compliance filtering based on 40-105% dry
weight sum._

> **Source:**
> [`analysis/composition/compositional_distribution_viz.py`](analysis/composition/compositional_distribution_viz.py)
> | **Generated:** 2026-06-27 20:00 UTC

## Ultimate Analysis Distribution

[Interactive Visualization](plots/composition/ultimate_distribution.html)
_Interactive dashboard for ultimate analysis (C, H, N, O, S). Features whitelist
parameter filtering and 100% value constraints._

> **Source:**
> [`analysis/composition/ultimate_distribution_viz.py`](analysis/composition/ultimate_distribution_viz.py)
> | **Generated:** 2026-06-27 20:00 UTC

## ICP Analysis Distribution

[Interactive Visualization](plots/composition/icp_distribution.html)
_Interactive dashboard for ICP-OES elemental analysis. Features unit-based
filtering (ppm) and 500,000 ppm threshold for portal compliance._

> **Source:**
> [`analysis/composition/icp_distribution_viz.py`](analysis/composition/icp_distribution_viz.py)
> | **Generated:** 2026-06-27 20:00 UTC

## XRF Analysis Distribution

[Interactive Visualization](plots/composition/xrf_distribution.html)
_Interactive dashboard for XRF analysis data distribution across resources._

> **Source:**
> [`analysis/composition/xrf_distribution_viz.py`](analysis/composition/xrf_distribution_viz.py)
> | **Generated:** 2026-06-27 20:00 UTC

## XRD Analysis Distribution

[Interactive Visualization](plots/composition/xrd_distribution.html)
_Interactive dashboard for XRD analysis data distribution._

> **Source:**
> [`analysis/composition/xrd_distribution_viz.py`](analysis/composition/xrd_distribution_viz.py)
> | **Generated:** 2026-06-27 20:00 UTC

## Fermentation Analysis Distribution

[Interactive Visualization](plots/conversion/fermentation_distribution.html)
_Interactive dashboard for Aim 2 fermentation data. Features sugar consumption
consistency validation, yield percentage constraints, and cross-filtering by Ag
Product and Provider._

> **Source:**
> [`analysis/conversion/fermentation_distribution_viz.py`](analysis/conversion/fermentation_distribution_viz.py)
> | **Generated:** 2026-06-28 20:58 UTC

## Pretreatment Analysis Distribution

[Interactive Visualization](plots/conversion/pretreatment_distribution.html)
_Interactive dashboard for Aim 2 pretreatment analysis data. Features
multi-dimensional cross-filtering by Resource, Provider, and Pretreatment Method
(Experiment)._

> **Source:**
> [`analysis/conversion/pretreatment_distribution_viz.py`](analysis/conversion/pretreatment_distribution_viz.py)
> | **Generated:** 2026-07-08 19:15 UTC

## Gasification Analysis Distribution

[Interactive Visualization](plots/conversion/gasification_distribution.html)
_Interactive dashboard for Aim 2 gasification data distribution across reactor
types. Now includes filtering by Ag Product and Provider._

> **Source:**
> [`analysis/conversion/gasification_distribution_viz.py`](analysis/conversion/gasification_distribution_viz.py)
> | **Generated:** 2026-06-28 20:58 UTC

## Database Metadata Dashboard

[Interactive Analysis Distribution](plots/metadata/database_analysis_type_dist.html)
| [Interactive Resource Stats](plots/metadata/database_resource_stats.html) |
[Interactive Resource Hierarchy](plots/metadata/database_resource_hierarchy.html)
|
[Interactive Samples Over Time (Resource)](plots/metadata/database_samples_over_time.html)
|
[Interactive Samples Over Time (Product)](plots/metadata/database_samples_over_time_ag.html)

_A cohesive dashboard package outlining database metadata, including
distribution of observations by analysis type, sample/supplier counts for top
resources, and a hierarchical breakdown of resource classifications and primary
products._

> **Source:**
> [`analysis/metadata/database_metadata_dashboard.py`](analysis/metadata/database_metadata_dashboard.py)
> | **Generated:** 2026-06-28 19:27 UTC

## Sample Lineage Flow

[Interactive Visualization](plots/lineage/sample_lineage_flow.html) _Sankey
diagram showing the flow of samples from Resource through Field Sample and
Prepared Sample to final Analysis records. Flows are color-coded by Primary Ag
Product._

> **Source:**
> [`analysis/sample_lineage_flow_viz.py`](analysis/sample_lineage_flow_viz.py)

## Biomass Composition: Moisture vs Ash

[Interactive Visualization](plots/composition/moisture_vs_ash.html) _A
comparison of moisture and ash content across all biomass resources. Almond
residues are highlighted in yellow to show their specific positioning relative
to other feedstocks._

> **Source:**
> [`analysis/composition/moisture_vs_ash_viz.py`](analysis/composition/moisture_vs_ash_viz.py)
> | **Generated:** 2026-07-08 20:13 UTC
