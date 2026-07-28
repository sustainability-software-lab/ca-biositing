# compositional

## Target Overview

This data represents compositional analysis aggregated by resource and
parameter. It specifically focuses on the `compositional` analysis type, which
details the structural components of the biomass. There are some cananonical
parameters, such as xylan, glucan, xylose, glucose and lignin, and some samples
will also have arabinose and arabinan measurements.

## Audit Dimensions & Reasoning

- **`provider_codename`**: Different providers may supply biomass with varying
  characteristics that can influence the compositional analysis results.
- **`analyst_email`**: Can help identify potential systematic errors or biases
  introduced by specific operators during sample preparation or analysis.
- **`experiment_date`**: Useful for detecting temporal trends or shifts in
  equipment performance over time.

## Known Anomalies & Expected Patterns

- **Glucan and Xylan Correlation**: Xylan and glucan are derived or calculated
  values from xylose and glucose. Therefore, they should always be highly
  correlated. Arabinan is also a derived value from arabinose.
- **Lignin vs. Lignin +**: Both represent the acid detergent insoluble fraction.
  "Lignin +" signifies that there was substantial "non-lignin" like residue in
  this fraction, likely from polyphenols or insoluble carbohydrate. Most of the
  data is just "lignin", which is expected and acceptable.
- **Total Mass Closure**: The sum of all major compositional components will not
  necessarily constitute a complete mass closure (parts will not always sum to
  100%).
- **High Variance in Certain Parameters**: Some parameters, such as moisture
  content or specific elemental concentrations, may naturally exhibit high
  variance depending on the biomass source and environmental factors.

## Flagged Anomalies Examples

When reviewing grouped summaries, pay close attention to flagged anomalies and
their associated resource types for traceability. Examples of anomalies to look
out for:

- A specific resource type showing a significant deviation in the expected
  Glucan/Xylan ratio.
- Unusually high "Lignin +" values for a resource type not typically known for
  high polyphenol content.
- Mass closures significantly above or below 100% for a specific provider or
  analyst.
