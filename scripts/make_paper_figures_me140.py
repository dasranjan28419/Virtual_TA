"""
Generates the paper figures for the ME 140 (December 2025) Virtual TA
deployment. Figure sizing, palette and panel construction follow the house
style established in scripts/make_paper_figures.py so that every figure in
the paper typesets consistently; the ME 140 analysis itself stands alone and
draws no comparison to other deployments.

Output: vector PDFs sized for an IEEE single-column measure (3.45 in),
written to figures/paper/me140_dec2025/, with a PNG preview of each.

Percentages and within-user tests use the n = 79 Virtual TA users unless
stated otherwise. Answer labels come from scripts/codebook_me140.py, which
reads the option order out of Appendix D of data/ME 140 questions.pdf.

A machine-readable dump of every number quoted in the accompanying LaTeX
section is written to outputs/me140_dec2025/paper_figure_stats.txt.

Run:  python3 scripts/make_paper_figures_me140.py
"""

import os
import sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import spearmanr, chi2_contingency, fisher_exact, mannwhitneyu

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import codebook_me140 as cb
from vta_survey_analysis_me140 import load_and_clean_data, apply_fdr_correction

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "figures", "paper", "me140_dec2025")
STATS_DIR = os.path.join(ROOT, "outputs", "me140_dec2025")
os.makedirs(OUT, exist_ok=True)
os.makedirs(STATS_DIR, exist_ok=True)

# -- palette (house style, validated for CVD separation and print contrast) --
C_ENGAGE = "#1E6DB5"
C_LEARN  = "#8E3C86"
C_BENE   = "#C2661A"
C_MUTED  = "#97A0AE"
C_INK    = "#161A20"
C_GRID   = "#D8DCE2"

COL_W = 3.45     # IEEE single-column width, inches

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman", "Nimbus Roman", "STIXGeneral", "DejaVu Serif"],
    "mathtext.fontset": "stix",
    "font.size": 7.5,
    "axes.labelsize": 7.5,
    "axes.titlesize": 8,
    "xtick.labelsize": 7,
    "ytick.labelsize": 7,
    "legend.fontsize": 7,
    "axes.linewidth": 0.6,
    "xtick.major.width": 0.6,
    "ytick.major.width": 0.6,
    "xtick.major.size": 2.5,
    "ytick.major.size": 0,
    "axes.edgecolor": "#4A5361",
    "figure.dpi": 200,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.02,
    "pdf.fonttype": 42,
})

_LOG = []


def note(msg=""):
    """Records a line for the stats dump and echoes it."""
    print(msg)
    _LOG.append(msg)


def save(fig, name):
    """Write a vector PDF for LaTeX and a PNG preview for quick inspection."""
    fig.savefig(os.path.join(OUT, name + ".pdf"))
    fig.savefig(os.path.join(OUT, name + ".png"), dpi=300)


def wilson(k, n):
    if n == 0:
        return np.nan, np.nan
    z = 1.959964
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return 100 * max(0.0, c - h), 100 * min(1.0, c + h)


def hbars(ax, labels, pcts, counts, color, n, show_ci=True, xmax=100):
    """Horizontal bar panel with direct value labels and optional Wilson CI."""
    y = np.arange(len(labels))[::-1]
    colors = color if isinstance(color, list) else [color] * len(labels)
    ax.barh(y, pcts, height=0.62, color=colors, zorder=3)
    if show_ci:
        for yi, k in zip(y, counts):
            lo, hi = wilson(k, n)
            ax.plot([lo, hi], [yi, yi], color=C_INK, lw=0.8, alpha=0.65,
                    zorder=4, solid_capstyle="butt")
            for x in (lo, hi):
                ax.plot([x, x], [yi - 0.16, yi + 0.16], color=C_INK,
                        lw=0.8, alpha=0.65, zorder=4)
    for yi, p, k in zip(y, pcts, counts):
        end = max(p, wilson(k, n)[1]) if show_ci else p
        ax.text(min(end, xmax) + 2.2, yi, f"{p:.0f}%  ({k})", va="center",
                ha="left", fontsize=6.8, color=C_INK)
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.set_xlim(0, xmax)
    ax.set_xticks(np.arange(0, xmax + 1, 25))
    ax.xaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
    ax.grid(axis="x", color=C_GRID, lw=0.5, zorder=0)
    ax.set_axisbelow(True)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)


