Final synthesis — BioCirV Exploratory Precision & Outlier Analysis
Goal

Create one comprehensive, colleague-facing Markdown report summarizing the completed BioCirV Exploratory Outlier & Variance Analysis.

The analysis itself is complete through Steps 0–10. This task is verification + synthesis only, not another analysis step.

The final report should explain:

what data and questions were included;
what we learned about replicate precision;
why relative and absolute variability need to be distinguished;
what the candidate outlier/high-variance screens detect;
how large the resulting review backlog is and where it is concentrated;
how that backlog can be organized into practical human investigations;
implications for analysts;
implications for frontend data visualization;
what remains unresolved and should be discussed by the team.

Do NOT describe this work as an “MVP.” Use:

Exploratory Outlier & Variance Analysis

throughout.

Critical guardrail: Steps 0–10 are frozen

Do NOT:

modify any Step 0–10 scripts;
modify any existing Step findings documents;
modify any Step 0–10 CSV outputs;
rerun the statistical pipeline;
change RSD, Dixon, or 3×SD methodology;
implement ROUT;
introduce new statistical thresholds;
create new exploratory analyses;
create new figures or CSVs;
state or imply that a statistical flag establishes that an observation is wrong or should be deleted.

You MAY perform simple arithmetic/checks needed to verify values already reported, such as percentages, denominator checks, enrichment ratios, or review-time conversions.

Create one new file only:

audit/outliers/biocirv_outlier_assessment/BIOCIRV_REPLICATE_PRECISION_OUTLIER_ASSESSMENT.md

1. Verify source material before writing

Before drafting the report, inspect the current analysis directory and verify the values you will use.

Read the relevant findings documents:

README.md
STEP0_FINDINGS.md
STEP2_FINDINGS.md
STEP3_FINDINGS.md
STEP4_5_FINDINGS.md
STEP6_FINDINGS.md
STEP8_FINDINGS.md
STEP9_FINDINGS.md
STEP10_FINDINGS.md
favorite_findings_sections.md if present

Also inspect the current output CSVs as needed, especially:

outputs/replicate_group_summary.csv
analysis×parameter summary output
precision-model diagnostics output
Step 8 candidate-rule comparison/overlap outputs
outputs/flagged_review_queue.csv
outputs/review_queue_by_analysis_parameter.csv
outputs/review_queue_by_dimension_summary.csv
outputs/investigation_packets.csv
outputs/human_review_priorities.csv
Verification expectations

Confirm against the current files rather than blindly copying numbers from this prompt.

Expected major invariants include:

2712 replicate groups total
RSD >10: 407
RSD >20: 177
Dixon: 246
exploratory 3×SD: 51
flagged by at least one of RSD>20 / Dixon / 3×SD: 427
Step 9 queue: 427
investigation packets: 114
packet membership total: 427
final relative/absolute precision categories:
26 insufficient data
10 unclear
20 concentration-dependent mixed
13 approximately constant relative RSD
5 approximately constant absolute SD

Verify the final Step 10 priority table and its cumulative unique coverage directly from STEP10_FINDINGS.md / human_review_priorities.csv.

Source precedence / inconsistencies

Some earlier findings documents may contain terminology or numerical framing that was corrected later.

Prefer the latest corrected outputs/findings for that topic, particularly:

corrected precision diagnostics for relative/absolute behavior;
final Step 8 candidate-screen counts;
corrected Step 9 terminology and baseline/enrichment framing;
final Step 10 review priorities.

If two current sources genuinely conflict and there is no obvious corrected/latest source resolving them, do not silently invent a resolution. Note the inconsistency in your completion summary and use cautious wording in the report.

Correct human-facing terminology throughout:

provider = source/provider (Source_codename), not laboratory
sample preparation method = legacy normalized method field, not analytical method

Do not call rigging a lab.

Do not call knife mill (2mm) or oven dry + knife mill (2mm) analytical methods.

Writing approach

Write this as an analytical report for colleagues, not as a coding/pipeline log.

Explain only the methodology necessary to understand:

what a result means;
its denominator/applicability;
what conclusion is supported;
what conclusion is NOT supported.

Be generous with informative existing tables and figures.

Use concise prose around them so readers understand why each matters.

Add prominent callouts throughout:

Flagged for further discussion: ...

