"""
=============================================================================
VTA Survey Statistical Analysis -- ME 140, December 2025 cohort
=============================================================================

This is an adaptation of scripts/vta_survey_analysis.py for the ME 140
December 2025 Qualtrics export. The original script is left untouched.

WHAT CHANGED, AND WHY
---------------------
1. INPUT FORMAT. The original read a two-sheet Excel workbook whose answers
   were already text ("act_data" + a hand-built "cleaned_data" sheet). The
   ME 140 file is a Qualtrics CSV with three header rows and numeric recode
   values. This script parses that layout and rebuilds both frames itself:
   the "cleaned_data" sheet has no equivalent here, so the ordinal columns
   are derived directly from the recode values.

2. LABELS. Answer text does not exist in the export, so code -> label mapping
   comes from scripts/codebook_me140.py, which reads the option order straight
   out of Appendix D of data/ME 140 questions.pdf. The single exception is Q1,
   whose Qualtrics stem disagrees with the instrument; figures using it are
   stamped. See the codebook for the evidence.

3. SAMPLE FILTERING. The export holds 121 rows, but 22 are Qualtrics
   preview/test submissions and 6 more are consent-only blanks. Both are
   dropped, giving N = 93. The original had no such step (its workbook was
   pre-filtered to N = 97).

4. DROPPED ANALYSES. The ME 140 instrument asks neither academic level nor
   the FAQ question, so the original's two academic-level chi-square tests,
   its Kruskal-Wallis test, and its figure 8 cannot be reproduced. Prior AI
   familiarity IS asked (as Q1), so those tests are retained.

5. REPLACEMENT ANALYSES. To keep the same method chain from
   "Statistical methods.pdf", the vacated slots are filled with tests the
   ME 140 instrument does support -- endorsement and session length -- and
   figure 8 becomes intensity by semester timing rather than academic level.
   Two new figures (12, 13) cover items the earlier survey did not have.

Outputs
-------
  figures/me140_dec2025/    fig01..fig13 PNG
  outputs/me140_dec2025/    frequency tables, test results, codebook review,
                            open-text responses, and a run summary
=============================================================================
"""

import os
import sys
import warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from scipy.stats import (chi2_contingency, spearmanr, mannwhitneyu,
                         kruskal, fisher_exact)
from itertools import combinations

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import codebook_me140 as cb

warnings.filterwarnings("ignore")

# -- Path configuration ------------------------------------------------------
ROOT       = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CSV_NAME  = "Virtual TA ME 140_December 20, 2025_17.07.csv"
_CANDIDATES = [os.path.join(ROOT, "data", _CSV_NAME),
               os.path.join(ROOT, "docs", _CSV_NAME)]
DATA_PATH  = next((p for p in _CANDIDATES if os.path.exists(p)), _CANDIDATES[0])
FIG_DIR    = os.path.join(ROOT, "figures", "me140_dec2025")
OUT_DIR    = os.path.join(ROOT, "outputs", "me140_dec2025")
ALPHA      = 0.05

COLORS = {
    "primary": "#2563EB", "secondary": "#10B981", "warning": "#F59E0B",
    "danger": "#EF4444",  "neutral": "#6B7280",   "purple": "#7C3AED",
}
BAR_PALETTE = ["#2563EB", "#10B981", "#F59E0B", "#EF4444",
               "#7C3AED", "#EC4899", "#14B8A6"]

N_TOTAL = None          # set by load_and_clean_data(), used in figure titles


# =============================================================================
# DATA LOADING AND CLEANING
# =============================================================================

def load_and_clean_data(filepath=DATA_PATH):
    """
    Reads the Qualtrics CSV and rebuilds the two frames the original script
    expected.

    The export has three header rows: row 0 is the column key (StartDate,
    Q1, Q2, ...), row 1 repeats the full question wording, and row 2 holds
    Qualtrics ImportId JSON. Rows 1-2 are metadata and are skipped.

    Rows are then filtered to genuine submissions:
      - DistributionChannel "preview" and Status != 0 are test responses
      - rows answering none of Q2..Q17 are consent-only dropouts

    Returns
    -------
    df_num   : pd.DataFrame - numeric recode values, analysis sample only
    df_label : pd.DataFrame - the same rows decoded to text labels, with
                              multi-selects joined by ";" so that the
                              original split_multiselect_column() logic works
    """
    global N_TOTAL

    df = pd.read_csv(filepath, skiprows=[1, 2])
    n_raw = len(df)

    q_cols = [f"Q{i}" for i in range(2, 18)]
    is_preview = (df.get("DistributionChannel") == "preview") | (df.get("Status") != 0)
    answered_any = df[q_cols].notna().sum(axis=1) > 0

    df_num = df[(~is_preview) & answered_any].copy().reset_index(drop=True)

    n_preview = int(is_preview.sum())
    n_blank = int(((~is_preview) & (~answered_any)).sum())
    N_TOTAL = len(df_num)

    print(f"    Raw rows in export:        {n_raw}")
    print(f"    Dropped (preview/test):    {n_preview}")
    print(f"    Dropped (consent-only):    {n_blank}")
    print(f"    Analysis sample:           N = {N_TOTAL}")

    # Decode every coded question to text labels
    df_label = df_num.copy()
    for qid in list(cb.SINGLE_SELECT):
        if qid in df_label.columns:
            df_label[qid] = df_num[qid].apply(
                lambda v: cb.label_for(qid, v) if pd.notna(v) else np.nan)

    for qid in cb.MULTISELECT_QS:
        if qid in df_label.columns:
            df_label[qid] = df_num[qid].apply(
                lambda v: decode_multiselect(qid, v))

    return df_num, df_label


def decode_multiselect(qid, value):
    """
    Turns a Qualtrics multi-select cell ("1,4,6") into the ";"-joined label
    string the original plotting helpers expect.
    """
    if pd.isna(value):
        return np.nan
    codes = [c.strip() for c in str(value).split(",") if c.strip()]
    return ";".join(cb.label_for(qid, c) for c in codes)


def split_multiselect_column(series, separator=";"):
    """
    Expands a Series of delimited multi-select strings into a flat list of
    individual option strings (one element per student choice).
    """
    all_choices = []
    for response in series.dropna():
        for choice in str(response).split(separator):
            choice = choice.strip()
            if choice:
                all_choices.append(choice)
    return all_choices


def compute_frequencies(series, category_order=None):
    """
    Counts occurrences of each value and converts to percentages.
    Returns a DataFrame with columns ['Category', 'Count', 'Percentage'].
    """
    counts = series.value_counts()

    if category_order is not None:
        ordered = [c for c in category_order if c in counts.index]
        remaining = [c for c in counts.index if c not in ordered]
        counts = counts.reindex(ordered + remaining)

    total = counts.sum()
    return pd.DataFrame({
        "Category": counts.index,
        "Count": counts.values,
        "Percentage": (counts.values / total * 100).round(1),
    }).reset_index(drop=True)


