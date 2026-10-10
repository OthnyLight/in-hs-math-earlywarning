#!/usr/bin/env python3
"""03_model.py — fit, validate, calibrate and audit the school-level early-warning models.

Inputs : data/processed/school_panel.csv
Outputs: data/processed/predictions.csv, paper/stats.json (every number the documents quote),
         paper/tables/*.csv

Models (all weighted by n_enr, the number of graduates enrolled at an Indiana public college):
  LIN   linear model on standardized levers, with missing-value indicators (the headline,
        interpretable model; coefficients are "per 1 SD of the lever")
  GAM   additive spline model (cubic B-splines per lever + ridge): still one curve per lever
  GBM   gradient-boosted trees (comparator: what interpretability costs, if anything)
  PERSIST  the school's own outcome for the previous cohort (a benchmark, not an early warning:
        it only exists after a cohort has already reached college)

Feature sets
  FULL  g8_z, sat_math, alg1_late, alg1_hs, offers_adv, offers_calc, adv_share, ap_pass, dual
        (classes of 2023 and 2024: the only cohorts with both state SAT and grade 7/8 tests)
  HARM  g8_z, alg1_late, alg1_hs, offers_adv, offers_calc, ap_pass, dual
        (classes of 2021-2024; used for the multi-cohort drift check)

Validation
  (a) grouped 5-fold cross-validation by school corporation within the class of 2023 (FULL)
  (b) temporal transfer: fit class of 2023 -> predict class of 2024 (FULL)  <- headline
  (c) cohort drift: fit 2021 -> predict 2022/2023/2024; fit 2021-22 -> 2023/2024 (HARM)
  (d) calibration on (b): slope, intercept, calibration-in-the-large, decile table
  (e) warning flag: predicted worst quintile vs observed worst quintile (precision/recall)
  (f) failure audit: residuals by locale, FRL tercile, size tercile, charter, virtual,
      grade-8 attribution level; worst-predicted schools
  (g) lever importance: standardized coefficients with corporation-cluster bootstrap CIs
  (h) sensitivity: add FRL share to the model; refit without small schools
"""
import json
import pathlib
import warnings

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import SplineTransformer, StandardScaler

warnings.filterwarnings("ignore")
ROOT = pathlib.Path(__file__).resolve().parents[1]
PROC, PAPER = ROOT / "data" / "processed", ROOT / "paper"
(PAPER / "tables").mkdir(parents=True, exist_ok=True)
RNG = np.random.default_rng(20261009)
B = 500  # bootstrap replicates

df = pd.read_csv(PROC / "school_panel.csv", dtype={"sid": str, "cid": str, "ncessch": str})
df = df[df.has_outcome & (df.n_enr >= 10)].copy()

FULL = ["g8_z", "sat_math", "alg1_late", "alg1_hs", "offers_adv", "offers_calc", "adv_share", "ap_pass", "dual"]
HARM = ["g8_z", "alg1_late", "alg1_hs", "offers_adv", "offers_calc", "ap_pass", "dual"]
# information available at three points in a cohort's high-school career
TIERS = {"T1_grade9": ["g8_z", "alg1_late", "alg1_hs", "offers_adv", "offers_calc", "adv_share"],
         "T2_grade11": ["g8_z", "alg1_late", "alg1_hs", "offers_adv", "offers_calc", "adv_share", "sat_math"],
         "T3_graduation": FULL}
LABEL = {"g8_z": "Grade 7/8 math proficiency (z)", "sat_math": "Grade 11 SAT math benchmark rate",
         "alg1_late": "Algebra I passed late (gr 11-12 share)", "alg1_hs": "Algebra I passers in HS per student",
         "offers_adv": "Offers advanced math", "offers_calc": "Offers calculus",
         "adv_share": "Advanced math + calculus enrollment share", "ap_pass": "Graduates passing an AP exam",
         "dual": "Graduates earning dual credit"}
OUTCOMES = {"credits": "Mean first-year credits", "gpa": "Mean first-year GPA",
            "p_offtrack": "Share earning < 24 credits", "p_gpa_lt2": "Share with GPA < 2.0"}
