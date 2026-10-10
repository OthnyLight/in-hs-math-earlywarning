**Status: v0.1.0, released 2026-10-09. Verified by the author. Zenodo DOI to be added.**

# Indiana high school early-warning model for first-year college outcomes

An interpretable, calibrated model that estimates, for each Indiana public high school, how its graduates will fare in their first college year (credits earned and GPA at Indiana public colleges), using only public school-level signals available while students are still in high school: grade 7/8 state math results, grade 11 SAT math results, the grade in which students pass Algebra I, whether advanced math and calculus are offered, AP exam passing and dual-credit earning. The model is tested on a cohort it never saw, calibrated, audited for where it fails, and checked across the graduating classes of 2021–2024.

**Why:** weak first-year outcomes cost students time and money and lower completion, but schools learn about them years after graduation. A transparent warning lets districts and the state act while students are still in high school.

Headline results are in `docs/MODEL_CARD.md`, the short manuscript `paper/manuscript.pdf`, and the detailed technical paper `paper/journal/technical_paper.pdf` (all numbers generated from `paper/stats.json`).

## Contents
| Path | What |
|---|---|
| `data/raw/` | Every input as downloaded, plus `PROVENANCE.txt` (URL, date, bytes, SHA-256) |
| `data/processed/school_panel.csv` | School × cohort analysis panel (see `docs/CODEBOOK.md`) |
| `data/processed/predictions_2024.csv` | Out-of-sample predictions, flags and residuals for the class of 2024 |
| `data/processed/qa_report.txt` | Row counts, match rates, range checks, named spot checks |
| `paper/` | `stats.json`, figures, tables, `manuscript.docx`/`.pdf`; `journal/` holds the LaTeX technical paper and its vector figures |
| `map/index.html` | Interactive school map (single self-contained file; a copy in `docs/map/` is served by GitHub Pages) |
| `docs/` | Model card, codebook, limitations, verification checklist, next steps, publish guide, build spec |
| `code/` | Numbered pipeline scripts |

## Run it
Requires Python 3.10+ (pandas, numpy, scikit-learn, matplotlib, openpyxl), Node 18+ with the `docx` package, and LibreOffice for the PDF.

```bash
pip install -r requirements.txt
npm install docx
python code/01_fetch.py          # downloads/verifies the in.gov files (committed copies are used if present)
python code/01b_fetch_urban.py   # optional: rebuild the CRDC/CCD extracts from the Urban Institute API
bash run_all.sh                  # 02 build → 03 model → 04 figures → 05 map → 06 manuscript → 07 model card
```
`03_model.py` takes about three minutes (cluster bootstraps). Add `--final` to `run_all.sh` only after the verification checklist is complete; it removes the draft stamps.

## Sources (all public)
- Indiana Commission for Higher Education, College-Going / College-Readiness datasets, classes of 2021–2024 (released 2023–2026): https://www.in.gov/che/college-going-reports/
- Indiana Department of Education: ISTEP+ 2017–2018 and ILEARN 2019/2021 grade 3–8 school results; SAT grade 11 school results 2022–2023; AP school results; 2025–26 school directory: https://www.in.gov/doe/it/data-center-and-reports/
- U.S. Department of Education Office for Civil Rights, Civil Rights Data Collection 2017–18, 2020–21, 2023–24, and NCES Common Core of Data 2022–23, both via the Urban Institute Education Data Portal: https://educationdata.urban.org/
Access verified 2026-10-06; files fetched 2026-10-09.

## Limitations
See `docs/LIMITATIONS.md`. In short: outcomes cover only Indiana public college enrollees; school-level only, never for individual students; grade 8 results are mostly district averages; the full model rests on one cohort transition; coefficients are associations.

## License and citation
Code: MIT (`LICENSE`). Derived data, figures and documents: CC BY 4.0 (`LICENSE-DATA.md`), with attribution to the public sources above. Cite with `CITATION.cff`.

Maintainer: Othniel Iyassa Sa'anga, Independent Researcher (ORCID 0009-0002-6113-6158), othnylight@gmail.com.