def multiselect_frequencies(series):
    """
    Counts each option of a multi-select independently. Percentages are of
    respondents who answered the question, so they sum to >100%.
    """
    choices = split_multiselect_column(series)
    counts = pd.Series(choices).value_counts()
    n_resp = int(series.notna().sum())
    return pd.DataFrame({
        "Category": counts.index,
        "Count": counts.values,
        "Percentage": (counts.values / n_resp * 100).round(1),
    }).reset_index(drop=True), n_resp


# =============================================================================
# STATISTICAL TESTS  (unchanged in method from the original script)
# =============================================================================

def run_chi_square(df, col_a, col_b):
    """Chi-Square test of independence plus Cramer's V."""
    subset = df[[col_a, col_b]].dropna()
    contingency_table = pd.crosstab(subset[col_a], subset[col_b])

    if contingency_table.shape[0] < 2 or contingency_table.shape[1] < 2:
        return None

    chi2_stat, p_value, dof, expected = chi2_contingency(contingency_table)

    n = contingency_table.values.sum()
    rows, cols = contingency_table.shape
    cramers_v = np.sqrt(chi2_stat / (n * min(rows - 1, cols - 1)))

    return {
        "chi2": chi2_stat, "p_value": p_value, "dof": dof,
        "cramers_v": cramers_v, "contingency_table": contingency_table,
        "n": int(n), "min_expected": float(expected.min()),
    }


def apply_fdr_correction(p_values):
    """
    Benjamini-Hochberg FDR correction.
    Returns (adjusted_p_values, is_significant) in the original input order.
    """
    p = np.asarray(p_values, dtype=float)
    m = len(p)
    order = np.argsort(p)
    ranked = p[order]

    adjusted = ranked * m / np.arange(1, m + 1)
    # Enforce monotonicity from the largest p-value downwards
    adjusted = np.minimum.accumulate(adjusted[::-1])[::-1]
    adjusted = np.clip(adjusted, 0, 1)

    out = np.empty(m, dtype=float)
    out[order] = adjusted
    return out, out < ALPHA


def run_spearman(df, col_a, col_b):
    """Spearman rank correlation between two ordinal columns."""
    subset = df[[col_a, col_b]].dropna()
    rho, p_value = spearmanr(subset[col_a], subset[col_b])
    return {"rho": rho, "p_value": p_value, "n": len(subset)}


def run_fisher_exact(contingency_2x2):
    """Fisher's exact test plus odds ratio for a 2x2 table."""
    odds_ratio, p_value = fisher_exact(contingency_2x2)
    return {"odds_ratio": odds_ratio, "p_value": p_value}


def run_mann_whitney(group1_values, group2_values,
                     group1_name="Group 1", group2_name="Group 2"):
    """Mann-Whitney U for two independent ordinal groups, with rank-biserial r."""
    u_stat, p_value = mannwhitneyu(group1_values, group2_values,
                                   alternative="two-sided")
    n1, n2 = len(group1_values), len(group2_values)
    effect_r = 1 - (2 * u_stat) / (n1 * n2)   # rank-biserial correlation
    return {
        "u_stat": u_stat, "p_value": p_value, "n1": n1, "n2": n2,
        "median1": float(np.median(group1_values)),
        "median2": float(np.median(group2_values)),
        "effect_r": effect_r,
        "group1_name": group1_name, "group2_name": group2_name,
    }


def run_kruskal_wallis(groups_dict):
    """
    Kruskal-Wallis across 3+ groups, with Dunn-style pairwise Mann-Whitney
    post-hoc tests corrected by Benjamini-Hochberg when the omnibus is
    significant.
    """
    groups = {k: np.asarray(v) for k, v in groups_dict.items() if len(v) >= 3}
    if len(groups) < 3:
        return None

    h_stat, p_value = kruskal(*groups.values())

    post_hoc = []
    if p_value < ALPHA:
        pairs, raw_p = [], []
        for a, b in combinations(groups, 2):
            u, p = mannwhitneyu(groups[a], groups[b], alternative="two-sided")
            pairs.append(f"{a} vs {b}")
            raw_p.append(p)
        adj_p, sig = apply_fdr_correction(raw_p)
        post_hoc = [{"pair": pr, "raw_p": rp, "adjusted_p": ap, "significant": bool(s)}
                    for pr, rp, ap, s in zip(pairs, raw_p, adj_p, sig)]

    return {"h_stat": h_stat, "p_value": p_value, "post_hoc": post_hoc,
            "group_sizes": {k: len(v) for k, v in groups.items()}}


# =============================================================================
# PLOTTING HELPERS
# =============================================================================

def ensure_dirs():
    """Creates the figure and output directories if they do not exist."""
    os.makedirs(FIG_DIR, exist_ok=True)
    os.makedirs(OUT_DIR, exist_ok=True)


def stamp_provisional(fig, qids):
    """
    Marks a figure whose category labels rest on an assumed code ordering.

    Any figure built on a question flagged "provisional" in the codebook gets
    a visible footer, so an assumed label ordering can never be mistaken for
    an established one when the figure is reused elsewhere.
    """
    flagged = [q for q in qids if cb.is_provisional(q)]
    if not flagged:
        return
    fig.text(
        0.5, -0.02,
        "UNCONFIRMED ITEM (" + ", ".join(flagged) + ") - the instrument lists Q1 as prior AI "
        "familiarity, but the Qualtrics question stem reads \"Did you find this explanation "
        "useful?\". The response pattern supports familiarity; see codebook_me140.py.",
        ha="center", va="top", fontsize=7.5, style="italic", color=COLORS["danger"],
        wrap=True,
    )


