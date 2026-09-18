"""
Generates the figures for the inferential-statistics subsection of the paper
"AI-Driven Pedagogical Companions" (Section III-D).

Output: vector PDFs sized for an IEEE two-column single-column measure
(3.45 in). Written to figures/paper/.

All figures use the n = 78 Virtual TA user denominator, matching the
convention of Section III-C. Every bar carries a direct value label so the
figures remain readable in grayscale print and for colorblind readers.

Run:  python3 scripts/make_paper_figures.py
"""

import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import spearmanr

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data", "Student Survey Did the Virtual TA help "
                                  "make your learning easier and more effective.xlsx")
OUT = os.path.join(ROOT, "figures", "paper", "ENGR 151 2026")
os.makedirs(OUT, exist_ok=True)

# ── palette (validated for CVD separation and print contrast) ──────────────
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


def save(fig, name):
    """Write a vector PDF for LaTeX and a PNG preview for quick inspection."""
    fig.savefig(os.path.join(OUT, name + ".pdf"))
    fig.savefig(os.path.join(OUT, name + ".png"), dpi=300)


def load():
    raw = pd.read_excel(DATA, sheet_name="act_data")
    cl = pd.read_excel(DATA, sheet_name="cleaned_data")
    cl["int"] = cl["VTA_freq/intensity"]
    mask = cl["int"] > 0
    return raw[mask.values].reset_index(drop=True), cl[mask].reset_index(drop=True)


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
    ax.barh(y, pcts, height=0.62, color=color, zorder=3)
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


# ═══════════════════════════════════════════════════════════════════════════
raw, cl = load()
N = len(cl)
LEARN = "Learning & understanding (select all that apply)."
EFF = "Efficiency and workload (select all that apply)"
QUAL = ("I sometimes encountered responses from the Virtual TA that were "
        "unclear, incomplete, or incorrect.")
DEPTH = "Depth vs superficial understanding"

def cnt(col, opt):
    return int(raw[col].str.contains(opt, regex=False, na=False).sum())


# ── Figure 1: engagement profile ───────────────────────────────────────────
fig, axes = plt.subplots(2, 1, figsize=(COL_W, 2.85),
                         gridspec_kw={"height_ratios": [4, 5], "hspace": 0.62})

freq = raw["How often did you use the course chatbot (Virtual TA) this semester?"]
f_lab = ["1–2 times total", "A few times per month",
         "1–2 times per week", "3+ times per week"]
f_key = ["1-2 times total", "A few times per month",
         "1-2 times per week", "3+ times per week"]
f_cnt = [int((freq == k).sum()) for k in f_key]
hbars(axes[0], f_lab, [100 * c / N for c in f_cnt], f_cnt, C_ENGAGE, N)
axes[0].set_title("(a) Frequency of use over the semester", loc="left",
                  fontsize=7.5, pad=4)

ses = raw["Typical session length with the Virtual TA (average time per session):"]
s_key = ["Less than 5 minutes", "5-15 minutes", "15-30 minutes",
         "30-60 minutes", "More than 60 minutes"]
s_lab = ["<5 min", "5–15 min", "15–30 min", "30–60 min", ">60 min"]
s_cnt = [int((ses == k).sum()) for k in s_key]
hbars(axes[1], s_lab, [100 * c / N for c in s_cnt], s_cnt, C_ENGAGE, N)
axes[1].set_title("(b) Typical session length", loc="left", fontsize=7.5, pad=4)
save(fig, "fig_vta_engagement")
plt.close(fig)


# ── Figure 2: reported benefits ────────────────────────────────────────────
fig, axes = plt.subplots(2, 1, figsize=(COL_W, 3.05),
                         gridspec_kw={"height_ratios": [4, 5], "hspace": 0.55})

l_lab = ["Understood concepts\nmore deeply", "Made connections\nacross topics",
         "Increased confidence\nin the subject", "No effect on\nmy learning"]
l_cnt = [cnt(LEARN, "more deeply"), cnt(LEARN, "connections across topics"),
         cnt(LEARN, "more confident"), cnt(LEARN, "didn't affect my learning")]
cols = [C_LEARN, C_LEARN, C_LEARN, C_MUTED]
y = np.arange(4)[::-1]
axes[0].barh(y, [100 * c / N for c in l_cnt], height=0.62, color=cols, zorder=3)
for yi, c in zip(y, l_cnt):
    lo, hi = wilson(c, N)
    axes[0].plot([lo, hi], [yi, yi], color=C_INK, lw=0.8, alpha=0.65, zorder=4)
    for x in (lo, hi):
        axes[0].plot([x, x], [yi - 0.16, yi + 0.16], color=C_INK, lw=0.8,
                     alpha=0.65, zorder=4)
    axes[0].text(max(100 * c / N, hi) + 2.2, yi, f"{100*c/N:.0f}%  ({c})", va="center",
                 fontsize=6.8, color=C_INK)