LOWER_IS_WORSE = {"credits": True, "gpa": True, "p_offtrack": False, "p_gpa_lt2": False}
S = {}  # stats.json


# ------------------------------------------------------------------ helpers
class Prep:
    """Median-impute with missing indicators; medians learned on the training data only."""

    def __init__(self, feats):
        self.feats = feats

    def fit(self, X):
        self.med = X[self.feats].median()
        self.miss = [f for f in self.feats if X[f].isna().any()]
        return self

    def transform(self, X):
        Z = X[self.feats].fillna(self.med).copy()
        for f in self.miss:
            Z[f + "_missing"] = X[f].isna().astype(float)
        return Z


def make_model(kind):
    if kind == "LIN":
        return make_pipeline(StandardScaler(), LinearRegression())
    if kind == "GAM":
        return make_pipeline(StandardScaler(), SplineTransformer(n_knots=4, degree=3), Ridge(alpha=3.0))
    if kind == "GBM":
        return HistGradientBoostingRegressor(max_depth=3, learning_rate=0.05, max_iter=300,
                                             min_samples_leaf=20, l2_regularization=1.0, random_state=0)


def fit_predict(kind, feats, train, test, y):
    if kind == "GBM":
        m = make_model(kind).fit(train[feats], train[y], sample_weight=train.n_enr)
        return m.predict(test[feats]), m, None
    p = Prep(feats).fit(train)
    m = make_model(kind)
    m.fit(p.transform(train), train[y], **{m.steps[-1][0] + "__sample_weight": train.n_enr.values})
    return m.predict(p.transform(test)), m, p


def wmetrics(y, yhat, w):
    w = np.asarray(w, float)
    r = y - yhat
    sse = np.sum(w * r ** 2)
    sst = np.sum(w * (y - np.average(y, weights=w)) ** 2)
    return {"r2": 1 - sse / sst, "rmse": float(np.sqrt(sse / w.sum())), "mae": float(np.average(np.abs(r), weights=w)),
            "corr": float(np.corrcoef(y, yhat)[0, 1]), "n": int(len(y))}


def calib(y, yhat, w):
    lr = LinearRegression().fit(yhat.reshape(-1, 1), y, sample_weight=w)
    return {"slope": float(lr.coef_[0]), "intercept": float(lr.intercept_),
            "citl": float(np.average(y - yhat, weights=w))}


def boot_ci(fn, data, groups, b=B):
    """Corporation-cluster bootstrap of a scalar statistic fn(resampled_df)."""
    g = data[groups].fillna("none").values
    ug = np.unique(g)
    idx = {k: np.where(g == k)[0] for k in ug}
    vals = []
    for _ in range(b):
        pick = RNG.choice(ug, size=len(ug), replace=True)
        rows = np.concatenate([idx[k] for k in pick])
        try:
            vals.append(fn(data.iloc[rows]))
        except Exception:
            pass
    return [float(np.nanpercentile(vals, 2.5)), float(np.nanpercentile(vals, 97.5))]


def r(x, k=3):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), k)


# ------------------------------------------------------------------ sample description
S["sample"] = {}
for y in (2021, 2022, 2023, 2024):
    d = df[df.cohort == y]
    S["sample"][str(y)] = {"schools": int(len(d)), "enrollees": int(d.n_enr.sum()),
                           "credits_mean": r(np.average(d.credits, weights=d.n_enr), 2),
                           "gpa_mean": r(np.average(d.gpa, weights=d.n_enr), 2),
                           "offtrack_mean": r(np.average(d.p_offtrack, weights=d.n_enr)),
                           "credits_p10": r(d.credits.quantile(.1), 1), "credits_p90": r(d.credits.quantile(.9), 1)}
S["sample"]["min_enrollees"] = 10
raw = pd.read_csv(PROC / "school_panel.csv", dtype={"sid": str})
S["sample"]["public_school_rows_all"] = int(len(raw))
S["sample"]["rows_modeled"] = int(len(df))