# ===========================================================================
# DATA
# ===========================================================================
df_num, df_lab = load_and_clean_data()
N_ALL = len(df_num)

# Usage intensity re-based to 0 = never .. 4 = 3+ times per week, so that the
# zero point is "no use" and the scale reads directly as intensity.
df_num["int"] = df_num["Q5"] - 1
users = df_num["int"] > 0
u_num = df_num[users].reset_index(drop=True)
u_lab = df_lab[users].reset_index(drop=True)
N = len(u_num)

note("=" * 72)
note("  ME 140 (Dec 2025) -- paper figure statistics")
note("=" * 72)
note(f"Respondents (analysis sample) : {N_ALL}")
note(f"Virtual TA users (Q5 > Never) : {N}")
note(f"Non-users (Q5 = Never)        : {N_ALL - N}  "
     f"({100*(N_ALL-N)/N_ALL:.1f}% non-adoption)")


def has(frame, qid, needle):
    """Boolean Series: did this respondent select the option matching needle?"""
    return frame[qid].str.contains(needle, regex=False, na=False)


def cnt(qid, needle, frame=None):
    frame = u_lab if frame is None else frame
    return int(has(frame, qid, needle).sum())


# ===========================================================================
# Figure 1: engagement profile
# ===========================================================================
fig, axes = plt.subplots(2, 1, figsize=(COL_W, 2.85),
                         gridspec_kw={"height_ratios": [4, 5], "hspace": 0.62})

f_lab = ["1–2 times total", "A few times per month",
         "1–2 times per week", "3+ times per week"]
f_cnt = [int((u_num["Q5"] == k).sum()) for k in (2, 3, 4, 5)]
hbars(axes[0], f_lab, [100 * c / N for c in f_cnt], f_cnt, C_ENGAGE, N)
axes[0].set_title("(a) Frequency of use over the semester", loc="left",
                  fontsize=7.5, pad=4)

s_lab = ["<5 min", "5–15 min", "15–30 min", "30–60 min", ">60 min"]
s_cnt = [int((u_num["Q8"] == k).sum()) for k in range(1, 6)]
n_ses = int(u_num["Q8"].notna().sum())
hbars(axes[1], s_lab, [100 * c / n_ses for c in s_cnt], s_cnt, C_ENGAGE, n_ses)
axes[1].set_title("(b) Typical session length", loc="left", fontsize=7.5, pad=4)
save(fig, "fig_me140_engagement")
plt.close(fig)

note("")
note("[Fig 1] Engagement among users")
for l, c in zip(f_lab, f_cnt):
    note(f"    {l:<24} {c:>3}  ({100*c/N:.1f}%)")
note(f"    once-or-twice share      : {100*f_cnt[0]/N:.1f}%")
note(f"    weekly-or-more share     : {100*(f_cnt[2]+f_cnt[3])/N:.1f}%  "
     f"(n={f_cnt[2]+f_cnt[3]})")
for l, c in zip(s_lab, s_cnt):
    note(f"    session {l:<16} {c:>3}  ({100*c/n_ses:.1f}%)")
note(f"    under 15 min share       : {100*(s_cnt[0]+s_cnt[1])/n_ses:.1f}%")


# ===========================================================================
# Figure 2: reported benefits
# ===========================================================================
fig, axes = plt.subplots(2, 1, figsize=(COL_W, 3.05),
                         gridspec_kw={"height_ratios": [4, 5], "hspace": 0.55})

l_lab = ["Understood concepts\nmore deeply", "Made connections\nacross topics",
         "Increased confidence\nin the subject", "No effect on\nmy learning"]
l_keys = ["Deeper concept understanding", "Connected topics better",
          "Gained subject confidence", "No effect on learning"]
l_cnt = [cnt("Q9", k) for k in l_keys]
n_learn = int(u_lab["Q9"].notna().sum())
hbars(axes[0], l_lab, [100 * c / n_learn for c in l_cnt], l_cnt,
      [C_LEARN, C_LEARN, C_LEARN, C_MUTED], n_learn)
axes[0].set_title("(a) Learning and understanding", loc="left", fontsize=7.5, pad=4)

e_lab = ["Reduced time spent\nstuck on problems", "More efficient\nhomework/studying",
         "Saved time overall", "Less time on other\nresources", "None of these"]
