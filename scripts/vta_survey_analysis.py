"""
=============================================================================
VTA Survey Statistical Analysis
=============================================================================

Overview:
    This script analyses the Virtual TA (VTA) student survey (N=97) and
    produces a series of clearly labelled, publication-ready plots.

    It implements the exact chain of methods described in Statistical_methods.pdf:
      1. Descriptive frequency analysis          (Section 2)
      2. Chi-Square test + Cramér's V            (Sections 3 & 4)
      3. Benjamini-Hochberg FDR correction       (Section 5)
      4. Spearman rank correlation               (Section 6.1.1)
      5. Fisher's exact test + odds ratio        (Section 7)
      6. Mann-Whitney U test (two groups)        (Section 9.1)
      7. Kruskal-Wallis + Dunn post-hoc          (Section 9.2)

Major functions:
    load_and_clean_data()         – reads the Excel file and fixes known issues
    split_multiselect_column()    – expands semicolon-delimited multi-select answers
    compute_frequencies()         – counts and percentages for a single column
    run_chi_square()              – Chi-Square + Cramér's V for two categorical variables
    apply_fdr_correction()        – Benjamini-Hochberg FDR on a list of p-values
    run_spearman()                – Spearman rank correlation between two ordinal columns
    run_fisher_exact()            – Fisher's exact test + odds ratio for 2×2 tables
    run_mann_whitney()            – Mann-Whitney U for two independent ordinal groups
    run_kruskal_wallis()          – Kruskal-Wallis + Dunn post-hoc for 3+ groups
    plot_*()                      – one plotting function per figure

Execution flow (main):
    main() orchestrates all steps in the order defined in the PDF,
    saves every figure to "figures/engr 151 2026/", writes the result tables
    to outputs/engr_151/, and prints a results summary.

=============================================================================
"""

import os
import sys
import contextlib
import warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from scipy import stats
from scipy.stats import chi2_contingency, spearmanr, mannwhitneyu, kruskal, fisher_exact
from itertools import combinations

warnings.filterwarnings("ignore")

# ── Path configuration ─────────────────────────────────────────────────────
ROOT        = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH   = os.path.join(ROOT, "data", "Student Survey Did the Virtual TA help "
                                         "make your learning easier and more effective.xlsx")
OUTPUT_DIR  = os.path.join(ROOT, "figures", "engr 151 2026")   # figures
OUT_DIR     = os.path.join(ROOT, "outputs", "engr_151")        # result tables
ALPHA       = 0.05      # significance threshold used throughout

# Questions answered by ticking several boxes; stored semicolon-delimited.
MULTISELECT_COLS = [
    "For what learning or coursework-related purposes do you typically use AI tools? (Select all that apply.)",
    "What did you use the Virtual TA for? (Select all that apply.)",
    "Learning & understanding (select all that apply).",
    "Efficiency and workload (select all that apply)",
    "How did you use or perceive the FAQ materials provided during the course, which were generated from questions students asked to the VTA? (Select all that apply)",
]

# act_data columns 0-5 are the form's own bookkeeping, not survey answers.
NON_QUESTION_COLS = ["ID", "Start time", "Completion time", "Email", "Name",
                     "Last modified time"]

# ── Ordinal scale mappings (from cleaned_data sheet) ──────────────────────
FAMILIARITY_ORDER  = ["Low", "Moderate", "High", "Very HIgh"]
AI_BEFORE_ORDER    = ["Never", "A few times per semester",
                       "A few times per month", "A few times per week",
                       "Daily or almost daily"]
VTA_USE_ORDER      = ["Never",
                       "I was not aware of the course chatbot( Virtual TA)",
                       "1-2 times total",
                       "A few times per month",
                       "1-2 times per week",
                       "3+ times per week"]
SESSION_LEN_ORDER  = ["Less than 5 minutes", "5-15 minutes",
                       "15-30 minutes", "30-60 minutes", "More than 60 minutes"]
LIKERT_ORDER       = ["Strongly disagree", "Disagree", "Neutral",
                       "Agree", "Strongly agree"]

# ── Colour palette (colour-blind-friendly) ────────────────────────────────
COLORS = {
    "primary"   : "#2563EB",   # blue
    "secondary" : "#10B981",   # green
    "warning"   : "#F59E0B",   # amber
    "danger"    : "#EF4444",   # red
    "neutral"   : "#6B7280",   # grey
    "purple"    : "#7C3AED",
}
BAR_PALETTE = ["#2563EB", "#10B981", "#F59E0B", "#EF4444",
               "#7C3AED", "#EC4899", "#14B8A6"]


# =============================================================================
# DATA LOADING AND CLEANING
# =============================================================================

def load_and_clean_data(filepath):
    """
    Reads both sheets from the Excel workbook and applies basic cleaning.

    Parameters
    ----------
    filepath : str – full path to the .xlsx file

    Returns
    -------
    df_raw   : pd.DataFrame – the raw act_data sheet (all 25 columns)
    df_clean : pd.DataFrame – the pre-cleaned cleaned_data sheet (14 columns)
    """
    df_raw   = pd.read_excel(filepath, sheet_name="act_data")
    df_clean = pd.read_excel(filepath, sheet_name="cleaned_data")

    # Fix the known typo in Familiarity: "Very HIgh" → kept as-is to match
    # cleaned_data, but we strip stray whitespace everywhere.
    for df in [df_raw, df_clean]:
        for col in df.select_dtypes(include="object").columns:
            df[col] = df[col].str.strip()

    return df_raw, df_clean


def split_multiselect_column(series, separator=";"):
    """
    Expands a Series of semicolon-delimited multi-select strings into a flat
    list of individual option strings (one element per student choice).

    Parameters
    ----------
    series    : pd.Series – raw multi-select column
    separator : str       – delimiter used in the data (default ";")

    Returns
    -------
    all_choices : list[str] – every individual option selected across all rows
    """
    all_choices = []

    # Iterate over each student's combined response string
    for response in series.dropna():
        choices = [choice.strip() for choice in response.split(separator)]
        for choice in choices:
            if choice:   # skip empty strings left after trailing ";"
                all_choices.append(choice)

    return all_choices


def compute_frequencies(series, category_order=None):
    """
    Counts occurrences of each value and converts to percentages.

    Parameters
    ----------
    series         : pd.Series  – column to summarise
    category_order : list | None – optional ordering for the categories

    Returns
    -------
    freq_df : pd.DataFrame with columns ['Category', 'Count', 'Percentage']
    """
    counts = series.value_counts()

    if category_order is not None:
        # Keep only categories that actually appear in the data
        ordered = [c for c in category_order if c in counts.index]
        remaining = [c for c in counts.index if c not in ordered]
        counts = counts.reindex(ordered + remaining)

    total = counts.sum()
    freq_df = pd.DataFrame({
        "Category"   : counts.index,
        "Count"      : counts.values,
        "Percentage" : (counts.values / total * 100).round(1),
    })
    return freq_df.reset_index(drop=True)


