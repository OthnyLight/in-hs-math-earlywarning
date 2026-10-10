#!/usr/bin/env python3
"""02_build.py — assemble the school x cohort analysis panel and write the QA report.

Inputs : data/raw/*  (see 01_fetch.py, 01b_fetch_urban.py, PROVENANCE.txt)
Outputs: data/processed/school_panel.csv, data/processed/qa_report.txt

Unit: Indiana PUBLIC high school (traditional or charter) x graduating cohort 2021-2024.

Outcomes (CHE College-Going/Readiness file, Average row and distribution breakouts; all refer to
graduates who enrolled at an Indiana public college the fall after graduation):
  gpa        AvgFreshmanGPA
  credits    AvgFreshmanCreditEarned
  p_offtrack share of enrollees earning < 24 credits in year 1  ("<12" + "12 to 23.75")
  p_gpa_lt2  share of enrollees with first-year GPA < 2.0
  p_mathrem  share of enrollees needing math remediation ("Math Only" + "Both Math and ELA")
  n_enr      EnrINPubCollegeN (the denominator and the model weight)

School-level signals (all observable before or during high school):
  g8_math   grade-8 math proficiency of the cohort (ILEARN 2019 gr8 for class of 2023,
            ILEARN 2019 gr7 for 2024 [no 2020 test], ISTEP+ 2018 gr8 for 2022, ISTEP+ 2017 gr8
            for 2021); attributed to the high school when that building tested grade 8, else to
            the school corporation; z-scored within assessment year (g8_z)
  sat_math  % of grade-11 SAT takers at the math benchmark (classes of 2023 and 2024 only)
  alg1_late share of the school's Algebra I passers who passed in grades 11-12 (CRDC)
  alg1_hs   Algebra I passers in grades 9-12 per enrolled student (CRDC; high = most students
            meet Algebra I in high school rather than middle school)
  offers_alg2 / offers_adv / offers_calc  course offered (CRDC classes > 0)
  adv_share (advanced math + calculus enrollment) / school enrollment (CRDC 2020-21 only)
  ap_pass   share of graduates who took and passed an AP exam (CHE breakout)
  dual      share of graduates who earned dual credit from an Indiana public college (CHE)
Audit-only covariates (kept OUT of the headline model): frl_share, locale4, enroll, charter, virtual.
"""
import pathlib
import re

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW, OUT = ROOT / "data" / "raw", ROOT / "data" / "processed"
OUT.mkdir(parents=True, exist_ok=True)
QA = []


def qa(*a):
    line = " ".join(str(x) for x in a)
    QA.append(line)
    print(line)


def num(x):
    return pd.to_numeric(x.replace({"DS": np.nan, "***": np.nan}) if hasattr(x, "replace") else x, errors="coerce")


# ------------------------------------------------------------------ directory (public schools)
sch = pd.read_excel(RAW / "school_directory_2025_26.xlsx", sheet_name="SCHL", dtype=str)
sch["sid"] = sch.IDOE_SCHOOL_ID.str.zfill(4)
sch = sch.drop_duplicates("sid", keep="last")  # one id (6864) listed under two charter holders; keep the current one
public_ids = set(sch.sid)
qa("== Directory: public schools listed (2025-26 IDOE SCHL sheet):", len(public_ids))

# ------------------------------------------------------------------ CHE outcomes
def che(year):
    d = pd.read_excel(RAW / f"che_{year}_cohort.xlsx", sheet_name="Data")
    d = d[d.LocationType == "School"].copy()
    d = d.rename(columns={"HSGradsN": "HSGrads"})
    return d


che24 = che(2024)
id_by_name = (che24[che24.Category == "Average"][["Location", "LocationId"]]
              .drop_duplicates().set_index("Location").LocationId.astype(str).str.zfill(4))