d23, d24 = df[df.cohort == 2023].copy(), df[df.cohort == 2024].copy()

# ------------------------------------------------------------------ (a) grouped CV within 2023
S["cv2023"] = {}
for y in OUTCOMES:
    S["cv2023"][y] = {}
    for kind in ("LIN", "GAM", "GBM"):
        pred = np.full(len(d23), np.nan)
        for tr, te in GroupKFold(n_splits=5).split(d23, groups=d23.cid.fillna(d23.sid)):
            pred[te], _, _ = fit_predict(kind, FULL, d23.iloc[tr], d23.iloc[te], y)
        S["cv2023"][y][kind] = {k: r(v) for k, v in wmetrics(d23[y].values, pred, d23.n_enr).items()}

# ------------------------------------------------------------------ (b) temporal transfer 2023 -> 2024
S["temporal"] = {}
pred_tab = d24[["sid", "school", "cid", "cohort", "n_enr", "lat", "lon", "locale4", "frl_share", "enroll", "charter",
                "virtual", "g8_source", "single_hs_corp"] + FULL + list(OUTCOMES) + ["p_mathrem", "c_alg2_2023",
                                                                                     "c_adv_2023", "c_calc_2023"]].copy()
for y in OUTCOMES:
    S["temporal"][y] = {}
    for kind in ("LIN", "GAM", "GBM"):
        p, _, _ = fit_predict(kind, FULL, d23, d24, y)
        met = wmetrics(d24[y].values, p, d24.n_enr)
        cal = calib(d24[y].values, p, d24.n_enr)
        S["temporal"][y][kind] = {**{k: r(v) for k, v in met.items()}, **{k: r(v) for k, v in cal.items()}}
        if kind == "LIN":
            pred_tab[f"pred_{y}"] = p
            tmp = d24.assign(_p=p)
            S["temporal"][y]["LIN"]["r2_ci"] = [r(v) for v in boot_ci(
                lambda z: wmetrics(z[y].values, z._p.values, z.n_enr)["r2"], tmp, "cid")]
            S["temporal"][y]["LIN"]["slope_ci"] = [r(v) for v in boot_ci(
                lambda z: calib(z[y].values, z._p.values, z.n_enr.values)["slope"], tmp, "cid")]
    # persistence benchmark: the school's own class-of-2023 outcome
    prev = d23.set_index("sid")[y]
    pp = d24.sid.map(prev)
    m = pp.notna()
    S["temporal"][y]["PERSIST"] = {**{k: r(v) for k, v in wmetrics(d24[y][m].values, pp[m].values, d24.n_enr[m]).items()}}
    lp = pred_tab[f"pred_{y}"][m]
    S["temporal"][y]["LIN_same_schools"] = {k: r(v) for k, v in wmetrics(d24[y][m].values, lp.values, d24.n_enr[m]).items()}
    # blend: model + persistence (what a state would actually run once outcomes exist)
    blend = 0.5 * lp.values + 0.5 * pp[m].values
    S["temporal"][y]["BLEND"] = {k: r(v) for k, v in wmetrics(d24[y][m].values, blend, d24.n_enr[m]).items()}

# ------------------------------------------------------------------ (b2) how early? information tiers, 2023 -> 2024
S["tiers"] = {}
for y in OUTCOMES:
    S["tiers"][y] = {}
    for tier, feats in TIERS.items():
        p, _, _ = fit_predict("LIN", feats, d23, d24, y)
        tmp = d24.assign(_p=p)
        S["tiers"][y][tier] = {"r2": r(wmetrics(d24[y].values, p, d24.n_enr)["r2"]),
                               "r2_ci": [r(v) for v in boot_ci(lambda z: wmetrics(z[y].values, z._p.values, z.n_enr)["r2"], tmp, "cid", b=300)]}
        if tier == "T1_grade9":
            pred_tab[f"pred_T1_{y}"] = p
    for base in ("frl_share",):
        p, _, _ = fit_predict("LIN", [base], d23, d24, y)
        S["tiers"][y]["FRL_only"] = {"r2": r(wmetrics(d24[y].values, p, d24.n_enr)["r2"])}