def save_figure(fig, filename):
    """Saves a figure to FIG_DIR and closes it."""
    filepath = os.path.join(FIG_DIR, filename)
    fig.savefig(filepath, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  [saved] figures/me140_dec2025/{filename}")


def _bar_labels(ax, bars, counts, pcts, pad):
    """Writes 'n=... (..%)' at the end of each horizontal bar."""
    for bar, count, pct in zip(bars, counts, pcts):
        ax.text(bar.get_width() + pad, bar.get_y() + bar.get_height() / 2,
                f"n={count} ({pct}%)", va="center", fontsize=10)


# =============================================================================
# FIGURES
# =============================================================================

def plot_vta_usage_frequency(df_label):
    """Fig 1 - How often students used the VTA this semester (Q5)."""
    order = [cb.SINGLE_SELECT["Q5"][i] for i in range(1, 6)]
    freq_df = compute_frequencies(df_label["Q5"], category_order=order)

    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.barh(freq_df["Category"], freq_df["Count"],
                   color=COLORS["primary"], edgecolor="white")
    _bar_labels(ax, bars, freq_df["Count"], freq_df["Percentage"], 0.3)

    ax.set_xlabel("Number of Students", fontsize=12)
    ax.set_title(f"Fig 1 - VTA Usage Frequency This Semester\n"
                 f"(ME 140, Dec 2025; N={N_TOTAL})",
                 fontsize=13, fontweight="bold")
    ax.set_xlim(0, freq_df["Count"].max() + 10)
    ax.invert_yaxis()
    ax.grid(axis="x", linestyle="--", alpha=0.4)
    fig.tight_layout()
    stamp_provisional(fig, ["Q5"])
    save_figure(fig, "fig01_vta_usage_frequency.png")


def plot_learning_understanding_benefits(df_label):
    """Fig 2 - Multi-select learning & understanding benefits (Q9)."""
    freq_df, n_resp = multiselect_frequencies(df_label["Q9"])
    freq_df = freq_df.sort_values("Count")

    fig, ax = plt.subplots(figsize=(10, 5))
    colors = [COLORS["danger"] if "No effect" in c else COLORS["secondary"]
              for c in freq_df["Category"]]
    bars = ax.barh(freq_df["Category"], freq_df["Count"],
                   color=colors, edgecolor="white")
    _bar_labels(ax, bars, freq_df["Count"], freq_df["Percentage"], 0.4)

    ax.set_xlabel(f"Number of Selections (multi-select, n={n_resp} respondents)", fontsize=11)
    ax.set_title("Fig 2 - Learning & Understanding Benefits Reported\n"
                 "(Multi-select; students could choose multiple options)",
                 fontsize=13, fontweight="bold")
    ax.set_xlim(0, freq_df["Count"].max() + 14)
    ax.grid(axis="x", linestyle="--", alpha=0.4)
    ax.legend(handles=[mpatches.Patch(color=COLORS["secondary"], label="Positive benefit"),
                       mpatches.Patch(color=COLORS["danger"], label="No / neutral effect")],
              loc="lower right")
    fig.tight_layout()
    stamp_provisional(fig, ["Q9"])
    save_figure(fig, "fig02_learning_understanding_benefits.png")


def plot_efficiency_benefits(df_label):
    """Fig 3 - Multi-select efficiency & workload benefits (Q10)."""
    freq_df, n_resp = multiselect_frequencies(df_label["Q10"])
    freq_df = freq_df.sort_values("Count")

    fig, ax = plt.subplots(figsize=(10, 5))
    colors = [COLORS["danger"] if "No efficiency" in c else COLORS["warning"]
              for c in freq_df["Category"]]
    bars = ax.barh(freq_df["Category"], freq_df["Count"],
                   color=colors, edgecolor="white")
    _bar_labels(ax, bars, freq_df["Count"], freq_df["Percentage"], 0.3)

    ax.set_xlabel(f"Number of Selections (multi-select, n={n_resp} respondents)", fontsize=11)
    ax.set_title("Fig 3 - Efficiency & Workload Benefits Reported\n"
                 "(Multi-select; students could choose multiple options)",
                 fontsize=13, fontweight="bold")
    ax.set_xlim(0, freq_df["Count"].max() + 12)
    ax.grid(axis="x", linestyle="--", alpha=0.4)
    ax.legend(handles=[mpatches.Patch(color=COLORS["warning"], label="Efficiency benefit"),
                       mpatches.Patch(color=COLORS["danger"], label="No benefit")],
              loc="lower right")
    fig.tight_layout()
    stamp_provisional(fig, ["Q10"])
    save_figure(fig, "fig03_efficiency_benefits.png")


def plot_likert_quality_concern(df_label):
    """Fig 4 - Likert distribution for the response-quality concern item (Q14)."""
    freq_df = compute_frequencies(df_label["Q14"], category_order=cb.LIKERT_ORDER)
    bar_colors = ["#EF4444", "#F97316", "#9CA3AF", "#60A5FA", "#2563EB"]

    fig, ax = plt.subplots(figsize=(9, 4.4))
    bars = ax.bar(freq_df["Category"], freq_df["Percentage"],
                  color=bar_colors[:len(freq_df)], edgecolor="white", width=0.6)
    for bar, pct, cnt in zip(bars, freq_df["Percentage"], freq_df["Count"]):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                f"{pct}%\n(n={cnt})", ha="center", va="bottom", fontsize=10)

    ax.set_ylabel("Percentage of Respondents (%)", fontsize=11)
    ax.set_title("Fig 4 - Perceived Quality Concerns with VTA Responses\n"
                 "\"I sometimes encountered responses that were unclear, incomplete, or incorrect.\"",
                 fontsize=12, fontweight="bold")
    ax.set_ylim(0, freq_df["Percentage"].max() + 10)
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    fig.tight_layout()
    save_figure(fig, "fig04_likert_quality_concern.png")


def plot_recommendation_vs_desire(df_label):
    """Fig 5 - Recommend to future students (Q17) vs want a VTA elsewhere (Q16)."""
    response_order = cb.YES_NO_ORDER
    recommend = df_label["Q17"].value_counts().reindex(response_order, fill_value=0)
    desire = df_label["Q16"].value_counts().reindex(response_order, fill_value=0)

    x = np.arange(len(response_order))
    w = 0.35

    fig, ax = plt.subplots(figsize=(10, 5))
    bars_a = ax.bar(x - w / 2, recommend.values, width=w,
                    label="Recommend to future students",
                    color=COLORS["primary"], edgecolor="white")
    bars_b = ax.bar(x + w / 2, desire.values, width=w,
                    label="Want VTA in other courses",
                    color=COLORS["secondary"], edgecolor="white")

    for bar in list(bars_a) + list(bars_b):
        h = bar.get_height()
        if h > 0:
            ax.text(bar.get_x() + bar.get_width() / 2, h + 0.5,
                    str(int(h)), ha="center", va="bottom", fontsize=10)

    ax.set_xticks(x)
    ax.set_xticklabels([r.replace(" / ", " /\n") for r in response_order], fontsize=9)
    ax.set_ylabel("Number of Students", fontsize=11)
    ax.set_title(f"Fig 5 - Student Endorsement and Desire for the VTA\n"
                 f"(N={N_TOTAL}; two separate questions)",
                 fontsize=13, fontweight="bold")
    ax.legend(fontsize=10)
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    fig.tight_layout()
    stamp_provisional(fig, ["Q16", "Q17"])
    save_figure(fig, "fig05_recommendation_vs_desire.png")


