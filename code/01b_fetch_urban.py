#!/usr/bin/env python3
"""01b_fetch_urban.py — rebuild the two Urban Institute extracts from the Education Data API.

  data/raw/urban_ccd_dir_2022_hs.csv          NCES CCD 2022-23 directory, Indiana schools whose
                                              highest grade is 12 (coordinates, locale, FRL, ...)
  data/raw/urban_crdc_hs_2017_2020_2023.csv   CRDC 2017-18 and 2020-21 Algebra I passing by grade
                                              band, math enrollment, and course offerings
                                              (offerings also for 2023-24), same schools

API docs: https://educationdata.urban.org/documentation/  (fips=18 is Indiana; race=99&sex=99
selects school totals). Writes to data/raw/rebuilt_*.csv so the committed files are never
overwritten; compare with  diff  or the QA report.

The committed files were produced by code/01b_fetch_urban_browser.js (see that file's header).
This script implements the same selection with one intentional difference: blank or negative
codes in the grade-7/8 Algebra I columns are treated as missing rather than summed (the
browser script's quirk). Those columns are not used by the model.
"""
import csv
import json
import pathlib
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
B = "https://educationdata.urban.org/api/v1/schools/"


def get_all(url):
    out = []
    while url:
        with urllib.request.urlopen(url, timeout=120) as r:
            j = json.load(r)
        out += j["results"]
        url = j["next"]
    return out


def code(v):
    """Urban codes: -1 missing, -2 not applicable, -3 suppressed."""
    if v is None:
        return ""
    if isinstance(v, (int, float)) and v < 0:
        return "NA" if v == -2 else "X"
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v)


def main():
    d = [r for r in get_all(B + "ccd/directory/2022/?fips=18") if r.get("highest_grade_offered") == 12]
    hs = {r["ncessch"] for r in d}
    with open(RAW / "rebuilt_urban_ccd_dir_2022_hs.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ncessch", "seasch", "lat", "lon", "locale", "charter", "enrollment", "frl", "lowgr", "virtual"])
        for r in d:
            w.writerow([r["ncessch"], r["seasch"], f'{r["latitude"]:.4f}', f'{r["longitude"]:.4f}',
                        r["urban_centric_locale"], r["charter"], r["enrollment"],
                        r["free_or_reduced_price_lunch"] if r["free_or_reduced_price_lunch"] is not None else "",
                        r["lowest_grade_offered"], r.get("virtual", "")])

    rec = {}
    g = lambda s, y: rec.setdefault((s, y), {"s": s, "y": y})
    band = {20: "78", 7: "78", 8: "78", 21: "910", 22: "1112"}
    for y in (2017, 2020):
        for r in get_all(B + f"crdc/algebra1/{y}/race/sex/?fips=18&race=99&sex=99"):
            if r["ncessch"] not in hs or r["grade_crdc"] not in band:
                continue
            o, b = g(r["ncessch"], y), band[r["grade_crdc"]]
            for k, v in (("a1e" + b, r["enrl_algebra1"]), ("a1p" + b, r["students_passing_algebra1"])):
                if v is not None and v >= 0:
                    o[k] = o.get(k, 0) + v
        for r in get_all(B + f"crdc/math-and-science/{y}/race/sex/?fips=18&race=99&sex=99"):
            if r["ncessch"] in hs:
                o = g(r["ncessch"], y)
                o.update(e_alg2=r["enrl_algebra2"], e_adv=r["enrl_advanced_math"], e_calc=r["enrl_calculus"])
    for y in (2017, 2020, 2023):
        for r in get_all(B + f"crdc/offerings/{y}/?fips=18"):
            if r["ncessch"] in hs:
                o = g(r["ncessch"], y)
                o.update(c_alg2=r["num_classes_algebra2"], c_adv=r["num_classes_advanced_math"],
                         c_calc=r["num_classes_calculus"], ap_math=r["ap_courses_math_indicator"],
                         n_ap=r["num_courses_ap"], dual=r["sch_dual_indicator"])
    cols = ["s", "y", "a1e78", "a1p78", "a1e910", "a1p910", "a1e1112", "a1p1112", "e_alg2", "e_adv",
            "e_calc", "c_alg2", "c_adv", "c_calc", "ap_math", "n_ap", "dual"]
    with open(RAW / "rebuilt_urban_crdc_hs_2017_2020_2023.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for o in rec.values():
            w.writerow([o["s"], o["y"]] + [code(o.get(k)) for k in cols[2:]])
    print("wrote rebuilt_urban_*.csv to", RAW)


if __name__ == "__main__":
    main()
