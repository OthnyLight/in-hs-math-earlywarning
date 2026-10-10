# Model card: Indiana high school early-warning model for first-year college outcomes (v0.1)

## Model details
- **Developer:** Othniel Iyassa Sa'anga (Independent Researcher). Contact: othnylight@gmail.com.
- **Version and date:** 0.1, built from data released through May 2026.
- **Type:** enrollee-weighted linear regression on nine standardized school-level levers, with median imputation and missing-value indicators (code/03_model.py). Comparators: additive splines and gradient-boosted trees.
- **Training data:** Indiana public high schools, class of 2023 (for the headline test) or classes of 2023–2024 pooled (for the lever coefficients).
- **License:** code MIT; data and documents CC BY 4.0.
- **Citation:** see CITATION.cff.

## Intended use
- **Primary use:** flag Indiana public high schools whose graduates are likely to earn few credits or low grades in their first year at an Indiana public college, two to four years before those outcomes are published, so that districts and the state can look closer at mathematics pathways, SAT math preparation and dual-credit access.
- **Primary users:** district and school leaders, Indiana Department of Education and Commission for Higher Education analysts, researchers.
- **Out of scope:** decisions about individual students; ranking or rating schools for accountability; funding or sanction decisions; any claim that changing a lever will change outcomes; private schools; graduates who attend private or out-of-state colleges.

## Factors
School locale, poverty (free/reduced-price lunch share), size, type (traditional, charter, virtual), the level at which grade 8 results are attributed (own building or district average), and whether the school is the only high school in its district. Results by factor are in paper/tables/failure_audit_2024.csv.

## Metrics
Enrollee-weighted R² and RMSE out of sample; calibration slope, intercept and calibration-in-the-large; precision and recall of a worst-fifth flag; 95% intervals from bootstrap resampling of school corporations.

## Evaluation data
Class of 2024 (368 public high schools with ≥10 Indiana public college enrollees; 25,591 enrollees), scored by a model fit only on the class of 2023. Multi-cohort drift: classes of 2021–2024 with a reduced lever set (no SAT).

## Quantitative results (class of 2024, model fit on 2023)

| Outcome | R² (95% CI) | RMSE | Calibration slope (95% CI) | Observed − predicted | Prior-cohort R² |
|---|---|---|---|---|---|
| Mean first-year credits | 0.59 (0.45–0.68) | 1.98 | 0.87 (0.79–0.96) | 0.67 | 0.50 |
| Mean first-year GPA | 0.56 (0.41–0.64) | 0.183 | 0.90 (0.81–1.00) | 0.042 | 0.55 |
| Share earning < 24 credits | 0.61 (0.49–0.69) | 0.081 | 0.88 | -0.016 | 0.51 |

**How early:** credits R² 0.45 with information available by grade 9, 0.58 by grade 11, 0.59 at graduation. A poverty-only model reaches 0.51 for credits and 0.61 for GPA.

**Warning flag (lowest fifth of predicted credits):** precision 62%, recall 61% (chance 20%; prior-cohort flag 55%).

**Lever coefficients** (change per 1 SD, classes of 2023–2024 pooled, 95% cluster-bootstrap CI):

| Lever | First-year credits | First-year GPA |
|---|---|---|
| sat_math | 1.97 (1.55 to 2.32) | 0.194 (0.146 to 0.229) |
| dual | 0.36 (0.16 to 0.58) | 0.050 (0.016 to 0.081) |
| ap_pass | 0.22 (-0.02 to 0.45) | -0.025 (-0.056 to 0.002) |
| offers_calc | 0.12 (-0.09 to 0.33) | 0.008 (-0.015 to 0.031) |
| offers_adv | 0.07 (-0.16 to 0.27) | 0.004 (-0.014 to 0.026) |
| alg1_hs | 0.03 (-0.11 to 0.19) | 0.012 (-0.011 to 0.035) |
| g8_z | -0.10 (-0.32 to 0.19) | 0.003 (-0.027 to 0.036) |
| adv_share | -0.12 (-0.32 to 0.07) | -0.016 (-0.033 to 0.003) |
| alg1_late | -0.14 (-0.45 to 0.05) | -0.002 (-0.024 to 0.024) |

## Known failure modes
- **Level drift.** Statewide first-year credits rose from 23.0 to 23.6; the 2023-trained model under-predicted 2024 by 0.67 credits. Update the intercept each year.
- **Over-dispersion.** Calibration slope below 1: extreme predictions should be shrunk toward the mean.
- **High-poverty schools:** GPA over-predicted by 0.04 points on average relative to the statewide shift; the model can miss struggling high-poverty schools.
- **Small, rural, virtual and junior/senior high schools:** larger and systematically signed errors; 18 of the 20 worst-predicted schools had fewer than 30 enrollees.
- **Math remediation** cannot be predicted from these data (rare, 4.2% statewide in 2024, and suppressed for most schools).

## Ethical considerations
Aggregate public data only, with source suppression of small cells. A school-level flag can stigmatize a school or its students if published as a rating; present it as a prompt for review, alongside the school's own context. Because poverty predicts outcomes about as well as the levers, any use for resource allocation should consider whether flags simply track poverty.

## Caveats and recommendations
Refit each year on the two most recent cohorts; update the intercept from the latest statewide figure; report calibration on the newest cohort before using flags; never use for individual students.
