# BioCIRV Zenodo Authorship & Smartsheet Audit Report

## 1. Executive Summary Statistics

- **Total Named Rows in Smartsheet:** 75
- **Active Contributors (`Active? = Yes`):** 56
- **Tagged `Data contributor` in Smartsheet:** 5
- **ORCIDs Populated in Smartsheet (`orcid.org/`):** 1 / 75 (James Gardner)
- **Additional ORCIDs Backfilled from `CITATION.cff`:** 3 (Meili Gong, Peter
  Smith, Tyler Huntington)
- **Candidate Zenodo `creators` (Byline Authors):** 30 (3 with ORCID, 27 missing
  ORCID)
- **Candidate Zenodo `contributors` (DataCite Roles):** 41
- **Excluded Rows (Inactive / Admin / Comms only):** 34

---

## 2. Data Quality & Anomaly Flags in Current Smartsheet

| Line ID  | Name             | Email                        | Detected Issue                                                                                               |
| :------- | :--------------- | :--------------------------- | :----------------------------------------------------------------------------------------------------------- |
| `con079` | Giya Kuriakose   | `giyakuriakose@ucmerced.edu` | First/Last name columns appear swapped or misspelled (Name='Giya Kuriakose', First='Kariakose', Last='Giya') |
| `con079` | Giya Kuriakose   | `giyakuriakose@ucmerced.edu` | Blank 'Active?' status in Smartsheet                                                                         |
| `con060` | Meili Gong       | `meili_gong@berkeley.edu`    | ORCID backfilled from CITATION.cff (0000-0001-8480-9306); missing in Smartsheet                              |
| `con058` | Peter Smith      | `petersmith@lbl.gov`         | ORCID backfilled from CITATION.cff (0000-0002-9276-5099); missing in Smartsheet                              |
| `con054` | Tai-Yuan Huang   | `taiyhuang@berkeley.edu`     | Blank 'Active?' status in Smartsheet                                                                         |
| `con062` | Tyler Huntington | `tylerhuntington222@lbl.gov` | ORCID backfilled from CITATION.cff (0000-0002-3213-0382); missing in Smartsheet                              |

---

## 3. Candidate Zenodo `creators` (Primary Byline Preview)

> **Note:** Currently sorted by Heuristic Tier (`Tier 1` = tagged
> `Data contributor`, `Tier 2` = Core Team Aim 1/2/3 Researchers, `Tier 3` = PIs
> / Co-PIs / Leads), then alphabetically by last name. Once the
> `Zenodo Release Role` and `Zenodo Author Order` columns are added to
> Smartsheet, this table will reflect explicit ordering.