axes[0].set_yticks(y); axes[0].set_yticklabels(l_lab)
axes[0].set_xlim(0, 100); axes[0].set_xticks(np.arange(0, 101, 25))
axes[0].xaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
axes[0].grid(axis="x", color=C_GRID, lw=0.5, zorder=0); axes[0].set_axisbelow(True)
for s in ("top", "right", "left"):
    axes[0].spines[s].set_visible(False)
axes[0].set_title("(a) Learning and understanding", loc="left", fontsize=7.5, pad=4)

e_lab = ["Reduced time spent\nstuck on problems", "More efficient\nhomework/studying",
         "Saved time overall", "Less time on other\nresources", "None of these"]
e_cnt = [cnt(EFF, "reduced the amount of time"),
         cnt(EFF, "complete my homework or studying"),
         cnt(EFF, "saved me time overall"),
         cnt(EFF, "spend less time using other"),
         cnt(EFF, "None of the Above")]
cols = [C_BENE] * 4 + [C_MUTED]
y = np.arange(5)[::-1]
axes[1].barh(y, [100 * c / N for c in e_cnt], height=0.62, color=cols, zorder=3)
for yi, c in zip(y, e_cnt):
    lo, hi = wilson(c, N)
    axes[1].plot([lo, hi], [yi, yi], color=C_INK, lw=0.8, alpha=0.65, zorder=4)
    for x in (lo, hi):
        axes[1].plot([x, x], [yi - 0.16, yi + 0.16], color=C_INK, lw=0.8,
                     alpha=0.65, zorder=4)
    axes[1].text(max(100 * c / N, hi) + 2.2, yi, f"{100*c/N:.0f}%  ({c})", va="center",
                 fontsize=6.8, color=C_INK)
axes[1].set_yticks(y); axes[1].set_yticklabels(e_lab)
axes[1].set_xlim(0, 100); axes[1].set_xticks(np.arange(0, 101, 25))
axes[1].xaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
axes[1].grid(axis="x", color=C_GRID, lw=0.5, zorder=0); axes[1].set_axisbelow(True)
for s in ("top", "right", "left"):
    axes[1].spines[s].set_visible(False)
axes[1].set_title("(b) Efficiency and workload", loc="left", fontsize=7.5, pad=4)
save(fig, "fig_vta_benefits")
plt.close(fig)


# ── Figure 3: Spearman rho with 95% CI ─────────────────────────────────────
cl["deep"] = raw[LEARN].str.contains("more deeply", na=False).values
cl["conn"] = raw[LEARN].str.contains("connections across topics", na=False).values
cl["conf"] = raw[LEARN].str.contains("more confident", na=False).values
cl["anyl"] = raw[LEARN].str.contains(
    "more deeply|connections across topics|more confident", na=False).values
cl["effb"] = (~raw[EFF].str.contains("None of the Above", na=False)).values
rm = {"No": 1, "Not sure / It depends on the design": 2, "Maybe": 3, "Yes": 4}
cl["rec"] = raw["Would you recommend future students in this course make "
                "active use of the Virtual TA?"].map(rm).values
cl["want"] = raw["Would you like to have a Virtual TA (or something similar) "
                 "in other technical courses?"].map(rm).values
LIK = ["Strongly disagree", "Disagree", "Neutral", "Agree", "Strongly agree"]
cl["lik"] = raw[QUAL].map({l: i + 1 for i, l in enumerate(LIK)}).values

items = [("Deeper conceptual\nunderstanding", "deep"),
         ("Encountered flawed\nresponses", "lik"),
         ("Wants a VTA in\nother courses", "want"),
         ("Would recommend\nto future students", "rec"),
         ("Increased confidence", "conf"),
         ("Any learning benefit", "anyl"),
         ("Any efficiency benefit", "effb"),
         ("Connections across\ntopics", "conn")]

fig, ax = plt.subplots(figsize=(COL_W, 2.6))
for i, (lab, col) in enumerate(items):
    s = cl[["int", col]].dropna().astype(float)
    r, p = spearmanr(s["int"], s[col])
    se = 1 / np.sqrt(len(s) - 3)
    lo, hi = np.tanh(np.arctanh(r) - 1.96 * se), np.tanh(np.arctanh(r) + 1.96 * se)
    sig = p < 0.05
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
save(fig, "fig_vta_intensity_rho")
plt.close(fig)


