# Verification checklist (author completes before any release)

Initial and date each line in your own copy. `publish_gate.py` checks the mechanical items; these are yours. Nothing is published until every box is ticked and you say so in your own words.

## Reproduce
- [ ] On a normal internet connection, run `python code/01_fetch.py`: all 12 in.gov files show `ok` (hash matches PROVENANCE.txt), or explain any mismatch (state agencies re-post corrected files).
- [ ] Run `python code/01b_fetch_urban.py` and compare `data/raw/rebuilt_urban_*.csv` with the committed Urban extracts (differences should be limited to the a1e78/a1p78 quirk in LIMITATIONS #8).
- [ ] Run `bash run_all.sh`; outputs match the committed versions (paper/stats.json, data/processed/*.csv).
- [ ] Every number in the manuscript and model card came from the regenerated stats.json (they are interpolated; rebuild both after any change).

## Source-level spot checks (open the original Excel files)
- [ ] The six named schools in `data/processed/qa_report.txt` (Adams Central, Carmel, Crispus Attucks, West Side Leadership Academy, Signature School, Muncie Central): grads, enrollees, GPA, credits, off-track share, SAT math rate, grade 7 rate.
- [ ] Statewide class-of-2024 figures in the paper (credits 23.6, GPA 2.86, < 24 credits 35.6%, math remediation 4.2%) against the CHE 2024 file's State rows.
- [ ] Five schools you know personally: does the map's predicted vs observed picture match what you know?
- [ ] Five extreme schools from `paper/tables/worst_predicted_2024.csv`: confirm the observed values in CHE and look for a real explanation (closure, merger, program change, data error).
- [ ] Five random schools (pick with a seed you record) traced from raw file to panel row.

## Judgment calls to own (agree, or change and rerun)
- [ ] **Outcome definition:** mean credits and mean GPA of Indiana-public-college enrollees as primary; share < 24 credits and share GPA < 2.0 as secondary; math remediation reported but not modeled.
- [ ] **Grade 8 attribution:** own-building rate when the high school tested ≥ 10 grade 8 students, otherwise the corporation rate.
- [ ] **COVID gap:** class of 2024 uses its grade 7 ILEARN 2019 results.
- [ ] **Sample floor:** ≥ 10 Indiana public college enrollees.
- [ ] **Warning threshold:** lowest fifth of predicted credits (or highest fifth of predicted off-track share).
- [ ] **Demographics out of the headline model:** poverty used only in the audit and a sensitivity check (your answer on 2026-10-06).
- [ ] **Map scope:** only the 367 test-set schools are shown; adult-learner and correctional schools without reportable outcomes are excluded.
- [ ] **References:** each of the 15 references checked against the original (title, journal, volume, pages).

## Before it goes public
- [ ] AUTHORS.json filled in (name, ORCID, affiliation); funding and competing-interest statements written in the manuscript.
- [ ] Manuscript, README, model card and limitations reread and revised in your own voice; nothing you cannot defend remains.
- [ ] AI-use statement in the manuscript is accurate as you revised it.
- [ ] Regenerate everything with `--final` (`bash run_all.sh --final`); `python publish_gate.py . --allow-draft-in code/` passes.
- [ ] Evidence log row written the day of each release (docs/evidence_log.csv).