| Tier | Zenodo Formatted Name      | Organization                                               | ORCID                                | Group(s)                                                                | Current Smartsheet Tags                 |
| :--: | :------------------------- | :--------------------------------------------------------- | :----------------------------------- | :---------------------------------------------------------------------- | :-------------------------------------- |
|  1   | **Bailey, Andrea**         | University of California Berkeley                          | **MISSING**                          | Aim 3: Modeling, Portal / Knowledge Base Development                    | Core team, Data contributor, MVP Tester |
|  1   | **Duong, Jenny**           | Lawrence Berkeley National Lab                             | **MISSING**                          | Aim 1: Feedstocks, Aim 2: Conversion                                    | Core team, Data contributor, MVP Tester |
|  1   | **Gardner, James**         | Lawrence Berkeley National Lab                             | `0000-0002-8106-3817` (smartsheet)   | Aim 1: Feedstocks, ExComm                                               | Core team, Data contributor, MVP Tester |
|  1   | **Krishnamoorthy, Anagha** | Lawrence Berkeley National Lab                             | **MISSING**                          | Aim 2: Conversion                                                       | Data contributor, ECR, MVP Tester       |
|  1   | **Smith, Peter**           | University of California Berkeley                          | `0000-0002-9276-5099` (citation.cff) | Aim 3: Modeling, Portal / Knowledge Base Development                    | Core team, Data contributor, MVP Tester |
|  2   | **Downey, Spencer**        | University of California Merced                            | **MISSING**                          | Aim 1: Feedstocks, Aim 2: Conversion                                    | Core team, MVP Tester                   |
|  2   | **Duran, Maria**           | Lawrence Berkeley National Lab                             | **MISSING**                          | Aim 1: Feedstocks                                                       | Core team, MVP Tester                   |
|  2   | **Duwadi, Shrijana**       | University of California Merced                            | **MISSING**                          | Aim 1: Feedstocks, Aim 3: Modeling                                      | ECR, MVP Tester                         |
|  2   | **Gong, Meili**            | University of California Berkeley                          | `0000-0001-8480-9306` (citation.cff) | Aim 3: Modeling, Portal / Knowledge Base Development                    | Core team, MVP Tester                   |
|  2   | **Heeley, Kieran**         | University of California Davis                             | **MISSING**                          | Aim 1: Feedstocks                                                       | Core team, MVP Tester                   |
|  2   | **Hilboldt, Jessica**      | BEAM Circular                                              | **MISSING**                          | Aim 3: Modeling                                                         | Core team, MVP Tester                   |
|  2   | **Hoffman, Beau**          | Bobolink Sustainability Group, LLC                         | **MISSING**                          | Aim 3: Modeling, External - Individual                                  | Core team, MVP Tester                   |
|  2   | **Kang, Xihui**            | Lawrence Berkeley National Lab                             | **MISSING**                          | Aim 1: Feedstocks, Aim 2: Conversion                                    | ECR                                     |
|  2   | **McManus, Jim**           | Lawrence Berkeley National Lab                             | **MISSING**                          | Aim 2: Conversion, ExComm                                               | MVP Tester                              |
|  2   | **Nasef, Ziad**            | University of California Merced                            | **MISSING**                          | Aim 2: Conversion                                                       |                                         |
|  2   | **Nematian, Maryam**       | University of California Berkeley                          | **MISSING**                          | Aim 3: Modeling                                                         |                                         |
|  2   | **Newell, Eli**            | University of California Davis                             | **MISSING**                          | Administrative, Aim 1: Feedstocks, DEIA & Community Engagement          | Core team, ECR, MVP Tester              |
|  2   | **Ni, Cynthia**            | BEAM Circular                                              | **MISSING**                          | Aim 3: Modeling, DEIA & Community Engagement, ExComm                    | Core team, MVP Tester                   |
|  2   | **Odim, Rebecca**          | BEAM Circular                                              | **MISSING**                          | Aim 3: Modeling, Portal / Knowledge Base Development                    |                                         |
|  2   | **Okonkwo, Onyinye**       | Lawrence Berkeley National Lab                             | **MISSING**                          | Aim 2: Conversion                                                       | Core team, MVP Tester                   |
|  2   | **Poddar, Tuhin**          | University of California Berkeley                          | **MISSING**                          | Aim 3: Modeling                                                         | Core team, MVP Tester                   |
|  2   | **Ryals, Becca**           | University of California Merced                            | **MISSING**                          | Aim 2: Conversion, Aim 3: Modeling, DEIA & Community Engagement, ExComm | Core team, MVP Tester                   |
|  2   | **Tapia, Mariana**         | University of California Davis                             | **MISSING**                          | Aim 1: Feedstocks, Aim 3: Modeling                                      | Core team, ECR                          |
|  2   | **Teran, Isaias**          | University of California Merced                            | **MISSING**                          | Aim 2: Conversion                                                       | Core team, ECR                          |
|  3   | **Diaz, Gerardo**          | University of California Merced                            | **MISSING**                          | Aim 2: Conversion, ExComm                                               | Core team, MVP Tester                   |
|  3   | **Scown, Corinne**         | University of California Berkeley                          | **MISSING**                          | Aim 3: Modeling, ExComm, Portal / Knowledge Base Development            | Core team, MVP Tester, PI / Co-PI       |
|  3   | **Simmons, Blake**         | Lawrence Berkeley National Lab                             | **MISSING**                          | Aim 2: Conversion, ExComm                                               | Core team, MVP Tester, PI / Co-PI       |
|  3   | **Spang, Edward S.**       | University of California Davis                             | **MISSING**                          | Aim 1: Feedstocks, Aim 3: Modeling, ExComm                              | Core team, MVP Tester                   |
|  3   | **Warner, Karen**          | BEAM Circular                                              | **MISSING**                          | Aim 3: Modeling, Communications, DEIA & Community Engagement, ExComm    | Core team                               |
|  3   | **Youtsey, Gabe**          | University of California Agriculture and Natural Resources | **MISSING**                          | Aim 1: Feedstocks, ExComm                                               | Adv Board, MVP Tester                   |

---

## 4. Additional Aim 1–3 Contributors (`Active? = Yes` or Research Group, Not in Core Team)

| Zenodo Formatted Name | Suggested DataCite Role | Active? | Organization                                               | Group(s)                                                                                            | Role(s)                                         |
| :-------------------- | :---------------------- | :-----: | :--------------------------------------------------------- | :-------------------------------------------------------------------------------------------------- | :---------------------------------------------- |
| Chen, Cindy           | `DataCollector`         |   Yes   | UC ANR Cooperative Extension                               | Aim 1: Feedstocks                                                                                   | Feedstock sourcing; Provider relationships      |
| Culumber, Mae         | `DataCollector`         |   Yes   | UC ANR Cooperative Extension                               | Aim 1: Feedstocks                                                                                   | Feedstock sourcing; Provider relationships      |
| Fugere-Sousa, Taylor  | `DataCollector`         |   Yes   | University of California Merced                            | Aim 3: Modeling                                                                                     |                                                 |
| Galdi, Giuliano       | `DataCollector`         |   Yes   | UC ANR Cooperative Extension                               | Aim 1: Feedstocks                                                                                   | Farm Advisor (Agronomic Crops, Weed Management) |
| Gomez, Hector         | `DataCollector`         |   Yes   | University of California Merced                            | Aim 2: Conversion                                                                                   | Diaz graduate student                           |
| Huang, Tai-Yuan       | `DataCollector`         |  Blank  | University of California Berkeley                          | Aim 3: Modeling                                                                                     | Postdoc, Scown Lab                              |
| Huntington, Tyler     | `DataCollector`         |   Yes   | Lawrence Berkeley National Lab                             | Aim 3: Modeling                                                                                     | Software Developer (JBEI), Scown Group          |
| Kuriakose, Giya       | `DataCollector`         |  Blank  | University of California Merced                            | Aim 2: Conversion                                                                                   |                                                 |
| Petersen, Helle       | `DataCollector`         |   Yes   | University of California Agriculture and Natural Resources | Administrative, Aim 1: Feedstocks, DEIA & Community Engagement, Portal / Knowledge Base Development | Deputy Chief Innovation Officer, UCANR Innovate |
| Rachbauer, Lydia      | `DataCollector`         |   Yes   | Lawrence Berkeley National Lab                             | Aim 2: Conversion                                                                                   |                                                 |
| Tanner, Justin        | `DataCollector`         |   Yes   | UC ANR Cooperative Extension                               | Aim 1: Feedstocks                                                                                   | Farm Advisor (viticulture)                      |