# =============================================================================
# STATISTICAL TESTS
# =============================================================================

def run_chi_square(df, col_a, col_b):
    """
    Runs a Chi-Square test of independence and computes Cramér's V.

    Parameters
    ----------
    df    : pd.DataFrame
    col_a : str – first categorical column name
    col_b : str – second categorical column name

    Returns
    -------
    result : dict with keys chi2, p_value, dof, cramers_v, contingency_table
    """
    # Drop rows where either column is missing
    subset = df[[col_a, col_b]].dropna()
    contingency_table = pd.crosstab(subset[col_a], subset[col_b])

    chi2_stat, p_value, dof, expected = chi2_contingency(contingency_table)

    # Cramér's V formula: sqrt(chi2 / (N * min(r-1, c-1)))
    n = contingency_table.values.sum()
    rows, cols = contingency_table.shape
    cramers_v = np.sqrt(chi2_stat / (n * min(rows - 1, cols - 1)))

    return {
        "chi2"              : chi2_stat,
        "p_value"           : p_value,
        "dof"               : dof,
        "cramers_v"         : cramers_v,
        "contingency_table" : contingency_table,
        "expected"          : expected,
    }


def apply_fdr_correction(p_values):
    """
    Applies the Benjamini-Hochberg FDR correction to a list of raw p-values.

    Parameters
    ----------
    p_values : list[float] – raw p-values from multiple tests

    Returns
    -------
    adjusted_p : np.ndarray – BH-adjusted p-values (same order as input)
    is_sig     : np.ndarray – boolean array; True if adjusted p < ALPHA
    """
    m = len(p_values)
    # Sort p-values and remember their original positions
    sorted_indices = np.argsort(p_values)
    sorted_p       = np.array(p_values)[sorted_indices]

    # BH adjusted value at rank k: p(k) * m / k  (then enforce monotonicity)
    adjusted = np.zeros(m)
    for k, idx in enumerate(sorted_indices):
        rank        = k + 1          # 1-based rank
        raw_adjust  = sorted_p[k] * m / rank
        adjusted[idx] = raw_adjust

    # Enforce monotonicity: walk from largest rank downward
    adjusted_sorted_pos = np.argsort(sorted_indices)   # undo the sort
    running_min = 1.0
    for k in range(m - 1, -1, -1):
        idx = sorted_indices[k]
        adjusted[idx] = min(adjusted[idx], running_min)
        running_min = adjusted[idx]

    # Cap at 1.0
    adjusted = np.minimum(adjusted, 1.0)

    is_sig = adjusted < ALPHA
    return adjusted, is_sig


def run_spearman(df, col_a, col_b):
    """
    Computes the Spearman rank correlation between two ordinal columns.

    Parameters
    ----------
    df    : pd.DataFrame
    col_a : str – first ordinal column (numeric codes)
    col_b : str – second ordinal column (numeric codes)

    Returns
    -------
    result : dict with keys rho, p_value, n
    """
    subset = df[[col_a, col_b]].dropna()
    rho, p_value = spearmanr(subset[col_a], subset[col_b])
    return {"rho": rho, "p_value": p_value, "n": len(subset)}


def run_fisher_exact(contingency_2x2):
    """
    Runs Fisher's exact test on a 2×2 contingency table and returns the odds ratio.

    Parameters
    ----------
    contingency_2x2 : 2×2 array-like – observed counts [[a,b],[c,d]]

    Returns
    -------
    result : dict with keys odds_ratio, p_value
    """
    table = np.array(contingency_2x2)
    odds_ratio, p_value = fisher_exact(table)
    return {"odds_ratio": odds_ratio, "p_value": p_value}


def run_mann_whitney(group1_values, group2_values, group1_name="Group 1", group2_name="Group 2"):
    """
    Runs the Mann-Whitney U test comparing an ordinal outcome between two groups.

    Parameters
    ----------
    group1_values : array-like – ordinal scores for group 1
    group2_values : array-like – ordinal scores for group 2
    group1_name   : str – label for group 1 (used in the returned dict)
    group2_name   : str – label for group 2

    Returns
    -------
    result : dict with keys u_stat, p_value, group1_name, group2_name, n1, n2
    """
    u_stat, p_value = mannwhitneyu(group1_values, group2_values, alternative="two-sided")
    return {
        "u_stat"      : u_stat,
        "p_value"     : p_value,
        "group1_name" : group1_name,
        "group2_name" : group2_name,
        "n1"          : len(group1_values),
        "n2"          : len(group2_values),
    }


def run_kruskal_wallis(groups_dict):
    """
    Runs the Kruskal-Wallis test across three or more groups and, if significant,
    performs Dunn's pairwise post-hoc test with BH FDR correction.

    Parameters
    ----------
    groups_dict : dict[str, array-like] – group name → ordinal values

    Returns
    -------
    result : dict with keys h_stat, p_value, post_hoc (list of dicts, if significant)
    """
    group_names  = list(groups_dict.keys())
    group_arrays = [np.array(v) for v in groups_dict.values()]

    h_stat, p_value = kruskal(*group_arrays)

    post_hoc_results = []

    if p_value < ALPHA:
        # Dunn's test: compute pairwise standardised rank differences
        all_values = np.concatenate(group_arrays)
        all_ranks  = stats.rankdata(all_values)

        # Assign ranks back to each group
        start = 0
        group_ranks = {}
        for name, arr in zip(group_names, group_arrays):
            group_ranks[name] = all_ranks[start : start + len(arr)]
            start += len(arr)

        total_n = len(all_values)
        pairs = list(combinations(group_names, 2))

        raw_p_values = []
        pair_labels  = []

        # Compute z-statistic for each pair using Dunn's formula
        for name_i, name_j in pairs:
            ranks_i = group_ranks[name_i]
            ranks_j = group_ranks[name_j]
            ni = len(ranks_i)
            nj = len(ranks_j)
            mean_rank_i = np.mean(ranks_i)
            mean_rank_j = np.mean(ranks_j)

            # Standard error under Dunn's formula
            se = np.sqrt(
                (total_n * (total_n + 1) / 12.0) * (1.0 / ni + 1.0 / nj)
            )
            z_stat = (mean_rank_i - mean_rank_j) / se

            # Two-sided p-value from the normal distribution
            p = 2 * (1 - stats.norm.cdf(abs(z_stat)))
            raw_p_values.append(p)
            pair_labels.append((name_i, name_j))

        # Apply FDR correction to all pairwise p-values
        adjusted_p, is_sig = apply_fdr_correction(raw_p_values)

        for (name_i, name_j), raw_p, adj_p, sig in zip(
            pair_labels, raw_p_values, adjusted_p, is_sig
        ):
            post_hoc_results.append({
                "pair"       : f"{name_i} vs {name_j}",
                "raw_p"      : raw_p,
                "adjusted_p" : adj_p,
                "significant": sig,
            })

    return {
        "h_stat"    : h_stat,
        "p_value"   : p_value,
        "post_hoc"  : post_hoc_results,
    }


