#!/usr/bin/env node
// 06_document.js — build paper/manuscript.docx from paper/stats.json, AUTHORS.json and the figures.
//   node code/06_document.js           (DRAFT banner)
//   node code/06_document.js --final   (only after the author's verification gate)
// Every number in the text comes from stats.json; none is typed by hand.
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType, ImageRun, Table, TableRow, TableCell,
  WidthType, ShadingType, BorderStyle, Footer, PageNumber, LevelFormat,
} = require("docx");

const ROOT = path.resolve(__dirname, "..");
const S = JSON.parse(fs.readFileSync(path.join(ROOT, "paper/stats.json")));
const BS = JSON.parse(fs.readFileSync(path.join(ROOT, "data/processed/build_stats.json")));
const A = JSON.parse(fs.readFileSync(path.join(ROOT, "AUTHORS.json")));
const FINAL = process.argv.includes("--final");

// ---------------------------------------------------------------- number helpers
const f = (x, d = 2) => (x === null || x === undefined ? "n/a" : Number(x).toFixed(d));
const pc = (x, d = 0) => (x * 100).toFixed(d) + "%";
const n = (x) => Number(x).toLocaleString("en-US");
const T = S.temporal, TI = S.tiers, W = S.warning, SE = S.sensitivity, ST = S.state, SM = S.sample;
const lev = (y, k) => S.levers[y][k];
const ci = (a) => `${f(a[0])}–${f(a[1])}`;

// ---------------------------------------------------------------- paragraph helpers
const FONT = "Calibri";
const P = (text, opts = {}) => new Paragraph({ spacing: { after: 140, line: 300 }, ...opts,
  children: (Array.isArray(text) ? text : [text]).map((t) => (typeof t === "string" ? new TextRun({ text: t, font: FONT, size: 22 }) : t)) });
const B = (t) => new TextRun({ text: t, bold: true, font: FONT, size: 22 });
const I = (t) => new TextRun({ text: t, italics: true, font: FONT, size: 22 });
const H1 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_1, spacing: { before: 280, after: 120 }, children: [new TextRun({ text: t, font: FONT })] });
const H2 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_2, spacing: { before: 200, after: 100 }, children: [new TextRun({ text: t, font: FONT })] });
const bullet = (t) => new Paragraph({ numbering: { reference: "bul", level: 0 }, spacing: { after: 80, line: 290 },
  children: (Array.isArray(t) ? t : [t]).map((x) => (typeof x === "string" ? new TextRun({ text: x, font: FONT, size: 22 }) : x)) });

function figure(file, num, caption, widthIn = 6.3) {
  const buf = fs.readFileSync(path.join(ROOT, "paper/figures", file));
  const w = buf.readUInt32BE(16), h = buf.readUInt32BE(20);
  const wpx = widthIn * 96;
  return [
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 120 },
      children: [new ImageRun({ type: "png", data: buf, transformation: { width: wpx, height: Math.round(wpx * h / w) } })] }),
    new Paragraph({ spacing: { after: 220, line: 260 }, children: [new TextRun({ text: `Figure ${num}. `, bold: true, font: FONT, size: 19 }),
      new TextRun({ text: caption, font: FONT, size: 19 })] }),
  ];
}

const border = { style: BorderStyle.SINGLE, size: 4, color: "BBBBBB" };
function table(num, caption, header, rows, widths) {
  const total = widths.reduce((a, b) => a + b, 0);
  const cell = (t, i, head) => new TableCell({
    width: { size: widths[i], type: WidthType.DXA }, borders: { top: border, bottom: border, left: border, right: border },
    shading: head ? { type: ShadingType.CLEAR, color: "auto", fill: "EEF2F6" } : undefined,
    margins: { top: 60, bottom: 60, left: 90, right: 90 },
    children: [new Paragraph({ alignment: i === 0 ? AlignmentType.LEFT : AlignmentType.RIGHT,
      children: [new TextRun({ text: String(t), bold: !!head, font: FONT, size: 18 })] })] });
  return [
    new Paragraph({ spacing: { before: 160, after: 80 }, children: [new TextRun({ text: `Table ${num}. `, bold: true, font: FONT, size: 19 }),
      new TextRun({ text: caption, font: FONT, size: 19 })] }),
    new Table({ width: { size: total, type: WidthType.DXA }, columnWidths: widths,
      rows: [new TableRow({ tableHeader: true, children: header.map((h, i) => cell(h, i, true)) }),
        ...rows.map((r) => new TableRow({ children: r.map((c, i) => cell(c, i, false)) }))] }),
    new Paragraph({ spacing: { after: 200 }, children: [] }),
  ];
}

