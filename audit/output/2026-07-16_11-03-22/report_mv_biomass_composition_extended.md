# ⚠️ Anomaly Report — 2026-07-16

**Audit Target:** mv_biomass_composition_extended

**Flagged Observations:** 261 (0 HIGH, 0 MEDIUM, 261 LOW)

**Z-Score Threshold:** 1.0 | **Min Group Size:** 3

**[🔗 View and Manage Anomalies in Google Sheets](https://docs.google.com/spreadsheets/d/10aFbZznW6dH_3iZZqJm0dcDNPKXDqOFcE1FLAVGt52U)**

---

## 🧠 LLM Synthesis

This audit report for `mv_biomass_composition_extended` provides a holistic synthesis of the data distribution and flagged anomalies, focusing on identifying root causes and actionable insights.

---

### Holistic Synthesis: mv_biomass_composition_extended Audit

**Distribution Shape Overview:**
The dataset consists of 215 unique observations, with an average analytical value of approximately 22.05% dry weight and a relatively high standard deviation of 12.34, indicating significant variability in biomass component values across the dataset. The average number of observations per unique resource/parameter group is 3.77, with a minimum of 3 and a maximum of 9, suggesting that statistical comparisons are generally based on a small number of samples per group. The flagging mechanism identifies observations with z-scores exceeding 1.0, indicating values that deviate from their respective group means by at least one standard deviation. This threshold is relatively sensitive, flagging values that are mildly anomalous rather than only extreme outliers.

**Cross-Parameter and Cross-Resource Patterns:**
A total of 253 anomalies were flagged. The most frequently flagged parameters are **xylan (56), xylose (53), glucose (48), glucan (48), and lignin (46)**. These are fundamental components of biomass, and their frequent flagging suggests potential systemic issues related to their measurement. A strong pattern observed is the co-occurrence of anomalies for chemically related parameters:
*   **Glucose and Glucan**: For instance, `(a8)29ea` (glucose) and `(a8)a893` (glucan) for 'almond hulls' are both flagged with high z-scores (2.47). Similarly, many other glucose/glucan pairs for the same `record_id` and resource are flagged together, reinforcing their chemical relationship (glucose is a monomer of glucan/cellulose).
*   **Xylose and Xylan**: A similar trend is seen with xylose and xylan, where `(da)0242` (xylose) and `(da)6f36` (xylan) for 'wheat straw' are both flagged.
This consistent co-flagging points towards analytical methods that affect the quantification of both the polymer and its constituent monomer, or vice-versa, for the same sample.

In terms of resources, **almond hulls (37 anomalies)**, **almond shells (24 anomalies)**, and **almond branches (20 anomalies)** exhibit a disproportionately high number of flagged observations. This suggests that samples derived from almond biomass are particularly prone to generating anomalous results, either due to inherent variability, unique compositional characteristics, or challenges specific to their analysis.

Further, a critical pattern emerges from the `record_id` prefixes. Many anomalies cluster under specific two-character prefixes, which often denote individual analysts, laboratories, or sample batches. For example, prefixes `(a8)` (9 anomalies, mostly almond hulls, glucose/glucan/xylose/xylan), `(da)` (7 anomalies, mostly wheat straw, various carbohydrates), `(71)` (6 anomalies, all almond shells, various carbohydrates and lignin), and `(b8)` (6 anomalies, all alfalfa, various carbohydrates and lignin) are highly represented among the flagged observations. This strong clustering by presumed analytical source is a powerful indicator of systematic rather than random errors.

**Root Causes Analysis:**
The observed patterns point to several likely root causes:
1.  **Analyst/Laboratory-Specific Methodological Deviations**: The clustering of anomalies by `record_id` prefixes strongly suggests that specific analysts, laboratories, or analytical batches are producing data that deviates from the overall population mean. This could be due to inconsistencies in:
    *   **Equipment calibration**: Improper or infrequent calibration leading to systematic biases.
    *   **Sample preparation**: Variations in hydrolysis conditions (for carbohydrates), extraction, or other preparatory steps.
    *   **Procedural adherence**: Inconsistent application of Standard Operating Procedures (SOPs).
2.  **Resource-Specific Analytical Challenges**: Almond biomass (hulls, shells, branches) appears to be particularly problematic. This could be due to:
    *   **Matrix effects**: Complex sample matrices interfering with analytical methods.
    *   **Natural variability**: While some natural variation is expected, the high frequency and consistent nature of co-flagged parameters suggest more than just natural range.
    *   **Lack of suitable controls**: Insufficient or inappropriate quality control (QC) samples specifically for these challenging matrices.
3.  **Analytical Method Limitations**: Given the co-flagging of glucan/glucose and xylan/xylose, there might be inherent limitations or sensitivities in the analytical methods used for carbohydrate quantification (e.g., acid hydrolysis, subsequent chromatography) that lead to consistent over- or under-estimation for certain samples or batches.
4.  **Data Entry/Processing Errors**: While z-scores are calculated from values, systematic data entry errors, or errors during initial data processing and aggregation, cannot be entirely ruled out if one specific analyst or lab handles their data in a unique way.

**Action Items:**
To address these findings, the following action items are recommended:

1.  **Prioritize Investigation by `record_id` Prefix**:
    *   Identify the analysts, labs, or batches associated with the prefixes `(a8)`, `(da)`, `(71)`, `(b8)`, `(b3)`, `(42)`, `(3c)`, `(15)`, `(62)`, `(7e)`, `(c7)`.
    *   Conduct a targeted review of their analytical logs, equipment calibration records, and specific SOP adherence for the flagged periods/samples.
    *   Interview personnel involved to understand their processes and identify potential deviations.
2.  **Deep Dive into Problematic Parameters and Resources**:
    *   Review the analytical methods for `xylan`, `xylose`, `glucose`, `glucan`, and `lignin` to identify common points of failure or sensitivity, especially concerning almond biomass.
    *   Implement enhanced quality control procedures, including more frequent calibration and the use of matrix-matched reference materials for almond-derived samples.
3.  **Cross-Validation of High-Z-Score Anomalies**:
    *   For the most extreme outliers (e.g., z-scores > 2.0), attempt to re-analyze retained samples if available.
    *   Compare results from different labs/analysts for similar samples to establish inter-laboratory comparability.
4.  **Review Z-Score Thresholds**:
    *   Evaluate if the current z-score threshold of 1.0 is appropriate across all parameters and resources. Consider a tiered flagging system where higher z-scores trigger more immediate and intensive investigation, while lower z-scores serve as early warning indicators.
5.  **Training and Standardization**:
    *   Based on findings from the investigations, provide targeted training to analysts on SOPs, calibration, and sample preparation, particularly for challenging biomass types.
    *   Ensure strict standardization of methods across all participating laboratories or analysts to minimize inter-operator variability.

By focusing on the identified clusters of anomalies by `record_id` prefix, problematic parameters, and high-frequency resources, the data team can efficiently pinpoint the root causes and implement effective corrective actions to improve the data quality for the CA Biositing project.