# =============================================================================
# PLOTTING FUNCTIONS
# =============================================================================

def ensure_output_dir(directory):
    """Creates the output directory if it does not already exist."""
    os.makedirs(directory, exist_ok=True)


def save_figure(fig, filename, output_dir=OUTPUT_DIR):
    """Saves a matplotlib figure to disk and closes it to free memory."""
    filepath = os.path.join(output_dir, filename)
    fig.savefig(filepath, dpi=150, bbox_inches="tight")
    plt.close(fig)
    # Log the repo-relative path so the run log carries no local home directory.
    print(f"  [saved] {os.path.relpath(filepath, ROOT)}")


def plot_vta_usage_frequency(df_clean):
    """
    Fig 1 – Bar chart of how often students used the VTA this semester.
    Shows count and percentage labels on each bar.
    """
    freq_df = compute_frequencies(df_clean["VTA_semester_use"], category_order=VTA_USE_ORDER)

    # Shorten long label for display
    freq_df["Category"] = freq_df["Category"].str.replace(
        "I was not aware of the course chatbot( Virtual TA)", "Not aware of VTA", regex=False
    )

    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.barh(freq_df["Category"], freq_df["Count"],
                   color=COLORS["primary"], edgecolor="white")

    # Add count and percentage labels at the end of each bar
    for bar, count, pct in zip(bars, freq_df["Count"], freq_df["Percentage"]):
        ax.text(
            bar.get_width() + 0.3, bar.get_y() + bar.get_height() / 2,
            f"n={count} ({pct}%)", va="center", fontsize=10
        )

    ax.set_xlabel("Number of Students", fontsize=12)
    ax.set_title(
        "Fig 1 – VTA Usage Frequency This Semester\n(N=97 students)",
        fontsize=13, fontweight="bold"
    )
    ax.set_xlim(0, freq_df["Count"].max() + 10)
    ax.invert_yaxis()
    ax.grid(axis="x", linestyle="--", alpha=0.4)
    fig.tight_layout()

    save_figure(fig, "fig01_vta_usage_frequency.png")


def plot_learning_understanding_benefits(df_raw):
    """
    Fig 2 – Horizontal bar chart of multi-select learning & understanding benefits.
    Each option is counted independently (students could select multiple).
    """
    col = "Learning & understanding (select all that apply)."
    all_choices = split_multiselect_column(df_raw[col])

    # Count each unique benefit option
    benefit_counts = pd.Series(all_choices).value_counts()

    # Shorten labels for readability
    label_map = {
        "The Virtual TA didn't affect my learning"                             : "No effect on learning",
        "The Virtual TA helped me understand course concepts more deeply"       : "Deeper concept understanding",
        "The Virtual TA helped me make connections across topics"               : "Connected topics better",
        "Using the Virtual TA made me more confident in this subject"           : "Gained subject confidence",
    }
    benefit_counts.index = [label_map.get(i, i) for i in benefit_counts.index]
    benefit_counts = benefit_counts.sort_values()

    total_students = len(df_raw[col].dropna())
    pct_values = (benefit_counts / total_students * 100).round(1)

    fig, ax = plt.subplots(figsize=(10, 5))
    colors = [COLORS["danger"] if "No effect" in label else COLORS["secondary"]
              for label in benefit_counts.index]
    bars = ax.barh(benefit_counts.index, benefit_counts.values,
                   color=colors, edgecolor="white")

    for bar, count, pct in zip(bars, benefit_counts.values, pct_values):
        ax.text(
            bar.get_width() + 0.4, bar.get_y() + bar.get_height() / 2,
            f"n={count} ({pct}%)", va="center", fontsize=10
        )

    ax.set_xlabel("Number of Selections (multi-select, N=97)", fontsize=11)
    ax.set_title(
        "Fig 2 – Learning & Understanding Benefits Reported\n"
        "(Multi-select; students could choose multiple options)",
        fontsize=13, fontweight="bold"
    )
    ax.set_xlim(0, benefit_counts.max() + 14)
    ax.grid(axis="x", linestyle="--", alpha=0.4)

    # Legend: green = positive, red = negative
    positive_patch = mpatches.Patch(color=COLORS["secondary"], label="Positive benefit")
    negative_patch = mpatches.Patch(color=COLORS["danger"],    label="No / neutral effect")
    ax.legend(handles=[positive_patch, negative_patch], loc="lower right")

    fig.tight_layout()
    save_figure(fig, "fig02_learning_understanding_benefits.png")


def plot_efficiency_benefits(df_raw):
    """
    Fig 3 – Horizontal bar chart of multi-select efficiency & workload benefits.
    """
    col = "Efficiency and workload (select all that apply)"
    all_choices = split_multiselect_column(df_raw[col])

    benefit_counts = pd.Series(all_choices).value_counts()

    label_map = {
        "None of the Above"                                                                        : "No efficiency benefit",
        "The Virtual TA reduced the amount of time I felt stuck on problems."                       : "Less time stuck",
        "The Virtual TA helped me complete my homework or studying more efficiently"                 : "More efficient studying",
        "The Virtual TA saved me time overall in this course."                                      : "Saved overall time",
        "Because of the Virtual TA, I can spend less time using other resources (office hours, peers, internet, etc)": "Replaced other resources",
    }
    benefit_counts.index = [label_map.get(i, i) for i in benefit_counts.index]
    benefit_counts = benefit_counts.sort_values()

    total_students = len(df_raw[col].dropna())
    pct_values = (benefit_counts / total_students * 100).round(1)

    fig, ax = plt.subplots(figsize=(10, 5))
    colors = [COLORS["danger"] if "No efficiency" in label else COLORS["warning"]
              for label in benefit_counts.index]
    bars = ax.barh(benefit_counts.index, benefit_counts.values,
                   color=colors, edgecolor="white")

    for bar, count, pct in zip(bars, benefit_counts.values, pct_values):
        ax.text(
            bar.get_width() + 0.3, bar.get_y() + bar.get_height() / 2,
            f"n={count} ({pct}%)", va="center", fontsize=10
        )

    ax.set_xlabel("Number of Selections (multi-select, N=97)", fontsize=11)
    ax.set_title(
        "Fig 3 – Efficiency & Workload Benefits Reported\n"
        "(Multi-select; students could choose multiple options)",
        fontsize=13, fontweight="bold"
    )
    ax.set_xlim(0, benefit_counts.max() + 12)
    ax.grid(axis="x", linestyle="--", alpha=0.4)

    positive_patch = mpatches.Patch(color=COLORS["warning"], label="Efficiency benefit")
    negative_patch = mpatches.Patch(color=COLORS["danger"],  label="No benefit")
    ax.legend(handles=[positive_patch, negative_patch], loc="lower right")

    fig.tight_layout()
    save_figure(fig, "fig03_efficiency_benefits.png")


