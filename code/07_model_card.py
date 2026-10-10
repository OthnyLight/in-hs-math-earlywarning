#!/usr/bin/env python3
"""07_model_card.py — write docs/MODEL_CARD.md from paper/stats.json (Mitchell et al., 2019 format).

  python code/07_model_card.py [--final]
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
S = json.loads((ROOT / "paper" / "stats.json").read_text())
A = json.loads((ROOT / "AUTHORS.json").read_text())
FINAL = "--final" in sys.argv
T, TI, W, SE, ST = S["temporal"], S["tiers"], S["warning"], S["sensitivity"], S["state"]
pc = lambda x, d=0: f"{x*100:.{d}f}%"
f = lambda x, d=2: f"{x:.{d}f}"
au = A["authors"][0]

lev = S["levers"]
rows_lev = "\n".join(
    f"| {k} | {f(lev['credits'][k]['coef_per_sd'])} ({f(lev['credits'][k]['ci'][0])} to {f(lev['credits'][k]['ci'][1])}) "
    f"| {f(lev['gpa'][k]['coef_per_sd'],3)} ({f(lev['gpa'][k]['ci'][0],3)} to {f(lev['gpa'][k]['ci'][1],3)}) |"
    for k in ["sat_math", "dual", "ap_pass", "offers_calc", "offers_adv", "alg1_hs", "g8_z", "adv_share", "alg1_late"])

md = f"""{'> **DRAFT — not verified by the author.** Regenerate with `--final` after the verification checklist is complete.' if not FINAL else ''}

# Model card: Indiana high school early-warning model for first-year college outcomes (v0.1)

## Model details
- **Developer:** {au['name']} ({au['affiliation']}). Contact: {au['email']}.
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
Class of 2024 ({S['sample']['2024']['schools']} public high schools with ≥10 Indiana public college enrollees; {S['sample']['2024']['enrollees']:,} enrollees), scored by a model fit only on the class of 2023. Multi-cohort drift: classes of 2021–2024 with a reduced lever set (no SAT).

## Quantitative results (class of 2024, model fit on 2023)

| Outcome | R² (95% CI) | RMSE | Calibration slope (95% CI) | Observed − predicted | Prior-cohort R² |
|---|---|---|---|---|---|
| Mean first-year credits | {f(T['credits']['LIN']['r2'])} ({f(T['credits']['LIN']['r2_ci'][0])}–{f(T['credits']['LIN']['r2_ci'][1])}) | {f(T['credits']['LIN']['rmse'])} | {f(T['credits']['LIN']['slope'])} ({f(T['credits']['LIN']['slope_ci'][0])}–{f(T['credits']['LIN']['slope_ci'][1])}) | {f(T['credits']['LIN']['citl'])} | {f(T['credits']['PERSIST']['r2'])} |
| Mean first-year GPA | {f(T['gpa']['LIN']['r2'])} ({f(T['gpa']['LIN']['r2_ci'][0])}–{f(T['gpa']['LIN']['r2_ci'][1])}) | {f(T['gpa']['LIN']['rmse'],3)} | {f(T['gpa']['LIN']['slope'])} ({f(T['gpa']['LIN']['slope_ci'][0])}–{f(T['gpa']['LIN']['slope_ci'][1])}) | {f(T['gpa']['LIN']['citl'],3)} | {f(T['gpa']['PERSIST']['r2'])} |
| Share earning < 24 credits | {f(T['p_offtrack']['LIN']['r2'])} ({f(T['p_offtrack']['LIN']['r2_ci'][0])}–{f(T['p_offtrack']['LIN']['r2_ci'][1])}) | {f(T['p_offtrack']['LIN']['rmse'],3)} | {f(T['p_offtrack']['LIN']['slope'])} | {f(T['p_offtrack']['LIN']['citl'],3)} | {f(T['p_offtrack']['PERSIST']['r2'])} |

**How early:** credits R² {f(TI['credits']['T1_grade9']['r2'])} with information available by grade 9, {f(TI['credits']['T2_grade11']['r2'])} by grade 11, {f(TI['credits']['T3_graduation']['r2'])} at graduation. A poverty-only model reaches {f(TI['credits']['FRL_only']['r2'])} for credits and {f(TI['gpa']['FRL_only']['r2'])} for GPA.

**Warning flag (lowest fifth of predicted credits):** precision {pc(W['credits']['precision'])}, recall {pc(W['credits']['recall'])} (chance 20%; prior-cohort flag {pc(W['credits']['persistence_precision'])}).

**Lever coefficients** (change per 1 SD, classes of 2023–2024 pooled, 95% cluster-bootstrap CI):

| Lever | First-year credits | First-year GPA |
|---|---|---|
{rows_lev}

## Known failure modes
- **Level drift.** Statewide first-year credits rose from {ST['2023']['credits']} to {ST['2024']['credits']}; the 2023-trained model under-predicted 2024 by {f(T['credits']['LIN']['citl'])} credits. Update the intercept each year.
- **Over-dispersion.** Calibration slope below 1: extreme predictions should be shrunk toward the mean.
- **High-poverty schools:** GPA over-predicted by {f(abs(S['audit']['frl_tercile:high FRL:gpa']['mean_resid']))} points on average relative to the statewide shift; the model can miss struggling high-poverty schools.
- **Small, rural, virtual and junior/senior high schools:** larger and systematically signed errors; {S['worst']['n_small_in_top20']} of the 20 worst-predicted schools had fewer than 30 enrollees.
- **Math remediation** cannot be predicted from these data (rare, {pc(ST['2024']['math_remediation_share'],1)} statewide in 2024, and suppressed for most schools).

## Ethical considerations
Aggregate public data only, with source suppression of small cells. A school-level flag can stigmatize a school or its students if published as a rating; present it as a prompt for review, alongside the school's own context. Because poverty predicts outcomes about as well as the levers, any use for resource allocation should consider whether flags simply track poverty.

## Caveats and recommendations
Refit each year on the two most recent cohorts; update the intercept from the latest statewide figure; report calibration on the newest cohort before using flags; never use for individual students.
"""
(ROOT / "docs" / "MODEL_CARD.md").write_text(md.lstrip())
print("wrote docs/MODEL_CARD.md")
