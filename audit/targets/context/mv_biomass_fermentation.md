# Biomass Fermentation Domain Context

## Target Overview

The `mv_biomass_fermentation` target tracks bioconversion yields (e.g., ethanol,
succinic acid, lactic acid) from various biomass substrates using specific
microbial strains and pretreatment methods.

## Audit Dimensions & Reasoning

- **Microbial Strain (`strain_name`)**: Performance is highly dependent on the
  strain. Inconsistencies across the same strain for different resources might
  indicate contamination or incorrect strain labeling.
- **Reactor Vessel (`reactor_vessel`)**: Specific reactor types (e.g., 2L
  Sartorius, 96-well plate) have different oxygen transfer rates and scalability
  profiles. Anomalies clustered by vessel often suggest mechanical issues or
  calibration drift.
- **Primary Product (`primary_product`)**: This refers to the agricultural
  commodity (e.g., Corn, Almonds, Wheat). Yields should be reasonable for the
  specific carbohydrate profile of that product.
- **Yield Expectations**:
  - **Theoretical Maximums**: Ethanol yields should not exceed ~0.51 g ethanol /
    g glucose. Values significantly higher than this are likely unit errors or
    calculation mistakes.
  - **Unit Consistency**: Watch for `g/L` vs `g/g` substrate. A swap here can
    cause 10x-100x order-of-magnitude errors.

## Known Anomalies & Expected Patterns

- **Baseline Zeros**: Small negative values or exact zeros for product
  concentration in the first 2 hours of a fermentation are expected; do not flag
  as data errors unless they persist at the harvest timepoint.
- **Inoculum Effects**: High variance in initial `observed_value` for biomass
  concentration may indicate inconsistent inoculum preparation by the
  `analyst_email`.
- **Note Field Context**: Always check the `note` field for mentions of
  "contamination", "leak", or "power failure" which may explain outliers.