def plot_likert_quality_concern(df_raw):
    """
    Fig 4 – Diverging stacked bar chart for the Likert quality-concern item
    ("I sometimes encountered unclear / incorrect responses from the VTA").
    """
    col = "I sometimes encountered responses from the Virtual TA that were unclear, incomplete, or incorrect."
    freq_df = compute_frequencies(df_raw[col], category_order=LIKERT_ORDER)

    # Assign colours from negative (red) to positive (blue) for a diverging look
    bar_colors = ["#EF4444", "#F97316", "#9CA3AF", "#60A5FA", "#2563EB"]

    fig, ax = plt.subplots(figsize=(9, 4))
    bars = ax.bar(freq_df["Category"], freq_df["Percentage"],
                  color=bar_colors, edgecolor="white", width=0.6)

    for bar, pct, cnt in zip(bars, freq_df["Percentage"], freq_df["Count"]):
        ax.text(
            bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
            f"{pct}%\n(n={cnt})", ha="center", va="bottom", fontsize=10
        )

    ax.set_ylabel("Percentage of Students (%)", fontsize=11)
    ax.set_title(
        "Fig 4 – Perceived Quality Concerns with VTA Responses\n"
        "\"I sometimes encountered responses that were unclear, incomplete, or incorrect.\"",
        fontsize=12, fontweight="bold"
    )
    ax.set_ylim(0, freq_df["Percentage"].max() + 10)
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    fig.tight_layout()
    save_figure(fig, "fig04_likert_quality_concern.png")


def plot_recommendation_vs_desire(df_raw):
    """
    Fig 5 – Side-by-side bar chart comparing:
      - Would you RECOMMEND future students use the VTA?
      - Would you LIKE to have a VTA in other courses?
    """
    col_recommend = "Would you recommend future students in this course make active use of the Virtual TA?"
    col_desire    = "Would you like to have a Virtual TA (or something similar) in other technical courses?"
    response_order = ["Yes", "Maybe", "Not sure / It depends on the design", "No"]

    recommend_counts = df_raw[col_recommend].value_counts().reindex(response_order, fill_value=0)
    desire_counts    = df_raw[col_desire   ].value_counts().reindex(response_order, fill_value=0)

    n_groups = len(response_order)
    x = np.arange(n_groups)
    bar_width = 0.35

    fig, ax = plt.subplots(figsize=(10, 5))
    bars_a = ax.bar(x - bar_width / 2, recommend_counts.values,
                    width=bar_width, label="Recommend to future students",
                    color=COLORS["primary"], edgecolor="white")
    bars_b = ax.bar(x + bar_width / 2, desire_counts.values,
                    width=bar_width, label="Want VTA in other courses",
                    color=COLORS["secondary"], edgecolor="white")

    # Label each bar with its count
    for bar in list(bars_a) + list(bars_b):
        height = bar.get_height()
        if height > 0:
            ax.text(
                bar.get_x() + bar.get_width() / 2, height + 0.5,
                str(int(height)), ha="center", va="bottom", fontsize=10
            )

    ax.set_xticks(x)
    ax.set_xticklabels(response_order, fontsize=10)
    ax.set_ylabel("Number of Students", fontsize=11)
    ax.set_title(
        "Fig 5 – Student Endorsement and Desire for the VTA\n"
        "(N=97; two separate questions)",
        fontsize=13, fontweight="bold"
    )
    ax.legend(fontsize=10)
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    fig.tight_layout()
    save_figure(fig, "fig05_recommendation_vs_desire.png")


def plot_spearman_heatmap(spearman_results):
    """
    Fig 6 – Heatmap of Spearman ρ values between ordinal survey variables.
    Cells are annotated with ρ and a significance star if p < 0.05.

    Parameters
    ----------
    spearman_results : list[dict] – output from multiple run_spearman() calls
    """
    # Collect unique variable labels
    labels = sorted(set(
        r["col_a_label"] for r in spearman_results
    ) | set(
        r["col_b_label"] for r in spearman_results
    ))
    n = len(labels)
    label_index = {label: i for i, label in enumerate(labels)}

    # Build a matrix of ρ values (NaN on diagonal and untested pairs)
    rho_matrix = np.full((n, n), np.nan)
    np.fill_diagonal(rho_matrix, 1.0)

    for r in spearman_results:
        i = label_index[r["col_a_label"]]
        j = label_index[r["col_b_label"]]
        rho_matrix[i, j] = r["rho"]
        rho_matrix[j, i] = r["rho"]

    fig, ax = plt.subplots(figsize=(8, 6))
    im = ax.imshow(rho_matrix, cmap="RdYlGn", vmin=-1, vmax=1, aspect="auto")

    plt.colorbar(im, ax=ax, label="Spearman ρ")

    # Annotate each cell with the ρ value (and * if significant)
    for r in spearman_results:
        i = label_index[r["col_a_label"]]
        j = label_index[r["col_b_label"]]
        star = "*" if r["p_value"] < ALPHA else ""
        cell_value = f"{r['rho']:.2f}{star}"
        ax.text(j, i, cell_value, ha="center", va="center", fontsize=9, color="black")
        ax.text(i, j, cell_value, ha="center", va="center", fontsize=9, color="black")

    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    ax.set_xticklabels(labels, rotation=30, ha="right", fontsize=9)
    ax.set_yticklabels(labels, fontsize=9)
    ax.set_title(
        "Fig 6 – Spearman Rank Correlations Between Ordinal Survey Variables\n"
        "(*  p < 0.05; green = positive, red = negative association)",
        fontsize=12, fontweight="bold"
    )
    fig.tight_layout()
    save_figure(fig, "fig06_spearman_heatmap.png")


