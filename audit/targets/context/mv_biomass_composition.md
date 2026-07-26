# mv_biomass_composition

## Target Overview

This data represents compositional analysis aggregated by resource and
parameter. It covers all AIM1 analysis types: compositional, proximate,
ultimate, xrf, icp, calorimetry, xrd, ftnir, and pretreatment.

## Audit Dimensions & Reasoning

- **`provider_codename`**: Different providers may supply biomass with varying
  characteristics that can influence the compositional analysis results.
- **`analysis_type`**: The specific type of analysis (e.g., compositional,
  proximate, ultimate) determines the expected parameters and their typical
  ranges.
- **`analyst_email`**: Can help identify potential systematic errors or biases
  introduced by specific operators during sample preparation or analysis.
- **`experiment_date`**: Useful for detecting temporal trends or shifts in
  equipment performance over time.

## Known Anomalies & Expected Patterns

- **High Variance in Certain Parameters**: Some parameters, such as moisture
  content or specific elemental concentrations, may naturally exhibit high
  variance depending on the biomass source and environmental factors.
- **Below Detection Limit (BDL) Zeros**: In analyses like ICP or XRF, trace
  elements might frequently be reported as zero or BDL, which is expected and
  should not necessarily be flagged as an anomaly unless it deviates from
  historical patterns for that specific resource.