e_keys = ["Less time stuck", "More efficient studying", "Saved overall time",
          "Replaced other resources", "No efficiency benefit"]
e_cnt = [cnt("Q10", k) for k in e_keys]
n_eff = int(u_lab["Q10"].notna().sum())
hbars(axes[1], e_lab, [100 * c / n_eff for c in e_cnt], e_cnt,
      [C_BENE] * 4 + [C_MUTED], n_eff)
axes[1].set_title("(b) Efficiency and workload", loc="left", fontsize=7.5, pad=4)
save(fig, "fig_me140_benefits")
plt.close(fig)

note("")
note(f"[Fig 2] Reported benefits (learning n={n_learn}, efficiency n={n_eff})")
for l, c in zip(l_keys, l_cnt):
    note(f"    {l:<32} {c:>3}  ({100*c/n_learn:.1f}%)")
for l, c in zip(e_keys, e_cnt):
    note(f"    {l:<32} {c:>3}  ({100*c/n_eff:.1f}%)")
any_learn = int((~has(u_lab, "Q9", "No effect on learning") & u_lab["Q9"].notna()).sum())
any_eff = int((~has(u_lab, "Q10", "No efficiency benefit") & u_lab["Q10"].notna()).sum())
note(f"    ANY learning benefit             {any_learn:>3}  ({100*any_learn/n_learn:.1f}%)")
note(f"    ANY efficiency benefit           {any_eff:>3}  ({100*any_eff/n_eff:.1f}%)")


# ===========================================================================
# Figure 3: Spearman rho between usage intensity and each outcome
# ===========================================================================
# Binary outcome flags and ordinal endorsement scales, computed within users.
u_num["deep"] = has(u_lab, "Q9", "Deeper concept understanding").values
u_num["conn"] = has(u_lab, "Q9", "Connected topics better").values
u_num["conf"] = has(u_lab, "Q9", "Gained subject confidence").values
u_num["anyl"] = np.where(u_lab["Q9"].isna(), np.nan,
                         (~has(u_lab, "Q9", "No effect on learning")).astype(float))
u_num["effb"] = np.where(u_lab["Q10"].isna(), np.nan,
                         (~has(u_lab, "Q10", "No efficiency benefit")).astype(float))

# ME 140 items 16 and 17 offer three options: Yes / No / Not sure.
rm = {"No": 1, "Not sure / It depends on the design": 2, "Yes": 3}
u_num["rec"] = u_lab["Q17"].map(rm).values
u_num["want"] = u_lab["Q16"].map(rm).values
u_num["lik"] = u_num["Q14"].values

items = [("Deeper conceptual\nunderstanding", "deep"),
         ("Encountered flawed\nresponses", "lik"),
         ("Wants a VTA in\nother courses", "want"),
         ("Would recommend\nto future students", "rec"),
         ("Increased confidence", "conf"),
         ("Any learning benefit", "anyl"),
         ("Any efficiency benefit", "effb"),
         ("Connections across\ntopics", "conn")]

# Benjamini-Hochberg across the eight within-user correlations.
raw_rows = []
for lab, col in items:
    s = u_num[["int", col]].dropna().astype(float)
    r, p = spearmanr(s["int"], s[col])
    raw_rows.append({"label": lab.replace("\n", " "), "col": col,
                     "rho": r, "p": p, "n": len(s)})
adj_p, _ = apply_fdr_correction([r["p"] for r in raw_rows])
for row, ap in zip(raw_rows, adj_p):
    row["p_adj"] = ap

fig, ax = plt.subplots(figsize=(COL_W, 2.6))
for i, row in enumerate(raw_rows):
    s = u_num[["int", row["col"]]].dropna().astype(float)
    r = row["rho"]
    se = 1 / np.sqrt(len(s) - 3)
    lo, hi = np.tanh(np.arctanh(r) - 1.96 * se), np.tanh(np.arctanh(r) + 1.96 * se)
    sig = row["p_adj"] < 0.05
    c = C_BENE if sig else C_MUTED
    ax.plot([lo, hi], [i, i], color=c, lw=1.3, solid_capstyle="round", zorder=3)
    ax.plot(r, i, "o", ms=4.6, color=c, mec="white", mew=0.7, zorder=4)
    txt = "0.00" if abs(r) < 0.005 else f"{r:+.2f}"
    ax.text(hi + 0.035, i, txt + ("*" if sig else ""), va="center",
            fontsize=6.8, color=C_INK)