def plot_chi_square_summary(chi_sq_results, fdr_adjusted_p):
    """
    Fig 7 – Dot-plot summarising Chi-Square results with Cramér's V and FDR p-values.
    Each row is one test; colour codes significance after FDR correction.

    Parameters
    ----------
    chi_sq_results  : list[dict] – output from multiple run_chi_square() calls
    fdr_adjusted_p  : np.ndarray – BH-adjusted p-values in the same order
    """
    labels   = [r["label"]    for r in chi_sq_results]
    cramers  = [r["cramers_v"] for r in chi_sq_results]
    p_raw    = [r["p_value"]   for r in chi_sq_results]
    p_adj    = list(fdr_adjusted_p)
    sig_mask = [p < ALPHA for p in p_adj]

    fig, axes = plt.subplots(1, 2, figsize=(13, 5))

    # Left panel – Cramér's V (effect size)
    ax = axes[0]
    colors = [COLORS["primary"] if s else COLORS["neutral"] for s in sig_mask]
    bars = ax.barh(labels, cramers, color=colors, edgecolor="white")
    ax.axvline(0.10, color="gray",        linestyle="--", alpha=0.6, label="Weak (0.10)")
    ax.axvline(0.30, color=COLORS["warning"], linestyle="--", alpha=0.8, label="Moderate (0.30)")
    ax.axvline(0.50, color=COLORS["danger"],  linestyle="--", alpha=0.8, label="Strong (0.50)")
    for bar, v in zip(bars, cramers):
        ax.text(bar.get_width() + 0.005, bar.get_y() + bar.get_height() / 2,
                f"{v:.3f}", va="center", fontsize=9)
    ax.set_xlabel("Cramér's V (Effect Size)", fontsize=11)
    ax.set_title("Effect Size (Cramér's V)", fontsize=12, fontweight="bold")
    ax.legend(fontsize=8, loc="lower right")
    ax.set_xlim(0, max(cramers) + 0.12)
    ax.invert_yaxis()
    ax.grid(axis="x", linestyle="--", alpha=0.3)

    # Right panel – raw vs BH-adjusted p-values (log scale)
    ax2 = axes[1]
    y_pos = np.arange(len(labels))
    ax2.scatter(p_raw, y_pos, color=COLORS["neutral"],  label="Raw p-value",      zorder=3, s=60)
    ax2.scatter(p_adj, y_pos, color=COLORS["primary"],  label="BH-adjusted p",    zorder=4, s=80, marker="D")
    ax2.axvline(ALPHA, color=COLORS["danger"], linestyle="--", label=f"α = {ALPHA}")
    ax2.set_xscale("log")
    ax2.set_yticks(y_pos)
    ax2.set_yticklabels(labels, fontsize=9)
    ax2.set_xlabel("p-value (log scale)", fontsize=11)
    ax2.set_title("Raw vs BH FDR-Adjusted p-Values", fontsize=12, fontweight="bold")
    ax2.legend(fontsize=9)
    ax2.invert_yaxis()
    ax2.grid(axis="x", linestyle="--", alpha=0.3)

    fig.suptitle(
        "Fig 7 – Chi-Square Test Summary with Cramér's V and FDR Correction\n"
        "(Blue bars/dots = significant after BH FDR correction; grey = not significant)",
        fontsize=12, fontweight="bold", y=1.01
    )
    fig.tight_layout()
    save_figure(fig, "fig07_chi_square_summary.png")


def plot_vta_usage_by_academic_level(df_clean):
    """
    Fig 8 – Grouped bar chart of VTA intensity score by academic level,
    showing median and interquartile range alongside the Kruskal-Wallis result.
    """
    # Compute median and IQR for each academic level group
    level_groups = df_clean.groupby("Level")["VTA_freq/intensity"]

    levels = ["Sophomore", "Junior", "Senior"]
    medians = []
    q1_vals = []
    q3_vals = []

    for level in levels:
        group_data = df_clean[df_clean["Level"] == level]["VTA_freq/intensity"].dropna()
        medians.append(np.median(group_data))
        q1_vals.append(np.percentile(group_data, 25))
        q3_vals.append(np.percentile(group_data, 75))

    # Run the Kruskal-Wallis test to display the result on the plot
    groups_dict = {
        level: df_clean[df_clean["Level"] == level]["VTA_freq/intensity"].dropna().values
        for level in levels
    }
    kw_result = run_kruskal_wallis(groups_dict)

    fig, ax = plt.subplots(figsize=(8, 5))
    x = np.arange(len(levels))
    bars = ax.bar(x, medians, color=BAR_PALETTE[:3], edgecolor="white", width=0.5)

    # Draw IQR error bars manually (Q1 to Q3)
    for i, (med, q1, q3) in enumerate(zip(medians, q1_vals, q3_vals)):
        ax.plot([i, i], [q1, q3], color="black", linewidth=2)
        ax.plot([i - 0.1, i + 0.1], [q1, q1], color="black", linewidth=2)
        ax.plot([i - 0.1, i + 0.1], [q3, q3], color="black", linewidth=2)

    ax.set_xticks(x)
    ax.set_xticklabels(levels, fontsize=12)
    ax.set_ylabel("VTA Frequency / Intensity (Ordinal 0–4)", fontsize=11)
    ax.set_title(
        "Fig 8 – VTA Usage Intensity by Academic Level\n"
        "(Bars = median; error bars = IQR Q1–Q3)",
        fontsize=13, fontweight="bold"
    )

    # Annotate with Kruskal-Wallis result
    sig_text = f"Kruskal-Wallis H={kw_result['h_stat']:.2f}, p={kw_result['p_value']:.3f}"
    sig_text += "  (significant)" if kw_result["p_value"] < ALPHA else "  (not significant)"
    ax.text(0.5, 0.95, sig_text,
            transform=ax.transAxes, ha="center", va="top",
            fontsize=9, color=COLORS["danger"] if kw_result["p_value"] < ALPHA else COLORS["neutral"],
            bbox=dict(boxstyle="round,pad=0.3", facecolor="lightyellow", alpha=0.8))

    ax.set_ylim(0, max(q3_vals) + 0.6)
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    fig.tight_layout()
    save_figure(fig, "fig08_vta_usage_by_level.png")


def plot_mann_whitney_quality_concern(df_raw, df_clean):
    """
    Fig 9 – Box-plot + strip-plot comparing the quality-concern Likert score
    between students who reported deeper understanding vs those who did not.
    Mann-Whitney U result is annotated on the plot.
    """
    # Encode the quality-concern Likert column as an ordinal integer 1–5
    likert_col = "I sometimes encountered responses from the Virtual TA that were unclear, incomplete, or incorrect."
    likert_encode = {label: i + 1 for i, label in enumerate(LIKERT_ORDER)}
    df_raw["likert_score"] = df_raw[likert_col].map(likert_encode)

    # Define the binary grouping: reported deeper understanding = yes / no
    understanding_col = "Learning & understanding (select all that apply)."
    df_raw["deeper_understanding"] = df_raw[understanding_col].str.contains(
        "helped me understand course concepts more deeply", na=False
    )

    group_yes = df_raw[df_raw["deeper_understanding"] == True]["likert_score"].dropna()
    group_no  = df_raw[df_raw["deeper_understanding"] == False]["likert_score"].dropna()

    mw_result = run_mann_whitney(
        group_yes.values, group_no.values,
        group1_name="Reported deeper\nunderstanding",
        group2_name="Did NOT report\ndeeper understanding"
    )

    fig, ax = plt.subplots(figsize=(7, 5))

    # Box plots for each group
    data_to_plot = [group_yes.values, group_no.values]
    group_labels  = ["Deeper\nunderstanding\n(Yes)", "Deeper\nunderstanding\n(No)"]
    bp = ax.boxplot(data_to_plot, labels=group_labels, patch_artist=True,
                    medianprops=dict(color="black", linewidth=2))

    box_colors = [COLORS["secondary"], COLORS["danger"]]
    for patch, color in zip(bp["boxes"], box_colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.6)

    # Jitter raw data points over the boxes
    for i, group_data in enumerate(data_to_plot, start=1):
        jitter = np.random.uniform(-0.08, 0.08, size=len(group_data))
        ax.scatter(np.full(len(group_data), i) + jitter, group_data,
                   alpha=0.4, s=20, color="black", zorder=3)

    ax.set_ylabel("Quality-Concern Likert Score (1=Strongly Disagree, 5=Strongly Agree)", fontsize=9)
    ax.set_title(
        "Fig 9 – Quality Concern by Reported Deeper Understanding\n"
        "(Mann-Whitney U Test)",
        fontsize=12, fontweight="bold"
    )

    sig_text = (
        f"Mann-Whitney U = {mw_result['u_stat']:.1f}, p = {mw_result['p_value']:.3f}\n"
        f"n₁ = {mw_result['n1']}, n₂ = {mw_result['n2']}"
    )
    ax.text(0.97, 0.97, sig_text, transform=ax.transAxes,
            ha="right", va="top", fontsize=9,
            bbox=dict(boxstyle="round,pad=0.3", facecolor="lightyellow", alpha=0.8))

    ax.set_ylim(0.5, 5.8)
    ax.set_yticks([1, 2, 3, 4, 5])
    ax.set_yticklabels(LIKERT_ORDER, fontsize=8)
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    fig.tight_layout()
    save_figure(fig, "fig09_mann_whitney_quality_concern.png")


