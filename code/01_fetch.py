#!/usr/bin/env python3
"""01_fetch.py — download every raw input from in.gov and verify it against PROVENANCE.txt.

Run from the repository root:  python code/01_fetch.py
Files land in data/raw/ under the short names used by the rest of the pipeline.

Note on this release: the build sandbox could not reach in.gov, so the committed raw files
were downloaded through the author's own browser on 2026-10-09 and their SHA-256 hashes
recorded in data/raw/PROVENANCE.txt. This script reproduces that step on any normal
internet connection and stops if a file on the server has changed since then (state
agencies sometimes re-post files under the same URL with corrections).
"""
import hashlib
import pathlib
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"

FILES = {
    # Indiana Commission for Higher Education, College-Going / College-Readiness datasets
    # https://www.in.gov/che/college-going-reports/
    "che_2024_cohort.xlsx": "https://www.in.gov/dA/d1c423c709/2026-College-Going-Dataset-2024-Cohort.xlsx?language_id=1",
    "che_2023_cohort.xlsx": "https://www.in.gov/dA/2f8404d686/2025-College-Readiness-Dataset-2023-Cohort_update.xlsx?language_id=1",
    "che_2022_cohort.xlsx": "https://www.in.gov/dA/667abc107d/2024-College-Readiness-Dataset-2022-Cohort.xlsx?language_id=1",
    "che_2021_cohort.xlsx": "https://www.in.gov/dA/412db3af32/2023-College-Readiness-Dataset-2021-Cohort.xlsx?language_id=1",
    # Indiana Department of Education, https://www.in.gov/doe/it/data-center-and-reports/
    "ilearn_2019_school.xlsx": "https://www.in.gov/doe/files/ilearn-2019-grade3-8-final-school.xlsx",
    "ilearn_2021_school.xlsx": "https://www.in.gov/doe/files/ILEARN-2021-Grade3-8-Final-School.xlsx",
    "istep_2017_school.xlsx": "https://www.in.gov/doe/files/istep-2017-grade3-8-final-school.xlsx",
    "istep_2018_school.xlsx": "https://www.in.gov/doe/files/ISTEP-2018-Grade3-8-Final-School.xlsx",
    "sat_2022_gr11_school.xlsx": "https://www.in.gov/doe/files/SAT-2022-Grade11-Final-School-v2.xlsx",
    "sat_2023_gr11_school.xlsx": "https://www.in.gov/doe/files/SAT-2023-Grade11-Final-School.xlsx",
    "ap_school_results.xlsx": "https://www.in.gov/doe/files/corporation-and-school-ap-grad-results.xlsx",
    "school_directory_2025_26.xlsx": "https://www.in.gov/doe/files/2025-2026-school-directory-2026-03-23.xlsx",
}


def expected_hashes():
    out = {}
    prov = RAW / "PROVENANCE.txt"
    if prov.exists():
        for line in prov.read_text().splitlines():
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 4 and parts[3].startswith("sha256:"):
                out[parts[1]] = parts[3].split(":", 1)[1]
    return out


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    want = expected_hashes()
    bad = 0
    for name, url in FILES.items():
        dest = RAW / name
        if not dest.exists():
            print(f"fetch  {name}")
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (replication script)"})
            with urllib.request.urlopen(req, timeout=120) as r, open(dest, "wb") as f:
                f.write(r.read())
        got = sha256(dest)
        status = "ok" if want.get(name) in (None, got) else "HASH MISMATCH"
        if status != "ok":
            bad += 1
        print(f"{status:14s} {name}  {got[:16]}")
    print("\nCRDC and CCD inputs come from the Urban Institute Education Data API; run code/01b_fetch_urban.py.")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