Flagged for further analysis: ...

Place these directly beside the relevant finding instead of collecting all unresolved issues at the end.

Step terminology

There is one exception where Step numbers should be prominent: the Methods overview table showing how Steps 0–10 built on one another.

Outside that table:

avoid Step numbers in section/subsection headings;
prefer descriptive headings such as “Observed Relative vs. Absolute Error Behavior” rather than “Step 6 Results”;
avoid repeatedly saying “Step 8 found…” or “Step 9 showed…” unless a Step reference is useful for traceability.
Report structure
1. Executive Summary

Keep this concise and decision-oriented.

Summarize:

scope of the exploratory analysis;
broad picture of replicate precision;
major analysis families / parameters needing attention;
final review backlog of 427 / 2712 replicate groups;
the fact that the statistical screens detect different forms of unusual replicate behavior;
concentration of the review burden;
ability to organize most of the backlog into a small number of coherent human investigations.

Avoid reducing analyses to “good” or “bad.”

Explicitly distinguish:

typical precision;
upper-tail variability;
flag rate;
raw contribution to the queue;
evidence sufficiency.

State clearly:

Statistical flag ≠ bad data. A statistical flag identifies a replicate group worth reviewing; it does not independently establish measurement error or justify exclusion.

2. Methods and Scope
Scope of the Exploratory Outlier & Variance Analysis

Briefly describe what was and was not evaluated.

Include:

focus on characterization measurements;
no bioconversion/process-performance data;
several characterization analyses were skipped if the available data/schema did not support this replicate-analysis workflow;
identify the analyses actually included using the source files;
the exploratory analysis used the available extracted dataset rather than querying the live BioCirV database;
future work would make this a repeatable workflow operating against the staging database.

Do not imply that staging/live integration already exists.

How the analysis activities built on each other

Include:

Step	Activity	Goal / question answered

Give a concise overview of Steps 0–10.

The table should make clear the progression:

replicate-group validation
→ replicate precision
→ candidate flags
→ analysis×parameter summaries
→ relative-vs-absolute error behavior
→ candidate-screen comparison
→ review backlog characterization
→ investigation consolidation
→ human-review prioritization.

This table is the primary place in the report where Step numbers should be used.

3. Precision Findings
What variability at different grains tells us

Explain the theory behind examining variability at several levels:

Replicate group

within-sample technical repeatability;
asks how consistently the same sample is measured under the same analysis/parameter conditions.

Independent sample

distinguishes within-sample analytical variability from differences among separate physical samples;
between-sample variation can reflect genuine material heterogeneity and should not automatically be interpreted as analytical error.

Analysis × parameter

pools many replicate groups for a particular measurement;
characterizes what precision typically looks like for that measurement across the dataset.

Analysis type

provides a higher-level view of whether precision concerns are broadly distributed across an analytical family or concentrated in particular parameters.

Explain why this is useful to BioCirV.

An absolute statement such as “SD = 3” is not inherently meaningful across all measurements. Whether SD=3 is small or large depends on:

units;
concentration/value range;
expected within-replicate precision;
whether error behaves more like constant absolute error or constant relative error.

Also explain the limits:

between-sample/resource variability is not automatically measurement error;
a precision distribution does not tell us which individual observation is wrong;
statistical summaries do not independently justify deletion;
sparse replicate evidence cannot support strong precision conclusions.
Metrics used to characterize precision

Preserve a useful version of the column-definition table in favorite_findings_sections.md.

Use a reader-friendly format such as:

Metric	Definition / denominator	How to interpret it

Include at minimum:

n_replicate_groups
n_independent_samples
replicate_n_counts
median replicate n
min/max/sample-mean span
median / Q1 / Q3 SD
median / Q1 / Q3 / P90 / P95 RSD
n_RSD_defined / % RSD defined
% RSD >10
% RSD >20
Dixon applicability
Dixon flagged %

Preserve these important qualifications:

absolute SD retains each parameter's units and should not be directly compared across unrelated parameters;
RSD is relative (%) and therefore better suited to comparing measurements operating at different concentration scales;
singleton groups have undefined SD/RSD where appropriate and were not coerced to zero;
RSD>10 and RSD>20 are exploratory comparison benchmarks here, not adopted BioCirV production thresholds;
ROUT was not implemented and should not be given a fabricated result.
Precision by analysis × parameter