def plot_spearman_heatmap(rho_matrix, p_matrix, labels):
    """
    Fig 6 - Heatmap of Spearman rho among the ordinal items.

    Unlike the original (which drew only the five pairs it tested), this
    fills the full matrix, since every ordinal item here is on a numeric
    recode scale and all pairs are computable.
    """
    n = len(labels)
    fig, ax = plt.subplots(figsize=(8.5, 6.5))
    im = ax.imshow(rho_matrix, cmap="RdYlGn", vmin=-1, vmax=1, aspect="auto")
    plt.colorbar(im, ax=ax, label="Spearman rho")

    for i in range(n):
        for j in range(n):
            if np.isnan(rho_matrix[i, j]):
                continue
            star = "*" if (i != j and p_matrix[i, j] < ALPHA) else ""
            ax.text(j, i, f"{rho_matrix[i, j]:.2f}{star}",
                    ha="center", va="center", fontsize=9, color="black")

    ax.set_xticks(range(n)); ax.set_yticks(range(n))
    ax.set_xticklabels(labels, rotation=30, ha="right", fontsize=9)
    ax.set_yticklabels(labels, fontsize=9)
    ax.set_title("Fig 6 - Spearman Rank Correlations Between Ordinal Survey Variables\n"
                 "(*  p < 0.05; green = positive, red = negative association)",
                 fontsize=12, fontweight="bold")
    fig.tight_layout()
    if "Prior AI Familiarity" in labels:
        stamp_provisional(fig, ["Q1"])
    save_figure(fig, "fig06_spearman_heatmap.png")


def plot_chi_square_summary(chi_sq_results, fdr_adjusted_p):
    """Fig 7 - Cramer's V effect sizes beside raw vs BH-adjusted p-values."""
    labels = [r["label"] for r in chi_sq_results]
    cramers = [r["cramers_v"] for r in chi_sq_results]
    p_raw = [r["p_value"] for r in chi_sq_results]
    p_adj = list(fdr_adjusted_p)
    sig_mask = [p < ALPHA for p in p_adj]

    fig, axes = plt.subplots(1, 2, figsize=(13.5, 5))

    ax = axes[0]
    colors = [COLORS["primary"] if s else COLORS["neutral"] for s in sig_mask]
    bars = ax.barh(labels, cramers, color=colors, edgecolor="white")
    ax.axvline(0.10, color="gray", linestyle="--", alpha=0.6, label="Weak (0.10)")
    ax.axvline(0.30, color=COLORS["warning"], linestyle="--", alpha=0.8, label="Moderate (0.30)")
    ax.axvline(0.50, color=COLORS["danger"], linestyle="--", alpha=0.8, label="Strong (0.50)")
    for bar, v in zip(bars, cramers):
        ax.text(bar.get_width() + 0.005, bar.get_y() + bar.get_height() / 2,
                f"{v:.3f}", va="center", fontsize=9)
    ax.set_xlabel("Cramer's V (Effect Size)", fontsize=11)
    ax.set_title("Effect Size (Cramer's V)", fontsize=12, fontweight="bold")
    # The two short bars leave the middle-right of the panel empty; parking the
    # legend there keeps it clear of every bar value label.
    ax.legend(fontsize=8, loc="center right", framealpha=0.95)
    ax.set_xlim(0, max(cramers) + 0.30)
    ax.invert_yaxis()
    ax.grid(axis="x", linestyle="--", alpha=0.3)

    ax2 = axes[1]
    y_pos = np.arange(len(labels))
    ax2.scatter(p_raw, y_pos, color=COLORS["neutral"], label="Raw p-value", zorder=3, s=60)
    ax2.scatter(p_adj, y_pos, color=COLORS["primary"], label="BH-adjusted p", zorder=4, s=80, marker="D")
    ax2.axvline(ALPHA, color=COLORS["danger"], linestyle="--", label=f"alpha = {ALPHA}")
    ax2.set_xscale("log")
    ax2.set_yticks(y_pos); ax2.set_yticklabels(labels, fontsize=9)
    ax2.set_xlabel("p-value (log scale)", fontsize=11)
    ax2.set_title("Raw vs BH FDR-Adjusted p-Values", fontsize=12, fontweight="bold")
    ax2.legend(fontsize=9)
    ax2.invert_yaxis()
    ax2.grid(axis="x", linestyle="--", alpha=0.3)

    fig.suptitle("Fig 7 - Chi-Square Test Summary with Cramer's V and FDR Correction\n"
                 "(Blue = significant after BH FDR correction; grey = not significant)",
                 fontsize=12, fontweight="bold", y=1.02)
    fig.tight_layout()
    # Two of the tests are built on Q1, whose item identity is unconfirmed.
    if any("Familiarity" in lbl for lbl in labels):
        stamp_provisional(fig, ["Q1"])
    save_figure(fig, "fig07_chi_square_summary.png")


def plot_vta_intensity_by_timing(df_num, df_label, kw_result):
    """
    Fig 8 - VTA usage intensity by when in the semester it was used most (Q6).

    Replaces the original figure 8 (intensity by academic level), which the
    ME 140 instrument cannot support because it does not ask academic level.
    """
    groups = [cb.SINGLE_SELECT["Q6"][i] for i in range(1, 6)]
    medians, q1s, q3s, ns = [], [], [], []

    for g in groups:
        data = df_num.loc[df_label["Q6"] == g, "Q5"].dropna()
        ns.append(len(data))
        medians.append(np.median(data) if len(data) else np.nan)
        q1s.append(np.percentile(data, 25) if len(data) else np.nan)
        q3s.append(np.percentile(data, 75) if len(data) else np.nan)

    fig, ax = plt.subplots(figsize=(10, 5.5))
    x = np.arange(len(groups))
    ax.bar(x, medians, color=BAR_PALETTE[:len(groups)], edgecolor="white", width=0.5)

    for i, (q1, q3) in enumerate(zip(q1s, q3s)):
        if np.isnan(q1):
            continue
        ax.plot([i, i], [q1, q3], color="black", linewidth=2)
        ax.plot([i - 0.1, i + 0.1], [q1, q1], color="black", linewidth=2)
        ax.plot([i - 0.1, i + 0.1], [q3, q3], color="black", linewidth=2)

    # Wrapped short labels: the full option text collides at this figure width.
    short = ["Beginning\nof course", "Middle\nof course", "Near exams /\ndeadlines",
             "Consistently\nall semester", "Only tried it\nonce or twice"]
    ax.set_xticks(x)
    ax.set_xticklabels([f"{lbl}\n(n={n})" for lbl, n in zip(short, ns)], fontsize=8.5)
    ax.set_ylabel("VTA Usage Frequency (ordinal code 1-5)", fontsize=11)
    ax.set_title("Fig 8 - VTA Usage Intensity by Semester Timing\n"
                 "(Bars = median; error bars = IQR Q1-Q3)",
                 fontsize=13, fontweight="bold")

    if kw_result:
        txt = (f"Kruskal-Wallis H={kw_result['h_stat']:.2f}, p={kw_result['p_value']:.3f}"
               + ("  (significant)" if kw_result["p_value"] < ALPHA else "  (not significant)"))
        color = COLORS["danger"] if kw_result["p_value"] < ALPHA else COLORS["neutral"]
        ax.text(0.5, 0.97, txt, transform=ax.transAxes, ha="center", va="top",
                fontsize=9, color=color,
                bbox=dict(boxstyle="round,pad=0.3", facecolor="lightyellow", alpha=0.8))

    ax.text(0.5, 0.88,
            "Note: partly definitional - the \"only tried it once or twice\" option\n"
            "overlaps in meaning with the low end of the usage-frequency item.",
            transform=ax.transAxes, ha="center", va="top", fontsize=7.5,
            style="italic", color=COLORS["neutral"])

    ax.set_ylim(0, np.nanmax(q3s) + 1.0)
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    fig.tight_layout()
    stamp_provisional(fig, ["Q6"])
    save_figure(fig, "fig08_vta_intensity_by_timing.png")


