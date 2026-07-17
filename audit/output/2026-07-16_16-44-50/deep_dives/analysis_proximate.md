# Analysis Type Review: proximate

## Summary
- **Total Flagged Observations:** 307
- **Resources Impacted:** 32

## Resource Impact Breakdown
| resource_name            |   count |
|:-------------------------|--------:|
| tomato pomace            |      44 |
| almond hulls             |      38 |
| grape pomace             |      31 |
| almond shells            |      21 |
| walnut tree sticks       |      18 |
| almond branches          |      18 |
| cotton stem mix          |      17 |
| spent oak chips          |      12 |
| grape stem               |      12 |
| spent yeast              |      10 |
| unused oak stick         |      10 |
| walnut shells            |       7 |
| rice straw               |       6 |
| pistachio hulls          |       6 |
| corn stover cobs         |       5 |
| olive prunings           |       4 |
| wheat straw              |       3 |
| olive pomace             |       3 |
| grape vines              |       3 |
| corn stover whole        |       3 |
| walnut shelling fines    |       3 |
| peach tree prunings      |       3 |
| corn stover stalks       |       3 |
| rice hulls               |       3 |
| corn stover husks        |       3 |
| lees                     |       3 |
| pistachio stems & leaves |       3 |
| grape vine prunings      |       3 |
| peach screening waste    |       3 |
| olive stems / leaves     |       3 |
| peach pomace             |       3 |
| peach stems / leaves     |       3 |

## Parameter Breakdown
| parameter_name   |   count |
|:-----------------|--------:|
| volatile solids  |     117 |
| total solids     |     112 |
| moisture         |      78 |

## Top 10 Anomalies
| record_id   | resource_name    | parameter_name   |   observed_value |   z_score | severity   |
|:------------|:-----------------|:-----------------|-----------------:|----------:|:-----------|
| (c4)29ca    | unused oak stick | volatile solids  |             9.25 |   764.519 | HIGH       |
| (c4)48ba    | unused oak stick | volatile solids  |             9.8  |   759.809 | HIGH       |
| (c4)08a8    | unused oak stick | volatile solids  |            10.8  |   751.244 | HIGH       |
| (e8)9f94    | spent yeast      | moisture         |             1.57 |   356.977 | HIGH       |
| (c4)821f    | unused oak stick | total solids     |            89.06 |   193.261 | HIGH       |
| (c4)3411    | unused oak stick | total solids     |            89.99 |   174.408 | HIGH       |
| (82)bb5d    | walnut shells    | volatile solids  |             1.54 |   167.928 | HIGH       |
| (82)ebbf    | walnut shells    | volatile solids  |             1.67 |   167.679 | HIGH       |
| (82)0834    | walnut shells    | volatile solids  |             2.14 |   166.782 | HIGH       |
| (c4)aa4e    | unused oak stick | total solids     |            90.61 |   161.839 | HIGH       |