Include a useful analysis×parameter table containing:

| Analysis | Parameter | n replicate groups | % RSD defined | Median RSD | P90 RSD | Median SD |

Keep enough rows to make the result substantive.

If the full table is manageable, include it.

If it is too long:

place a representative / notable subset in the main narrative;
place the complete table in the appendix.

Accompany the table with interpretation of:

typical precision;
upper-tail variability;
data sufficiency;
parameters with particularly notable patterns.
Precision by analysis type

Include:

| Analysis | Overall precision | Typical precision across parameters | Main issue | Parameters needing attention | Frontend implication |

Use nuanced wording supported by the actual metrics.

Important interpretive guardrails:

Proximate

Typical replicate precision may be generally good while some high-volume parameters still contribute many flagged groups.

Do not equate presence in the Step 10 review queue with poor overall precision.

For example, verify the final values for:

volatile solids;
total solids;
ash.

Volatile solids and total solids contribute meaningful numbers of flagged groups despite their overall flag rates being below the dataset-wide 15.7% baseline, while ash is somewhat more elevated.

Explain the distinction between:

typical precision and review-queue contribution.

XRF

Do not simply say “XRF is poor.”

XRF contributes a large share of the queue partly because it is the largest analysis family.

Verify and explain the difference between:

XRF's share of the dataset;
its overall flag rate;
the much higher flag rates of particular XRF parameters such as Rb, Cu, Sr, U and others.
Other analyses

Describe ICP, compositional, ultimate, XRD, etc. according to the actual evidence.

Sparse analyses should be described as insufficient evidence, not as high precision because they happened to produce few flags.

Add Flagged for further discussion callouts where parameter-level precision may warrant:

additional replicate collection;
analyst attention;
frontend context.
4. Relative vs. Absolute Error Behavior
Why distinguish relative and absolute variability?

Explain:

RSD / relative variability

How large is replicate disagreement relative to the magnitude of the measurement?

SD / absolute variability

How large is replicate disagreement on the measurement's absolute scale?

Explain why this distinction matters:

values near zero can produce very high RSD despite modest absolute differences;
some measurements may have roughly constant absolute error;
some errors may scale with concentration;
some measurements show mixed behavior;
therefore one universal RSD or absolute-SD error model may not work for every analysis×parameter.

Include this table:

What you see	Best interpretation
SD flat; RSD decreases with mean	Absolute-SD-like
SD rises with mean; RSD flat	Relative/RSD-like
Both strongly depend on mean	Neither simple model fits
Neither clearly depends on mean	Could be either; possibly too little range/data
High RSD mostly near zero	Possible low-concentration artifact; inspect absolute SD
Observed precision-model behavior

Verify and include the final category counts:

Category	Count
Insufficient data	26
Unclear	10
Concentration-dependent mixed	20
Approximately constant relative RSD	13
Approximately constant absolute SD	5

Explain the implication:

Only a minority of analysis×parameter combinations clearly support a constant-absolute-SD model; many behave more like relative error, mixed concentration dependence, unclear behavior, or lack sufficient evidence.

Use existing diagnostic figures generously if they help readers visually understand:

absolute-like;
relative-like;
mixed;
unclear.

Do NOT generate new figures.

Flagged for further analysis: Manually review mixed and unclear diagnostic plots before assigning an analysis×parameter to a relative- or absolute-error model.

Flagged for further analysis: During visual diagnostic review, consider labeling unusually extreme RSD>20 / 3×SD points with their replicate-group IDs so conspicuous cases can be traced directly back to source records.

5. Candidate Outlier & High-Variance Screens
What question does each screen ask?

Make this conceptual distinction prominent.

RSD >10 / RSD >20

Does this replicate group have unusually large overall disagreement relative to its own mean?

RSD is a relative, within-group statistic.

Dixon Q

Does one individual measurement appear unusually extreme relative to the other measurements in this same replicate group?

Dixon is also within-group, but focuses on a single extreme value rather than total group spread.

3× pooled within-replicate SD

Does an individual value deviate unusually far on an absolute scale relative to the historical within-replicate precision observed for this analysis×parameter?

This is a cross-group, absolute-scale comparator.

Explicitly state that it is exploratory only, not a proposed production threshold.

Screen applicability and review burden

