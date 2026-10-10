# Codebook — data/processed/school_panel.csv

One row per Indiana **public** high school × graduating cohort (2021–2024): 1,665 rows. Modeling uses rows with `has_outcome` and `n_enr >= 10`.
Sources: CHE = Indiana Commission for Higher Education College-Going/Readiness dataset for that cohort; IDOE = Indiana Department of Education school files; CRDC = Civil Rights Data Collection via the Urban Institute Education Data Portal; CCD = NCES Common Core of Data 2022–23 via the same portal. "Enrollees" always means graduates who enrolled at an Indiana public college the fall after graduation.

| Column | Definition | Source and transformation |
|---|---|---|
| `sid` | IDOE school number (4 characters) | CHE 2024 `LocationId`; earlier CHE files linked by exact `Location` name to 2024 |
| `school` | School name and city as CHE prints it ("Name-City") | CHE `Location` |
| `cohort` | Graduating class | CHE `Cohort` |
| `cid` | IDOE school corporation (district) number | IDOE 2025–26 school directory |
| `hs_grads` | High school graduates | CHE Average row, `HSGrads` |
| `n_college` | Graduates enrolling in any college (NSC-participating) | CHE `EnrCollegeN` |
| `n_enr` | Graduates enrolling at an Indiana public college; model weight | CHE `EnrINPubCollegeN` |
| `gpa` | Average first-year GPA of enrollees | CHE `AvgFreshmanGPA`; `DS`/`***` (suppressed) → missing |
| `credits` | Average first-year credits earned by enrollees | CHE `AvgFreshmanCreditEarned` |
| `p_offtrack` | Share of enrollees earning < 24 credits | CHE Credit Distribution (`<12` + `12 to 23.75`) ÷ `n_enr` |
| `p_gpa_lt2` | Share of enrollees with first-year GPA < 2.0 | CHE GPA Distribution `<2.0` ÷ `n_enr` |
| `p_mathrem` | Share of enrollees needing math remediation | CHE Remediation Type (`Math Only` + `Both Math and English/Language Arts`) ÷ `n_enr`; mostly suppressed |
| `ap_pass` | Share of graduates who took and passed an AP exam | CHE Advanced Placement breakout, `HSGrads` ÷ `hs_grads` |
| `dual` | Share of graduates earning dual credit from an Indiana public college | CHE Dual Credit breakout ÷ `hs_grads` |
| `g8_math` | Grade 8 math pass/proficiency rate for the cohort (grade 7 for 2024) | IDOE: ISTEP+ 2017 gr8 → 2021; ISTEP+ 2018 gr8 → 2022; ILEARN 2019 gr8 → 2023; ILEARN 2019 gr7 → 2024. School's own rate if it tested ≥10 students in that grade, else corporation rate (pooled across the corporation's schools) |
| `g8_source` | `school` or `corporation` (attribution level) | as above |
| `g8_z` | `g8_math` standardized within cohort | mean 0, SD 1 among public high schools in that cohort |
| `single_hs_corp` | School is the only high school of its corporation in the 2024 panel | derived |
| `sat_math` | Share of grade 11 SAT takers at the math benchmark | IDOE SAT school file, `Math` sheet: At Benchmark ÷ Total Tested. 2022 file → class of 2023; 2023 file → class of 2024; missing before |
| `sat_tested` | Grade 11 SAT math testers | same |
| `ncessch` | NCES school ID | CCD (`seasch` = corporation-school) matched on IDOE school number |
| `lat`, `lon` | School location | CCD 2022 |
| `locale4` | City / Suburb / Town / Rural | CCD urban-centric locale, first digit |
| `enroll` | Total enrollment, 2022–23 | CCD |
| `frl_share` | Free or reduced-price lunch share, 2022–23 | CCD `free_or_reduced_price_lunch` ÷ `enroll`. Audit only, not a model input |
| `charter`, `virtual` | 1 = charter / virtual school | CCD |
| `crdc_year` | CRDC collection matched to the cohort (2017 = 2017–18, 2020 = 2020–21) | 2017 for classes 2021–22; 2020 for 2023–24 |
| `a1e910`, `a1p910`, `a1e1112`, `a1p1112` | Algebra I enrollment / passers in grades 9–10 and 11–12 | CRDC algebra1 (school totals). Urban codes −2 → `NA`, −1/−3 → `X` → missing |
| `a1e78`, `a1p78` | Algebra I in grades 7–8 inside the same building | CRDC; affected by a known extraction quirk (see LIMITATIONS); not used |
| `e_alg2`, `e_adv`, `e_calc` | Enrollment in Algebra II, advanced math, calculus | CRDC math-and-science; Algebra II blank in the 2017–18 extract |
| `c_alg2`, `c_adv`, `c_calc` | Number of classes (sections) offered | CRDC offerings |
| `ap_math`, `n_ap`, `crdc_dual_offered` | AP math offered (1/0), number of AP courses, dual enrollment offered (1/0) | CRDC offerings |
| `alg1_late` | Share of the school's Algebra I passers who passed in grades 11–12 | `a1p1112 ÷ (a1p910 + a1p1112)` |
| `alg1_hs` | Algebra I passers in grades 9–12 per enrolled student | `(a1p910 + a1p1112) ÷ enroll` |
| `offers_alg2`, `offers_adv`, `offers_calc` | Course offered (classes > 0) | from `c_*` |
| `adv_share` | (advanced math + calculus enrollment) ÷ enrollment | CRDC 2020–21 only (classes 2023–24) |
| `c_alg2_2023`, `c_adv_2023`, `c_calc_2023` | Sections offered in CRDC 2023–24 | for the map's "currently offered" panel |
| `small` | `n_enr < 10` | derived |
| `has_outcome` | GPA and credits both reported | derived |

## data/processed/predictions_2024.csv
Class-of-2024 test set (368 schools) with the panel fields above plus: `pred_*` (linear model fit on 2023, full lever set), `pred_T1_*` (grade-9 information only), `warn_*` (predicted worst fifth), `worst_*` (observed worst fifth), `resid_*` (observed − predicted), and audit groupings `frl_tercile`, `size_tercile`, `type`.

## data/processed/map_schools_2024.csv
The 367 schools on the map (one test-set school lacks coordinates) with the map's predictions and flag `warn` (lowest fifth of predicted credits or highest fifth of predicted off-track share).