# ------------------------------------------------------------------ (c) cohort drift (HARM)
S["drift"] = {}
for y in ("credits", "gpa", "p_offtrack"):
    S["drift"][y] = {}
    for train_years in ([2021], [2021, 2022], [2023]):
        tr = df[df.cohort.isin(train_years)]
        key = "fit_" + "_".join(map(str, train_years))
        S["drift"][y][key] = {}
        for test_year in (2021, 2022, 2023, 2024):
            if test_year in train_years:
                continue
            te = df[df.cohort == test_year]
            p, _, _ = fit_predict("LIN", HARM, tr, te, y)
            met = wmetrics(te[y].values, p, te.n_enr)
            cal = calib(te[y].values, p, te.n_enr.values)
            S["drift"][y][key][str(test_year)] = {"r2": r(met["r2"]), "rmse": r(met["rmse"]),
                                                  "slope": r(cal["slope"]), "citl": r(cal["citl"])}

# ------------------------------------------------------------------ (d) calibration table (credits, LIN, 2024)
dec = []
for y in OUTCOMES:
    t = pred_tab.assign(_bin=pd.qcut(pred_tab[f"pred_{y}"], 10, labels=False, duplicates="drop"))
    for b, g in t.groupby("_bin"):
        dec.append({"outcome": y, "decile": int(b) + 1, "n_schools": len(g),
                    "pred_mean": np.average(g[f"pred_{y}"], weights=g.n_enr), "obs_mean": np.average(g[y], weights=g.n_enr)})
pd.DataFrame(dec).to_csv(PAPER / "tables" / "calibration_deciles_2024.csv", index=False)

# ------------------------------------------------------------------ (e) warning flag (worst quintile)
S["warning"] = {}
for y in OUTCOMES:
    worse_low = LOWER_IS_WORSE[y]
    obs, pr = pred_tab[y], pred_tab[f"pred_{y}"]
    thr_o = obs.quantile(0.2 if worse_low else 0.8)
    thr_p = pr.quantile(0.2 if worse_low else 0.8)
    o_flag = obs <= thr_o if worse_low else obs >= thr_o
    p_flag = pr <= thr_p if worse_low else pr >= thr_p
    tp = int((o_flag & p_flag).sum())
    S["warning"][y] = {"flagged": int(p_flag.sum()), "true_worst": int(o_flag.sum()), "hits": tp,
                       "precision": r(tp / p_flag.sum()), "recall": r(tp / o_flag.sum()),
                       "chance_precision": 0.2}
    pred_tab[f"warn_{y}"] = p_flag.astype(int)
    pred_tab[f"worst_{y}"] = o_flag.astype(int)
    # persistence flag on the same schools for comparison
    prev = d23.set_index("sid")[y]
    pp = pred_tab.sid.map(prev)
    m = pp.notna()
    thr_pp = pp[m].quantile(0.2 if worse_low else 0.8)
    pp_flag = (pp <= thr_pp) if worse_low else (pp >= thr_pp)
    tpp = int((o_flag[m] & pp_flag[m]).sum())
    S["warning"][y]["persistence_precision"] = r(tpp / pp_flag[m].sum())
S["warning"]["any_flag_schools"] = int((pred_tab.warn_credits.astype(bool) | pred_tab.warn_p_offtrack.astype(bool)).sum())