def plot_study_strategies(df_raw):
    """
    Fig 10 – Horizontal bar chart for study strategy responses (single-select).
    """
    col = "Study Strategies"
    freq_df = compute_frequencies(df_raw[col])
    freq_df = freq_df.sort_values("Count")

    label_map = {
        "I used the Virtual TA mainly after trying problems on my own."                     : "Used VTA after self-attempt",
        "I used the Virtual TA mainly before trying problems on my own."                    : "Used VTA before self-attempt",
        "I sometimes accepted the Virtual TA's answers without critically evlaluating them.": "Accepted answers uncritically",
        "Using Virtual TA encouraged me to attempt more challenging problems."               : "Attempted harder problems",
        "Using the Virtual TA made me more likely to postpone starting homework (procrastinate).": "Led to procrastination",
    }
    freq_df["Category"] = freq_df["Category"].map(label_map).fillna(freq_df["Category"])

    fig, ax = plt.subplots(figsize=(10, 5))
    colors = [COLORS["secondary"] if "after" in cat else
              COLORS["warning"]   if "harder" in cat else
              COLORS["danger"]    for cat in freq_df["Category"]]
    bars = ax.barh(freq_df["Category"], freq_df["Count"],
                   color=colors, edgecolor="white")

    for bar, count, pct in zip(bars, freq_df["Count"], freq_df["Percentage"]):
        ax.text(
            bar.get_width() + 0.3, bar.get_y() + bar.get_height() / 2,
            f"n={count} ({pct}%)", va="center", fontsize=10
        )

    ax.set_xlabel("Number of Students", fontsize=11)
    ax.set_title(
        "Fig 10 – Self-Reported Study Strategies When Using the VTA\n(N=97, single-select)",
        fontsize=13, fontweight="bold"
    )
    ax.set_xlim(0, freq_df["Count"].max() + 16)
    ax.grid(axis="x", linestyle="--", alpha=0.4)
    fig.tight_layout()
    save_figure(fig, "fig10_study_strategies.png")


def plot_adherence(df_raw):
    """
    Fig 11 – Pie chart of self-reported adherence to course rules.
    """
    col = "Self-reported adherence."
    freq_df = compute_frequencies(df_raw[col])
    freq_df = freq_df.sort_values("Count", ascending=False)

    label_map = {
        "I always used the Virtual TA in ways that I believe are consistent with the course rules."             : "Always rule-compliant",
        "I have used AI mainly to check or improve work I already did myself."                                  : "Used to improve own work",
        "I sometimes used the Virtual TA (or other AI tools) in ways that I suspect the instructor might not approve of.": "Possibly not approved",
        "I have used AI to generate solutions that I submitted with minimal modification."                       : "Submitted AI output directly",
    }
    freq_df["Category"] = freq_df["Category"].map(label_map).fillna(freq_df["Category"])

    pie_colors = [COLORS["secondary"], COLORS["primary"], COLORS["warning"], COLORS["danger"]]
    labels = [f"{cat}\n(n={cnt}, {pct}%)"
              for cat, cnt, pct in zip(freq_df["Category"], freq_df["Count"], freq_df["Percentage"])]

    fig, ax = plt.subplots(figsize=(8, 6))
    wedges, _ = ax.pie(freq_df["Count"], colors=pie_colors[:len(freq_df)],
                       startangle=140, wedgeprops=dict(edgecolor="white", linewidth=2))
    ax.legend(wedges, labels, loc="center left", bbox_to_anchor=(1, 0.5),
              fontsize=9, title="Adherence category")
    ax.set_title(
        "Fig 11 – Self-Reported Adherence to Course Rules\n(N=97 students)",
        fontsize=13, fontweight="bold"
    )
    fig.tight_layout()
    save_figure(fig, "fig11_adherence_pie.png")


# =============================================================================
# TABLE OUTPUTS
# =============================================================================

def multiselect_frequencies(series):
    """
    Frequency table for a semicolon-delimited multi-select column.

    Percentages use the number of *respondents* to the item as denominator,
    not the number of ticks, so they sum to more than 100 by design.
    """
    choices = split_multiselect_column(series)
    n_resp  = int(series.dropna().shape[0])
    counts  = pd.Series(choices).value_counts()

    return pd.DataFrame({
        "Category"  : counts.index,
        "Count"     : counts.values,
        "Percentage": (counts.values / n_resp * 100).round(1) if n_resp else 0,
    }), n_resp


def write_frequency_tables(df_raw):
    """
    Writes one tidy CSV holding the frequency table for every survey question,
    plus the per-question response count.
    """
    ensure_output_dir(OUT_DIR)
    question_cols = [c for c in df_raw.columns if c not in NON_QUESTION_COLS]

    frames = []
    for col in question_cols:
        if col in MULTISELECT_COLS:
            tbl, n_resp = multiselect_frequencies(df_raw[col])
            kind = "multi-select"
        else:
            tbl = compute_frequencies(df_raw[col])
            n_resp = int(df_raw[col].notna().sum())
            kind = "single-select"
        tbl.insert(0, "Question_text", col)
        tbl.insert(1, "Type", kind)
        tbl.insert(2, "N_respondents", n_resp)
        frames.append(tbl)

    out = pd.concat(frames, ignore_index=True)
    out.to_csv(os.path.join(OUT_DIR, "frequency_tables.csv"), index=False)
    print(f"    [saved] outputs/engr_151/frequency_tables.csv  ({len(out)} rows)")
    return out


