# Biomass Fermentation Domain Context

## Target Overview

The `mv_biomass_fermentation` target tracks bioconversion yields (e.g., ethanol,
3HP) from various biomass substrates using specific microbial strains and
pretreatment methods. This data is typically collected via high-throughput,
low-volume assays where a standard assay might have different pretreatment
methods applied.

## Experimental Structure

The fermentation assay tracks values from the beginning of fermentation (T0) to
the end of fermentation (TEOF):

- **T0 (Start)**: Initial sugar concentrations are measured (e.g., `SugarT0`,
  `GluConcT0`, `XylConcT0`). These are the "input" values.
- **TEOF (End)**: Final product concentrations and residual sugars are measured
  (e.g., `EtOHtiter`, `EtOHyield`, `SugarTEOF`, `OD600TEOF`). These are the
  "output" values.
- **EFT (Elapsed Fermentation Time)**: The duration in hours between T0 and
  TEOF.

_Note for reasoning_: T0 and TEOF values for the same `record_id` are linked.
When evaluating anomalies, consider if a low TEOF product yield correlates with
a low T0 initial sugar concentration.

## Audit Dimensions & Reasoning

- **Microbial Strain (`strain_name`)**: Performance is highly dependent on the
  strain. Inconsistencies across the same strain for different resources might
  indicate contamination or incorrect strain labeling.
- **Pretreatment Method (`pretreatment_method`)**: The method used to prepare
  the biomass (e.g., cholinium lysinate concentration) significantly impacts the
  availability of fermentable sugars and subsequent yields.
- **Reactor Vessel (`reactor_vessel`)**: Specific reactor types have different
  oxygen transfer rates and scalability profiles. Anomalies clustered by vessel
  often suggest mechanical issues or calibration drift.
- **Primary Product (`primary_product`)**: This refers to the agricultural
  commodity (e.g., Corn, Almonds, Wheat). Yields should be reasonable for the
  specific carbohydrate profile of that product.

## Parameter Definitions & Expected Ranges

### Product (Bioconversion Output)

- **`EtOHtiter` (Ethanol concentration)**: End point concentration. Unit: `g/L`.
  Expected: < 100 g/L.
- **`EtOHrate`**: Unit: `g/Lh`. Expected: < 5 g/Lh. Very high rates suggest unit
  error.
- **`EtOHyield`**: Unit: `mol%`. Expected: < 100 mol%. Values >100 are
  physically impossible.
- **`3HPtiter` (3 Hydroxypropionate)**: Unit: `g/L`.
- **`3HPrate`**: Unit: `g/Lh`.
- **`3HPyield`**: Measured as grams 3HP produced per gram carbon consumed. Unit:
  `g/g`. Expected: ~1.0 g/g max.

### Fermentable Carbon (Sugars)

- **Concentrations (`Fructose_gL`, `Mannose_gL`, `SugarT0`, `SugarTEOF`,
  `GluConcT0`, `XylConcT0`, `GluConcTEOF`, `XylConcTEOF`)**: Unit: `g/L`.
- **Yields (`Glucose_yld`, `Xylose_yld`, `Sugar_yld`)**: Percentage of
  glucan/xylan/sugar. Unit: `%`.
- **Consumption (`Glucose_cons`, `Xylose_cons`, `Sugar_cons`)**: Percentage
  consumed. Unit: `%`. Expected: 0-100%. Cannot consume more than 100%.

### Lignin (Pretreatment Output)

- **`Lignin`, `G-Lignin_pc`, `H-Lignin_pc`, `S-Lignin_pc`**: Percentages. G+H+S
  should sum to ~100% of total lignin. Unit: `%`.

### Fermentation Growth

- **`OD600TEOF`**: A measure of growth density at the end of fermentation.
  Unitless. Expected: 0.1-5.0. Values >10 are unusual for this assay.
- **`Rel_growth` (growth relative)**: OD600EOF / (OD600EOFave for synthetic
  media). Unit: `%`. Expected: 0-200%. >200% is unusual; negative values
  indicate growth inhibition.

### Pretreatment Conditions

- **`TotSug` (total sugar)**: Unit: `g/L`.
- **`ChoLys_pc` (cholinium lysinate concentration)**: Ionic liquid pretreatment
  agent. Unit: `%`.

### Fermentation Timing

- **`EFT` (Elapsed fermentation time)**: Unit: `hours`. Expected: 24-120h.

## Known Anomalies & Expected Patterns

- **Baseline Zeros**: Small negative values or exact zeros for product
  concentration in the first 2 hours of a fermentation are expected; do not flag
  as data errors unless they persist at the harvest timepoint.
- **Inoculum Effects**: High variance in initial `observed_value` for biomass
  concentration may indicate inconsistent inoculum preparation by the
  `analyst_email`.
- **Note Field Context**: Always check the `note` field for mentions of
  "contamination", "leak", or "power failure" which may explain outliers.