ax.axvline(0, color=C_INK, lw=0.7, ls=(0, (3, 2)), alpha=0.8, zorder=2)
ax.set_yticks(range(len(items)))
ax.set_yticklabels([l for l, _ in items])
ax.set_ylim(-0.6, len(items) - 0.4)
ax.set_xlim(-0.45, 0.78)
ax.set_xticks([-0.25, 0, 0.25, 0.5])
ax.set_xlabel(r"Spearman $\rho$ with usage intensity  (95% CI)", labelpad=2)
ax.grid(axis="x", color=C_GRID, lw=0.5, zorder=0)
ax.set_axisbelow(True)
for s in ("top", "right", "left"):
    ax.spines[s].set_visible(False)
ax.tick_params(axis="y", length=0)
save(fig, "fig_me140_intensity_rho")
plt.close(fig)

note("")
note("[Fig 3 / Table] Spearman rho with usage intensity, within users")
note(f"    {'outcome':<34}{'rho':>8}{'p':>10}{'p_adj':>10}{'n':>5}")
for row in sorted(raw_rows, key=lambda r: -r["rho"]):
    star = "*" if row["p_adj"] < 0.05 else " "
    note(f"    {row['label']:<34}{row['rho']:>+8.3f}{row['p']:>10.3f}"
         f"{row['p_adj']:>10.3f}{row['n']:>5}{star}")


# ===========================================================================
# Figure 4: dose-response across usage bands
# ===========================================================================
band = pd.cut(u_num["int"], [0, 1, 2, 4],
              labels=["1–2 times\ntotal", "A few times\nper month", "Weekly\nor more"])
series = [("Connections across topics", "conn", C_ENGAGE, "o", "-"),
          ("Any efficiency benefit", "effb", C_BENE, "s", "-"),
          ("Deeper understanding", "deep", C_LEARN, "^", "--")]

fig, ax = plt.subplots(figsize=(COL_W, 2.25))
xs = np.arange(3)
stats = []
for j, (lab, col, c, mk, ls) in enumerate(series):
    dodge = (j - 1) * 0.055
    pct, los, his, ks, nns = [], [], [], [], []
    for b in band.cat.categories:
        s = u_num[(band == b).values]
        v = s[col].dropna()
        k, nn = int(v.sum()), len(v)
        pct.append(100 * k / nn)
        lo, hi = wilson(k, nn)
        los.append(lo); his.append(hi); ks.append(k); nns.append(nn)
    ax.errorbar(xs + dodge, pct,
                yerr=[np.array(pct) - np.array(los), np.array(his) - np.array(pct)],
                color=c, lw=1.3, ls=ls, marker=mk, ms=4.2, mec="white", mew=0.7,
                capsize=1.8, elinewidth=0.8, zorder=3, label=lab)
    stats.append((c, pct, ks, nns, lab))

# Direct value label on every point, nudged apart where two series coincide.
GAP = 8.5
for i in range(3):
    order = sorted(range(len(series)), key=lambda j: stats[j][1][i])
    ys = [stats[j][1][i] for j in order]
    for a in range(1, len(ys)):
        ys[a] = max(ys[a], ys[a - 1] + GAP)
    shift = np.mean([stats[j][1][i] for j in order]) - np.mean(ys)
    for j, y in zip(order, ys):
        c, pct = stats[j][0], stats[j][1]
        ax.text(xs[i] + 0.10, min(max(y + shift, 3), 102), f"{pct[i]:.0f}%",
                color=c, fontsize=6.8, va="center", fontweight="bold", zorder=5,
                bbox=dict(facecolor="white", edgecolor="none", alpha=0.62,
                          boxstyle="square,pad=0.1"))

ns = [int((band == b).sum()) for b in band.cat.categories]
ax.set_xticks(xs)
ax.set_xticklabels([f"{b}\n($n$={nn})" for b, nn in zip(band.cat.categories, ns)])
ax.set_xlim(-0.3, 2.62)
ax.set_ylim(0, 105)
ax.set_yticks(np.arange(0, 101, 25))
ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
ax.set_ylabel("Users reporting the benefit", labelpad=2)
ax.grid(axis="y", color=C_GRID, lw=0.5, zorder=0)
ax.set_axisbelow(True)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
ax.legend(frameon=False, loc="lower center", bbox_to_anchor=(0.5, 1.0),
          ncol=1, handlelength=2.0, borderaxespad=0, labelspacing=0.25)
