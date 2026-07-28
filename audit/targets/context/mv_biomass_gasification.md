# mv_biomass_gasification

## Target Overview

This data represents gasification syngas composition and yield data. It tracks
the performance of different biomass resources when subjected to gasification
processes in various reactor types.

## Audit Dimensions & Reasoning

- **`provider_codename`**: Different providers may supply biomass with varying
  characteristics (e.g., moisture content, ash content) that can influence
  gasification yields and syngas composition.
- **`reactor_type`**: The type of gasification reactor (e.g., fluidized bed,
  entrained flow) significantly impacts the process conditions (temperature,
  residence time) and consequently the product distribution.
- **`analyst_email`**: Can help identify potential systematic errors or biases
  introduced by specific operators during sample preparation or analysis.
- **`experiment_date`**: Useful for detecting temporal trends or shifts in
  equipment performance over time.

## Known Anomalies & Expected Patterns

- **High Variance in Syngas Composition**: Syngas composition (H2, CO, CO2, CH4)
  can vary significantly depending on the specific biomass feedstock and reactor
  conditions.
- **Trace Contaminants**: Certain parameters like tar or particulate matter
  might have high variance or frequent non-detects depending on the gas cleanup
  system used.