rows = []
LINK = {}
for year in (2021, 2022, 2023, 2024):
    d = che24 if year == 2024 else che(year)
    if year == 2024:
        d["sid"] = d.LocationId.astype(str).str.zfill(4)
    else:
        d["sid"] = d.Location.map(id_by_name)
    names = d.Location.unique()
    linked = d.dropna(subset=["sid"]).Location.nunique()
    qa(f"== CHE {year}: schools {len(names)}, linked to IDOE id {linked} ({linked/len(names):.1%})")
    LINK[year] = linked / len(names)
    d = d.dropna(subset=["sid"])

    def pick(cat, brk, col):
        x = d[(d.Category == cat) & (d.Breakout == brk)].set_index("sid")[col]
        return num(x)

    avg = d[d.Category == "Average"].set_index("sid")
    out = pd.DataFrame({
        "school": avg.Location,
        "hs_grads": num(avg.HSGrads),
        "n_college": num(avg.EnrCollegeN),
        "n_enr": num(avg.EnrINPubCollegeN),
        "gpa": num(avg.AvgFreshmanGPA),
        "credits": num(avg.AvgFreshmanCreditEarned),
    })
    lt12 = pick("Credit Distribution", "<12", "EnrINPubCollegeN")
    c12 = pick("Credit Distribution", "12 to 23.75", "EnrINPubCollegeN")
    g2 = pick("GPA Distribution", "<2.0", "EnrINPubCollegeN")
    mo = pick("Remediation Type", "Math Only", "EnrINPubCollegeN")
    mb = pick("Remediation Type", "Both Math and English/Language Arts", "EnrINPubCollegeN")
    out["p_offtrack"] = (lt12 + c12) / out.n_enr
    out["p_gpa_lt2"] = g2 / out.n_enr
    out["p_mathrem"] = (mo + mb) / out.n_enr
    out["ap_pass"] = pick("Advanced Placement", "Took and Passed an AP Test", "HSGrads" if "HSGrads" in d else "HSGradsN") / out.hs_grads
    out["dual"] = pick("Dual Credit", "Earned Dual Credit from an Indiana Public College", "HSGrads") / out.hs_grads
    out["cohort"] = year
    rows.append(out.reset_index())

panel = pd.concat(rows, ignore_index=True)
n0 = len(panel)
panel = panel[panel.sid.isin(public_ids)].copy()
qa(f"== Kept public schools: {len(panel)} of {n0} school-cohort rows (dropped nonpublic/closed)")

# ------------------------------------------------------------------ grade-8 (or 7) math
def read_idoe(fname, sheet, header_row, cols):
    d = pd.read_excel(RAW / fname, sheet_name=sheet, header=None, dtype=object, skiprows=header_row + 1)
    d = d[d[0].astype(str).str.fullmatch(r"\w{4}")]
    out = pd.DataFrame({"cid": d[0].astype(str), "sid": d[2].astype(str)})
    for k, j in cols.items():
        out[k] = pd.to_numeric(d[j], errors="coerce")
    return out


g8_sources = {
    2021: ("istep_2017_school.xlsx", 0, 1, {"pass": 52, "tested": 53}, "ISTEP+ 2017 grade 8"),
    2022: ("istep_2018_school.xlsx", 0, 1, {"pass": 52, "tested": 53}, "ISTEP+ 2018 grade 8"),
    2023: ("ilearn_2019_school.xlsx", "Math", 5, {"pass": 43, "tested": 44}, "ILEARN 2019 grade 8"),
    2024: ("ilearn_2019_school.xlsx", "Math", 5, {"pass": 36, "tested": 37}, "ILEARN 2019 grade 7 (no 2020 test)"),
}
g8_frames = []
for cohort, (f, sh, hr, cols, label) in g8_sources.items():
    d = read_idoe(f, sh, hr, cols)
    d = d.dropna(subset=["tested"])
    d = d[d.tested > 0]
    corp = d.groupby("cid")[["pass", "tested"]].sum()
    corp["corp_rate"] = corp["pass"] / corp["tested"]
    school = d.set_index("sid")
    school["rate"] = school["pass"] / school["tested"]
    state = d["pass"].sum() / d["tested"].sum()
    qa(f"== {label} (class of {cohort}): {len(d)} schools tested, state rate {state:.3f}")
    g8_frames.append((cohort, school[["rate", "tested"]], corp[["corp_rate", "tested"]], label))