save(fig, "fig_me140_dose_response")
plt.close(fig)

note("")
note(f"[Fig 4] Dose-response by usage band (band sizes: {ns})")
for c, pct, ks, nns, lab in stats:
    cells = "  ".join(f"{p:.0f}% ({k}/{n})" for p, k, n in zip(pct, ks, nns))
    note(f"    {lab:<26} {cells}")


# ===========================================================================
# Figure 5: perceptions (cognitive-effect choice + accuracy Likert)
# ===========================================================================
fig, axes = plt.subplots(2, 1, figsize=(COL_W, 2.5),
                         gridspec_kw={"height_ratios": [5, 2.1], "hspace": 0.75})

d_lab = ["Changed how I approach\nproblem solving",
         "Encouraged asking\n“why”, not just answers",
         "Worry about weakened\nindependent ability",
         "Occasional illusion\nof understanding"]
d_keys = ["Changed how I think about problem solving",
          "Encouraged me to ask",
          "Worry it may weaken independent problem solving",
          "Felt I understood more than I actually did"]
d_cnt = [cnt("Q13", k) for k in d_keys]
n_depth = int(u_lab["Q13"].notna().sum())
d_pct = [100 * c / n_depth for c in d_cnt]
cols = [C_LEARN, C_LEARN, C_MUTED, C_MUTED]
y = np.arange(4)[::-1]
axes[0].barh(y, d_pct, height=0.6, color=cols, zorder=3)
for yi, c, p in zip(y, d_cnt, d_pct):
    axes[0].text(p + 1.8, yi, f"{p:.0f}%  ({c})", va="center",
                 fontsize=6.8, color=C_INK)
axes[0].set_yticks(y); axes[0].set_yticklabels(d_lab)
axes[0].set_xlim(0, 60); axes[0].set_xticks(np.arange(0, 61, 15))
axes[0].xaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
axes[0].grid(axis="x", color=C_GRID, lw=0.5, zorder=0); axes[0].set_axisbelow(True)
for s in ("top", "right", "left"):
    axes[0].spines[s].set_visible(False)
axes[0].set_title("(a) Most representative cognitive effect (single choice)",
                  loc="left", fontsize=7.5, pad=4)

LIK = cb.LIKERT_ORDER
lk = [int((u_num["Q14"] == i).sum()) for i in range(1, 6)]
n_lik = int(u_num["Q14"].notna().sum())
shades = ["#1E6DB5", "#6FA3D3", C_MUTED, "#D69A62", C_BENE]
left = 0
for c, sh in zip(lk, shades):
    w = 100 * c / n_lik
    axes[1].barh(0, w - 0.35, left=left, height=0.5, color=sh, zorder=3)
    if w > 6:
        axes[1].text(left + w / 2, 0, f"{w:.0f}%", ha="center", va="center",
                     fontsize=6.6, color="white")
    left += w
axes[1].set_xlim(0, 100); axes[1].set_ylim(-0.5, 0.5)
axes[1].set_yticks([])
axes[1].set_xticks(np.arange(0, 101, 25))
axes[1].xaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
for s in ("top", "right", "left"):
    axes[1].spines[s].set_visible(False)
axes[1].set_title("(b) “Encountered unclear, incomplete, or incorrect responses”",
                  loc="left", fontsize=7.5, pad=4)
handles = [plt.Rectangle((0, 0), 1, 1, color=sh) for sh in shades]
axes[1].legend(handles, ["Str. disagree", "Disagree", "Neutral", "Agree", "Str. agree"],
               frameon=False, ncol=5, fontsize=6.0, loc="upper center",
               bbox_to_anchor=(0.5, -0.55), handlelength=1.0, columnspacing=0.7,
               handleheight=0.9)
save(fig, "fig_me140_perceptions")
plt.close(fig)

note("")
note(f"[Fig 5] Perceptions (depth n={n_depth}, Likert n={n_lik})")
for l, c, p in zip(d_keys, d_cnt, d_pct):
    note(f"    {l:<48} {c:>3}  ({p:.1f}%)")
note(f"    constructive (items 2+3 of instrument)  "
     f"{d_cnt[0]+d_cnt[1]:>3}  ({100*(d_cnt[0]+d_cnt[1])/n_depth:.1f}%)")
