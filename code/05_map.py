#!/usr/bin/env python3
"""05_map.py — build map/index.html, the interactive school map (single self-contained file).

Every Indiana public high school in the class-of-2024 panel with predictors gets a prediction
from the linear model fit on the class of 2023 (same specification as 03_model.py). The map shows
the schools in the class-of-2024 test set (>= 10 Indiana-public-college enrollees, most levers present).

  python code/05_map.py            # DRAFT banner (default)
  python code/05_map.py --final
"""
import json
import pathlib
import sys

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = pathlib.Path(__file__).resolve().parents[1]
PROC, MAP = ROOT / "data" / "processed", ROOT / "map"
MAP.mkdir(exist_ok=True)
FINAL = "--final" in sys.argv
FULL = ["g8_z", "sat_math", "alg1_late", "alg1_hs", "offers_adv", "offers_calc", "adv_share", "ap_pass", "dual"]

panel = pd.read_csv(PROC / "school_panel.csv", dtype={"sid": str, "cid": str})
train = panel[(panel.cohort == 2023) & panel.has_outcome & (panel.n_enr >= 10)]
cur = panel[panel.cohort == 2024].copy()
cur = cur[cur.lat.notna()]
cur["_npred"] = cur[FULL].notna().sum(axis=1)
cur = cur[(cur._npred >= 5) & cur.has_outcome & (cur.n_enr >= 10)]  # the schools the model was tested on

med = train[FULL].median()
miss = [f for f in FULL if train[f].isna().any()]


def X(d):
    z = d[FULL].fillna(med).copy()
    for f in miss:
        z[f + "_missing"] = d[f].isna().astype(float)
    return z


for y in ("credits", "gpa", "p_offtrack"):
    m = make_pipeline(StandardScaler(), LinearRegression())
    m.fit(X(train), train[y], linearregression__sample_weight=train.n_enr.values)
    cur[f"pred_{y}"] = m.predict(X(cur))

# consistency with 03_model.py
chk = pd.read_csv(PROC / "predictions_2024.csv", dtype={"sid": str}).set_index("sid").pred_credits
both = cur.set_index("sid").pred_credits.reindex(chk.index).dropna()
maxdiff = float((both - chk.reindex(both.index)).abs().max())
assert maxdiff < 1e-6, f"map predictions differ from 03_model.py by {maxdiff}"

obs_ok = cur.has_outcome & (cur.n_enr >= 10)
q20 = cur.loc[obs_ok, "pred_credits"].quantile(0.2)
q80 = cur.loc[obs_ok, "pred_p_offtrack"].quantile(0.8)
cur["warn"] = ((cur.pred_credits <= q20) | (cur.pred_p_offtrack >= q80)).astype(int)
state_med = {f: float(train[f].median()) for f in FULL}


def rnd(v, k):
    return None if pd.isna(v) else round(float(v), k)


rows = []
for r in cur.itertuples():
    has = bool(r.has_outcome and r.n_enr >= 10)
    rows.append({
        "id": r.sid, "n": r.school.rsplit("-", 1)[0], "city": r.school.rsplit("-", 1)[-1],
        "lat": rnd(r.lat, 4), "lon": rnd(r.lon, 4), "loc": r.locale4 if isinstance(r.locale4, str) else "",
        "type": "virtual" if r.virtual == 1 else ("charter" if r.charter == 1 else "traditional"),
        "grads": rnd(r.hs_grads, 0), "enr": rnd(r.n_enr, 0) if has else None,
        "pc": rnd(r.pred_credits, 1), "pg": rnd(r.pred_gpa, 2), "po": rnd(r.pred_p_offtrack, 3),
        "oc": rnd(r.credits, 1) if has else None, "og": rnd(r.gpa, 2) if has else None,
        "oo": rnd(r.p_offtrack, 3) if has else None, "w": int(r.warn),
        "lv": {"g8": rnd(r.g8_math, 3), "g8s": r.g8_source if isinstance(r.g8_source, str) else "",
               "sat": rnd(r.sat_math, 3), "late": rnd(r.alg1_late, 3), "ap": rnd(r.ap_pass, 3), "dual": rnd(r.dual, 3),
               "a2": rnd(r.c_alg2_2023, 0), "adv": rnd(r.c_adv_2023, 0), "calc": rnd(r.c_calc_2023, 0)},
    })

meta = {"n_schools": len(rows), "n_observed": int(obs_ok.sum()), "n_warn": int(cur.warn.sum()),
        "q20_credits": round(float(q20), 1), "q80_offtrack": round(float(q80), 3),
        "state_med": {"sat": round(state_med["sat_math"], 3), "ap": round(state_med["ap_pass"], 3),
                      "dual": round(state_med["dual"], 3), "late": round(state_med["alg1_late"], 3)},
        "draft": "" if FINAL else "Draft for author verification. Numbers come from public files and have not yet been checked against the sources by the author."}
tpl = (ROOT / "code" / "map_template.html").read_text()
html = tpl.replace("/*__DATA__*/[]", json.dumps(rows, separators=(",", ":"))).replace(
    "/*__META__*/{}", json.dumps(meta, separators=(",", ":")))
(MAP / "index.html").write_text(html)
cur.drop(columns=["_npred"]).to_csv(PROC / "map_schools_2024.csv", index=False)
print(f"wrote map/index.html: {len(rows)} schools, {meta['n_observed']} with observed outcomes, {meta['n_warn']} flagged; "
      f"max diff vs 03_model {maxdiff:.2e}")