cid_of = sch.set_index("sid").IDOE_CORPORATION_ID.str.zfill(4)
panel["cid"] = panel.sid.map(cid_of)
panel["g8_math"] = np.nan
panel["g8_source"] = ""
for cohort, school, corp, label in g8_frames:
    m = panel.cohort == cohort
    s_rate = panel.loc[m, "sid"].map(school.rate)
    s_n = panel.loc[m, "sid"].map(school.tested)
    c_rate = panel.loc[m, "cid"].map(corp.corp_rate)
    use_school = s_rate.notna() & (s_n >= 10)
    panel.loc[m, "g8_math"] = np.where(use_school, s_rate, c_rate)
    panel.loc[m, "g8_source"] = np.where(use_school, "school", np.where(c_rate.notna(), "corporation", ""))
    qa(f"   class of {cohort}: attributed at school {use_school.sum()}, corporation {(~use_school & c_rate.notna()).sum()}, missing {panel.loc[m,'g8_math'].isna().sum()}")
# z-score within cohort (ISTEP+ and ILEARN are different scales; grade 7 vs 8 also differ)
panel["g8_z"] = panel.groupby("cohort").g8_math.transform(lambda x: (x - x.mean()) / x.std())

# corporations with one high school in the panel: feeder attribution is cleanest there
nhs = panel[panel.cohort == 2024].groupby("cid").sid.nunique()
panel["single_hs_corp"] = panel.cid.map(nhs).eq(1)

# ------------------------------------------------------------------ SAT grade 11 math
sat_sources = {2023: "sat_2022_gr11_school.xlsx", 2024: "sat_2023_gr11_school.xlsx"}
panel["sat_math"] = np.nan
panel["sat_tested"] = np.nan
for cohort, f in sat_sources.items():
    d = read_idoe(f, "Math", 4, {"at": 6, "tested": 7})
    d = d[d.tested > 0].set_index("sid")
    m = panel.cohort == cohort
    panel.loc[m, "sat_math"] = panel.loc[m, "sid"].map(d["at"] / d["tested"])
    panel.loc[m, "sat_tested"] = panel.loc[m, "sid"].map(d["tested"])
    qa(f"== SAT grade 11 ({f}) -> class of {cohort}: matched {panel.loc[m,'sat_math'].notna().sum()} of {m.sum()}")