note(f"    concern      (items 1+4 of instrument)  "
     f"{d_cnt[2]+d_cnt[3]:>3}  ({100*(d_cnt[2]+d_cnt[3])/n_depth:.1f}%)")
for l, c in zip(LIK, lk):
    note(f"    Likert {l:<28} {c:>3}  ({100*c/n_lik:.1f}%)")
note(f"    agree or stronger : {100*(lk[3]+lk[4])/n_lik:.1f}%   "
     f"neutral: {100*lk[2]/n_lik:.1f}%")


# ===========================================================================
# Supporting tests quoted in the LaTeX section
# ===========================================================================
note("")
note("[Adoption] Was adoption patterned by student background?")

adopted = (df_num["int"] > 0).map({True: "User", False: "Non-user"})

# Prior AI familiarity (Q1) -- see codebook_me140.py on this item's identity.
# The full 5x2 table has expected counts far below 5 (the "None" level holds a
# single respondent), so the chi-square there is not interpretable. Following
# the convention stated in the paper, the test is reported on the collapsed
# 2x2 table via Fisher's exact test; the uncorrected chi-square is printed
# only to show why it was replaced.
if cb.Q1_IS_FAMILIARITY:
    ct = pd.crosstab(df_lab["Q1"], adopted)
    chi2, p, dof, exp = chi2_contingency(ct)
    note(f"    Familiarity x adoption (5x2 chi2, NOT USED): chi2({dof})={chi2:.2f}, "
         f"p={p:.3f}, min expected={exp.min():.2f}  <- assumption violated")

    fam_hi = df_num["Q1"].apply(lambda v: np.nan if pd.isna(v) else float(v >= 4))
    sub = pd.DataFrame({"fam": fam_hi, "adopt": adopted}).dropna()
    ct2 = pd.crosstab(sub["fam"], sub["adopt"])
    orr, pf = fisher_exact(ct2.values)
    chi2b, pb, dofb, expb = chi2_contingency(ct2)
    vb = np.sqrt(chi2b / (ct2.values.sum() * min(np.array(ct2.shape) - 1)))
    note(f"    Familiarity (high vs low/mod) x adoption : Fisher OR={orr:.2f}, "
         f"p={pf:.3f}; chi2({dofb})={chi2b:.2f}, V={vb:.3f}, "
         f"min expected={expb.min():.2f}")
    note(f"        table (rows low/mod, high; cols non-user, user): "
         f"{ct2.values.tolist()}")

ct = pd.crosstab(df_lab["Q2"], adopted)
chi2, p, dof, exp = chi2_contingency(ct)
v = np.sqrt(chi2 / (ct.values.sum() * min(np.array(ct.shape) - 1)))
note(f"    Pre-course AI use x adoption (5x2) : chi2({dof})={chi2:.2f}, p={p:.3f}, "
     f"V={v:.3f}, min expected={exp.min():.2f}")

ai_hi = df_num["Q2"].apply(lambda v: np.nan if pd.isna(v) else float(v >= 4))
sub = pd.DataFrame({"ai": ai_hi, "adopt": adopted}).dropna()
ct2 = pd.crosstab(sub["ai"], sub["adopt"])
orr, pf = fisher_exact(ct2.values)
note(f"    Pre-course AI use (freq vs infreq) x adoption : Fisher OR={orr:.2f}, "
     f"p={pf:.3f}; table {ct2.values.tolist()}")

for col, lab in [("Q1", "prior familiarity"), ("Q2", "pre-course academic AI use"),
                 ("Q3", "this-semester AI use")]:
    s = u_num[["int", col]].dropna()
    r, p = spearmanr(s["int"], s[col])
    note(f"    Intensity vs {lab:<28} rho={r:+.3f}, p={p:.3f}, n={len(s)}")