def plot_mann_whitney_quality_concern(df_num, df_label, mw_result):
    """Fig 9 - Quality-concern score split by whether deeper understanding was reported."""
    deeper = df_label["Q9"].str.contains("Deeper concept understanding", na=False)
    g_yes = df_num.loc[deeper, "Q14"].dropna()
    g_no = df_num.loc[(~deeper) & df_label["Q9"].notna(), "Q14"].dropna()

    fig, ax = plt.subplots(figsize=(7.5, 5.5))
    data = [g_yes.values, g_no.values]
    bp = ax.boxplot(data, tick_labels=["Deeper\nunderstanding\n(Yes)",
                                       "Deeper\nunderstanding\n(No)"],
                    patch_artist=True, medianprops=dict(color="black", linewidth=2))
    for patch, color in zip(bp["boxes"], [COLORS["secondary"], COLORS["danger"]]):
        patch.set_facecolor(color)
        patch.set_alpha(0.6)

    rng = np.random.default_rng(0)
    for i, grp in enumerate(data, start=1):
        jitter = rng.uniform(-0.08, 0.08, size=len(grp))
        ax.scatter(np.full(len(grp), i) + jitter, grp,
                   alpha=0.4, s=20, color="black", zorder=3)

    ax.set_ylabel("Quality-Concern Score", fontsize=10)
    ax.set_title("Fig 9 - Quality Concern by Reported Deeper Understanding\n"
                 "(Mann-Whitney U Test)", fontsize=12, fontweight="bold")

    txt = (f"Mann-Whitney U = {mw_result['u_stat']:.1f}, p = {mw_result['p_value']:.3f}\n"
           f"n1 = {mw_result['n1']}, n2 = {mw_result['n2']}, "
           f"rank-biserial r = {mw_result['effect_r']:.2f}")
    ax.text(0.97, 0.97, txt, transform=ax.transAxes, ha="right", va="top", fontsize=9,
            bbox=dict(boxstyle="round,pad=0.3", facecolor="lightyellow", alpha=0.8))

    ax.set_ylim(0.5, 5.9)
    ax.set_yticks([1, 2, 3, 4, 5])
    ax.set_yticklabels(cb.LIKERT_ORDER, fontsize=8)
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    fig.tight_layout()
    stamp_provisional(fig, ["Q9"])
    save_figure(fig, "fig09_mann_whitney_quality_concern.png")


def plot_study_strategies(df_label):
    """Fig 10 - Self-reported study strategies (Q11, single-select)."""
    freq_df = compute_frequencies(df_label["Q11"]).sort_values("Count")

    fig, ax = plt.subplots(figsize=(10, 5))
    colors = [COLORS["secondary"] if "after" in c else
              COLORS["warning"] if "harder" in c else
              COLORS["danger"] for c in freq_df["Category"]]
    bars = ax.barh(freq_df["Category"], freq_df["Count"],
                   color=colors, edgecolor="white")
    _bar_labels(ax, bars, freq_df["Count"], freq_df["Percentage"], 0.3)

    ax.set_xlabel("Number of Students", fontsize=11)
    ax.set_title(f"Fig 10 - Self-Reported Study Strategies When Using the VTA\n"
                 f"(n={int(df_label['Q11'].notna().sum())}, single-select)",
                 fontsize=13, fontweight="bold")
    ax.set_xlim(0, freq_df["Count"].max() + 16)
    ax.grid(axis="x", linestyle="--", alpha=0.4)
    fig.tight_layout()
    stamp_provisional(fig, ["Q11"])
    save_figure(fig, "fig10_study_strategies.png")


def plot_adherence(df_label):
    """Fig 11 - Self-reported adherence to course rules (Q15)."""
    freq_df = compute_frequencies(df_label["Q15"]).sort_values("Count", ascending=False)
    pie_colors = [COLORS["secondary"], COLORS["primary"], COLORS["warning"], COLORS["danger"]]
    labels = [f"{c}\n(n={n}, {p}%)" for c, n, p in
              zip(freq_df["Category"], freq_df["Count"], freq_df["Percentage"])]

    fig, ax = plt.subplots(figsize=(8.5, 6))
    wedges, _ = ax.pie(freq_df["Count"], colors=pie_colors[:len(freq_df)],
                       startangle=140, wedgeprops=dict(edgecolor="white", linewidth=2))
    ax.legend(wedges, labels, loc="center left", bbox_to_anchor=(1, 0.5),
              fontsize=9, title="Adherence category")
    ax.set_title(f"Fig 11 - Self-Reported Adherence to Course Rules\n"
                 f"(n={int(df_label['Q15'].notna().sum())} respondents)",
                 fontsize=13, fontweight="bold")
    fig.tight_layout()
    stamp_provisional(fig, ["Q15"])
    save_figure(fig, "fig11_adherence_pie.png")