# ------------------------------------------------------------------ CCD directory + CRDC
ccd = pd.read_csv(RAW / "urban_ccd_dir_2022_hs.csv", dtype={"ncessch": str, "seasch": str})
ccd["sid"] = ccd.seasch.str.split("-").str[1]
ccd = ccd[ccd.sid.str.fullmatch(r"\d{4}", na=False)].drop_duplicates("sid").set_index("sid")
locale_map = {1: "City", 2: "Suburb", 3: "Town", 4: "Rural"}
panel["ncessch"] = panel.sid.map(ccd.ncessch)
panel["lat"] = panel.sid.map(ccd.lat)
panel["lon"] = panel.sid.map(ccd.lon)
panel["locale4"] = panel.sid.map((ccd.locale // 10).map(locale_map))
panel["enroll"] = panel.sid.map(ccd.enrollment)
panel["frl_share"] = panel.sid.map(ccd.frl / ccd.enrollment.replace(0, np.nan))
panel["charter"] = panel.sid.map(ccd.charter)
panel["virtual"] = panel.sid.map(ccd.virtual)
qa(f"== CCD 2022 directory matched (coords/locale): {panel.drop_duplicates('sid').lat.notna().sum()} of {panel.sid.nunique()} schools")

cr = pd.read_csv(RAW / "urban_crdc_hs_2017_2020_2023.csv", dtype={"s": str}, na_values=["NA", "X"])
cr = cr.rename(columns={"s": "ncessch", "y": "crdc_year", "dual": "crdc_dual_offered"})
crdc_for_cohort = {2021: 2017, 2022: 2017, 2023: 2020, 2024: 2020}
panel["crdc_year"] = panel.cohort.map(crdc_for_cohort)
panel = panel.merge(cr, on=["ncessch", "crdc_year"], how="left")
for c in ["a1p910", "a1p1112", "a1e910", "a1e1112", "c_alg2", "c_adv", "c_calc", "e_adv", "e_calc"]:
    panel.loc[panel[c] < 0, c] = np.nan
hs_pass = panel.a1p910 + panel.a1p1112
panel["alg1_late"] = np.where(hs_pass > 0, panel.a1p1112 / hs_pass, np.nan)
panel["alg1_hs"] = hs_pass / panel.enroll.replace(0, np.nan)
panel["offers_alg2"] = (panel.c_alg2 > 0).astype(float).where(panel.c_alg2.notna())
panel["offers_adv"] = (panel.c_adv > 0).astype(float).where(panel.c_adv.notna())
panel["offers_calc"] = (panel.c_calc > 0).astype(float).where(panel.c_calc.notna())
panel["adv_share"] = (panel.e_adv.fillna(0) + panel.e_calc.fillna(0)) / panel.enroll.replace(0, np.nan)
panel.loc[panel.crdc_year == 2017, "adv_share"] = np.nan  # 2017-18 extract lacks a usable enrollment split
qa(f"== CRDC rows matched: " + ", ".join(
    f"{y}: {panel[(panel.cohort==y)].c_alg2.notna().sum()}/{(panel.cohort==y).sum()}" for y in (2021, 2022, 2023, 2024)))

# current offerings (CRDC 2023-24) for the map
cur = cr[cr.crdc_year == 2023].set_index("ncessch")
for k in ("c_alg2", "c_adv", "c_calc"):
    panel[k + "_2023"] = panel.ncessch.map(cur[k])

# ------------------------------------------------------------------ sample definition
panel["small"] = panel.n_enr < 10
panel["has_outcome"] = panel.gpa.notna() & panel.credits.notna()
qa("\n== Sample")
for y in (2021, 2022, 2023, 2024):
    p = panel[panel.cohort == y]
    qa(f"   class of {y}: public schools {len(p)}, with GPA+credits {p.has_outcome.sum()}, "
       f"with off-track share {p.p_offtrack.notna().sum()}, with math remediation share {p.p_mathrem.notna().sum()}, "
       f"enrollees covered {int(p[p.has_outcome].n_enr.sum())} of {int(p.n_enr.sum())}")

# ------------------------------------------------------------------ range checks
qa("\n== Range checks (outcome rows)")
o = panel[panel.has_outcome]
for c in ["gpa", "credits", "p_offtrack", "p_gpa_lt2", "p_mathrem", "g8_math", "sat_math", "alg1_late",
          "alg1_hs", "ap_pass", "dual", "adv_share", "frl_share"]:
    x = o[c]
    qa(f"   {c:11s} n={x.notna().sum():4d}  min={x.min():.3f}  median={x.median():.3f}  max={x.max():.3f}")
bad = o[(o.gpa < 0) | (o.gpa > 4) | (o.credits < 0) | (o.credits > 60) | (o.p_offtrack > 1) | (o.ap_pass > 1) | (o.dual > 1)]
qa(f"   out-of-range rows: {len(bad)}")
if len(bad):
    qa(bad[["school", "cohort", "gpa", "credits", "p_offtrack", "ap_pass", "dual"]].to_string())

# ------------------------------------------------------------------ named spot checks (verify by hand against the source files)
qa("\n== Spot checks — open the named source file and confirm these values")
spot = ["Adams Central High School-Monroe", "Carmel High School-Carmel", "Crispus Attucks High School-Indianapolis",
        "West Side Leadership Academy-Gary", "Signature School Inc-Evansville", "Muncie Central High School-Muncie"]
for nm in spot:
    r = panel[(panel.school == nm) & (panel.cohort == 2024)]
    if len(r):
        r = r.iloc[0]
        qa(f"   {nm} (id {r.sid}), class of 2024: grads {r.hs_grads:.0f}, IN-public enrollees {r.n_enr:.0f}, "
           f"GPA {r.gpa}, credits {r.credits}, off-track share {r.p_offtrack:.3f}, SAT math benchmark {r.sat_math:.3f} "
           f"(SAT-2023-Grade11 'Math' sheet), grade-7 ILEARN math {r.g8_math:.3f} [{r.g8_source}]")
    else:
        qa(f"   {nm}: not found in 2024 panel")

panel = panel.sort_values(["cohort", "sid"])
panel.to_csv(OUT / "school_panel.csv", index=False)
(OUT / "qa_report.txt").write_text("\n".join(QA) + "\n")
import json
(OUT / "build_stats.json").write_text(json.dumps({"che_name_link_rate": {str(k): round(v, 3) for k, v in LINK.items()}}, indent=1))
qa(f"\nwrote {OUT/'school_panel.csv'} ({len(panel)} rows)")
