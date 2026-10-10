#!/usr/bin/env python3
"""04_figures.py — paper figures from paper/stats.json and paper/tables/*.csv.

  python code/04_figures.py            # DRAFT-stamped (default)
  python code/04_figures.py --final    # only after the author's verification gate
  python code/04_figures.py --final --journal   # vector PDFs without in-image titles/captions,
                                               # for the LaTeX technical paper (paper/journal/figures)

Palette: validated reference categorical slots (blue #2a78d6, orange #eb6834), recessive chrome.
"""
import json
import pathlib
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
PAPER, PROC = ROOT / "paper", ROOT / "data" / "processed"
FIG = PAPER / "figures"
FIG.mkdir(parents=True, exist_ok=True)
FINAL = "--final" in sys.argv
JOURNAL = "--journal" in sys.argv
if JOURNAL:
    FIG = PAPER / "journal" / "figures"
    FIG.mkdir(parents=True, exist_ok=True)
S = json.loads((PAPER / "stats.json").read_text())

BLUE, ORANGE, INK, INK2, MUTED, GRID, BASE = "#2a78d6", "#eb6834", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 9.5, "axes.edgecolor": BASE, "axes.labelcolor": INK2,
    "xtick.color": MUTED, "ytick.color": MUTED, "axes.titlesize": 11, "axes.titleweight": "bold",
    "axes.titlecolor": INK, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
    "grid.color": GRID, "grid.linewidth": 0.6, "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb",
    "savefig.dpi": 200, "savefig.bbox": "tight", "legend.frameon": False})


def finish(fig, name, caption):
    import textwrap
    if JOURNAL:
        if fig._suptitle is not None:
            fig._suptitle.set_text("")
        if len(fig.axes) == 1:
            for loc in ("left", "center", "right"):
                fig.axes[0].set_title("", loc=loc)
        for a in fig.axes:
            a.set_facecolor("white")
        fig.set_facecolor("white")
        fig.savefig(FIG / f"{name}.pdf", facecolor="white")
        plt.close(fig)
        print("wrote", name, "(journal)")
        return
    fig.canvas.draw()
    # place the caption below everything already drawn (tick labels included)
    r = fig.canvas.get_renderer()
    low = min(a.get_tightbbox(r).y0 for a in fig.axes) / fig.bbox.height
    fig.text(0.01, low - 0.03, "\n".join(textwrap.wrap(caption, 150)), ha="left", va="top", fontsize=7, color=MUTED)
    if not FINAL:
        fig.text(0.01, low - 0.11, "DRAFT — not verified by the author", ha="left", va="top", fontsize=8, color="#d03b3b")
    fig.savefig(FIG / f"{name}.png")
    plt.close(fig)
    print("wrote", name)


# ---------------------------------------------------------------- Fig 1: how early can we warn?
tiers = [("T1_grade9", "By grade 9\n(grade 7/8 math, Algebra I\ntiming, course offerings)"),
         ("T2_grade11", "By grade 11\n(+ SAT math)"),
         ("T3_graduation", "At graduation\n(+ AP pass, dual credit)")]
fig, ax = plt.subplots(figsize=(7.2, 3.8))
x = np.arange(len(tiers))
for k, (y, col, lab) in enumerate([("credits", BLUE, "Mean first-year credits"), ("gpa", ORANGE, "Mean first-year GPA")]):
    v = [S["tiers"][y][t]["r2"] for t, _ in tiers]
    lo = [S["tiers"][y][t]["r2_ci"][0] for t, _ in tiers]
    hi = [S["tiers"][y][t]["r2_ci"][1] for t, _ in tiers]
    xx = x + (k - 0.5) * 0.18
    ax.vlines(xx, lo, hi, color=col, lw=2)
    ax.plot(xx, v, "o", color=col, ms=8, mec="#fcfcfb", mew=2, label=lab, zorder=3)
    for xi, vi in zip(xx, v):
        ax.text(xi + 0.05, vi, f"{vi:.2f}", va="center", fontsize=8, color=INK2)
    frl = S["tiers"][y]["FRL_only"]["r2"]
    ax.axhline(frl, color=col, lw=1, ls=(0, (4, 3)), alpha=0.7)
    ax.text(2.42, frl, f"poverty share only\n({lab.split()[-1]}): {frl:.2f}", fontsize=7, color=INK2, va="center")
ax.set_xticks(x, [t[1] for t in tiers], fontsize=8)
ax.set_ylim(0, 0.8)
ax.set_xlim(-0.5, 2.9)
ax.set_ylabel("Out-of-sample R² (class of 2024)")
ax.set_title("Most of the warning is available by grade 11", loc="left")
ax.legend(loc="upper left", fontsize=8)
finish(fig, "fig1_information_tiers",
       "Models fit on the class of 2023, scored on the class of 2024; enrollee-weighted R²; bars are 95% corporation-cluster bootstrap intervals.")

# ---------------------------------------------------------------- Fig 2: calibration (credits)
pt = pd.read_csv(PROC / "predictions_2024.csv")
dec = pd.read_csv(PAPER / "tables" / "calibration_deciles_2024.csv")
fig, axes = plt.subplots(1, 2, figsize=(7.6, 3.8))
for ax, y, lab, fmt in [(axes[0], "credits", "Mean first-year credits", "{:.0f}"), (axes[1], "gpa", "Mean first-year GPA", "{:.1f}")]:
    sz = np.clip(pt.n_enr / 6, 8, 120)
    ax.scatter(pt[f"pred_{y}"], pt[y], s=sz, color=BLUE, alpha=0.28, lw=0)
    d = dec[dec.outcome == y]
    ax.plot(d.pred_mean, d.obs_mean, "o-", color=INK, ms=5, lw=1.5, label="decile means")
    lo, hi = min(pt[f"pred_{y}"].min(), pt[y].min()), max(pt[f"pred_{y}"].max(), pt[y].max())
    ax.plot([lo, hi], [lo, hi], color=MUTED, lw=1, ls="--")
    t = S["temporal"][y]["LIN"]
    ax.text(0.03, 0.97, f"R² {t['r2']:.2f}\nslope {t['slope']:.2f}\nobs − pred {t['citl']:+.2f}",
            transform=ax.transAxes, va="top", fontsize=8, color=INK2)
    ax.set_xlabel(f"Predicted ({lab.lower()})")
    ax.set_ylabel("Observed")
    ax.set_title(lab, loc="left", fontsize=10)
