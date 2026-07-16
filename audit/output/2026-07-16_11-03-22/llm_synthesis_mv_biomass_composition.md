## Audit Report: mv_biomass_composition

### Distribution Shape
The `mv_biomass_composition` dataset contains 760 observations. The numerical distribution shows a wide range, with `min_value` at -244 and `max_value` at 161000. The mean value of 1985.11 and standard deviation of 9154.16 indicate a highly skewed distribution with significant outliers, which is consistent with the presence of flagged anomalies having extremely high Z-scores. The negative minimum value suggests data entry errors for at least one parameter.

### Cross-Parameter Patterns
A significant pattern emerges from the flagged observations, heavily concentrated in a few key parameter categories:
1.  **Percentage-based Measurements (Yields and Composition)**: `glucose_yld` (118 anomalies), `volatile solids` (117 anomalies), `xylose_yld` (114 anomalies), `total solids` (112 anomalies), and `moisture` (78 anomalies) account for the majority of flagged records.
    *   Many of these parameters (e.g., `volatile solids`, `total solids`, `moisture`) frequently include the note "uc combined protocol", suggesting a common source or processing method that might introduce errors.
    *   Extreme values are observed: `glucose_yld` at 118% is chemically impossible and clearly an erroneous entry. Some `volatile solids` measurements are very low (e.g., 9.25% with a Z-score of 764.519, 1.54% with Z-score 167.928) while associated `total solids` for the same resource are often high (e.g., unused oak stick total solids 89.06%).
    *   Instances where `moisture` and `total solids` sum approximately to 100% are both flagged (e.g., almond shells moisture 19.06% and total solids 80.95%), indicating that the anomaly detection threshold for these related parameters might be too sensitive or that their expected range in specific resources needs refinement. However, other flagged moisture values are extremely low (e.g., almond hulls 0.73%, 0.98%), which could be actual low values but also prone to error if not handled carefully.
2.  **Elemental Analysis (ppm values)**: Parameters like `s`, `cu`, `fe`, `mn`, `k`, `p`, `zn`, `si`, `u`, `ca`, `th`, `sr`, `rb`, `ba`, `mg`, `al`, `ti`, `ce`, `nd`, `mo`, `na`, `pr`, `pb`, `la` show a substantial number of anomalies.
    *   Several elemental concentrations are flagged with values of 0 ppm (e.g., `mn`, `la`, `rb`, `ce`, `mo`, `pr`, `pb`, `ti` in different resources), which could represent values below the detection limit incorrectly entered as zero, or actual zeros being flagged due to being extreme lows in the overall distribution.
    *   Negative concentrations (e.g., `na` at -55 ppm, -212 ppm, -220 ppm) are direct data entry errors.
    *   High ppm values are also flagged (e.g., Ba 2090 ppm, K 11100 ppm, Si 1150 ppm, Ca 4200 ppm).
3.  **Resource-Specific Concentration**: `grape pomace`, `almond hulls`, and `almond shells` are disproportionately represented in the flagged observations, indicating that data collected or processed for these specific biomass types might be particularly susceptible to issues. This could be due to specific analysis protocols, sample preparation challenges, or dedicated analysts/teams working on these materials.

### Root Causes
Based on the analysis, several likely root causes for the anomalies can be identified:

1.  **Data Entry/Transcription Errors**:
    *   **Impossible Values**: The presence of `glucose_yld` > 100% (118%), negative elemental concentrations (e.g., `na` at -55 ppm), and extremely low or zero values for parameters typically expected to be non-zero (e.g., 0 ppm for various elements) strongly suggest manual transcription errors or faulty data import processes.
    *   **Magnitude Errors**: Extremely high Z-scores (up to 764) point to values that are orders of magnitude off, likely due to misplaced decimal points, incorrect unit conversions (e.g., % instead of ppm, or vice-versa), or accidental repetition of digits.
2.  **Inconsistent Protocol Application/Interpretation**: The recurring "uc combined protocol" note for many percentage-based measurements (volatile solids, total solids, moisture) hints at potential inconsistencies in how this protocol is applied, how results are interpreted, or how they are recorded. This could also involve errors in the underlying calculation models or physical limitations of the measurement.
3.  **Missing Data Handling**: Values recorded as `0 ppm` for various elements may indicate that detection limits are not being handled appropriately. Instead of recording 0, a specific indicator for "below detection limit" or the actual detection limit value might be more appropriate.
4.  **Inadequate Data Validation**: The presence of chemically impossible values (e.g., >100% yield, negative concentrations) suggests a lack of robust validation checks during data ingestion or entry.
5.  **Resource-Specific Issues**: The high anomaly counts for certain resources (grape pomace, almond hulls/shells) suggest that particular biomass types might have unique analytical challenges, require specific handling procedures, or are analyzed by specific personnel who may benefit from further training or clearer guidelines.

### Action Items

1.  **Prioritize High Z-Score Anomalies**: Immediately investigate records with Z-scores greater than 100, as these represent the most egregious data quality issues.
2.  **Implement Data Validation at Source**:
    *   **Range Checks**: Enforce strict validation rules for numerical ranges (e.g., percentages between 0-100%, non-negative concentrations for ppm values).
    *   **Unit Consistency**: Verify that units are consistently applied and that numerical values correspond to the expected unit scale (e.g., prevent entry of a 90% total solids value as if it were 90 ppm).
    *   **Handling of Non-Detects**: Establish a clear protocol for recording values below the detection limit for elemental analyses, instead of arbitrary zeros, which can skew statistical analysis.
3.  **Review "uc combined protocol" Data**: Conduct a focused audit on all data tagged with "uc combined protocol".
    *   **Consistency Check**: Verify calculation and recording consistency for `volatile solids`, `total solids`, and `moisture` for all resources analyzed under this protocol. Specifically, confirm that `total solids` + `moisture` = 100% (or within an acceptable tolerance). If an expected inverse relationship holds, investigate why both values are flagged.
    *   **Parameter Definition**: Clarify the precise definitions and expected ranges for these parameters, particularly `volatile solids` which shows both very low and expected-range anomalies.
4.  **Resource-Specific Deep Dive**: Perform a targeted investigation into the data collection and processing workflows for `grape pomace`, `almond hulls`, and `almond shells` to identify specific procedural or equipment-related issues that might contribute to their high anomaly rates.
5.  **Analyst Training/Feedback**: If analyst information is available (not provided in this audit), identify analysts associated with high anomaly rates for specific parameters or resources and provide targeted training or feedback on data entry, calculation, and quality control procedures.
6.  **Review Anomaly Detection Thresholds**: For parameters where both logically consistent pairs (e.g., moisture and total solids summing to 100%) are flagged, review and potentially adjust the Z-score or other anomaly detection thresholds to be more tolerant of natural variation within expected ranges.
7.  **Standardize Data Input Forms/Systems**: Evaluate current data input forms or LIMS (Laboratory Information Management System) to ensure they minimize the potential for transcription errors and guide users towards correct data entry and unit selection.