Include a compact table:

| Screen | Flagged | % of all 2712 groups | Applicable groups | % of applicable groups flagged |

Verify the current values.

Expected values to confirm include:

RSD >10: 407; 1955 applicable
RSD >20: 177; same RSD-defined denominator
Dixon: 246; 1447 applicable
3×SD: 51; 1966 applicable

Retain the applicability denominators. Raw flag counts are misleading without knowing how many groups each screen could actually evaluate.

Agreement and disagreement among screens

Include enough overlap information to show that the screens are not redundant.

Preserve the useful RSD>20 × Dixon comparison if supported by the final files, as well as the final combined flag-category breakdown where useful.

Explain:

Low overlap is expected because the screens answer different statistical questions. It is not evidence that one method is “wrong.”

If space allows, retain tables showing parameters with the highest:

RSD>20 rates;
Dixon flag rates;
3×SD flag rates.

These are useful because they demonstrate that different screens prioritize different analysis×parameter combinations.

Connect the 3×SD limitation back to the relative/absolute analysis:

only a small number of combinations clearly behaved like approximately constant absolute SD, providing limited empirical justification for a universal absolute-SD screening model.

Flagged for further discussion: Which signal—or combination of signals—should eventually trigger routine analyst review?

6. Review Backlog and Investigation Prioritization
Size and composition of the review backlog

State the verified final result:

427 of 2712 replicate groups (15.7%) were flagged by at least one of:

RSD>20;
Dixon;
exploratory 3×SD.

Include the final flag-category breakdown where useful:

Dixon only;
RSD only;
3×SD only;
pairwise combinations;
all three.

Explain what the distribution tells us about the different screening mechanisms.

Where flags are concentrated

Retain useful tables showing both counts and denominators.

Analysis × parameter

Include the top contributors and their within-combination flag rates.

Highlight the difference between cases such as:

XRF/Rb, Cu, Sr, U: high raw counts and high within-parameter flag rates;
proximate ash: substantial review contribution with only modest enrichment;
proximate volatile solids / total solids: meaningful queue contribution despite below-baseline flag rates.
Analysis type

Include:

| Analysis | Flagged groups | % of 427 | All replicate groups | Flag rate |

Explain that raw contribution and per-group propensity are different.

Other review dimensions

Include the final baseline/enrichment table covering important examples such as:

experiment 47;
experiment 43;
XRF;
provider = rigging;
knife mill (2mm);
oven dry + knife mill (2mm).

Explain:

% of flagged queue

= where analyst workload is concentrated.

Flag rate / enrichment vs baseline

= whether that category is flagged more often than expected given how much data it contributes.

Maintain descriptive, non-causal wording.

Verify experiment 47's final figures and describe its rate as elevated relative to baseline, not “similar.”

Do not state that experiment/provider/preparation method “causes” poor data.

Consolidating cases into investigations

Explain the provisional grouping key:

analysis_type + parameter + experiment_id

Include the grouping-key comparison:

| Grouping key | n packets | Median group size | Max group size | Singleton packets | % singleton |

Include the existing alternatives:

base key;
+resource_id;
+provider;
+sample preparation method;
+protocol_version;
all metadata dimensions.

Explain the practical finding:

adding more metadata rapidly fragments the backlog into mostly singleton packets, whereas the base grouping provides substantially more consolidation.

Explicitly preserve this limitation:

experiment_id is a convenient review grouping key. The available data do not establish that it represents a specific common day/run/batch or a validated shared root cause.

Review effort

Include a short planning table.

Verify the arithmetic from the final backlog before presenting it.

Do not reproduce stale approximate workload numbers if they conflict with the final 427-case queue.

For any 5 / 10 / 15-minute scenarios:

label them hypothetical assumptions;
distinguish individual flagged cases from investigation packets;
do not imply one packet requires the same time as one individual case;
do not claim that packet-count reduction produces an equivalent labor reduction.
Human-review priorities

Reuse the final Step 10 priority table:

| Priority | Review target | Grain | Flagged groups in target | Flag rate | Enrichment vs baseline | Cumulative % of 427 flagged groups addressed | Why review / suggested focus |

Verify all values against the final Step 10 files.

Explain that cumulative coverage uses the union of unique replicate-group IDs, so overlapping review targets are not double-counted.

Highlight the practical finding:

a small number of coherent investigations can address most of the 427-group backlog.

Retain useful sub-focuses for major experiment-level priorities, such as:

dominant XRF parameters within experiment 47;
dominant ICP parameters within experiment 43.

Do not imply these are validated common-root-cause clusters.

Flagged for further discussion: Is analysis_type + parameter + experiment_id actually a useful investigation grain for the analysts who will conduct review?

Flagged for further discussion: What is a reasonable analyst review load? The answer depends not only on case count but on how much friction the review interface and documentation workflow create.

7. Implications for Analysts

Keep this section specific to what this exploratory analysis demonstrated.

Avoid generic recommendations such as “improve data quality” or “monitor trends.”

Address:

Prioritize coherent investigations rather than reviewing randomly

The flagged queue is concentrated enough that analyst review can begin with a small number of high-coverage experiment / analysis×parameter investigations.

Different flags imply different review questions
high RSD → investigate large overall replicate disagreement;
Dixon → investigate a potentially isolated extreme replicate;
3×SD → investigate unusual absolute deviation relative to historical precision, while retaining its exploratory status.
Flags need contextual review

An analyst may need:

individual replicate values;
source record IDs;
existing QC status / notes;
experiment context;
resource/sample context;
relevant preparation/method metadata.

Do not prescribe the final interface, but explain why the statistical flag alone is insufficient.

Existing QC and statistical screening are complementary

Most statistically flagged groups are currently marked pass.

Clarify that:

this does not automatically imply existing QC was wrong;
statistical screening can identify forms of replicate disagreement not represented by the existing QC field.

Mixed values such as fail,pass or pass,provisional represent mixed within-group QC statuses, not standalone QC categories.

Investigation grain remains provisional

The current packet structure is useful analytically but has not yet been validated with the people who will actually perform review.

Flagged for further discussion: Is the proposed investigation-packet grain useful to analysts?

Flagged for further discussion: What information must be visible together in an analyst-review interface to make disposition fast and credible?

Flagged for further discussion: What recurring review workload is operationally acceptable?

8. Implications for Frontend Data Visualization

Keep frontend communication distinct from backend statistical QC.

Do not recommend displaying a statistical flag to users as “bad data.”

Explain how the findings could instead inform communication of:

expected precision;
parameter-specific variability;
evidence sufficiency;
methodological context.

Include a conceptual table:

Finding in analysis	Possible frontend treatment
Typical precision well characterized	Ordinary presentation; precision context/metadata if useful
Parameter shows elevated or long-tailed variability	Parameter-specific variability caveat
Sparse replicate evidence	Indicate limited precision evidence rather than implying high precision
Relevant methodological/preparation differences	Provide methodological context where useful
Individual statistical flag	Backend review signal; do not automatically label as bad data

Ground the discussion in actual analysis findings.

XRF

XRF warrants substantial parameter-specific consideration, but do not imply that every XRF measurement is equally problematic.

Emphasize particular parameters with elevated flag rates rather than a blanket XRF warning.

ICP

Typical median precision may be reasonable while some parameters exhibit important upper-tail variability.

Avoid representing ICP with one universal precision statement.

Proximate

Several major parameters may have strong typical repeatability while still contributing flagged cases due partly to dataset size.

Avoid equating presence in the human-review queue with poor user-facing reliability.

Compositional

Summarize actual typical precision and parameter-specific exceptions from the findings.

Sparse evidence

For ultimate or other sparsely replicated measurements, distinguish:

“limited evidence about precision”

from

“high precision.”

Flagged for further discussion: Which precision/variability information is useful to BioCirV users versus appropriate only for internal QC?

Flagged for further discussion: Should frontend caveats be defined at the analysis level, analysis×parameter level, or only after analyst disposition of individual cases?

Flagged for further discussion: How should insufficient replicate evidence be represented so absence of evidence is not mistaken for evidence of high precision?

9. Data Quality Due Diligence — Questions for Further Discussion

Keep this short.

Summarize what the Exploratory Outlier & Variance Analysis demonstrates:

BioCirV can quantify replicate precision at measurement-specific grains;
different statistical signals identify complementary review candidates;
the resulting review burden is measurable;
the burden is concentrated enough to prioritize coherent investigations;
none of these statistical signals independently proves an observation is erroneous.

End with:

Proposed Data Quality Due Diligence principle: BioCirV preserves raw observations, screens analysis-ready data for predefined quality signals, and uses flagged cases to prioritize documented human review. Statistical flags initiate due diligence; they do not independently establish that a measurement is erroneous or justify deletion.

Clearly label this as a proposed principle, not a claim that production infrastructure already implements it.

Flagged for further discussion: What exactly should a BioCirV “Data Quality Due Diligence Guarantee” promise?

Relevant unresolved decisions include:

which signals trigger review;
what evidence analysts should inspect;
what constitutes sufficient disposition/documentation;
what review burden is acceptable;
which findings stay backend-only versus become frontend context.

Do not attempt to settle these questions in this report.

10. Appendix: Supporting Tables and Figures

Be generous with existing supporting evidence.

Keep explanatory tables and figures in the main narrative when they materially improve understanding.

Put exhaustive or secondary material in the appendix.

Strong appendix candidates include:

complete analysis×parameter precision table;
extended column-definition table if the main version is condensed;
additional relative-vs-absolute diagnostic figures;
full candidate-screen overlap tables;
top analysis×parameter lists for each screen;
extended backlog-by-dimension tables;
supplementary grouping-key tables;
other existing figures from Steps 0–10 that materially support conclusions.

Do not aggressively move figures into the appendix merely to shorten the report.

I will manually move additional figures and captions down later if the document becomes too long.

Do not duplicate the same complete figure/table in both main text and appendix. A condensed main table plus complete appendix table is fine.

When embedding existing figures, use valid relative Markdown paths and descriptive captions.

Final quality-control pass

Before finishing:

Verify that every important numerical statement has a denominator/context where needed.
Verify terminology:
provider, not lab;
sample preparation method, not analytical method.
Verify no section outside the Methods overview unnecessarily uses “Step X” as its conceptual heading.
Check that precision, flag rate, raw backlog contribution, and evidence sufficiency are not conflated.
Check that statistical flags are never described as proof of bad data.
Verify all workload arithmetic.
Verify all Step 10 cumulative percentages against the actual final output.
Confirm existing figures/tables rather than inventing new ones.
Confirm no Steps 0–10 files were modified.
Completion

Use attempt_completion to report:

path to the completed report;
major numerical invariants verified;
tables and figures kept in the main narrative;
tables and figures placed in the appendix;
all Flagged for further discussion and Flagged for further analysis callouts included;
any genuine unresolved inconsistencies found among the source files;
confirmation that Steps 0–10 were treated as frozen inputs and no existing analysis files were modified;
confirmation that the single overall report was the only file created.

---

Meeting follow-up 9/1/2026: add frontend-oriented flag prevalence views to the overall report. Do not change any flag logic or Steps 0–10.

The frontend developer said the most useful result is flagged data relative to total data volume at analysis and analysis×parameter grain, not just share of the 427-case queue.

Add/report for every analysis type:
n_flagged_groups
n_total_groups
flag_rate = n_flagged / n_total
enrichment_vs_baseline = flag_rate / (427/2712)
Add the same table at analysis_type × parameter grain. Prefer including all analysis×parameter combinations, including zero-flag combinations, by joining/aggregating against the full replicate-group dataset rather than only combinations present in flagged_review_queue.csv.
Add the same descriptive comparison at resource_type / feedstock grain:
flagged
total
flag rate
enrichment vs baseline.
Keep resource_id separate if individual resources are also useful.
For priority experiment_id investigations, make the entries interpretable rather than displaying only experiment_id=47. Add structured columns summarizing:
experiment_id
n flagged / n total
flag rate
enrichment
analyses represented
main flagged parameters
resource types
resource_ids if useful
providers
sample preparation methods

Do not imply experiment_id is a validated run/batch/root cause; retain the existing caveat.

In the overall report, put the analysis and analysis×parameter prevalence tables under Review Backlog and Investigation Prioritization → Flag prevalence by analysis and parameter, and use them as the quantitative basis for Implications for Frontend Data Visualization.

Preserve the distinction:

% of 427 flags = where review workload is concentrated
flag rate = how frequently data in that category are flagged
enrichment vs baseline = how that rate compares with the overall 15.7% rate.

This is descriptive aggregation of the already-established flags only; do not create new QC rules or statistical analyses.