def plot_ai_use_shift(df_label, df_num):
    """
    Fig 12 - AI tool use before the course (Q2) vs during this semester (Q3).

    New figure: the ME 140 instrument asks both, letting the within-cohort
    shift in general AI use be shown directly.
    """
    order = [cb.SINGLE_SELECT["Q2"][i] for i in range(1, 6)]
    before = df_label["Q2"].value_counts().reindex(order, fill_value=0)
    during = df_label["Q3"].value_counts().reindex(order, fill_value=0)

    x = np.arange(len(order))
    w = 0.38

    fig, ax = plt.subplots(figsize=(11, 5.5))
    b1 = ax.bar(x - w / 2, before.values, width=w, label="Before this course",
                color=COLORS["neutral"], edgecolor="white")
    b2 = ax.bar(x + w / 2, during.values, width=w, label="This semester (all courses)",
                color=COLORS["purple"], edgecolor="white")
    for bar in list(b1) + list(b2):
        h = bar.get_height()
        if h > 0:
            ax.text(bar.get_x() + bar.get_width() / 2, h + 0.4,
                    str(int(h)), ha="center", va="bottom", fontsize=9)

    ax.set_xticks(x)
    ax.set_xticklabels([o.replace("A few times per ", "A few / ") for o in order], fontsize=9)
    ax.set_ylabel("Number of Students", fontsize=11)

    med_b = df_num["Q2"].median()
    med_d = df_num["Q3"].median()
    res = run_spearman(df_num, "Q2", "Q3")
    ax.set_title("Fig 12 - General AI Tool Use: Before the Course vs This Semester\n"
                 f"(median code {med_b:.0f} -> {med_d:.0f}; "
                 f"Spearman rho = {res['rho']:.2f}, p = {res['p_value']:.4f}, n = {res['n']})",
                 fontsize=12, fontweight="bold")
    ax.legend(fontsize=10)
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    fig.tight_layout()
    save_figure(fig, "fig12_ai_use_before_vs_during.png")


def plot_session_length(df_label):
    """
    Fig 13 - Typical VTA session length (Q8).

    New figure: the original script computed session length as an ordinal
    predictor but never plotted its distribution.
    """
    order = [cb.SINGLE_SELECT["Q8"][i] for i in range(1, 6)]
    freq_df = compute_frequencies(df_label["Q8"], category_order=order)

    fig, ax = plt.subplots(figsize=(9.5, 5))
    bars = ax.bar(freq_df["Category"], freq_df["Count"],
                  color=BAR_PALETTE[:len(freq_df)], edgecolor="white", width=0.6)
    for bar, cnt, pct in zip(bars, freq_df["Count"], freq_df["Percentage"]):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.4,
                f"n={cnt}\n({pct}%)", ha="center", va="bottom", fontsize=9)

    ax.set_ylabel("Number of Students", fontsize=11)
    ax.set_title(f"Fig 13 - Typical Session Length with the Virtual TA\n"
                 f"(n={int(df_label['Q8'].notna().sum())} respondents)",
                 fontsize=13, fontweight="bold")
    ax.set_ylim(0, freq_df["Count"].max() + 6)
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    fig.tight_layout()
    save_figure(fig, "fig13_session_length.png")


# =============================================================================
# TABLE OUTPUTS
# =============================================================================

def write_frequency_tables(df_label):
    """
    Writes one tidy CSV holding the frequency table for every coded question,
    plus the per-question response count.
    """
    frames = []
    for qid in [f"Q{i}" for i in range(1, 18)]:
        if qid not in df_label.columns:
            continue
        if qid in cb.MULTISELECT_QS:
            tbl, n_resp = multiselect_frequencies(df_label[qid])
            kind = "multi-select"
        else:
            tbl = compute_frequencies(df_label[qid])
            n_resp = int(df_label[qid].notna().sum())
            kind = "single-select"
        tbl.insert(0, "Question", qid)
        tbl.insert(1, "Question_text", cb.QUESTION_TEXT[qid])
        tbl.insert(2, "Type", kind)
        tbl.insert(3, "N_respondents", n_resp)
        tbl.insert(4, "Label_confidence", cb.CONFIDENCE.get(qid, "n/a"))
        frames.append(tbl)

    out = pd.concat(frames, ignore_index=True)
    path = os.path.join(OUT_DIR, "frequency_tables.csv")
    out.to_csv(path, index=False)
    print(f"  [saved] outputs/me140_dec2025/frequency_tables.csv  ({len(out)} rows)")
    return out


def write_codebook_review(df_num):
    """
    Writes every code -> label assignment with its evidence and confidence, so
    a mapping can be checked and corrected in one place.
    """
    rows = []
    for qid in [f"Q{i}" for i in range(1, 18)]:
        table = cb.SINGLE_SELECT.get(qid) or cb.MULTI_SELECT.get(qid) or {}
        if qid in cb.MULTISELECT_QS:
            used = set()
            for v in df_num[qid].dropna():
                used.update(int(c) for c in str(v).split(","))
        else:
            used = {int(v) for v in df_num[qid].dropna().unique()}

        for code, label in sorted(table.items()):
            rows.append({
                "Question": qid,
                "Question_text": cb.QUESTION_TEXT[qid],
                "Code": code,
                "Assigned_label": label,
                "Appears_in_data": "yes" if code in used else "no",
                "Confidence": cb.CONFIDENCE.get(qid, "n/a"),
                "Evidence": cb.EVIDENCE.get(qid, ""),
            })

    out = pd.DataFrame(rows)
    path = os.path.join(OUT_DIR, "codebook_review.csv")
    out.to_csv(path, index=False)
    print(f"  [saved] outputs/me140_dec2025/codebook_review.csv  ({len(out)} mappings)")
    return out


def write_open_text(df_num):
    """Exports the two free-response questions for qualitative coding."""
    out = pd.DataFrame({
        "ResponseId": df_num["ResponseId"],
        "Q18_helped_or_hindered": df_num["Q18"],
        "Q19_acceptable_use": df_num["Q19"],
    })
    out = out[out[["Q18_helped_or_hindered", "Q19_acceptable_use"]].notna().any(axis=1)]
    path = os.path.join(OUT_DIR, "open_text_responses.csv")
    out.to_csv(path, index=False)
    print(f"  [saved] outputs/me140_dec2025/open_text_responses.csv  ({len(out)} responses)")
    return out


def write_decoded_data(df_num, df_label):
    """Writes the analysis sample in both numeric and decoded form."""
    keep = ["ResponseId"] + [f"Q{i}" for i in range(1, 20)]
    num = df_num[keep].copy()
    num.columns = ["ResponseId"] + [f"{q}_{cb.SHORT_NAME[q]}" for q in keep[1:]]
    num.to_csv(os.path.join(OUT_DIR, "analysis_sample_numeric.csv"), index=False)

    lab = df_label[keep].copy()
    lab.columns = num.columns
    lab.to_csv(os.path.join(OUT_DIR, "analysis_sample_labeled.csv"), index=False)
    print(f"  [saved] outputs/me140_dec2025/analysis_sample_numeric.csv "
          f"and analysis_sample_labeled.csv  (N={len(num)})")


# =============================================================================
# MAIN
# =============================================================================

