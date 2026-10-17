# Supplementary Information (SI): Agricultural Biomass Residue Factors & Volume Estimation Methodology

> [!IMPORTANT] **Journal-Grade Supplementary Information & Data Portal
> Methodology Reference (`Sub-Issue #7` /
> [#512](https://github.com/sustainability-software-lab/ca-biositing/issues/512))**
>
> - **Parent Tracking Epic**:
>   [#505](https://github.com/sustainability-software-lab/ca-biositing/issues/505)
>   (`Sub-Issues #506–#512`)
> - **Machine-Readable Companion Exports**:
>   [`docs/audit/si_residue_factor_reference_table.csv`](file:///Users/pjsmitty301/ca-biositing/docs/audit/si_residue_factor_reference_table.csv)
>   and
>   [`docs/audit/si_residue_factor_reference_table.json`](file:///Users/pjsmitty301/ca-biositing/docs/audit/si_residue_factor_reference_table.json)
> - **Zero Hardcoded Primary Key IDs Policy**: All resources, primary
>   agricultural products, units, and parameters in this reference table are
>   keyed by their **immutable canonical lowercase names** (`resource.name`,
>   `primary_ag_product.name`, `unit.name`, `parameter.name`), never by volatile
>   database integer primary keys.
> - **Single-Year Reporting Rule**: `data_portal.mv_biomass_volume_estimate`
>   stores a multi-year panel (`2023` and `2024` for County Ag Commissioner
>   paths; `2017` and `2022` for USDA Census paths). Regional totals must always
>   filter on a single `dataset_year`.

---

## S1. Governing Mathematical Framework (`data_portal.mv_biomass_volume_estimate`)

For each county $c \in \{\text{Merced (06047)},\, \text{San Joaquin (06077)},\,
\text{Stanislaus (06099)}\}$, year $t$, primary agricultural commodity $k$, and
biomass residue stream $i$, annual dry-matter availability
($V_{\text{dry},i,c,t}$, in bone-dry short tons $\text{yr}^{-1}$ at $0\%$
moisture) and as-generated wet availability ($V_{\text{wet},i,c,t}$, in wet
short tons $\text{yr}^{-1}$ at moisture fraction $\text{MC}_i \in [0, 1)$) are
governed by four mutually exclusive calculation paths:

### Case 1 — Weight-Based Processing & Field Residues (`Path A: ag_report_volume`)

Applied when County Agricultural Commissioner reports provide marketed or
crushed primary commodity tonnage $P_{k,c,t}$ (`parameter.name = 'production'`,
`unit.name = 'tons'`) and the residue factor is expressed per ton of
marketed/crushed commodity (`residue_factor.factor_type = 'weight'`):

$$V_{\text{dry},i,c,t} = P_{k,c,t} \times \alpha_{\text{proc},i} \times \beta_{\text{collect},i} \times f_{i,\text{dry}}, \qquad V_{\text{wet},i,c,t} = \frac{V_{\text{dry},i,c,t}}{1 - \text{MC}_i}$$

where:

- $f_{i,\text{dry}} = f_{i,\text{wet}} \times (1 - \text{MC}_i)$ is the
  **bone-dry residue factor** (dry tons of residue $i$ generated per
  marketed/crushed ton of commodity $k$ entering the pathway),
- $\alpha_{\text{proc},i} \in (0, 1]$ is the **processing pathway share**
  (fraction of harvested commodity $k$ routed through the specific processing
  operation that generates residue $i$, e.g., $\alpha_{\text{proc}} = 0.25$ for
  commercial pistachio shell cracking vs. $\alpha_{\text{proc}} = 1.00$ for
  pistachio hulling), and
- $\beta_{\text{collect},i} \in (0, 1]$ is the **sustainable or regulatory
  collectible fraction** (e.g., $\beta_{\text{collect}} = 0.40$ for corn grain
  stover soil-carbon conservation).

### Case 2 — Acreage-Based Orchard Prunings & Field Crop Straw/Stalks (`Path B: prune_acres` & `Path D: acreage_calc`)

Applied when residue generation scales with managed orchard or harvested
field-crop area $A_{k,c,t}$ (in acres, resolved via
`func.lower(obs_unit.name) = 'acres'` from USDA Census of Agriculture
observations):

$$A_{k,c,t} = \text{COALESCE}\!\left(A_{\text{area bearing \& non-bearing}},\, A_{\text{area bearing}},\, A_{\text{area harvested}}\right)$$

$$V_{\text{dry},i,c,t} = A_{k,c,t} \times \beta_{\text{collect},i} \times y_{i,\text{dry}}, \qquad V_{\text{wet},i,c,t} = \frac{V_{\text{dry},i,c,t}}{1 - \text{MC}_i}$$

where $y_{i,\text{dry}}$ is the dry pruning or field residue yield
(`dry tons / acre / yr`).

### Case 3 — Direct Byproduct Commodity Reporting (`Path C: commodity_direct`)

Applied when County Agricultural Commissioner reports publish direct marketed
byproduct tonnages $P_{i,c,t}$ (`'almond hulls'`, `'almond shells'`):

$$V_{\text{wet},i,c,t} = P_{i,c,t}, \qquad V_{\text{dry},i,c,t} = P_{i,c,t} \times (1 - \text{MC}_i)$$

### Case 4 — USDA Census/Survey Production Fallback (`Path E: usda_weight_calc`)

Applied only when `factor_type = 'weight'` and
`residue_factor.primary_ag_product_id IS NULL`, matching USDA NASS commodity
production via `resource_usda_commodity_map`:

$$V_{\text{dry},i,c,t} = \left(P_{k,c,t}^{\text{(USDA)}} \times \gamma_{\text{unit}}\right) \times \beta_{\text{collect},i} \times f_{i,\text{dry}}$$

where $\gamma_{\text{unit}}$ converts commodity reporting units to short tons
(e.g., $\gamma_{\text{unit}} = 0.028\text{ tons bu}^{-1}$ for $56\text{ lb
bu}^{-1}$ grain corn, strictly distinguishing grain corn in bushels from
whole-plant corn silage in wet tons).

### Additive Regional Aggregation & Substream Exclusion Rule

To prevent anatomical or processing double-counting (e.g., summing
`'corn stover stalks'`, `'corn stover cobs'`, and `'corn stover husks'` on top
of `'corn stover whole'`, or summing `'walnut shelling fines'` on top of
`'walnut shells'`), regional totals sum exclusively over primary streams
($\text{is\_substream}(i) = \text{false}$):

$$V_{\text{dry},\text{NSJV},t} = \sum_{c \in \{\text{06047, 06077, 06099}\}} \sum_{i:\, \neg\text{is\_substream}(i)} V_{\text{dry},i,c,t}$$

---

## S2. Master Supplementary Information (SI) Residue Factor Reference Table

| Resource (`resource.name`) | Primary Ag Product (`primary_ag_product.name`)   | Calculation Path                                                                        | Substream Status                 | Current DB Factor (`mid` `[range]`)                                                            | Verified Wet Factor ($f_{\text{wet}}$)                                                                  | Moisture ($\text{MC}_i$) | $\alpha_{\text{proc}}$ | $\beta_{\text{collect}}$ | **Verified Dry Factor ($f\_{\text{dry}}$: `min / mid / max`)**                                                                          | Single-Year NSJV Baseline `dry_tons` | **Remediated NSJV `dry_tons` (`wet_tons`)**       | Reference Cultivar & CA Region                                                                                                               | Primary Citations                                                                                                                                                                       |
| :------------------------- | :----------------------------------------------- | :-------------------------------------------------------------------------------------- | :------------------------------- | :--------------------------------------------------------------------------------------------- | :------------------------------------------------------------------------------------------------------ | :----------------------- | :--------------------- | :----------------------- | :-------------------------------------------------------------------------------------------------------------------------------------- | :----------------------------------- | :------------------------------------------------ | :------------------------------------------------------------------------------------------------------------------------------------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `almond hulls`             | `almond hulls`                                   | Case 3 (Path C: commodity_direct)                                                       | Primary                          | `1` (1.0 (direct tons))                                                                        | `2` (1.80 - 2.20 wet t/t kernel (or 1.00 direct hull t))                                                | 11.0%                    | 1.00                   | 1.00                     | **`0.88 / 0.89 / 0.9`** (dry t / marketed hull t (or 1.60 - 1.95 dry t / t kernel))                                                     | `973,672.0 t` (2023)                 | **`866,568.1 dry t`** (`973,672.0 wet t`, 2023)   | Nonpareil, Monterey, Butte/Padre, Wood Colony; San Joaquin Valley North (Merced, Stanislaus, San Joaquin)                                    | Aktas et al. (2015) Int. J. LCA 20:939-952; Offeman et al. (2014) Ind. Crops Prod. 54:109-115; Williams et al. (2015) CBC/CEC-500-2015-035; UC Davis Almond Cost Study SJV North (2024) |
| `almond shells`            | `almond shells`                                  | Case 3 (Path C: commodity_direct)                                                       | Primary                          | `1` (1.0 (direct tons; 3/6 rows in DB copy almond meats 1:1))                                  | `0.65` (0.50 - 0.80 air-dry t/t kernel (or 1.00 direct shell t))                                        | 9.0%                     | 0.90                   | 1.00                     | **`0.9 / 0.91 / 0.92`** (dry t / marketed shell t (or 0.45 - 0.73 dry t / t kernel))                                                    | `466,374.0 t` (2023)                 | **`300,824.0 dry t`** (`330,576.0 wet t`, 2023)   | Nonpareil (soft-shell ~0.45-0.55 t/t kernel) & Monterey/Butte/Padre (hard-shell ~0.65-0.85 t/t kernel); SJV North                            | Aktas et al. (2015) Int. J. LCA 20:939-952; Almond Board of California (2024) Almond Almanac; Williams et al. (2015) CBC/CEC-500-2015-035                                               |
| `almond branches`          | `almonds (USDA Census acreage)`                  | Case 2 (Path D: acreage_calc)                                                           | Primary                          | `1.5` (1.0 / 1.5 / 2.0 dry t/ac)                                                               | `1.67` (0.83 - 2.50 wet t/ac)                                                                           | 40.0%                    | 1.00                   | 0.70                     | **`0.5 / 1 / 1.5`** (dry t / bearing acre / yr (gross); 0.70 dry t/ac collectible)                                                      | `0 t` (2022)                         | **`783,568.5 dry t`** (`1,305,947.5 wet t`, 2022) | Nonpareil / Monterey; San Joaquin Valley North (minimal mechanical hedging vs. hand pruning)                                                 | UC Davis Cooperative Extension (2024) Sample Costs to Establish an Orchard and Produce Almonds, SJV North; Williams et al. (2015) CBC                                                   |
| `almond woodchips`         | `almonds (USDA Census acreage)`                  | Case 2 (Path B/D: orchard removals & chipped prunings; currently in EXCLUDED_RESOURCES) | Primary                          | `1.5` (RF_ID=6 (prune_trim_yield=1.5) & RF_ID=38 (commodity min=0.1))                          | `2` (1.67 - 2.50 wet t/ac/yr (amortized 25-yr Whole Orchard Recycling))                                 | 40.0%                    | 1.00                   | 0.35                     | **`1 / 1.2 / 1.5`** (dry t / acre / yr (gross amortized removal); 0.35 - 0.50 dry t/ac exported off-farm)                               | `0 t` (2022)                         | **`219,399.0 dry t`** (`365,665.0 wet t`, 2022)   | Nonpareil / Monterey; San Joaquin Valley North                                                                                               | Holtz et al. (2018) HortScience 53(11):1586-1587; Jahanzad et al. (2020) Ag. Ecosyst. Environ. 300:106993; Breunig et al. (2017)                                                        |
| `walnut shells`            | `walnuts`                                        | Case 1 (Path A: ag_report_volume)                                                       | Primary                          | `1.494` (1.34 / 1.494 / 1.647 (erroneous kernel-basis ratio applied to in-shell tons))         | `0.587` (0.54 - 0.63 air-dry shell t / t in-shell walnuts)                                              | 8.0%                     | 0.70                   | 1.00                     | **`0.5 / 0.54 / 0.58`** (dry t / t in-shell walnuts (anatomical); 0.35 / 0.378 / 0.406 at 70% cracking share)                           | `362,023.1 t` (2023)                 | **`152,442.0 dry t`** (`165,698.0 wet t`, 2023)   | Chandler (~48-52% shell), Hartley/Howard (~54-58% shell); San Joaquin Valley North                                                           | California Walnut Board (2024); USDA NASS CA Walnut Objective Measurement Report; UC Davis Walnut Cost Study SJV North (2023); Williams et al. (2015)                                   |
| `walnut shelling fines`    | `walnuts`                                        | Case 1 (Path A: ag_report_volume; Substream of walnut shells)                           | Substream of `walnut shells`     | `1.494` (1.34 / 1.494 / 1.647 (copy-paste duplicate of walnut shells))                         | `0.022` (0.011 - 0.033 air-dry t / t in-shell walnuts)                                                  | 8.0%                     | 0.70                   | 1.00                     | **`0.01 / 0.02 / 0.03`** (dry t / t in-shell walnuts (substream of walnut shells + packing septum/dust))                                | `362,023.1 t` (2023)                 | **`5,646.0 dry t`** (`6,137.0 wet t`, 2023)       | Chandler, Howard, Hartley; San Joaquin Valley North shelling plants                                                                          | California Walnut Commission Technical Bulletins; Williams et al. (2015) CBC                                                                                                            |
| `walnut hulls`             | `walnuts`                                        | Case 1 (Path A: ag_report_volume)                                                       | Primary                          | `0.524` (0.469 / 0.524 / 0.578)                                                                | `1.33` (1.10 - 1.60 wet green hull t / t in-shell walnuts)                                              | 82.0%                    | 1.00                   | 1.00                     | **`0.2 / 0.24 / 0.28`** (dry t / t in-shell walnuts (at 82% green hull moisture))                                                       | `126,974.6 t` (2023)                 | **`67,752.0 dry t`** (`376,400.0 wet t`, 2023)    | Chandler, Howard, Tulare; San Joaquin Valley North on-farm hullers/dehydrators                                                               | Thompson et al. (1998) Walnut Dehydration in Commercial Walnut Marketing; UC ANR Pub 21586; Holtman et al. (2015)                                                                       |
| `walnut tree sticks`       | `walnuts (USDA Census acreage)`                  | Case 2 (Path D: acreage_calc)                                                           | Primary                          | `0.6` (0.50 / 0.60 / 0.70 dry t/ac (prune_trim_yield=1.0))                                     | `1.33` (0.83 - 1.67 wet t/ac)                                                                           | 40.0%                    | 1.00                   | 0.70                     | **`0.5 / 0.8 / 1`** (dry t / bearing acre / yr)                                                                                         | `0 t` (2022)                         | **`70,666.8 dry t`** (`117,778.0 wet t`, 2022)    | Chandler, Howard, Hartley; San Joaquin Valley North (San Joaquin, Stanislaus, Merced)                                                        | UC Davis Cooperative Extension (2023) Sample Costs to Produce English Walnuts, SJV North; Williams et al. (2015) CBC                                                                    |
| `pistachio hulls`          | `pistachios`                                     | Case 1 (Path A: ag_report_volume)                                                       | Primary                          | `0.147` (0.118 / 0.147 / 0.177)                                                                | `1.375` (1.15 - 1.60 wet hull t / t dry in-shell pistachios)                                            | 80.0%                    | 1.00                   | 1.00                     | **`0.24 / 0.275 / 0.32`** (dry t / t dry marketable in-shell pistachios)                                                                | `10,862.6 t` (2023)                  | **`20,321.1 dry t`** (`101,605.6 wet t`, 2023)    | Kerman, Golden Hills, Lost Hills; San Joaquin Valley (note: ~88% of CA pistachio hulling is in South SJV)                                    | Ferguson & Haviland (2016) Pistachio Production Manual, UC ANR Pub 3545; American Pistachio Growers (2024); Demiral & Sensoz (2006)                                                     |
| `pistachio shells`         | `pistachios`                                     | Case 1 (Path A: ag_report_volume)                                                       | Primary                          | `0.15` (0.12 / 0.15 / 0.18)                                                                    | `0.132` (0.108 - 0.161 air-dry shell t / t harvested in-shell (at 25% cracking share); 0.49 anatomical) | 7.0%                     | 0.25                   | 1.00                     | **`0.1 / 0.123 / 0.15`** (dry t / t in-shell pistachios at commercial cracking share (0.44 / 0.49 / 0.52 anatomical))                   | `11,084.3 t` (2023)                  | **`9,089.1 dry t`** (`9,773.2 wet t`, 2023)       | Kerman, Golden Hills; SJV (Closed-boundary NSJV crop vs. Open-boundary South SJV central processing plants)                                  | Administrative Committee for Pistachios (ACP 2024) Statistical Report; Ferguson & Haviland (2016) UC ANR Pub 3545; Williams et al. (2015)                                               |
| `pistachio stems & leaves` | `pistachios`                                     | Case 1 (Path A: ag_report_volume)                                                       | Primary                          | `0.335` (0.17 / 0.335 / 0.50)                                                                  | `0.25` (0.15 - 0.35 wet huller trash t / t dry in-shell pistachios)                                     | 60.0%                    | 1.00                   | 1.00                     | **`0.06 / 0.1 / 0.15`** (dry t / t dry in-shell pistachios (huller receiving trash: rachis clusters, twigs, leaves, blanks))            | `24,754.8 t` (2023)                  | **`7,389.5 dry t`** (`18,473.8 wet t`, 2023)      | Kerman, Golden Hills; San Joaquin Valley                                                                                                     | Ferguson & Haviland (2016) UC ANR Pub 3545; UC Davis Pistachio Cost Study SJV South (2023)                                                                                              |
| `grape pomace`             | `grapes - wine`                                  | Case 1 (Path A: ag_report_volume)                                                       | Primary                          | `0.25` (0.20 / 0.25 / 0.30 (wet pomace factor applied without moisture deduction))             | `0.2` (0.15 - 0.25 wet pomace t / wet t crushed wine grapes)                                            | 62.5%                    | 1.00                   | 1.00                     | **`0.05 / 0.075 / 0.1`** (dry t / wet t crushed wine grapes)                                                                            | `219,195.5 t` (2023)                 | **`65,758.7 dry t`** (`175,356.4 wet t`, 2023)    | Cabernet Sauvignon, Zinfandel, Chardonnay, French Colombard; CA Crush Districts 11 (Lodi/SJ) & 12 (Stanislaus/Merced)                        | Jin et al. (2021) ACS Sustainable Chem. Eng. 9(45):15022-15035; Spigno et al. (2017); Williams et al. (2015) CBC; CDFA Grape Crush Report (2024)                                        |
| `grape stem`               | `grapes - wine`                                  | Case 1 (Path A: ag_report_volume; currently misconfigured as area with NULL factors)    | Primary                          | `N/A` (NULL in residue_factor; 1.1 dry t/ac copied from grape vines in resource_availability)  | `0.04` (0.030 - 0.050 wet rachis t / wet t crushed grapes)                                              | 72.5%                    | 0.50                   | 1.00                     | **`0.008 / 0.011 / 0.015`** (dry t / wet t crushed wine grapes (anatomical); 0.0055 dry t/t at 50% winery destemming share)             | `0 t` (2023)                         | **`9,644.6 dry t`** (`35,071.3 wet t`, 2023)      | Cabernet Sauvignon, Zinfandel, Chardonnay; Crush Districts 11 & 12 (Gallo Modesto/Livingston, Lodi wineries)                                 | Jin et al. (2021) ACS Sustainable Chem. Eng. 9:15022; Boulton et al. (1999) Principles and Practices of Winemaking; Bustamante et al. (2008)                                            |
| `grape vines`              | `grapes (USDA Census acreage)`                   | Case 2 (Path B: prune_acres)                                                            | Primary                          | `1.1` (prune_trim_yield = 1.10 dry t/ac (0.04 / 0.045 / 0.05 weight cols unused by Path B))    | `2` (1.45 - 2.70 wet t/ac)                                                                              | 45.0%                    | 1.00                   | 0.70                     | **`0.8 / 1.1 / 1.5`** (dry t / bearing acre / yr)                                                                                       | `0 t` (2022)                         | **`152,647.0 dry t`** (`277,540.0 wet t`, 2022)   | Wine, table, and raisin grapes; Crush Districts 11 & 12 (San Joaquin, Stanislaus, Merced)                                                    | UC Davis Cooperative Extension (2023) Sample Costs to Produce Winegrapes, Lodi/SJV North (Crush District 11); Williams et al. (2015) CBC                                                |
| `olive pomace`             | `olives`                                         | Case 1 (Path A: ag_report_volume)                                                       | Primary                          | `0.35` (0.20 / 0.35 / 0.50)                                                                    | `0.8` (0.65 - 0.90 wet alperujo t / wet t milled olives (2-phase decanter))                             | 65.0%                    | 1.00                   | 1.00                     | **`0.22 / 0.28 / 0.34`** (dry t / wet t milled olives)                                                                                  | `5,309.5 t` (2023)                   | **`4,247.6 dry t`** (`12,136.0 wet t`, 2023)      | Arbequina, Arbosana, Koroneiki (SHD oil olives) & Manzanillo; San Joaquin & Sacramento Valleys                                               | UC Davis Olive Center (2013) Olive Mill Waste Management in California; Roig et al. (2006) Waste Manage. 26:960-969; Dermeche et al. (2013)                                             |
| `orange pomace`            | `oranges`                                        | Case 1 (Path A: ag_report_volume; 0 County Ag Report rows in NSJV)                      | Primary                          | `0.5` (0.40 / 0.50 / 0.60 (wet juicing peel/pulp/rag fraction))                                | `0.5` (0.45 - 0.60 wet pomace t / wet t juiced oranges)                                                 | 80.0%                    | 0.20                   | 1.00                     | **`0.08 / 0.1 / 0.12`** (dry t / wet t juiced oranges (or 0.016 / 0.020 / 0.024 per total harvested orange t at 20% juice utilization)) | `0 t` (2023)                         | **`0 dry t`** (`0 wet t`, 2023)                   | Washington Navel, Valencia; San Joaquin Valley (primarily Tulare/Kern/Fresno; minor in Merced/Stanislaus)                                    | Braddock (1999) Handbook of Citrus By-Products and Processing Technology; Wilkins et al. (2007); USDA NASS Citrus Summary (2024)                                                        |
| `peach pomace`             | `peaches`                                        | Case 1 (Path A: ag_report_volume)                                                       | Primary                          | `0.24` (0.15 / 0.24 / 0.35 (wet cannery waste factor))                                         | `0.2` (0.15 - 0.25 wet cannery solid waste t / wet t canned peaches)                                    | 82.5%                    | 0.85                   | 1.00                     | **`0.02 / 0.035 / 0.05`** (dry t / wet t processed peaches)                                                                             | `31,974.7 t` (2023)                  | **`4,663.0 dry t`** (`26,645.6 wet t`, 2023)      | Loadel, Andross, Carson, Ross (Clingstone peaches); Stanislaus (Modesto/Turlock), Merced & San Joaquin canneries                             | Hanson et al. (2004) Food Processing Solid Waste in CA; Williams et al. (2015) CBC; UC Davis Cling Peach Cost Study SJV North (2023)                                                    |
| `peach peels`              | `peaches`                                        | Case 1 (Path A: Substream of peach pomace / cannery waste)                              | Substream of `peach pomace`      | `N/A` (NULL (counted under pomace))                                                            | `0.09` (0.06 - 0.12 wet peel t / wet t canned peaches)                                                  | 86.0%                    | 0.85                   | 1.00                     | **`0.008 / 0.013 / 0.018`** (dry t / wet t canned peaches (substream of peach pomace))                                                  | `0 t` (2023)                         | **`1,732.0 dry t`** (`11,990.5 wet t`, 2023)      | Clingstone peaches; Stanislaus & Merced County canneries                                                                                     | Katsabekis et al. (2004); Hanson et al. (2004) Food Processing Solid Waste in CA                                                                                                        |
| `peach seeds`              | `peaches`                                        | Case 1 (Path A: Cannery pitting stream)                                                 | Primary                          | `N/A` (NULL (counted under pomace))                                                            | `0.08` (0.06 - 0.10 wet pit t / wet t canned peaches)                                                   | 45.0%                    | 0.85                   | 1.00                     | **`0.033 / 0.044 / 0.055`** (dry t / wet t canned peaches)                                                                              | `0 t` (2023)                         | **`5,862.0 dry t`** (`10,658.2 wet t`, 2023)      | Clingstone peaches; Stanislaus & Merced County canneries                                                                                     | Jenkins et al. (1998) Biomass Bioenergy 14(3):197-241; Williams et al. (2015) CBC                                                                                                       |
| `corn stover whole`        | `corn - grain`                                   | Case 1 (Path A: ag_report_volume on 'corn - grain'; currently Path E on silage tons!)   | Primary                          | `1` (0.80 / 1.00 / 1.20 (applied in Path E to 5.32M tons of whole-plant corn silage!))         | `1` (0.85 - 1.15 air-dry stover t / air-dry grain t (at 14% MC))                                        | 14.0%                    | 1.00                   | 0.40                     | **`0.73 / 0.86 / 1`** (dry t / marketed grain t (gross); 0.344 dry t/t sustainable collectible (at 40% removal))                        | `5,320,641.3 t` (2023)               | **`91,369.0 dry t`** (`106,243.0 wet t`, 2023)    | Field corn for grain; San Joaquin Delta (San Joaquin County) & Merced/Stanislaus                                                             | Wilhelm et al. (2004) Agron. J. 96:1-17; Pordesimo et al. (2004) Biomass Bioenergy 26:337-349; UC Davis Field Corn Cost Study SJV/Delta (2023)                                          |
| `corn stover stalks`       | `corn - grain`                                   | Case 1 (Path A: Substream of corn stover whole)                                         | Substream of `corn stover whole` | `0.56` (0.45 / 0.56 / 0.67)                                                                    | `0.56` (0.50 - 0.62 air-dry stalk t / air-dry grain t)                                                  | 14.0%                    | 1.00                   | 0.40                     | **`0.43 / 0.482 / 0.53`** (dry t / marketed grain t (gross substream); 0.193 dry t/t sustainable)                                       | `2,979,559.1 t` (2023)               | **`51,209.1 dry t`** (`59,496.1 wet t`, 2023)     | Field corn for grain; San Joaquin Valley North / Delta                                                                                       | Pordesimo et al. (2004) Biomass Bioenergy 26:337-349                                                                                                                                    |
| `corn stover cobs`         | `corn - grain`                                   | Case 1 (Path A: Substream of corn stover whole)                                         | Substream of `corn stover whole` | `0.15` (0.12 / 0.15 / 0.18)                                                                    | `0.15` (0.13 - 0.17 air-dry cob t / air-dry grain t)                                                    | 14.0%                    | 1.00                   | 0.80                     | **`0.11 / 0.129 / 0.15`** (dry t / marketed grain t (gross substream); 0.103 dry t/t single-pass cob caddy)                             | `798,096.2 t` (2023)                 | **`13,705.3 dry t`** (`15,936.5 wet t`, 2023)     | Field corn for grain; San Joaquin Valley North / Delta                                                                                       | Pordesimo et al. (2004) Biomass Bioenergy 26:337-349; Schwietzke et al. (2009)                                                                                                          |
| `corn stover husks`        | `corn - grain`                                   | Case 1 (Path A: Substream of corn stover whole)                                         | Substream of `corn stover whole` | `0.08` (0.064 / 0.08 / 0.096)                                                                  | `0.08` (0.07 - 0.09 air-dry husk t / air-dry grain t)                                                   | 14.0%                    | 1.00                   | 0.40                     | **`0.055 / 0.069 / 0.083`** (dry t / marketed grain t (gross substream); 0.028 dry t/t sustainable)                                     | `425,651.3 t` (2023)                 | **`7,330.8 dry t`** (`8,499.4 wet t`, 2023)       | Field corn for grain; San Joaquin Valley North / Delta                                                                                       | Pordesimo et al. (2004) Biomass Bioenergy 26:337-349                                                                                                                                    |
| `rice straw`               | `rice`                                           | Case 1 (Path A: ag_report_volume)                                                       | Primary                          | `1.05` (0.70 / 1.05 / 1.40)                                                                    | `1.05` (0.90 - 1.25 air-dry straw t / air-dry paddy rice t (at 14% MC))                                 | 14.0%                    | 1.00                   | 0.45                     | **`0.77 / 0.9 / 1.1`** (dry t / paddy rice t (gross); 0.405 dry t/t collectible baled straw (~1.6 dry t/ac))                            | `18,243.8 t` (2023)                  | **`15,637.5 dry t`** (`18,243.8 wet t`, 2023)     | Calrose medium-grain rice (M-206, M-209); San Joaquin & Merced Counties / Sacramento Valley                                                  | Summerson et al. (2015) CA Rice Commission; UC Davis Rice Cost Study (2023); Williams et al. (2015) CBC                                                                                 |
| `rice hulls`               | `rice`                                           | Case 1 (Path A: ag_report_volume)                                                       | Primary                          | `0.2` (0.16 / 0.20 / 0.24)                                                                     | `0.2` (0.18 - 0.22 air-dry hull t / paddy rice t)                                                       | 10.0%                    | 1.00                   | 1.00                     | **`0.16 / 0.18 / 0.2`** (dry t / paddy rice t)                                                                                          | `3,475.0 t` (2023)                   | **`3,127.5 dry t`** (`3,475.0 wet t`, 2023)       | Calrose medium-grain rice; San Joaquin & Sacramento Valleys                                                                                  | Juliano (2019) Rice Chemistry and Technology; Williams et al. (2015) CBC                                                                                                                |
| `wheat straw`              | `wheat (USDA Census acreage & County Ag Report)` | Case 1 & 2 (Path A on 'wheat' tons + Path D on Census 'wheat' acres)                    | Primary                          | `0.7` (Path D: 0.6 / 0.7 / 0.8 t/ac; Path A: 0.7 / 1.2 / 1.7 t/t)                              | `1.16` (0.80 - 1.50 air-dry t/ac)                                                                       | 14.0%                    | 0.25                   | 0.50                     | **`0.6 / 0.85 / 1.1`** (dry t / harvested grain acre (or 0.85 dry t / t wheat grain))                                                   | `399,458.4 t` (2023)                 | **`70,737.0 dry t`** (`82,252.0 wet t`, 2023)     | Hard Red Winter & Durum wheat; San Joaquin, Stanislaus & Merced Counties                                                                     | UC Davis Small Grains / Wheat Cost Study SJV (2023); Williams et al. (2015) CBC                                                                                                         |
| `cotton stem mix`          | `cotton (USDA Census acreage)`                   | Case 2 (Path D: acreage_calc)                                                           | Primary                          | `1.2` (1.0 / 1.2 / 1.4 dry t/ac (prune_trim_yield=1.2))                                        | `2.07` (1.72 - 2.41 wet t/ac at harvest (~42% MC); 1.50 air-dry t/ac at 14% MC)                         | 42.0%                    | 1.00                   | 0.25                     | **`1 / 1.2 / 1.4`** (dry t / harvested acre (gross); 0.30 dry t/ac collectible under CDFA Pink Bollworm plowdown rules)                 | `0 t` (2022)                         | **`39,981.6 dry t`** (`68,933.8 wet t`, 2022)     | Pima (American Egyptian) & Upland/Acala cotton; Merced County (Westside NSJV)                                                                | UC Davis Cotton Cost Study SJV (2023); CDFA Pink Bollworm Program (3 CCR § 3595); Coates (1996) Trans. ASAE 39(5):1593-1598; Williams et al. (2015)                                     |
| `tomato pomace`            | `tomatoes - processed`                           | Case 1 (Path A: ag_report_volume)                                                       | Primary                          | `0.04` (0.03 / 0.04 / 0.05 (wet pulper pomace factor applied without moisture deduction))      | `0.04` (0.03 - 0.05 wet pomace t / wet t processing tomatoes)                                           | 77.5%                    | 1.00                   | 1.00                     | **`0.006 / 0.009 / 0.012`** (dry t / wet t fresh processing tomatoes)                                                                   | `116,681.0 t` (2023)                 | **`26,253.2 dry t`** (`116,681.0 wet t`, 2023)    | Processing paste/dice cultivars (H8504, AB2, N6428); Merced, San Joaquin & Stanislaus canneries (Ingomar, Liberty, Stanislaus Food Products) | Del Valle et al. (2006) J. Sci. Food Agric. 86:1232-1236; Pan et al. (2015) UC Davis / CTRI; Achmon et al. (2019); Williams et al. (2015)                                               |
| `sweet potato culls`       | `sweet potatoes`                                 | Case 1 (Path A: ag_report_volume)                                                       | Primary                          | `0.406` (0.312 / 0.406 / 0.50 (wet cull/non-No.1 fraction applied without moisture deduction)) | `0.2` (0.125 - 0.300 wet cull t / wet t harvested sweet potatoes)                                       | 72.5%                    | 1.00                   | 1.00                     | **`0.035 / 0.055 / 0.085`** (dry t / wet t harvested sweet potatoes (0.112 dry t/t if 40.6% wet cull rate is retained))                 | `135,017.2 t` (2023)                 | **`18,290.5 dry t`** (`66,510.9 wet t`, 2023)     | Covington, Diane, Beauregard, Murasaki; Merced & Stanislaus Counties (Atwater/Livingston produces ~90% of CA crop)                           | Stoddard et al. (2023) UC Davis Sample Costs to Produce Sweetpotatoes, SJV North (Merced County); California Sweetpotato Council (2024)                                                 |
| `alfalfa`                  | `hay - alfalfa`                                  | Excluded via EXCLUDED_RESOURCES in common.py (0 rows in mv_biomass_volume_estimate)     | Primary                          | `1` (1.00 (excluded in common.py; 0 rows in MV))                                               | `0.05` (0.03 - 0.08 wet off-spec/rain-damaged hay t / marketed hay t)                                   | 14.0%                    | 1.00                   | 0.05                     | **`0.025 / 0.043 / 0.069`** (dry t off-spec/spoiled hay / marketed alfalfa hay t (0.00 for primary dairy hay))                          | `0 t` (2023)                         | **`0 dry t`** (`0 wet t`, 2023)                   | Semi-dormant / Non-dormant alfalfa (FD 6-9); San Joaquin, Merced & Stanislaus Counties                                                       | Putnam et al. (2023) UC Davis Sample Costs to Establish and Produce Alfalfa Hay, SJV North                                                                                              |
| `sargassum`                | `N/A (Marine Macroalgae)`                        | Excluded via EXCLUDED_RESOURCES in common.py (0 rows in mv_biomass_volume_estimate)     | Primary                          | `N/A` (Excluded in common.py; 0 rows in MV)                                                    | N/A                                                                                                     | 85.0%                    | N/A                    | N/A                      | N/A (Excluded)                                                                                                                          | `0 t` (2023)                         | **`0 dry t`** (`0 wet t`, 2023)                   | Sargassum natans / S. fluitans (Tropical Atlantic) or S. muticum (CA coast); N/A to NSJV                                                     | Milledge & Harvey (2016) J. Mar. Sci. Eng. 4(3):60                                                                                                                                      |

---

## S3. Open-Boundary vs. Closed-Boundary Facility Siting Caveats

1. **Pistachio Hulling & Cracking Concentration (`'pistachio hulls'`,
   `'pistachio shells'`, `'pistachio stems & leaves'`)**:
   - **Closed-Boundary (County Crop Origin)**: The NSJV (`Merced`, `Stanislaus`,
     `San Joaquin`) produced `73,895 tons` (`2023`) and `63,246 tons` (`2024`)
     of dry in-shell pistachios (`~9–11%` of California's statewide crop). At
     $\alpha_{\text{proc}} = 0.25$ commercial cracking share and $f_{\text{dry}}
     = 0.49$ anatomical shell fraction ($f_{\text{eff}} = 0.123\text{ dry
     t/t}$), NSJV-grown pistachios yield **`~9,089 dry t` (`2023`)** and
     **`~7,779 dry t` (`2024`)** of cracked pistachio shells.
   - **Open-Boundary (Centralized Huller/Sheller Siting)**: Approximately `88%`
     of California's pistachio crop is grown and processed in the **Southern San
     Joaquin Valley** (`Kern`, `Tulare`, `Fresno`, `Kings`, `Madera`), where the
     largest commercial huller/shellers (e.g., Wonderful Pistachios in Lost
     Hills/Firebaugh, Nichols Farms, Keenan Farms, Horizon Nut, Setton Farms)
     are located. A biorefinery contracting directly with centralized SJV
     cracking facilities can access statewide cracked shell inventories
     (**`~75,000–95,000 dry t/yr`**), whereas a facility relying strictly on
     within-NSJV hullers is bounded by the closed-boundary county total.
2. **Stone & Pome Fruit Cannery vs. Fresh-Market Packing (`peaches`, `apricots`,
   `pears` vs. `nectarines`, `plums`, `pluots`)**:
   - Clingstone peaches, Patterson/Tilton apricots, and Bartlett pears are
     heavily canned, diced, and pureed inside the NSJV (`Modesto`, `Turlock`,
     `Stockton`/`Thornton`), generating concentrated point-source cannery
     streams (`pomace`, `peels`, `seeds`/pits, `rejects`).
   - Conversely, nectarines, pluots, and fresh-market plums are `>95%`
     fresh-market packed (primarily in `Fresno`, `Tulare`, and `Kings` counties)
     and have **zero** commercial canning operations in California; their
     theoretical cannery rows (`peels`, `pomace`, `off-spec canned products`)
     are non-existent in practice, leaving only packinghouse `rejects`/culls
     (`~10–15%` wet weight at `85–88%` MC) and `prunings`.
3. **Whole-Plant Cereal & Corn Silage vs. Grain Harvest (`'corn stover whole'`,
   `'wheat straw'`)**:
   - In the NSJV dairy belt (`Merced`, `Stanislaus`, `San Joaquin`), `>85%` of
     corn acreage (`~200,000+ ac/yr`) and `~70–80%` of winter small-grain
     acreage are harvested green as **whole-plant silage or hay** for dairy
     cattle, leaving **zero** harvestable stover or dry straw on those acres.
     Stover and straw residue factors apply strictly to acreage harvested for
     dry grain (`'corn - grain'`, grain wheat).

---

## S4. Complete Peer-Reviewed & Institutional Bibliography

1. **Aktas, C. B., et al. (2015)**. "Lifecycle assessment of almond production
   in California." _International Journal of Life Cycle Assessment_, 20(7),
   939–952. DOI: `10.1007/s11367-015-0893-5`.
2. **Administrative Committee for Pistachios (ACP) (2024)**. _2023–2024
   Pistachio Statistical Report_. Fresno, CA: ACP.
3. **Almond Board of California (ABC) (2024)**. _2024 Almond Almanac_. Modesto,
   CA: Almond Board of California.
4. **Braddock, R. J. (1999)**. _Handbook of Citrus By-Products and Processing
   Technology_. New York: John Wiley & Sons.
5. **Breunig, H. M., Huntington, T., Jin, L., Robinson, A., & Scown, C. D.
   (2017)**. "Temporal and geographic drivers of biomass residues in
   California." _Resources, Conservation and Recycling_, 139, 287–297. DOI:
   `10.1016/j.resconrec.2018.08.022`.
6. **California Department of Food and Agriculture (CDFA) (2024)**. _Final Grape
   Crush Report 2023 & 2024 Crop_ (Crush Districts 11, 12, and 13). Sacramento,
   CA: CDFA / USDA NASS.
7. **Del Valle, M., Cámara, M., & Torija, M. E. (2006)**. "Chemical
   characterization of tomato pomace." _Journal of the Science of Food and
   Agriculture_, 86(8), 1232–1236. DOI: `10.1002/jsfa.2474`.
8. **Ferguson, L., & Haviland, D. R. (Eds.) (2016)**. _Pistachio Production
   Manual_ (Publication 3545). Oakland, CA: University of California Agriculture
   and Natural Resources (UC ANR).
9. **Holtz, B. A., Doll, D., Browne, G., et al. (2018)**. "Whole orchard
   recycling on second-generation almond trees." _HortScience_, 53(11),
   1586–1587.
10. **Jenkins, B. M., Baxter, L. L., Miles Jr., T. R., & Miles, T. R. (1998)**.
    "Combustion properties of biomass." _Fuel Processing Technology_, 54(1–3),
    17–46.
11. **Jin, Q., O'Hair, J., Stewart, A. C., O'Keefe, S. F., Neilson, A. P., Kim,
    Y. T., McGuire, M., Lee, A., Wilder, G., & Huang, H. (2021)**. "Integrated
    grape pomace valorization: Industrial-scale mass balance and technoeconomic
    analysis." _ACS Sustainable Chemistry & Engineering_, 9(45), 15022–15035.
12. **Offeman, R. D., Holtman, K. M., Covello, K. M., & Orts, W. J. (2014)**.
    "Almond hull and shell composition by variety and growing region in
    California." _Industrial Crops and Products_, 54, 109–115. DOI:
    `10.1016/j.indcrop.2014.01.010`.
13. **Pordesimo, L. O., Edens, W. C., & Sokhansanj, S. (2004)**. "Distribution
    of aboveground biomass in corn stover." _Biomass and Bioenergy_, 26(4),
    337–349. DOI: `10.1016/S0961-9534(03)00124-7`.
14. **Putnam, D. H., Ávila, L., & Murdock, M. (2023)**. _Sample Costs to
    Establish and Produce Alfalfa Hay: San Joaquin Valley North_. Davis, CA: UC
    Davis Department of Agricultural and Resource Economics / UC ANR.
15. **Stoddard, C. S., Murdock, M., & Sumner, D. A. (2023)**. _Sample Costs to
    Produce Sweetpotatoes: San Joaquin Valley North (Merced County)_. Davis, CA:
    UC ANR Cooperative Extension.
16. **UC Davis Cooperative Extension (2023–2024)**. _Cost and Return Studies:
    Almonds, Walnuts, Winegrapes (Crush District 11), Cling Peaches, Processing
    Tomatoes, Field Corn, and Small Grains — San Joaquin Valley North_. Davis,
    CA: UC ANR.
17. **Wilhelm, W. W., Johnson, J. M. F., Hatfield, J. L., Voorhees, W. B., &
    Linden, D. R. (2004)**. "Crop and soil productivity response to corn residue
    removal: A literature review." _Agronomy Journal_, 96(1), 1–17.
18. **Williams, R. B., Jenkins, B. M., & Kaffka, S. (2015)**. _An Assessment of
    Biomass Resources in California, 2013_ (CEC-500-2015-035 / California
    Biomass Collaborative). Davis, CA: University of California, Davis.