def write_analysis_sample(df_raw, df_clean):
    """
    Writes the analysis sample twice: the labelled answer text as collected,
    and the ordinal recoding the tests actually run on.
    """
    ensure_output_dir(OUT_DIR)
    keep = ["ID"] + [c for c in df_raw.columns if c not in NON_QUESTION_COLS]
    df_raw[keep].to_csv(
        os.path.join(OUT_DIR, "analysis_sample_labeled.csv"), index=False)

    # clarity/understanding are empty in the source workbook; drop them rather
    # than ship two all-NaN columns.
    numeric = df_clean.drop(columns=[c for c in ["clarity", "understanding"]
                                     if c in df_clean.columns])
    numeric.to_csv(
        os.path.join(OUT_DIR, "analysis_sample_numeric.csv"), index=False)
    print(f"    [saved] outputs/engr_151/analysis_sample_labeled.csv "
          f"and analysis_sample_numeric.csv  (N={len(df_raw)})")


def write_chi_square_results(chi_sq_results, adjusted_p, is_sig):
    """Writes the chi-square suite with its BH-adjusted p-values."""
    ensure_output_dir(OUT_DIR)
    rows = []
    for res, adj_p, sig in zip(chi_sq_results, adjusted_p, is_sig):
        rows.append({
            "Test"                  : res["label"],
            "chi2"                  : round(res["chi2"], 4),
            "dof"                   : res["dof"],
            "n"                     : int(res["contingency_table"].values.sum()),
            "p_raw"                 : res["p_value"],
            "p_BH_adjusted"         : adj_p,
            "cramers_v"             : round(res["cramers_v"], 4),
            "min_expected_count"    : round(float(res["expected"].min()), 2),
            "significant_after_FDR" : bool(sig),
        })
    pd.DataFrame(rows).to_csv(
        os.path.join(OUT_DIR, "chi_square_results.csv"), index=False)
    print(f"    [saved] outputs/engr_151/chi_square_results.csv  ({len(rows)} tests)")


def write_spearman_results(spearman_results):
    """Writes every Spearman pair with rho, p and the pairwise n."""
    ensure_output_dir(OUT_DIR)
    rows = [{
        "Variable_A"   : r["col_a_label"],
        "Variable_B"   : r["col_b_label"],
        "spearman_rho" : round(r["rho"], 4),
        "p_value"      : r["p_value"],
        "n"            : r["n"],
        "significant"  : bool(r["p_value"] < ALPHA),
    } for r in spearman_results]
    pd.DataFrame(rows).to_csv(
        os.path.join(OUT_DIR, "spearman_results.csv"), index=False)
    print(f"    [saved] outputs/engr_151/spearman_results.csv  ({len(rows)} pairs)")


def write_other_test_results(fisher_result, mw_result, kw_result):
    """Writes the tests that do not belong to the chi-square or Spearman suites."""
    ensure_output_dir(OUT_DIR)
    rows = []
    if fisher_result:
        rows.append({"Test": "Fisher exact: VTA use vs learning benefit",
                     "Statistic": "odds ratio",
                     "Value": round(fisher_result["odds_ratio"], 4),
                     "p_value": fisher_result["p_value"]})
    if mw_result:
        n1, n2 = mw_result["n1"], mw_result["n2"]
        rows.append({"Test": "Mann-Whitney U: quality concern by deeper understanding",
                     "Statistic": "U",
                     "Value": float(mw_result["u_stat"]),
                     "p_value": mw_result["p_value"]})
        # rank-biserial r = 2U/(n1*n2) - 1, the effect size paired with U
        rows.append({"Test": "Mann-Whitney effect size",
                     "Statistic": "rank-biserial r",
                     "Value": round(2 * mw_result["u_stat"] / (n1 * n2) - 1, 4)
                              if n1 and n2 else "",
                     "p_value": ""})
    if kw_result:
        rows.append({"Test": "Kruskal-Wallis: VTA intensity by academic level",
                     "Statistic": "H",
                     "Value": round(kw_result["h_stat"], 4),
                     "p_value": kw_result["p_value"]})
        for ph in kw_result["post_hoc"]:
            rows.append({"Test": f"Dunn post-hoc: {ph['pair']}",
                         "Statistic": "BH-adjusted p",
                         "Value": round(ph["adjusted_p"], 4),
                         "p_value": ph["raw_p"]})
    pd.DataFrame(rows).to_csv(
        os.path.join(OUT_DIR, "other_test_results.csv"), index=False)
    print(f"    [saved] outputs/engr_151/other_test_results.csv  ({len(rows)} rows)")


class _Tee:
    """
    Mirrors everything printed during a run into a buffer, so the console log
    can be saved verbatim as outputs/engr_151/analysis_summary.txt.
    """

    def __init__(self, stream):
        self._stream = stream
        self.parts = []

    def write(self, text):
        self._stream.write(text)
        self.parts.append(text)

    def flush(self):
        self._stream.flush()


# =============================================================================
# MAIN FUNCTION
# =============================================================================