# ── Figure 4: dose-response dissociation ───────────────────────────────────
band = pd.cut(cl["int"], [0, 1, 2, 4],
              labels=["1–2 times\ntotal", "A few times\nper month", "Weekly\nor more"])
series = [("Connections across topics", "conn", C_ENGAGE, "o", "-"),
          ("Any efficiency benefit", "effb", C_BENE, "s", "-"),
          ("Deeper understanding", "deep", C_LEARN, "^", "--")]

fig, ax = plt.subplots(figsize=(COL_W, 2.25))
xs = np.arange(3)
stats = []
for j, (lab, col, c, mk, ls) in enumerate(series):
    dodge = (j - 1) * 0.055
    pct, los, his = [], [], []
    for b in band.cat.categories:
        s = cl[band == b]
        k, nn = int(s[col].sum()), len(s)
        pct.append(100 * k / nn)
        lo, hi = wilson(k, nn)
        los.append(lo); his.append(hi)
    ax.errorbar(xs + dodge, pct,
                yerr=[np.array(pct) - np.array(los), np.array(his) - np.array(pct)],
                color=c, lw=1.3, ls=ls, marker=mk, ms=4.2, mec="white", mew=0.7,
                capsize=1.8, elinewidth=0.8, zorder=3, label=lab)
    stats.append((c, pct))

# Direct value label on every point, so each usage band can be read without
# tracing back to the axis. Labels sit in a column to the right of the band
# and are nudged apart vertically when two series land close together.
GAP = 8.5        # minimum separation between stacked labels, in percentage points
for i in range(3):
    order = sorted(range(len(series)), key=lambda j: stats[j][1][i])
    ys = [stats[j][1][i] for j in order]
    for a in range(1, len(ys)):
        ys[a] = max(ys[a], ys[a - 1] + GAP)
    shift = np.mean([stats[j][1][i] for j in order]) - np.mean(ys)
    for j, y in zip(order, ys):
        c, pct = stats[j]
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
save(fig, "fig_vta_dose_response")
plt.close(fig)


# ── Figure 5: perceptions (depth choice + accuracy Likert) ─────────────────
fig, axes = plt.subplots(2, 1, figsize=(COL_W, 2.5),
                         gridspec_kw={"height_ratios": [5, 2.1], "hspace": 0.75})

d_lab = ["Changed how I approach\nproblem solving",
         "Encouraged asking\n“why”, not just answers",
         "Worry about weakened\nindependent ability",
         "Occasional illusion\nof understanding"]
d_key = ["changed how I think", 'encouraged me to ask "why"',
         "might weaken my ability", "understood more than I actually did"]
d_cnt = [int(raw[DEPTH].str.contains(k, regex=False, na=False).sum()) for k in d_key]
cols = [C_LEARN, C_LEARN, C_MUTED, C_MUTED]
y = np.arange(4)[::-1]
axes[0].barh(y, [100 * c / N for c in d_cnt], height=0.6, color=cols, zorder=3)
for yi, c in zip(y, d_cnt):
    axes[0].text(100 * c / N + 1.8, yi, f"{100*c/N:.0f}%  ({c})", va="center",
                 fontsize=6.8, color=C_INK)
axes[0].set_yticks(y); axes[0].set_yticklabels(d_lab)
axes[0].set_xlim(0, 45); axes[0].set_xticks(np.arange(0, 46, 15))
axes[0].xaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
axes[0].grid(axis="x", color=C_GRID, lw=0.5, zorder=0); axes[0].set_axisbelow(True)
for s in ("top", "right", "left"):
    axes[0].spines[s].set_visible(False)
axes[0].set_title("(a) Most representative cognitive effect (single choice)",
                  loc="left", fontsize=7.5, pad=4)

lk = [int((raw[QUAL] == l).sum()) for l in LIK]
shades = ["#1E6DB5", "#6FA3D3", C_MUTED, "#D69A62", C_BENE]
left = 0
for c, sh, lab in zip(lk, shades, LIK):
    w = 100 * c / N
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
save(fig, "fig_vta_perceptions")
plt.close(fig)

print("Wrote 5 figures to", OUT)
for f in sorted(os.listdir(OUT)):
    print("   ", f, f"{os.path.getsize(os.path.join(OUT, f))/1024:.0f} KB")