# ------------------------------------------------------------------ (f) failure audit (credits, temporal LIN)
pred_tab["resid_credits"] = pred_tab.credits - pred_tab.pred_credits
pred_tab["resid_gpa"] = pred_tab.gpa - pred_tab.pred_gpa
pred_tab["frl_tercile"] = pd.qcut(pred_tab.frl_share, 3, labels=["low FRL", "middle FRL", "high FRL"])
pred_tab["size_tercile"] = pd.qcut(pred_tab.n_enr, 3, labels=["small", "medium", "large"])
pred_tab["type"] = np.where(pred_tab.virtual == 1, "virtual", np.where(pred_tab.charter == 1, "charter", "traditional"))
overall = {y: np.average(pred_tab[f"resid_{y}"], weights=pred_tab.n_enr) for y in ("credits", "gpa")}
S["overall_resid"] = {y: r(v, 3) for y, v in overall.items()}
audit = []
for grp in ["locale4", "frl_tercile", "size_tercile", "type", "g8_source", "single_hs_corp"]:
    for k, g in pred_tab.groupby(grp, observed=True):
        for y in ("credits", "gpa"):
            rr = g[f"resid_{y}"] - overall[y]  # relative to the statewide cohort shift
            se = np.sqrt(np.average((rr - np.average(rr, weights=g.n_enr)) ** 2, weights=g.n_enr) / len(g))
            audit.append({"group": grp, "level": str(k), "outcome": y, "n_schools": len(g),
                          "mean_resid": np.average(rr, weights=g.n_enr), "se": se,
                          "rmse": np.sqrt(np.average(rr ** 2, weights=g.n_enr)),
                          "abs_t": abs(np.average(rr, weights=g.n_enr)) / se if se > 0 else np.nan})
audit = pd.DataFrame(audit)
audit.to_csv(PAPER / "tables" / "failure_audit_2024.csv", index=False)
S["audit"] = {f"{a.group}:{a.level}:{a.outcome}": {"n": int(a.n_schools), "mean_resid": r(a.mean_resid, 2),
                                                   "rmse": r(a.rmse, 2), "abs_t": r(a.abs_t, 1)}
              for a in audit.itertuples()}
big = audit[(audit.abs_t > 2)]
S["audit_flags"] = [f"{a.group}={a.level} ({a.outcome}): mean residual {a.mean_resid:+.2f}, n={a.n_schools}"
                    for a in big.itertuples()]
worst = pred_tab.reindex(pred_tab.resid_credits.abs().sort_values(ascending=False).index).head(20)
worst[["school", "sid", "n_enr", "type", "locale4", "credits", "pred_credits", "resid_credits", "gpa", "pred_gpa",
       "g8_source"]].to_csv(PAPER / "tables" / "worst_predicted_2024.csv", index=False)
S["worst"] = {"n_virtual_or_charter_in_top20": int((worst.type != "traditional").sum()),
              "n_small_in_top20": int((worst.n_enr < 30).sum()),
              "share_virtual_charter_overall": r((pred_tab.type != "traditional").mean())}

# ------------------------------------------------------------------ (g) lever importance (LIN fit on 2023 + 2024 pooled, FULL)
pool = pd.concat([d23, d24])
S["levers"] = {}
coef_rows = []
for y in ("credits", "gpa", "p_offtrack"):
    _, m, prep = fit_predict("LIN", FULL, pool, pool, y)
    names = list(prep.transform(pool).columns)
    coefs = dict(zip(names, m.named_steps["linearregression"].coef_))

    def one(z, f):
        _, mm, pp = fit_predict("LIN", FULL, z, z, y)
        nm = list(pp.transform(z).columns)
        return dict(zip(nm, mm.named_steps["linearregression"].coef_)).get(f, np.nan)

    S["levers"][y] = {}
    for f in FULL:
        ci = boot_ci(lambda z: one(z, f), pool, "cid", b=300)
        S["levers"][y][f] = {"coef_per_sd": r(coefs[f]), "ci": [r(c) for c in ci]}
        coef_rows.append({"outcome": y, "lever": f, "label": LABEL[f], "coef_per_sd": coefs[f], "lo": ci[0], "hi": ci[1]})
pd.DataFrame(coef_rows).to_csv(PAPER / "tables" / "lever_coefficients.csv", index=False)

# univariate correlations (2024) for context
S["univariate_r_2024_credits"] = {f: r(d24[[f, "credits"]].dropna().corr().iloc[0, 1]) for f in FULL}

