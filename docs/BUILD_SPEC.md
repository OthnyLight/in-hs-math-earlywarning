# Build spec — P2 School-level early-warning model for first-year college math outcomes

Status: v0.1 (draft). Spec written 2026-10-06; "As built" section added 2026-10-10.

```
PROJECT:     Indiana HS early-warning model (archetypes: analysis paper + validation study,
             stacked with an open dataset and an atlas/map)

QUESTION:    Using only public school-level signals available while students are still in
             high school, how well can we predict how a school's graduates fare in their first
             college year — and which school-level levers carry the signal?

UNIT:        Indiana public high school x graduating cohort (≈530 schools/cohort)

OUTCOMES (from CHE College-Going / College-Readiness datasets, by high school):
  Y1  mean / % on-track first-year credits earned        (primary)
  Y2  mean first-year GPA (or % with GPA >= 2.0/2.5, whichever CHE reports)  (primary)
  Y3  % needing math remediation, where not suppressed   (secondary; suppression modeled explicitly)
  (column names confirmed against the CHE files; see CODEBOOK.md)

PREDICTORS (lag-aligned to the cohort — the class of 2024 sat ILEARN gr8 in spring 2020
            (no test: COVID) → use spring 2019 gr7 as documented fallback, and SAT gr11 in spring 2023):
  X1  ILEARN grade 8 math % proficient (attributed to the HS building if it tests grade 8, else the corporation — see VERIFY POINTS)
  X2  SAT grade 11 math % meeting benchmark / mean score
  X3  CRDC: % passing Algebra I by grade 8 vs grades 9-10 vs 11-12
  X4  CRDC: Algebra II offered, advanced math offered, calculus offered (0/1) and enrollment shares
  X5  AP: % of grads with an AP exam passed (math and overall)
  X6  Dual credit: % of grads earning dual credit (CHE file / IDOE)
  Controls reported but kept OUT of the headline model (so the model stays about levers, not
  demographics): enrollment, locale (CCD), % FRL; a fairness audit stratifies by them.

SOURCES (all access verified 2026-10-06 by page listing; files not yet fetched):
  CHE College-Going 2024 cohort  https://www.in.gov/dA/d1c423c709/2026-College-Going-Dataset-2024-Cohort.xlsx
  CHE College-Readiness 2017–2023 cohorts (one xlsx each) + 2008–2016 combined — same page
      → resolves the brief's open question: earlier cohorts ARE on the CHE page.
  IDOE ILEARN gr3-8 school results (2019, 2021–2026), SAT gr11 school (2022–2026),
      AP corporation & school results, graduation rates — in.gov/doe/it/data-center-and-reports
  CRDC 2017-18, 2020-21, 2023-24 school files — civilrightsdata.ed.gov
  NCES CCD school directory (NCES ID ↔ IDOE school number crosswalk, locale, enrollment)

MODEL:       Interpretable first: regularized linear / GAM with monotone splines per predictor,
             plus a shallow gradient-boosted comparator to show what interpretability costs.
             Weighted by number of college-going grads. Calibration: reliability plots by decile,
             calibration slope/intercept. "Warning" = predicted bottom quintile.
COHORT ALIGNMENT CONSTRAINT (drives the design):
             ILEARN began spring 2019 and was cancelled spring 2020; state SAT gr11 began spring 2022.
             Class of 2023 → gr8 ILEARN 2019 ✓, SAT gr11 2022 ✓
             Class of 2024 → gr8 test none (2020) ✗, SAT gr11 2023 ✓
             Class of 2022 and earlier → gr8 ISTEP+, no state SAT.
             So the full-signal model fits on 2023, tests transfer to 2024 (SAT-only variant),
             and a "harmonized" variant (ISTEP+/ILEARN z-scored within year, AP, dual credit, CRDC)
             spans 2017–2024 for the long cohort-drift check.
VALIDATION:  Temporal: fit on earlier cohort(s), test on later ones (cohort drift check).
             Grouped CV by district. Failure audit: residuals by locale, size, FRL tercile,
             charter status, single-feeder vs multi-feeder; list the 20 worst-predicted schools.

OUTPUTS:
  data/processed/school_panel.csv + CODEBOOK.md
  paper/stats.json, figures (calibration, partial-dependence per lever, cohort drift, failure map)
  paper/manuscript.docx (research article) + preprint PDF
  docs/MODEL_CARD.md
  map/index.html  (interactive Indiana school map: predicted vs observed, warning flag)
  code/01_fetch … 06_map, replication README

VENUES:      Zenodo (data+code DOI) → EdArXiv preprint → journal (e.g., AERA Open / Educational
             Evaluation and Policy Analysis / Research in Higher Education) → map on GitHub Pages
VERIFY POINTS (author's judgment):
  1. Outcome definition: which CHE columns count as "credits earned" and "GPA" success
  2. Feeder mapping: how gr8 ILEARN is attributed to a high school (district average vs feeder)
  3. COVID gap: handling of no 2020 ILEARN for the class of 2024
  4. Warning threshold (bottom quintile vs absolute cutoff)
  5. Whether demographic controls belong in the headline model
LICENSE:     Code MIT; derived data and documents CC BY 4.0 (sources: CHE, IDOE, USED/OCR, NCES)
ASSUMPTIONS: cohort window 2017–2024 (8 cohorts); public schools only; suppressed cells kept as missing
             with a suppression indicator, never imputed as zero.
```

## As built (2026-10-10) — where the build departed from the spec

- **Sources fetched:** CHE cohorts 2021–2024 (the 2017–2020 files were not needed once the design centered on 2021–2024); IDOE ISTEP+ 2017–2018, ILEARN 2019 and 2021, SAT 2022–2023, AP, 2025–26 directory; CRDC 2017–18, 2020–21 (Algebra I, math enrollment) and 2023–24 (offerings only) and CCD 2022–23 via the Urban Institute Education Data Portal, since civilrightsdata.ed.gov and nces.ed.gov serve only very large national files.
- **Earlier-cohort question resolved:** CHE posts every cohort from 2017 on the same page; the brief's verification flag on this point is closed.
- **Outcomes:** mean first-year credits and GPA (primary), share < 24 credits and share GPA < 2.0 (secondary). Math remediation could not be modeled (reported for 141 of 368 schools in 2024; 4.2% of enrollees statewide) and is reported as a finding.
- **AP and dual credit** come from CHE breakouts of each cohort rather than the IDOE AP file (which stops at 2021–22).
- **Unit and sample:** public high schools with ≥ 10 Indiana public college enrollees: 1,434 school-cohort rows.
- **Model:** linear model on nine levers (headline); additive splines and gradient boosting as comparators; persistence and a blend as benchmarks; information tiers (grade 9 / grade 11 / graduation) added to answer "how early".
- **Demographic controls:** kept out of the headline model (author's choice, 2026-10-06); poverty used in the audit and a sensitivity check.
- **Venue:** EdArXiv first (author's choice), then a journal.