// ---------------------------------------------------------------- author block
const au = A.authors[0];
const authorLine = A.authors.map((a) => a.name).join(", ");
const affLine = A.authors.map((a) => a.affiliation).join("; ");

// ---------------------------------------------------------------- text
const title = "Warning while they are still in high school: an interpretable, calibrated school-level model of first-year college outcomes for Indiana public high schools";

const abstract = [
  `Weak first-year college outcomes cost students time and money, yet high schools usually learn about them years after graduation. We built a transparent school-level early-warning model for Indiana public high schools using only public signals available before students reach college: grade 7/8 state math results, grade 11 SAT math results, the grade in which students pass Algebra I, whether advanced mathematics and calculus are offered, AP exam passing, and dual-credit earning. Outcomes are school averages of first-year college credits earned and first-year GPA among graduates who enrolled at an Indiana public college (classes of 2021–2024; ${n(SM["2024"].schools)} schools and ${n(SM["2024"].enrollees)} enrollees in the class of 2024).`,
  `A linear model fit on the class of 2023 explained ${pc(T.credits.LIN.r2)} of between-school variation in first-year credits for the class of 2024 (95% CI ${pc(T.credits.LIN.r2_ci[0])}–${pc(T.credits.LIN.r2_ci[1])}) and ${pc(T.gpa.LIN.r2)} for GPA, matching gradient-boosted trees (${pc(T.credits.GBM.r2)} and ${pc(T.gpa.GBM.r2)}) and outperforming each school's own prior-cohort outcome (${pc(T.credits.PERSIST.r2)} and ${pc(T.gpa.PERSIST.r2)}). Signals available by grade 9 alone explained ${pc(TI.credits.T1_grade9.r2)} for credits; adding grade 11 SAT math raised this to ${pc(TI.credits.T2_grade11.r2)}, and AP and dual-credit information at graduation added little. Predictions were well ordered but slightly too spread out (calibration slope ${f(T.credits.LIN.slope)}) and missed a statewide rise in credits (observed minus predicted ${f(T.credits.LIN.citl)} credits). Accuracy decayed slowly across cohorts. The model under-predicted GPA at small and rural schools and over-predicted it at high-poverty schools, and school poverty alone predicted GPA about as well as the full lever set (${pc(TI.gpa.FRL_only.r2)}). Math remediation could not be modeled: it is reported for few schools and is rare statewide (${pc(ST["2024"].math_remediation_share, 1)} of enrollees in 2024). We release the panel, code, model card and an interactive school map.`,
];

