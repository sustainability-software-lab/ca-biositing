# ICP Domain Context

- **Undetected Elements**: Many ICP records include a standard set of elements.
  If an element was not detected, it is recorded as **0.0** or a very low
  number. Do NOT flag these zeros or extremely low values as anomalies; treat
  them as "Below Detection Limit" (BDL).
- **Legacy Records**: Do not flag harvest_date variance for legacy ICP records.
- **Missing Units**: Missing units for elemental mass fractions (e.g., mg/kg)
  are common in older datasets. Note them as "legacy unit omission" but do not
  treat as critical errors if magnitudes are reasonable.
- **Silicon (Si) Outliers**: Z-scores between 3 and 5 for Silicon (Si) in
  agricultural residues (e.g., corn stover, grass-based residues) often indicate
  soil contamination rather than data errors. These are expected and should be
  prioritized lower.