def main():
    """
    Orchestrates the full analysis pipeline:
      1. Load and clean data
      2. Run all statistical tests
      3. Apply FDR correction across Chi-Square p-values
      4. Generate and save all figures
      5. Print a results summary
    """
    ensure_output_dir(OUTPUT_DIR)
    print("\n" + "=" * 60)
    print("  VTA Survey Statistical Analysis")
    print("=" * 60)

    # ── Step 1: Load data ─────────────────────────────────────────
    print("\n[1] Loading data...")
    df_raw, df_clean = load_and_clean_data(DATA_PATH)
    print(f"    Raw data:     {df_raw.shape[0]} rows, {df_raw.shape[1]} columns")
    print(f"    Cleaned data: {df_clean.shape[0]} rows, {df_clean.shape[1]} columns")

    # ── Step 2: Chi-Square tests (6 tests as described in the PDF) ─
    print("\n[2] Running Chi-Square tests + Cramér's V...")

    # Map VTA usage to binary: "used" vs "never/unaware"
    df_clean["vta_used_binary"] = df_clean["VTA_freq/intensity"].apply(
        lambda x: "Used VTA" if x > 0 else "Never / Unaware"
    )

    # Map benefit to binary from raw data
    col_learn = "Learning & understanding (select all that apply)."
    df_raw["benefit_learning"] = df_raw[col_learn].str.contains(
        "helped me understand course concepts more deeply", na=False
    ).map({True: "Reported benefit", False: "No benefit"})

    col_eff = "Efficiency and workload (select all that apply)"
    df_raw["benefit_efficiency"] = df_raw[col_eff].str.contains(
        "None of the Above", na=False
    ).map({True: "No efficiency benefit", False: "Efficiency benefit"})

    # Merge binary flags into df_clean for joint analysis
    df_clean["benefit_learning"]   = df_raw["benefit_learning"].values
    df_clean["benefit_efficiency"]  = df_raw["benefit_efficiency"].values

    # Define the 6 Chi-Square tests (label, col_a, col_b)
    chi_square_tests = [
        ("VTA Use vs Learning Benefit",
         "vta_used_binary", "benefit_learning"),
        ("VTA Use vs Efficiency Benefit",
         "vta_used_binary", "benefit_efficiency"),
        ("Academic Level vs VTA Use",
         "Level", "vta_used_binary"),
        ("Familiarity vs VTA Use",
         "Familiarity", "vta_used_binary"),
        ("Academic Level vs Learning Benefit",
         "Level", "benefit_learning"),
        ("Familiarity vs Learning Benefit",
         "Familiarity", "benefit_learning"),
    ]

    chi_sq_results = []
    raw_p_values   = []

    for label, col_a, col_b in chi_square_tests:
        result = run_chi_square(df_clean, col_a, col_b)
        result["label"] = label
        chi_sq_results.append(result)
        raw_p_values.append(result["p_value"])
        print(f"    {label}: χ²={result['chi2']:.2f}, p={result['p_value']:.4f}, "
              f"V={result['cramers_v']:.3f}")

    # ── Step 3: FDR correction ─────────────────────────────────────
    print("\n[3] Applying Benjamini-Hochberg FDR correction...")
    adjusted_p, is_sig = apply_fdr_correction(raw_p_values)
    for i, (label, adj_p, sig) in enumerate(zip(
        [r["label"] for r in chi_sq_results], adjusted_p, is_sig
    )):
        status = "SIGNIFICANT" if sig else "not significant"
        print(f"    [{i+1}] {label}: adj_p={adj_p:.4f}  → {status}")

    # ── Step 4: Spearman correlations ──────────────────────────────
    print("\n[4] Running Spearman rank correlations...")

    spearman_pairs = [
        ("VTA_freq/intensity", "VTA_session_len_ord",
         "VTA Intensity",      "Session Length"),
        ("VTA_freq/intensity", "Familiarity_ord",
         "VTA Intensity",      "Prior Familiarity"),
        ("VTA_freq/intensity", "AI_before_ord",
         "VTA Intensity",      "Pre-course AI Use"),
        ("AI_before_ord",      "Familiarity_ord",
         "Pre-course AI Use",  "Prior Familiarity"),
        ("VTA_session_len_ord", "Familiarity_ord",
         "Session Length",      "Prior Familiarity"),
    ]

    spearman_results = []
    for col_a, col_b, label_a, label_b in spearman_pairs:
        result = run_spearman(df_clean, col_a, col_b)
        result["col_a_label"] = label_a
        result["col_b_label"] = label_b
        spearman_results.append(result)
        sig = "*" if result["p_value"] < ALPHA else ""
        print(f"    {label_a} vs {label_b}: ρ={result['rho']:.3f}, "
              f"p={result['p_value']:.4f} {sig}")

    # ── Step 5: Fisher's exact test ────────────────────────────────
    print("\n[5] Running Fisher's exact test (VTA use vs Learning benefit)...")

    ct = pd.crosstab(df_clean["vta_used_binary"], df_clean["benefit_learning"])
    # Ensure the 2×2 shape is correct
    if ct.shape == (2, 2):
        fisher_result = run_fisher_exact(ct.values)
        print(f"    Odds Ratio = {fisher_result['odds_ratio']:.2f}, "
              f"p = {fisher_result['p_value']:.4f}")
    else:
        print(f"    Contingency table shape {ct.shape} is not 2×2; skipping.")
        fisher_result = None

    # ── Step 6: Mann-Whitney U ─────────────────────────────────────
    print("\n[6] Running Mann-Whitney U (quality concern by understanding group)...")

    likert_col = "I sometimes encountered responses from the Virtual TA that were unclear, incomplete, or incorrect."
    likert_encode = {label: i + 1 for i, label in enumerate(LIKERT_ORDER)}
    df_raw["likert_score"] = df_raw[likert_col].map(likert_encode)

    df_raw["deeper_understanding"] = df_raw[
        "Learning & understanding (select all that apply)."
    ].str.contains("helped me understand course concepts more deeply", na=False)

    group_yes = df_raw[df_raw["deeper_understanding"] == True]["likert_score"].dropna()
    group_no  = df_raw[df_raw["deeper_understanding"] == False]["likert_score"].dropna()

    mw_result = run_mann_whitney(group_yes.values, group_no.values,
                                 "Deeper understanding (Yes)", "Deeper understanding (No)")
    print(f"    U = {mw_result['u_stat']:.1f}, p = {mw_result['p_value']:.4f}")

    # ── Step 7: Kruskal-Wallis ─────────────────────────────────────
    print("\n[7] Running Kruskal-Wallis (VTA intensity by academic level)...")

    levels = ["Sophomore", "Junior", "Senior"]
    groups_dict = {
        level: df_clean[df_clean["Level"] == level]["VTA_freq/intensity"].dropna().values
        for level in levels
    }
    kw_result = run_kruskal_wallis(groups_dict)
    print(f"    H = {kw_result['h_stat']:.2f}, p = {kw_result['p_value']:.4f}")

    if kw_result["post_hoc"]:
        print("    Post-hoc Dunn's test (BH FDR-corrected):")
        for ph in kw_result["post_hoc"]:
            sig = "SIGNIFICANT" if ph["significant"] else "not significant"
            print(f"      {ph['pair']}: adj_p={ph['adjusted_p']:.4f} → {sig}")

    # ── Step 8: Generate all plots ─────────────────────────────────
    print("\n[8] Generating plots...")

    plot_vta_usage_frequency(df_clean)
    plot_learning_understanding_benefits(df_raw)
    plot_efficiency_benefits(df_raw)
    plot_likert_quality_concern(df_raw)
    plot_recommendation_vs_desire(df_raw)
    plot_spearman_heatmap(spearman_results)
    plot_chi_square_summary(chi_sq_results, adjusted_p)
    plot_vta_usage_by_academic_level(df_clean)
    plot_mann_whitney_quality_concern(df_raw, df_clean)
    plot_study_strategies(df_raw)
    plot_adherence(df_raw)

    # ── Step 9: Write the result tables ────────────────────────────
    print("\n[9] Writing result tables...")

    write_frequency_tables(df_raw)
    write_analysis_sample(df_raw, df_clean)
    write_chi_square_results(chi_sq_results, adjusted_p, is_sig)
    write_spearman_results(spearman_results)
    write_other_test_results(fisher_result, mw_result, kw_result)

    print("\n" + "=" * 60)
    print("  Analysis complete.  N =", df_raw.shape[0])
    print("  Figures -> figures/engr 151 2026/")
    print("  Tables  -> outputs/engr_151/")
    print("=" * 60 + "\n")


# ── Entry point ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Tee the run so the console log becomes analysis_summary.txt as well.
    _tee = _Tee(sys.stdout)
    with contextlib.redirect_stdout(_tee):
        main()

    ensure_output_dir(OUT_DIR)
    with open(os.path.join(OUT_DIR, "analysis_summary.txt"), "w") as fh:
        fh.write("".join(_tee.parts))
    print("    [saved] outputs/engr_151/analysis_summary.txt")