note("")
note("[Users vs non-users] Structurally confounded contrasts")
for qid, needle, lab in [("Q9", "No effect on learning", "any learning benefit"),
                         ("Q10", "No efficiency benefit", "any efficiency benefit")]:
    flag = np.where(df_lab[qid].isna(), np.nan,
                    (~has(df_lab, qid, needle)).astype(float))
    sub = pd.DataFrame({"adopt": adopted, "benefit": flag}).dropna()
    ct = pd.crosstab(sub["adopt"], sub["benefit"])
    chi2, p, dof, exp = chi2_contingency(ct)
    v = np.sqrt(chi2 / (ct.values.sum() * min(np.array(ct.shape) - 1)))
    note(f"    Use x {lab:<24} chi2({dof})={chi2:.2f}, p={p:.4g}, V={v:.3f}, "
         f"min expected={exp.min():.2f}")
    if ct.shape == (2, 2):
        orr, pf = fisher_exact(ct.values)
        note(f"        Fisher exact: OR={orr:.2f}, p={pf:.4g}")
    nonuser_null = int(((sub['adopt'] == 'Non-user') & (sub['benefit'] == 0)).sum())
    nonuser_tot = int((sub['adopt'] == 'Non-user').sum())
    user_null = int(((sub['adopt'] == 'User') & (sub['benefit'] == 0)).sum())
    user_tot = int((sub['adopt'] == 'User').sum())
    note(f"        null option chosen by {nonuser_null}/{nonuser_tot} non-users "
         f"vs {user_null}/{user_tot} users")

# Endorsement: within users vs across the whole sample.
note("")
note("[Endorsement] Within users vs across all respondents")
df_num["rec_all"] = df_lab["Q17"].map(rm).values
df_num["want_all"] = df_lab["Q16"].map(rm).values
for col, lab in [("rec_all", "Would recommend"), ("want_all", "Wants VTA elsewhere")]:
    s = df_num[["int", col]].dropna()
    r, p = spearmanr(s["int"], s[col])
    note(f"    {lab:<22} all respondents : rho={r:+.3f}, p={p:.4g}, n={len(s)}")
for row in raw_rows:
    if row["col"] in ("rec", "want"):
        note(f"    {row['label']:<22} users only      : rho={row['rho']:+.3f}, "
             f"p={row['p']:.3f}, n={row['n']}")

yes_rec = int((u_lab["Q17"] == "Yes").sum())
yes_want = int((u_lab["Q16"] == "Yes").sum())
note(f"    Users answering 'Yes' to recommend : {yes_rec}/{int(u_lab['Q17'].notna().sum())} "
     f"({100*yes_rec/int(u_lab['Q17'].notna().sum()):.1f}%)")
note(f"    Users answering 'Yes' to want      : {yes_want}/{int(u_lab['Q16'].notna().sum())} "
     f"({100*yes_want/int(u_lab['Q16'].notna().sum()):.1f}%)")

# Perceived accuracy vs perceived depth benefit.
note("")
note("[Accuracy x depth] Mann-Whitney U on the quality-concern item")
g_yes = u_num.loc[u_num["deep"] == True, "Q14"].dropna()
g_no = u_num.loc[(u_num["deep"] == False) & u_lab["Q9"].notna(), "Q14"].dropna()
uu, pu = mannwhitneyu(g_yes, g_no, alternative="two-sided")
rb = 1 - (2 * uu) / (len(g_yes) * len(g_no))
note(f"    U={uu:.1f}, p={pu:.3f}, rank-biserial r={rb:+.3f}")
note(f"    medians {np.median(g_yes):.1f} vs {np.median(g_no):.1f}; "
     f"means {g_yes.mean():.2f} vs {g_no.mean():.2f}; "
     f"n1={len(g_yes)}, n2={len(g_no)}")

# Study strategy, quoted in the discussion.
note("")
note("[Study strategy] Single-choice distribution among users")
ss = u_lab["Q11"].value_counts()
n_ss = int(u_lab["Q11"].notna().sum())
for k, c in ss.items():
    note(f"    {k:<34} {c:>3}  ({100*c/n_ss:.1f}%)")

# Adherence, quoted in the discussion.
note("")
note("[Adherence] Single-choice distribution among users")
ad = u_lab["Q15"].value_counts()
n_ad = int(u_lab["Q15"].notna().sum())
for k, c in ad.items():
    note(f"    {k:<34} {c:>3}  ({100*c/n_ad:.1f}%)")

path = os.path.join(STATS_DIR, "paper_figure_stats.txt")
with open(path, "w") as fh:
    fh.write("\n".join(_LOG) + "\n")

print("")
print("Wrote 5 figures to", os.path.relpath(OUT, ROOT))
for f in sorted(os.listdir(OUT)):
    print("   ", f, f"{os.path.getsize(os.path.join(OUT, f))/1024:.0f} KB")
print("Stats dump ->", os.path.relpath(path, ROOT))
