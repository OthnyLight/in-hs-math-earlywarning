# Publish guide — Indiana HS early-warning model, v0.1

Nothing has been pushed or submitted. No GitHub or Zenodo token was supplied, and the preprint server requires your personal attestation. Do these in order, **only after** every box in `docs/VERIFY_CHECKLIST.md` is ticked. Allow about 90 minutes in total.

## 0. Final build (5 min)
1. Fill in `AUTHORS.json` (name exactly as it should appear, ORCID, affiliation) and the funding and competing-interests lines in `code/06_document.js` (search for the insert placeholders).
2. `bash run_all.sh --final`
3. `python tools/publish_gate.py . --allow-draft-in code/ tools/` must print a clear result. It refuses while draft stamps or insert placeholders remain.

## 1. GitHub (15 min)
1. Create an empty public repository at github.com/new named `in-hs-math-earlywarning` (no README, no license; the project has both).
2. In the project folder:
   ```bash
   git init -b main
   git add -A
   git commit -m "v0.1.0: Indiana HS early-warning model for first-year college outcomes"
   git remote add origin https://github.com/<your-user>/in-hs-math-earlywarning.git
   git push -u origin main
   ```
   The raw Excel files total about 29 MB; every file is under GitHub's 100 MB limit.
3. GitHub Pages serves only the repository root or `/docs`, so copy the map there: `mkdir -p docs/map && cp map/index.html docs/map/index.html`, commit and push. Then Settings → Pages → deploy from branch `main`, folder `/docs`. The map will be at `https://<your-user>.github.io/in-hs-math-earlywarning/map/`.
4. Releases → Draft a new release → tag `v0.1.0`, title "v0.1.0 — first public release". Release notes: "First release: school × cohort panel for Indiana public high schools (classes of 2021–2024), interpretable early-warning model with temporal validation, calibration and failure audit, model card, manuscript and interactive map." Publish.

## 2. Zenodo DOI (10 min)
1. Log in at zenodo.org with your ORCID.
2. Account → GitHub → switch on `in-hs-math-earlywarning`. **Do this before step 1.4**, or create a new release (`v0.1.1`) afterwards; Zenodo archives the release and mints a DOI within minutes.
3. On the Zenodo record, check: upload type *Dataset* (or *Software*), creators from `AUTHORS.json` with ORCID, license CC BY 4.0, keywords "early warning; college readiness; mathematics; Indiana; calibration", related identifier = the GitHub URL.
4. Put the DOI into `CITATION.cff` (`doi:`), the README status line, and the manuscript's "Code and data" line (the DOI and repository-URL placeholders in `code/06_document.js`), then rebuild with `--final` and push.

## 3. EdArXiv preprint (20 min)
EdArXiv (OSF-hosted, for education research) is the first venue. Confirm current policies at https://edarxiv.org before submitting.
1. Sign in at osf.io with your ORCID; go to EdArXiv → Add a preprint.
2. Upload `paper/manuscript.pdf` (built with `--final`).
3. Title: *Warning while they are still in high school: an interpretable, calibrated school-level model of first-year college outcomes for Indiana public high schools*
4. Authors: exactly as in `AUTHORS.json`. Subjects: Education → Higher Education; Secondary Education; Educational Assessment, Evaluation, and Research.
5. Abstract: paste the two abstract paragraphs from the manuscript.
6. License: CC BY 4.0. Data/materials links: the Zenodo DOI and GitHub URL. Conflict of interest: as in the manuscript.
7. Submit. EdArXiv moderation usually takes a few days. Record the DOI (10.35542/osf.io/xxxxx) in the evidence log and in `CITATION.cff` as a related identifier.

## 4. Journal (after the preprint is live)
Candidate venues: *AERA Open* (open access, broad; check the current article processing charge), *Educational Evaluation and Policy Analysis*, *Research in Higher Education*. Prepare: anonymized manuscript (remove author block), cover letter stating the policy relevance for Indiana and the open data, data availability pointing to Zenodo. Record submission date and manuscript ID in the evidence log.

## 5. Interactive map
A private draft is already published as a Claude artifact ("Indiana College Math Readiness Map"). After the `--final` build, republish it from `map/index.html` and share it from the page's Share menu, or rely on the GitHub Pages copy from step 1.3.

## 6. Log every step the same day
Add one row per event to `docs/evidence_log.csv` (date, artifact, type, venue, link or DOI, status, files saved), and save a PDF of each live page.