axes[0].legend(loc="lower right", fontsize=8)
fig.suptitle("Calibration on the class of 2024 (model fit on 2023)", x=0.01, ha="left", fontweight="bold", color=INK)
fig.tight_layout(rect=(0, 0.04, 1, 1))
finish(fig, "fig2_calibration", "Dot area ∝ enrollees. Dashed line = perfect calibration. Linear model, full lever set.")

# ---------------------------------------------------------------- Fig 4: levers
co = pd.read_csv(PAPER / "tables" / "lever_coefficients.csv")
fig, axes = plt.subplots(1, 2, figsize=(7.8, 3.9), sharey=True)
order = co[co.outcome == "credits"].sort_values("coef_per_sd").label.tolist()
for ax, y, lab, unit in [(axes[0], "credits", "First-year credits", "credits"), (axes[1], "gpa", "First-year GPA", "GPA points")]:
    d = co[co.outcome == y].set_index("label").loc[order]
    yy = np.arange(len(d))
    sig = (d.lo > 0) | (d.hi < 0)
    ax.hlines(yy, d.lo, d.hi, color=np.where(sig, BLUE, BASE), lw=2)
    ax.plot(d.coef_per_sd, yy, "o", color=BLUE, ms=6, mec="#fcfcfb", mew=1.5)
    ax.axvline(0, color=BASE, lw=1)
    ax.set_yticks(yy, d.index, fontsize=8)
    ax.set_xlabel(f"Change per 1 SD of lever ({unit})")
    ax.set_title(lab, loc="left", fontsize=10)
    ax.grid(axis="y", visible=False)
fig.suptitle("Which school-level levers carry the signal, holding the others fixed", x=0.01, ha="left", fontweight="bold", color=INK)
fig.tight_layout(rect=(0, 0.04, 1, 1))
finish(fig, "fig4_levers", "Linear model on classes of 2023+2024; 95% corporation-cluster bootstrap intervals; gray = interval crosses zero. Associations, not causal effects.")

# ---------------------------------------------------------------- Fig 3: cohort drift
fig, ax = plt.subplots(figsize=(6.4, 3.5))
for key, col, lab in [("fit_2021", BLUE, "trained on class of 2021"), ("fit_2021_2022", ORANGE, "trained on 2021 + 2022")]:
    d = S["drift"]["credits"][key]
    yrs = sorted(d)
    ax.plot([int(v) for v in yrs], [d[v]["r2"] for v in yrs], "o-", color=col, lw=2, ms=7, mec="#fcfcfb", mew=1.5, label=lab)
    for v in yrs:
        ax.text(int(v) + 0.05, d[v]["r2"] + 0.012, f"{d[v]['r2']:.2f}", fontsize=8, color=INK2)
ax.set_xticks([2022, 2023, 2024], ["Class of 2022", "Class of 2023", "Class of 2024"])
ax.set_ylim(0.3, 0.7)
ax.set_ylabel("Out-of-sample R², first-year credits")
ax.set_title("Accuracy decays slowly across graduating cohorts", loc="left")
ax.legend(fontsize=8, loc="lower left")
finish(fig, "fig3_cohort_drift", "Harmonized lever set without SAT (no state SAT before the class of 2023). Linear model, enrollee-weighted.")

# ---------------------------------------------------------------- Fig 5: failure audit
au = pd.read_csv(PAPER / "tables" / "failure_audit_2024.csv")
au = au[au.outcome == "gpa"].copy()
nice = {"locale4": "Locale", "frl_tercile": "Poverty (FRL)", "size_tercile": "Size", "type": "Type",
        "g8_source": "Grade-8 data from", "single_hs_corp": "Only HS in district"}
au["lab"] = au.group.map(nice) + ": " + au.level.replace({"True": "yes", "False": "no", "school": "own building",
                                                          "corporation": "district avg."}) + "  (n=" + au.n_schools.astype(str) + ")"
au = au.iloc[::-1]
fig, ax = plt.subplots(figsize=(7.0, 5.0))
yy = np.arange(len(au))
flag = au.abs_t > 2
ax.hlines(yy, au.mean_resid - 2 * au.se, au.mean_resid + 2 * au.se, color=np.where(flag, ORANGE, BASE), lw=2)
ax.plot(au.mean_resid, yy, "o", color=np.where(flag, ORANGE, BLUE).tolist()[0] if False else BLUE, ms=0)
ax.scatter(au.mean_resid, yy, c=np.where(flag, ORANGE, BLUE), s=36, zorder=3, edgecolors="#fcfcfb", linewidths=1.2)
ax.axvline(0, color=BASE, lw=1)
ax.set_yticks(yy, au.lab, fontsize=8)
ax.set_xlabel("Observed − predicted first-year GPA, relative to the statewide shift")
ax.grid(axis="y", visible=False)
ax.set_title("Where the model fails: GPA residuals by school group", loc="right")
finish(fig, "fig5_failure_audit", "Class of 2024, model fit on 2023. Bars = ±2 SE; orange = |t| > 2. Positive = school did better than predicted.")