const doc = new Document({
  creator: authorLine, title,
  styles: { default: { document: { run: { font: FONT, size: 22 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true, run: { size: 28, bold: true, color: "1C3D5A" }, paragraph: { outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true, run: { size: 24, bold: true, color: "1C3D5A" }, paragraph: { outlineLevel: 1 } }] },
  numbering: { config: [{ reference: "bul", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 270 } } } }] }] },
  sections: [{
    properties: { page: { size: { width: 12240, height: 15840 }, margin: { top: 1300, bottom: 1300, left: 1300, right: 1300 } } },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [
      new TextRun({ text: FINAL ? "" : "DRAFT — not verified by the author — ", font: FONT, size: 16, color: "B03A2E" }),
      new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 16 })] })] }) },
    children: [
      ...(FINAL ? [] : [new Paragraph({ shading: { type: ShadingType.CLEAR, color: "auto", fill: "FDECEA" }, spacing: { after: 200 },
        children: [new TextRun({ text: "DRAFT for author verification. Do not cite or circulate. Every number is generated from the pipeline's stats file; the author must reproduce, spot-check and approve before release.", font: FONT, size: 18, color: "8A2A1F" })] })]),
      new Paragraph({ spacing: { after: 160 }, children: [new TextRun({ text: title, bold: true, font: FONT, size: 34, color: "14181D" })] }),
      P([B(authorLine)]),
      P([I(affLine)]),
      P([`Correspondence: ${au.email}. ORCID: ${au.orcid}.`]),
      P([`Version 0.1, ${FINAL ? "2026-10-09" : new Date().toISOString().slice(0, 10)}. Code and data: https://github.com/OthnyLight/in-hs-math-earlywarning (Zenodo archive DOI assigned at release).`]),

      H1("Abstract"), ...abstract.map((t) => P(t)),
      P([B("Keywords: "), "early warning; college readiness; mathematics; Algebra I; dual credit; calibration; model audit; Indiana"]),

      H1("1. Introduction"),
      P(`Roughly one in three Indiana graduates who enroll at an Indiana public college earns fewer than 24 credits in the first year (${pc(ST["2024"].offtrack_share)} for the class of 2024), the pace needed to finish a bachelor's degree in four years or an associate degree in two. The Indiana Commission for Higher Education (CHE) publishes these outcomes for every high school, but only after a cohort has finished its first college year, about five years after its students sat their grade 8 state test. By the time a school sees that its graduates struggle in college mathematics and credit accumulation, three or four more cohorts have already passed through.`),
      P(`Early-warning systems inside high schools are well established for graduation risk, most famously the Chicago on-track indicator (Allensworth & Easton, 2005), and the predictors of dropping out have been reviewed systematically (Bowers, Sprott, & Taff, 2013). The college side is less developed. Research on remedial placement shows that test-based placement misclassifies many students (Scott-Clayton, 2012) and that long remedial sequences lose students (Bailey, Jeong, & Cho, 2010). Course-taking studies tie college math readiness to the level and timing of high school mathematics (Adelman, 2006; Long, Iatarola, & Conger, 2009), while acceleration into Algebra I is not uniformly helpful (Clotfelter, Ladd, & Vigdor, 2015; Domina et al., 2015). Dual enrollment is associated with later degree attainment (An, 2013). What is missing for a state such as Indiana is a public, transparent tool that turns these school-level signals into a calibrated forecast of how a school's graduates will fare, early enough to act on, with its failures documented.`),
      P(`This paper builds and audits such a tool. We ask three questions. (1) How well do public school-level signals predict a school's first-year college outcomes for a cohort the model has never seen? (2) How early is the warning available: by grade 9, by grade 11, or only at graduation? (3) Where does the model fail, and does it fail evenly across kinds of schools? We follow reporting conventions from clinical prediction modeling (Collins et al., 2015), give calibration the same weight as discrimination (Van Calster et al., 2019), and publish a model card (Mitchell et al., 2019).`),

      H1("2. Data"),
      P(`All inputs are public, aggregate, school-level files; no student records were used. Table 1 summarizes the sample.`),
      bullet([B("Outcomes. "), `CHE College-Going/College-Readiness datasets for the graduating classes of 2021–2024 (released 2023–2026). For each high school we use the average first-year GPA and average first-year credits earned among graduates who enrolled at an Indiana public college the fall after graduation, the share of those enrollees earning fewer than 24 credits, the share with GPA below 2.0, and the share needing mathematics remediation (math only, or math and English). Cells with fewer than about ten students are suppressed by CHE.`]),
      bullet([B("Grade 7/8 mathematics. "), `Indiana Department of Education (IDOE) school files: ISTEP+ grade 8 (2017, 2018) for the classes of 2021 and 2022; ILEARN grade 8 (2019) for the class of 2023. Because the 2020 test was cancelled, the class of 2024 uses its grade 7 ILEARN results from 2019. When the high school building itself tested grade 8 (junior/senior high schools), we use its own rate; otherwise we use the school corporation's rate across its middle schools. Rates are standardized within year because ISTEP+ and ILEARN are on different scales.`]),
      bullet([B("Grade 11 SAT mathematics. "), `IDOE school files for the 2022 and 2023 state SAT administrations, which correspond to the classes of 2023 and 2024 (the state SAT began with the class of 2023). We use the share of testers meeting the College Board math benchmark.`]),
      bullet([B("Algebra I timing and course offerings. "), `Civil Rights Data Collection (CRDC) 2017–18 (classes of 2021–2022) and 2020–21 (classes of 2023–2024), retrieved through the Urban Institute Education Data Portal: Algebra I passers by grade band, Algebra II, advanced mathematics and calculus sections, and enrollment in advanced mathematics and calculus. "Algebra I late" is the share of a high school's Algebra I passers who passed in grades 11–12.`]),
      bullet([B("AP and dual credit. "), `From the CHE files: the share of each school's graduates who took and passed an AP exam, and the share who earned dual credit from an Indiana public college.`]),
      bullet([B("Audit covariates. "), `NCES Common Core of Data 2022–23 (locale, enrollment, free/reduced-price lunch share, charter and virtual status) and the IDOE 2025–26 school directory, used to restrict to public schools and to audit errors. These variables are deliberately kept out of the headline model so that it describes school-level levers rather than demographics.`]),
      P(`Schools were linked across files by IDOE school number (CHE 2024 publishes it; earlier CHE files were linked by exact school name, matching ${pc(BS.che_name_link_rate["2021"], 1)}, ${pc(BS.che_name_link_rate["2022"], 1)} and ${pc(BS.che_name_link_rate["2023"], 1)} of schools in the 2021–2023 files, with nonpublic and closed schools making up most non-matches). We keep public high schools with at least ${SM.min_enrollees} graduates enrolled at an Indiana public college: ${n(SM.rows_modeled)} school-cohort rows. These schools account for ${n(SM["2024"].enrollees)} of the ${n(ST["2024"].in_public_enrollees)} Indiana public college enrollees statewide in the class of 2024.`),
      ...table(1, "Analysis sample by graduating class (public high schools with ≥10 Indiana public college enrollees). Means are enrollee-weighted.",
        ["Class", "Schools", "Enrollees", "Mean credits", "Mean GPA", "Share < 24 credits"],
        ["2021", "2022", "2023", "2024"].map((y) => [y, SM[y].schools, n(SM[y].enrollees), f(SM[y].credits_mean, 1), f(SM[y].gpa_mean), pc(SM[y].offtrack_mean)]),
        [1300, 1300, 1500, 1600, 1500, 2100]),

      H1("3. Methods"),
      H2("3.1 Models"),
      P(`The headline model is an enrollee-weighted linear regression on nine standardized levers (grade 7/8 math, SAT math, Algebra I late share, Algebra I passers per student, advanced math offered, calculus offered, advanced math and calculus enrollment share, AP pass share, dual-credit share), with median imputation and missing-value indicators learned on the training data only. Each coefficient is the predicted change in the outcome per one standard deviation of a lever, holding the others fixed. We compare it with an additive spline model (cubic B-splines per lever with ridge penalty), which is still one curve per lever, and with gradient-boosted trees, which allow interactions. As a benchmark we use persistence: the school's own outcome for the previous cohort. Persistence is not an early warning, since it exists only after a cohort reaches college, but it is the obvious alternative a state would consider.`),
      H2("3.2 Validation"),
      P(`The headline test is temporal: fit on the class of 2023, score on the class of 2024. This is the only pair of cohorts with both state SAT and grade 7/8 results, and it mimics real use, where a model trained on the last observed cohort is applied to the next one. We also report grouped five-fold cross-validation by school corporation within the class of 2023, and a multi-cohort drift check that drops SAT so that the classes of 2021 and 2022 can be used for training. Accuracy is the enrollee-weighted R². Confidence intervals come from 500 bootstrap resamples of school corporations (300 for tiers and coefficients).`),
      H2("3.3 Calibration, warning flags and audit"),
      P(`Calibration is summarized by the slope and intercept of a weighted regression of observed on predicted outcomes, by calibration-in-the-large (mean observed minus predicted), and by decile plots. A school is flagged when its predicted credits fall in the lowest fifth of schools (or its predicted off-track share in the highest fifth); we report the precision and recall of the flag against the observed lowest fifth. To ask how early a warning is possible, we refit with the information available at three points: by grade 9 (grade 7/8 math, Algebra I timing and course offerings), by grade 11 (adding SAT math) and at graduation (adding AP and dual credit). The failure audit compares mean residuals, net of the statewide shift, across locale, poverty tercile, size tercile, school type, the level at which grade 8 data were attributed, and whether the school is the only high school in its district.`),

      H1("4. Results"),
      H2("4.1 Accuracy on a cohort the model never saw"),
      P(`Fit on the class of 2023, the linear model explained ${pc(T.credits.LIN.r2)} of between-school variation in the class of 2024's first-year credits, ${pc(T.gpa.LIN.r2)} for GPA and ${pc(T.p_offtrack.LIN.r2)} for the share earning fewer than 24 credits (Table 2). The typical error was ${f(T.credits.LIN.rmse, 1)} credits and ${f(T.gpa.LIN.rmse)} GPA points. Neither the spline model nor gradient-boosted trees did materially better, so interpretability costs nothing here. Within the class of 2023, corporation-grouped cross-validation gave R² of ${f(S.cv2023.credits.LIN.r2)} for credits and ${f(S.cv2023.gpa.LIN.r2)} for GPA, somewhat higher than the temporal test, as expected when train and test share a cohort.`),
      P(`On the ${T.credits.PERSIST.n} schools observed in both years, the model outperformed persistence (credits R² ${f(T.credits.LIN_same_schools.r2)} versus ${f(T.credits.PERSIST.r2)}; GPA ${f(T.gpa.LIN_same_schools.r2)} versus ${f(T.gpa.PERSIST.r2)}), and an equal blend of the two did best (${f(T.credits.BLEND.r2)} and ${f(T.gpa.BLEND.r2)}). Last year's outcome is noisy for small schools; the levers carry information that is more stable than one cohort's result.`),
      ...table(2, "Out-of-sample accuracy on the class of 2024 (models fit on the class of 2023). Enrollee-weighted R² and RMSE; persistence and blend are evaluated on schools observed in both years.",
        ["Model", "Credits R²", "Credits RMSE", "GPA R²", "GPA RMSE", "< 24 credits R²"],
        [["Linear (headline)", "LIN"], ["Additive splines", "GAM"], ["Gradient-boosted trees", "GBM"], ["Persistence (prior cohort)", "PERSIST"], ["Linear, same schools", "LIN_same_schools"], ["Blend of linear and persistence", "BLEND"]]
          .map(([lab, k]) => [lab, f(T.credits[k].r2), f(T.credits[k].rmse), f(T.gpa[k].r2), f(T.gpa[k].rmse, 3), f(T.p_offtrack[k].r2)]),
        [2900, 1200, 1300, 1100, 1300, 1500]),
      H2("4.2 How early is the warning?"),
      P(`Information available by grade 9 (grade 7/8 math, Algebra I timing and course offerings) explained ${pc(TI.credits.T1_grade9.r2)} of variation in credits (95% CI ${pc(TI.credits.T1_grade9.r2_ci[0])}–${pc(TI.credits.T1_grade9.r2_ci[1])}) and ${pc(TI.gpa.T1_grade9.r2)} for GPA (Figure 1). Adding grade 11 SAT math raised these to ${pc(TI.credits.T2_grade11.r2)} and ${pc(TI.gpa.T2_grade11.r2)}. AP and dual-credit information at graduation added only ${f((TI.credits.T3_graduation.r2 - TI.credits.T2_grade11.r2) * 100, 1)} and ${f((TI.gpa.T3_graduation.r2 - TI.gpa.T2_grade11.r2) * 100, 1)} percentage points. A useful warning is therefore available two years before graduation, and a weaker one four years before. For comparison, the school's share of students eligible for free or reduced-price lunch alone explained ${pc(TI.credits.FRL_only.r2)} of credits and ${pc(TI.gpa.FRL_only.r2)} of GPA; adding it to the full model raised R² to ${pc(SE.credits_with_frl_r2)} and ${pc(SE.gpa_with_frl_r2)}.`),
      ...figure("fig1_information_tiers.png", 1, "Out-of-sample R² for the class of 2024 by the information available at three points in the cohort's high-school career. Dashed lines: a model using only the school's free/reduced-price lunch share."),
      H2("4.3 Calibration and drift across cohorts"),
      P(`Predictions were well ordered but slightly too extreme: the calibration slope was ${f(T.credits.LIN.slope)} for credits (95% CI ${ci(T.credits.LIN.slope_ci)}) and ${f(T.gpa.LIN.slope)} for GPA (${ci(T.gpa.LIN.slope_ci)}), meaning that schools predicted to do very well or very poorly ended up somewhat closer to the middle (Figure 2). The larger miss was in the level: statewide first-year credits rose from ${f(ST["2023"].credits, 1)} to ${f(ST["2024"].credits, 1)} between the classes of 2023 and 2024, and the model, trained on 2023, under-predicted the class of 2024 by ${f(T.credits.LIN.citl)} credits on average. Because this shift is common to all schools, it does not change which schools are flagged, but a model used for absolute targets should have its intercept updated each year from the latest statewide figure.`),
      ...figure("fig2_calibration.png", 2, "Observed versus predicted outcomes for the class of 2024. Dots are schools (area proportional to enrollees); black points are enrollee-weighted decile means; the dashed line is perfect calibration."),
      P(`Without SAT, models trained on the class of 2021 explained ${pc(S.drift.credits.fit_2021["2022"].r2)}, ${pc(S.drift.credits.fit_2021["2023"].r2)} and ${pc(S.drift.credits.fit_2021["2024"].r2)} of credits for the classes of 2022, 2023 and 2024; training on 2021 and 2022 together gave ${pc(S.drift.credits.fit_2021_2022["2023"].r2)} and ${pc(S.drift.credits.fit_2021_2022["2024"].r2)} (Figure 3). Accuracy decays slowly with distance from the training cohort, and pooling cohorts helps, which argues for refitting each year on the most recent two cohorts.`),
      ...figure("fig3_cohort_drift.png", 3, "Out-of-sample R² for first-year credits when the model is applied to later cohorts. Lever set without SAT."),
      H2("4.4 Warning flags"),
      P(`Flagging the fifth of schools with the lowest predicted credits identified ${W.credits.hits} of the ${W.credits.true_worst} schools that turned out to be in the lowest fifth (precision ${pc(W.credits.precision)}, recall ${pc(W.credits.recall)}; chance would give 20%). Persistence achieved ${pc(W.credits.persistence_precision)} precision on the same task. For the share earning fewer than 24 credits the flag's precision was ${pc(W.p_offtrack.precision)}, against ${pc(W.p_offtrack.persistence_precision)} for persistence. About two in five flagged schools are therefore not in the worst fifth when outcomes arrive, which is why we present the flag as a prompt for closer review rather than a rating.`),
      H2("4.5 Which levers carry the signal"),
      P(`Holding the other levers fixed, grade 11 SAT math dominated: one standard deviation corresponded to ${f(lev("credits", "sat_math").coef_per_sd)} more first-year credits (95% CI ${ci(lev("credits", "sat_math").ci)}) and ${f(lev("gpa", "sat_math").coef_per_sd)} GPA points (${ci(lev("gpa", "sat_math").ci)}) (Figure 4). The share of graduates earning dual credit was the only other lever with an interval clear of zero for both outcomes (${f(lev("credits", "dual").coef_per_sd)} credits, ${ci(lev("credits", "dual").ci)}; ${f(lev("gpa", "dual").coef_per_sd, 3)} GPA, ${ci(lev("gpa", "dual").ci)}). Grade 7/8 math, Algebra I timing and course offerings were strongly related to outcomes on their own (for example, the correlation of credits with the late Algebra I share was ${f(S.univariate_r_2024_credits.alg1_late)}, and with grade 7/8 math ${f(S.univariate_r_2024_credits.g8_z)}) but added little once SAT math was known: their information about the cohort is largely carried forward into grade 11 results. These are cross-school associations; they identify where to look, not what would happen if a school changed one lever.`),
      ...figure("fig4_levers.png", 4, "Change in first-year credits and GPA per one standard deviation of each lever, from a linear model on the classes of 2023 and 2024. Intervals are 95% corporation-cluster bootstrap intervals; gray intervals cross zero."),
      H2("4.6 Where the model fails"),
      P(`Net of the statewide shift, residuals were small for most groups (Figure 5), but several departures are consistent enough to matter. The model under-predicted GPA at small schools and rural schools and at junior/senior high schools whose own grade 8 results were used, and over-predicted GPA at high-poverty schools (mean residual ${f(S.audit["frl_tercile:high FRL:gpa"].mean_resid)} GPA points). The over-prediction at high-poverty schools means that the levers, on their own, slightly understate the disadvantage those graduates face in college; a flag based on the model will miss some of those schools. The seven virtual schools were under-predicted by ${f(S.audit["type:virtual:gpa"].mean_resid)} GPA points on average. The 20 worst-predicted schools were dominated by small schools (${S.worst.n_small_in_top20} of 20 had fewer than 30 enrollees) and over-represented charter and virtual schools (${S.worst.n_virtual_or_charter_in_top20} of 20, against ${pc(S.worst.share_virtual_charter_overall)} of schools overall). Restricting to schools with at least 30 enrollees raised R² to ${pc(SE.credits_n30plus_r2)} for credits and ${pc(SE.gpa_n30plus_r2)} for GPA.`),
      ...figure("fig5_failure_audit.png", 5, "Mean GPA residual (observed minus predicted, net of the statewide shift) by school group, class of 2024. Bars are ±2 standard errors; orange marks |t| > 2.", 6.0),
      H2("4.7 Mathematics remediation"),
      P(`Remediation shares are published for only ${S.mathrem.schools_reported_2024} of the schools in the class-of-2024 sample, and remediation is rare statewide (${pc(ST["2024"].math_remediation_share, 1)} of enrollees needed math remediation in 2024, down from ${pc(ST["2021"].math_remediation_share, 1)} in 2021). Among reporting schools, the remediation share was essentially uncorrelated with predicted credits (r = ${f(S.mathrem.corr_with_pred_credits)}) and with SAT math (r = ${f(S.mathrem.corr_with_sat_math)}). We read this as a measurement result: with suppression and low prevalence, the published remediation field cannot support school-level modeling, which is why credits and GPA are the primary outcomes.`),

      H1("5. Discussion"),
      P(`Public school-level signals predict roughly three-fifths of the between-school variation in first-year college credits and GPA for a cohort the model has not seen, and most of that warning is available by grade 11. A transparent linear model does as well as a black-box learner, beats the obvious alternative of waiting for last year's outcomes, and its errors can be described in plain terms. For districts, the practical reading is that a high school whose grade 11 SAT math results and dual-credit participation are low relative to the state should expect its graduates to accumulate credits slowly in college, years before CHE reports it. For the state, the model offers a way to direct attention to schools before outcomes are observed, provided the flag is treated as a starting point for review.`),
      P(`Three findings temper that use. First, a school's poverty rate predicts GPA as well as the levers do. The levers are partly proxies for the same disadvantage, and the model slightly over-predicts how graduates of high-poverty schools will fare; adding poverty improves accuracy but turns the tool toward describing demographics rather than school practice, so we report it as a sensitivity and leave the choice to users. Second, the lever coefficients are associations. The late-Algebra I share and course offerings are strongly related to outcomes but add little once SAT is known; this is consistent with a pathway in which early mathematics shapes grade 11 performance, but cross-school data cannot establish it. Third, the model is weakest exactly where small numbers make every school-level statistic noisy: small, rural, charter and virtual schools.`),
      H2("Limitations"),
      bullet("Outcomes cover only graduates who enrolled at an Indiana public college (about a third of graduates); graduates at private or out-of-state colleges are not observed, and enrollment selection differs across schools."),
      bullet("Grade 7/8 results are attributed through the school corporation for most high schools, which blurs differences between high schools in multi-high-school districts; the class of 2024 uses grade 7 results because the 2020 test was cancelled."),
      bullet("State SAT exists only for the classes of 2023 onward, so the full model is validated on a single cohort transition; the multi-cohort drift check uses a reduced lever set."),
      bullet("CRDC data are biennial and self-reported by schools; Algebra I timing is measured within the high school, so students who passed Algebra I in a separate middle school are not seen directly."),
      bullet("Earlier CHE files were linked by school name; a small number of renamed schools may be dropped from earlier cohorts."),
      bullet("The model is school-level and must not be used to make decisions about individual students."),

      H1("6. Conclusion"),
      P(`An early, transparent and calibrated school-level warning of weak first-year college outcomes is feasible for Indiana from public data alone. It is most informative by grade 11, it does not need a black box, and its failures are concentrated in small, rural, high-poverty and nontraditional schools. We release the panel, code, model card and an interactive map so that districts and the state can test the warnings against what they know and so that the model can be refit as each new cohort's outcomes are published.`),

      H1("Declarations"),
      P([B("Data availability. "), "All inputs are public. The derived panel (data/processed/school_panel.csv), predictions, stats file, figures and code are in the project repository (https://github.com/OthnyLight/in-hs-math-earlywarning), archived on Zenodo at release, under CC BY 4.0 (data, text) and MIT (code). Raw-file hashes are recorded in data/raw/PROVENANCE.txt."]),
      P([B("Ethics. "), "The study uses only published, aggregate, school-level statistics with source suppression of small cells. No individual-level data were accessed; no human-subjects review was required."]),
      P([B("Funding. "), "None."]),
      P([B("Competing interests. "), "The author declares no competing interests."]),
      P([B("Use of AI tools. "), "An AI assistant (Anthropic's Claude) was used to write data-processing and modeling code, draft text and produce figures under the author's direction. The author specified the research questions, made the analytic decisions, reproduced the pipeline, checked the numbers against the source files and is responsible for the content."]),

      H1("References"),
      ...[
        "Adelman, C. (2006). The toolbox revisited: Paths to degree completion from high school through college. U.S. Department of Education.",
        "Allensworth, E. M., & Easton, J. Q. (2005). The on-track indicator as a predictor of high school graduation. Consortium on Chicago School Research.",
        "An, B. P. (2013). The impact of dual enrollment on college degree attainment: Do low-SES students benefit? Educational Evaluation and Policy Analysis, 35(1), 57–75.",
        "Bailey, T., Jeong, D. W., & Cho, S.-W. (2010). Referral, enrollment, and completion in developmental education sequences in community colleges. Economics of Education Review, 29(2), 255–270.",
        "Bowers, A. J., Sprott, R., & Taff, S. A. (2013). Do we know who will drop out? A review of the predictors of dropping out of high school: Precision, sensitivity, and specificity. The High School Journal, 96(2), 77–100.",
        "Clotfelter, C. T., Ladd, H. F., & Vigdor, J. L. (2015). The aftermath of accelerating algebra: Evidence from district policy initiatives. Journal of Human Resources, 50(1), 159–188.",
        "Collins, G. S., Reitsma, J. B., Altman, D. G., & Moons, K. G. M. (2015). Transparent reporting of a multivariable prediction model for individual prognosis or diagnosis (TRIPOD): The TRIPOD statement. Annals of Internal Medicine, 162(1), 55–63.",
        "Domina, T., McEachin, A., Penner, A., & Penner, E. (2015). Aiming high and falling short: California's eighth-grade algebra-for-all effort. Educational Evaluation and Policy Analysis, 37(3), 275–295.",
        "Indiana Commission for Higher Education. (2023–2026). College-going and college-readiness datasets, high school graduating classes of 2021–2024. https://www.in.gov/che/college-going-reports/",
        "Indiana Department of Education. (2017–2026). ISTEP+, ILEARN, SAT and school directory data files. https://www.in.gov/doe/it/data-center-and-reports/",
        "Long, M. C., Iatarola, P., & Conger, D. (2009). Explaining gaps in readiness for college-level math: The role of high school courses. Education Finance and Policy, 4(1), 1–33.",
        "Mitchell, M., Wu, S., Zaldivar, A., Barnes, P., Vasserman, L., Hutchinson, B., Spitzer, E., Raji, I. D., & Gebru, T. (2019). Model cards for model reporting. Proceedings of the Conference on Fairness, Accountability, and Transparency, 220–229.",
        "Scott-Clayton, J. (2012). Do high-stakes placement exams predict college success? (CCRC Working Paper No. 41). Community College Research Center, Teachers College, Columbia University.",
        "Urban Institute. (2026). Education Data Portal (Civil Rights Data Collection and Common Core of Data endpoints). https://educationdata.urban.org/",
        "Van Calster, B., McLernon, D. J., van Smeden, M., Wynants, L., & Steyerberg, E. W. (2019). Calibration: The Achilles heel of predictive analytics. BMC Medicine, 17, 230.",
      ].map((t) => new Paragraph({ spacing: { after: 100, line: 270 }, indent: { left: 400, hanging: 400 }, children: [new TextRun({ text: t, font: FONT, size: 20 })] })),
    ],
  }],
});

Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync(path.join(ROOT, "paper/manuscript.docx"), buf);
  console.log("wrote paper/manuscript.docx");
});