# ------------------------------------------------------------------ (h) sensitivity
S["sensitivity"] = {}
for y in ("credits", "gpa"):
    p, _, _ = fit_predict("LIN", FULL + ["frl_share"], d23, d24, y)
    S["sensitivity"][f"{y}_with_frl_r2"] = r(wmetrics(d24[y].values, p, d24.n_enr)["r2"])
    big23, big24 = d23[d23.n_enr >= 30], d24[d24.n_enr >= 30]
    p, _, _ = fit_predict("LIN", FULL, big23, big24, y)
    S["sensitivity"][f"{y}_n30plus_r2"] = r(wmetrics(big24[y].values, p, big24.n_enr)["r2"])
    S["sensitivity"][f"{y}_n30plus_schools"] = int(len(big24))
    pu = LinearRegression()
    p, _, _ = fit_predict("LIN", ["sat_math"], d23, d24, y)
    S["sensitivity"][f"{y}_sat_only_r2"] = r(wmetrics(d24[y].values, p, d24.n_enr)["r2"])
    p, _, _ = fit_predict("LIN", ["g8_z"], d23, d24, y)
    S["sensitivity"][f"{y}_g8_only_r2"] = r(wmetrics(d24[y].values, p, d24.n_enr)["r2"])
    p, _, _ = fit_predict("LIN", [f for f in FULL if f != "sat_math"], d23, d24, y)
    S["sensitivity"][f"{y}_no_sat_r2"] = r(wmetrics(d24[y].values, p, d24.n_enr)["r2"])
    p, _, _ = fit_predict("LIN", ["frl_share"], d23, d24, y)
    S["sensitivity"][f"{y}_frl_only_r2"] = r(wmetrics(d24[y].values, p, d24.n_enr)["r2"])

# ------------------------------------------------------------------ math remediation (secondary)
mr = pred_tab.dropna(subset=["p_mathrem"])
S["mathrem"] = {"schools_reported_2024": int(len(mr)),
                "state_rate_2024": None,
                "corr_with_pred_credits": r(np.corrcoef(mr.p_mathrem, mr.pred_credits)[0, 1]),
                "corr_with_sat_math": r(mr[["p_mathrem", "sat_math"]].dropna().corr().iloc[0, 1])}

# ------------------------------------------------------------------ statewide context (CHE State rows)
S["state"] = {}
for y in (2021, 2022, 2023, 2024):
    st = pd.read_excel(ROOT / "data" / "raw" / f"che_{y}_cohort.xlsx", sheet_name="Data")
    st = st[st.LocationType == "State"]
    g = lambda c, b, col="EnrINPubCollegeN": pd.to_numeric(st[(st.Category == c) & (st.Breakout == b)][col], errors="coerce").sum()
    enr = g("Average", "Average")
    S["state"][str(y)] = {
        "hs_grads": int(g("Average", "Average", "HSGrads" if "HSGrads" in st else "HSGradsN")),
        "in_public_enrollees": int(enr),
        "offtrack_share": r((g("Credit Distribution", "<12") + g("Credit Distribution", "12 to 23.75")) / enr),
        "math_remediation_share": r((g("Remediation Type", "Math Only") + g("Remediation Type", "Both Math and English/Language Arts")) / enr),
        "gpa": r(float(st[st.Category == "Average"].AvgFreshmanGPA.iloc[0]), 2),
        "credits": r(float(st[st.Category == "Average"].AvgFreshmanCreditEarned.iloc[0]), 1)}
S["mathrem"]["state_rate_2024"] = S["state"]["2024"]["math_remediation_share"]

# ------------------------------------------------------------------ write
pred_tab.to_csv(PROC / "predictions_2024.csv", index=False)
(PAPER / "stats.json").write_text(json.dumps(S, indent=2))
print(json.dumps({k: S[k] for k in ("cv2023", "temporal")}, indent=1)[:6000])
print("\nwarning:", json.dumps(S["warning"], indent=1))
print("\naudit flags:", S["audit_flags"])
print("\nsensitivity:", S["sensitivity"])
print("\ndrift credits:", json.dumps(S["drift"]["credits"], indent=1))