def main():
    """
    Runs the full ME 140 pipeline: load, decode, test, plot, and write tables.
    """
    ensure_dirs()
    lines = []

    def say(msg=""):
        print(msg)
        lines.append(msg)

    say("=" * 72)
    say("  VTA Survey Statistical Analysis -- ME 140, December 2025")
    say("=" * 72)

    # -- Step 1: load ------------------------------------------------------
    say("\n[1] Loading data...")
    df_num, df_label = load_and_clean_data()
    lines.append(f"    Analysis sample: N = {N_TOTAL}")

    # -- Step 2: derived binary variables ----------------------------------
    say("\n[2] Deriving binary variables for categorical tests...")

    df_label["vta_used_binary"] = df_num["Q5"].apply(
        lambda v: np.nan if pd.isna(v) else ("Used VTA" if v > 1 else "Never / minimal"))

    # np.where would coerce np.nan into the string "nan" here (it broadcasts to
    # a string dtype), silently creating a third category and corrupting every
    # contingency table built on these columns. Map on the Series instead so
    # non-respondents stay genuinely missing and are dropped by .dropna().
    df_label["benefit_learning"] = df_label["Q9"].apply(
        lambda v: np.nan if pd.isna(v) else
        ("No benefit" if "No effect on learning" in v else "Reported benefit"))

    df_label["benefit_efficiency"] = df_label["Q10"].apply(
        lambda v: np.nan if pd.isna(v) else
        ("No efficiency benefit" if "No efficiency benefit" in v else "Efficiency benefit"))

    df_label["recommend_binary"] = df_label["Q17"].apply(
        lambda v: np.nan if pd.isna(v) else ("Yes" if v == "Yes" else "Not an unqualified yes"))

    df_label["ai_before_binary"] = df_num["Q2"].apply(
        lambda v: np.nan if pd.isna(v) else ("Frequent prior AI use" if v >= 4
                                             else "Infrequent prior AI use"))

    df_label["session_binary"] = df_num["Q8"].apply(
        lambda v: np.nan if pd.isna(v) else ("Longer sessions (15+ min)" if v >= 3
                                             else "Shorter sessions (<15 min)"))

    binary_cols = ["vta_used_binary", "benefit_learning", "benefit_efficiency",
                   "recommend_binary", "ai_before_binary", "session_binary"]

    if cb.Q1_IS_FAMILIARITY:
        df_label["familiarity_binary"] = df_num["Q1"].apply(
            lambda v: np.nan if pd.isna(v) else ("High prior familiarity" if v >= 4
                                                 else "Low/moderate prior familiarity"))
        binary_cols.append("familiarity_binary")

    for col in binary_cols:
        vc = df_label[col].value_counts()
        say(f"    {col}: " + ", ".join(f"{k}={v}" for k, v in vc.items()))

    # -- Step 3: chi-square ------------------------------------------------
    say("\n[3] Running Chi-Square tests + Cramer's V...")
    say("    (Academic-level tests are omitted: the ME 140 instrument does not")
    say("     ask academic level. The familiarity tests are restored from Q1.)")

    chi_square_tests = [
        ("VTA Use vs Learning Benefit",       "vta_used_binary",  "benefit_learning"),
        ("VTA Use vs Efficiency Benefit",     "vta_used_binary",  "benefit_efficiency"),
        ("Prior AI Use vs VTA Use",           "ai_before_binary", "vta_used_binary"),
        ("VTA Use vs Recommendation",         "vta_used_binary",  "recommend_binary"),
        ("Learning Benefit vs Recommendation", "benefit_learning", "recommend_binary"),
        ("Session Length vs Learning Benefit", "session_binary",  "benefit_learning"),
    ]
    if cb.Q1_IS_FAMILIARITY:
        chi_square_tests += [
            ("Familiarity vs VTA Use",         "familiarity_binary", "vta_used_binary"),
            ("Familiarity vs Learning Benefit", "familiarity_binary", "benefit_learning"),
        ]

    chi_sq_results, raw_p = [], []
    for label, a, b in chi_square_tests:
        res = run_chi_square(df_label, a, b)
        if res is None:
            say(f"    {label}: skipped (degenerate contingency table)")
            continue
        res["label"] = label
        chi_sq_results.append(res)
        raw_p.append(res["p_value"])
        warn = "  [low expected count]" if res["min_expected"] < 5 else ""
        say(f"    {label}: chi2={res['chi2']:.2f}, p={res['p_value']:.4f}, "
            f"V={res['cramers_v']:.3f}, n={res['n']}{warn}")

    # -- Step 4: FDR -------------------------------------------------------
    say("\n[4] Applying Benjamini-Hochberg FDR correction...")
    adjusted_p, is_sig = apply_fdr_correction(raw_p)
    for i, (r, ap, s) in enumerate(zip(chi_sq_results, adjusted_p, is_sig), start=1):
        say(f"    [{i}] {r['label']}: adj_p={ap:.4f}  -> "
            f"{'SIGNIFICANT' if s else 'not significant'}")

    chi_df = pd.DataFrame([{
        "Test": r["label"], "chi2": round(r["chi2"], 4), "dof": r["dof"],
        "n": r["n"], "p_raw": r["p_value"], "p_BH_adjusted": ap,
        "cramers_v": round(r["cramers_v"], 4),
        "min_expected_count": round(r["min_expected"], 2),
        "significant_after_FDR": bool(s),
    } for r, ap, s in zip(chi_sq_results, adjusted_p, is_sig)])
    chi_df.to_csv(os.path.join(OUT_DIR, "chi_square_results.csv"), index=False)

    # -- Step 5: Spearman --------------------------------------------------
    say("\n[5] Running Spearman rank correlations...")

    ord_items = [("Q5", "VTA Intensity"), ("Q8", "Session Length"),
                 ("Q2", "Pre-course AI Use"), ("Q3", "Semester AI Use"),
                 ("Q14", "Quality Concern")]
    if cb.Q1_IS_FAMILIARITY:
        ord_items.insert(2, ("Q1", "Prior AI Familiarity"))
    ord_cols = [c for c, _ in ord_items]
    ord_labels = [l for _, l in ord_items]

    n_ord = len(ord_cols)
    rho_m = np.full((n_ord, n_ord), np.nan)
    p_m = np.ones((n_ord, n_ord))
    np.fill_diagonal(rho_m, 1.0)

    spearman_rows = []
    for i, j in combinations(range(n_ord), 2):
        r = run_spearman(df_num, ord_cols[i], ord_cols[j])
        rho_m[i, j] = rho_m[j, i] = r["rho"]
        p_m[i, j] = p_m[j, i] = r["p_value"]
        spearman_rows.append({
            "Variable_A": ord_labels[i], "Variable_B": ord_labels[j],
            "spearman_rho": round(r["rho"], 4), "p_value": r["p_value"],
            "n": r["n"], "significant": r["p_value"] < ALPHA,
        })
        say(f"    {ord_labels[i]} vs {ord_labels[j]}: rho={r['rho']:+.3f}, "
            f"p={r['p_value']:.4f}, n={r['n']} {'*' if r['p_value'] < ALPHA else ''}")

    pd.DataFrame(spearman_rows).to_csv(
        os.path.join(OUT_DIR, "spearman_results.csv"), index=False)

    # -- Step 6: Fisher ----------------------------------------------------
    say("\n[6] Running Fisher's exact test (VTA use vs learning benefit)...")
    ct = pd.crosstab(df_label["vta_used_binary"], df_label["benefit_learning"])
    fisher_result = None
    if ct.shape == (2, 2):
        fisher_result = run_fisher_exact(ct.values)
        say(f"    Odds Ratio = {fisher_result['odds_ratio']:.2f}, "
            f"p = {fisher_result['p_value']:.4f}")
        say("    Contingency table:")
        for line in ct.to_string().split("\n"):
            say("      " + line)
    else:
        say(f"    Contingency table shape {ct.shape} is not 2x2; skipping.")

    # -- Step 7: Mann-Whitney ----------------------------------------------
    say("\n[7] Running Mann-Whitney U (quality concern by understanding group)...")
    deeper = df_label["Q9"].str.contains("Deeper concept understanding", na=False)
    g_yes = df_num.loc[deeper, "Q14"].dropna()
    g_no = df_num.loc[(~deeper) & df_label["Q9"].notna(), "Q14"].dropna()

    mw_result = run_mann_whitney(g_yes.values, g_no.values,
                                 "Deeper understanding (Yes)",
                                 "Deeper understanding (No)")
    say(f"    U = {mw_result['u_stat']:.1f}, p = {mw_result['p_value']:.4f}, "
        f"n1={mw_result['n1']}, n2={mw_result['n2']}")
    say(f"    Medians: {mw_result['median1']:.1f} vs {mw_result['median2']:.1f}, "
        f"rank-biserial r = {mw_result['effect_r']:.3f}")

    # -- Step 8: Kruskal-Wallis --------------------------------------------
    say("\n[8] Running Kruskal-Wallis (VTA intensity by semester timing)...")
    say("    (Substituted for 'by academic level', which ME 140 does not ask.)")
    timing_groups = {
        lbl: df_num.loc[df_label["Q6"] == lbl, "Q5"].dropna().values
        for lbl in [cb.SINGLE_SELECT["Q6"][i] for i in range(1, 6)]
    }
    kw_result = run_kruskal_wallis(timing_groups)
    if kw_result:
        say(f"    H = {kw_result['h_stat']:.2f}, p = {kw_result['p_value']:.4f}")
        say(f"    Group sizes: {kw_result['group_sizes']}")
        say("    Caveat: this result is partly definitional -- the Q6 option")
        say("    'I only tried it once or twice' overlaps in meaning with the low")
        say("    end of the Q5 usage-frequency scale being compared.")
        if kw_result["post_hoc"]:
            say("    Post-hoc pairwise (BH FDR-corrected):")
            for ph in kw_result["post_hoc"]:
                say(f"      {ph['pair']}: adj_p={ph['adjusted_p']:.4f} -> "
                    f"{'SIGNIFICANT' if ph['significant'] else 'not significant'}")
    else:
        say("    Too few usable groups; skipped.")

    # Persist the non-chi-square tests
    other_rows = [{
        "Test": "Fisher exact: VTA use vs learning benefit",
        "Statistic": "odds ratio",
        "Value": round(fisher_result["odds_ratio"], 4) if fisher_result else None,
        "p_value": fisher_result["p_value"] if fisher_result else None,
    }, {
        "Test": "Mann-Whitney U: quality concern by deeper understanding",
        "Statistic": "U",
        "Value": mw_result["u_stat"], "p_value": mw_result["p_value"],
    }, {
        "Test": "Mann-Whitney effect size",
        "Statistic": "rank-biserial r",
        "Value": round(mw_result["effect_r"], 4), "p_value": None,
    }]
    if kw_result:
        other_rows.append({
            "Test": "Kruskal-Wallis: VTA intensity by semester timing",
            "Statistic": "H", "Value": round(kw_result["h_stat"], 4),
            "p_value": kw_result["p_value"],
        })
    pd.DataFrame(other_rows).to_csv(
        os.path.join(OUT_DIR, "other_test_results.csv"), index=False)

    # -- Step 9: figures ---------------------------------------------------
    say("\n[9] Generating figures...")
    plot_vta_usage_frequency(df_label)
    plot_learning_understanding_benefits(df_label)
    plot_efficiency_benefits(df_label)
    plot_likert_quality_concern(df_label)
    plot_recommendation_vs_desire(df_label)
    plot_spearman_heatmap(rho_m, p_m, ord_labels)  # stamped inside when Q1 is used
    plot_chi_square_summary(chi_sq_results, adjusted_p)
    plot_vta_intensity_by_timing(df_num, df_label, kw_result)
    plot_mann_whitney_quality_concern(df_num, df_label, mw_result)
    plot_study_strategies(df_label)
    plot_adherence(df_label)
    plot_ai_use_shift(df_label, df_num)
    plot_session_length(df_label)

    # -- Step 10: tables ---------------------------------------------------
    say("\n[10] Writing tables...")
    write_frequency_tables(df_label)
    write_codebook_review(df_num)
    write_open_text(df_num)
    write_decoded_data(df_num, df_label)

    # -- Step 11: summary --------------------------------------------------
    from_instrument = sorted([q for q, c in cb.CONFIDENCE.items() if c == "instrument"],
                             key=lambda q: int(q[1:]))
    unconfirmed = sorted([q for q, c in cb.CONFIDENCE.items() if c != "instrument"],
                         key=lambda q: int(q[1:]))
    say("\n" + "=" * 72)
    say("  LABEL PROVENANCE")
    say("=" * 72)
    say(f"  From instrument (ME 140 questions.pdf, Appendix D): {', '.join(from_instrument)}")
    if unconfirmed:
        say(f"  Unconfirmed item identity: {', '.join(unconfirmed)}")
        say("    Q1's Qualtrics stem reads 'Did you find this explanation useful?',")
        say("    but the instrument lists item 1 as prior AI familiarity and the")
        say("    response pattern matches familiarity. Figures using it are stamped.")
        say(f"    Currently treated as familiarity: {cb.Q1_IS_FAMILIARITY}")
    say("  See outputs/me140_dec2025/codebook_review.csv for every mapping.")

    say("\n" + "=" * 72)
    say(f"  Analysis complete.  N = {N_TOTAL}")
    say(f"  Figures -> figures/me140_dec2025/")
    say(f"  Tables  -> outputs/me140_dec2025/")
    say("=" * 72 + "\n")

    with open(os.path.join(OUT_DIR, "analysis_summary.txt"), "w") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"  [saved] outputs/me140_dec2025/analysis_summary.txt")


if __name__ == "__main__":
    main()
