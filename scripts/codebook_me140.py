"""
=============================================================================
Codebook for the ME 140 (December 2025) Virtual TA survey export
=============================================================================

SOURCE OF TRUTH
---------------
data/ME 140 questions.pdf, Appendix D ("ME 140 Virtual Teaching Assistant
Survey Instrument"), which lists all 17 questions with their answer options
in display order. Qualtrics numbers choices by display order, so option
position N in the instrument is recode value N in the export.

Instrument item 1..17 maps onto export columns Q1..Q17 one-for-one.

WHY THIS FILE EXISTS
--------------------
The export was downloaded from Qualtrics using numeric recode values rather
than choice text, so every answer is an integer (single-select) or a comma-
separated list of integers (multi-select) and the file carries no answer
labels. This module supplies them.

An earlier revision of this file inferred the orderings before the instrument
PDF was available. Those guesses were wrong for Q4, Q7, Q11, Q13, Q15, Q16
and Q17 and have been replaced by the instrument's own ordering.

THE ONE REMAINING UNCERTAINTY: Q1
---------------------------------
The instrument's item 1 is "How would you rate your prior familiarity with AI
tools (ChatGPT, Gemini, Copilot, etc.) before this course?" with five options
None / Low / Moderate / High / Very high.

The Qualtrics export, however, carries the question stem "Did you find this
explanation useful?" for Q1 -- apparently a stem left over from an earlier
draft, since no such item exists in the instrument.

The response pattern says the instrument is right and the stem is stale:
    Q1 vs Q2 (pre-course AI use)     rho = +0.52
    Q1 vs Q3 (this-semester AI use)  rho = +0.49
    Q1 vs Q5 (Virtual TA use)        rho = +0.08 (n.s.)
A question about whether an explanation was useful has no reason to track
pre-course AI-use frequency that closely, while a prior-AI-familiarity item
tracks it exactly that way. Q1 also has five codes, matching the five options,
and Q2..Q17 already account for instrument items 2..17.

Q1 is therefore treated as prior AI familiarity, but flagged "unconfirmed":
every figure built on it is stamped, and setting Q1_IS_FAMILIARITY = False
below drops it from the analysis entirely.

QUESTIONS THE ME 140 INSTRUMENT DOES NOT ASK
--------------------------------------------
Academic level and the FAQ-materials question appear in the earlier survey but
not in this instrument, so analyses keyed on them cannot be reproduced here.
=============================================================================
"""

# Set to False to treat Q1 as an unrelated intro item and drop it from the
# familiarity analyses (see "THE ONE REMAINING UNCERTAINTY" above).
Q1_IS_FAMILIARITY = True

# --- Question wording (instrument, Appendix D) ------------------------------
QUESTION_TEXT = {
    "Q1":  "How would you rate your prior familiarity with AI tools before this course?",
    "Q2":  "Before this course, how often did you use AI tools for academic work?",
    "Q3":  "This semester (overall, in all courses), how often did you use AI tools?",
    "Q4":  "For what learning or coursework-related purposes do you typically use AI tools?",
    "Q5":  "How often did you use the course chatbot (Virtual TA) this semester?",
    "Q6":  "When in the semester did you use it most?",
    "Q7":  "What did you use the Virtual TA for?",
    "Q8":  "Typical session length with the Virtual TA (average time per session)",
    "Q9":  "Learning & understanding",
    "Q10": "Efficiency & workload",
    "Q11": "Study strategies",
    "Q12": "Perceived learning outcomes",
    "Q13": "Depth vs. superficial understanding",
    "Q14": "I sometimes encountered responses from the Virtual TA that were "
           "unclear, incomplete, or incorrect.",
    "Q15": "Self-reported adherence",
    "Q16": "Would you like to have a Virtual TA (or something similar) in other "
           "technical courses?",
    "Q17": "Would you recommend future students in this course make active use of "
           "the Virtual TA?",
    "Q18": "Open text: a specific moment the VTA helped or hindered learning",
    "Q19": "Open text: how you decide acceptable vs unacceptable AI use",
}

# --- Short names used for output columns and figure axes --------------------
SHORT_NAME = {
    "Q1": "AI_familiarity",     "Q2": "AI_before",
    "Q3": "AI_semester",        "Q4": "AI_purposes",
    "Q5": "VTA_freq",           "Q6": "VTA_timing",
    "Q7": "VTA_purposes",       "Q8": "VTA_session_len",
    "Q9": "learning",           "Q10": "efficiency",
    "Q11": "study_strategy",    "Q12": "perceived_outcome",
    "Q13": "depth",             "Q14": "quality_concern",
    "Q15": "adherence",         "Q16": "want_elsewhere",
    "Q17": "recommend",         "Q18": "text_moment",
    "Q19": "text_acceptable_use",
}

# --- Single-select code -> label (instrument display order) ------------------
SINGLE_SELECT = {
    # Item 1: None / Low / Moderate / High / Very high.
    # "None" is written as "None (no prior familiarity)": the bare word "None"
    # sits in pandas' default NA list, so any CSV written with it would be read
    # back as a missing value rather than a real category.
    "Q1": {1: "None (no prior familiarity)", 2: "Low", 3: "Moderate",
           4: "High", 5: "Very high"},

    "Q2": {1: "Never", 2: "A few times per semester", 3: "A few times per month",
           4: "A few times per week", 5: "Daily or almost daily"},

    "Q3": {1: "Never", 2: "A few times per semester", 3: "A few times per month",
           4: "A few times per week", 5: "Daily or almost daily"},

    "Q5": {1: "Never", 2: "1-2 times total", 3: "A few times per month",
           4: "1-2 times per week", 5: "3+ times per week"},

    "Q6": {1: "Mostly at the beginning of the course",
           2: "Mostly in the middle of the course",
           3: "Mostly near exams / deadlines",
           4: "Consistently throughout the semester",
           5: "I only tried it once or twice"},

    "Q8": {1: "Less than 5 minutes", 2: "5-15 minutes", 3: "15-30 minutes",
           4: "30-60 minutes",       5: "More than 60 minutes"},

    "Q11": {1: "Used VTA after self-attempt",
            2: "Used VTA before self-attempt",
            3: "Attempted harder problems",
            4: "Led to procrastination",
            5: "Accepted answers uncritically"},

    "Q13": {1: "Felt I understood more than I actually did",
            2: "Encouraged me to ask \"why\", not just \"what\"",
            3: "Changed how I think about problem solving",
            4: "Worry it may weaken independent problem solving"},

    "Q14": {1: "Strongly disagree", 2: "Disagree",
            3: "Neither agree nor disagree", 4: "Agree", 5: "Strongly agree"},

    "Q15": {1: "Always rule-compliant",
            2: "Possibly not approved",
            3: "Submitted AI output directly",
            4: "Used to improve own work"},

    # Items 16 and 17 have three options, not four.
    "Q16": {1: "Yes", 2: "No", 3: "Not sure / It depends on the design"},
    "Q17": {1: "Yes", 2: "No", 3: "Not sure / It depends on the design"},
}

# --- Multi-select code -> label (instrument display order) -------------------
MULTI_SELECT = {
    "Q4": {1: "Explaining difficult concepts",
           2: "Checking my homework or solutions",
           3: "Generating or troubleshooting code",
           4: "Drafting written assignments",
           5: "Brainstorming ideas",
           6: "Creating study notes / summaries",
           7: "Preparing for midterms/exams",
           8: "Checking my understanding of class notes",
           9: "Mainly for non-academic tasks",
           10: "I generally do not use AI tools"},

    "Q7": {1: "Clarifying lecture concepts",
           2: "Clarifying homework problems before attempting",
           3: "Checking or debugging my homework solutions",
           4: "Understanding solutions after grading",
           5: "Preparing for quizzes",
           6: "Preparing for the midterm(s)",
           7: "Preparing for the final exam",
           8: "Clarifying lab instructions or lab analysis",
           9: "Just curious / playing with it"},

    "Q9": {1: "Deeper concept understanding",
           2: "Connected topics better",
           3: "Gained subject confidence",
           4: "No effect on learning"},

    "Q10": {1: "More efficient studying",
            2: "Less time stuck",
            3: "Saved overall time",
            4: "Replaced other resources",
            5: "No efficiency benefit"},

    "Q12": {1: "Better on homework",
            2: "Better on quizzes and exams",
            3: "Grade would have been lower without it",
            4: "Learned concepts more solidly"},
}

# --- Confidence per question ------------------------------------------------
# "instrument"  = read directly from Appendix D of ME 140 questions.pdf
# "unconfirmed" = item identity itself is in doubt (Q1 only)
CONFIDENCE = {q: "instrument" for q in
              ["Q2", "Q3", "Q4", "Q5", "Q6", "Q7", "Q8", "Q9", "Q10",
               "Q11", "Q12", "Q13", "Q14", "Q15", "Q16", "Q17"]}
CONFIDENCE["Q1"] = "unconfirmed"

_INSTRUMENT = "Option order read from Appendix D of data/ME 140 questions.pdf."

EVIDENCE = {q: _INSTRUMENT for q in CONFIDENCE}
EVIDENCE["Q1"] = (
    "Instrument item 1 is prior AI familiarity (None/Low/Moderate/High/Very high), "
    "but the Qualtrics stem reads 'Did you find this explanation useful?'. Response "
    "pattern supports the instrument: rho=+0.52 with pre-course AI use and +0.49 with "
    "semester AI use, but only +0.08 with Virtual TA use. Treated as familiarity; "
    "set Q1_IS_FAMILIARITY = False in codebook_me140.py to drop it."
)
EVIDENCE["Q5"] = (_INSTRUMENT + " The ME 140 instrument has no 'not aware of the "
                  "Virtual TA' option; the earlier survey did.")
EVIDENCE["Q16"] = _INSTRUMENT + " Three options only (Yes / No / Not sure), not four."
EVIDENCE["Q17"] = _INSTRUMENT + " Three options only (Yes / No / Not sure), not four."

# Ordinal items: the numeric code is the rank, so rank-based tests are valid.
ORDINAL = ["Q1", "Q2", "Q3", "Q5", "Q8", "Q14"]

MULTISELECT_QS = list(MULTI_SELECT.keys())
LIKERT_ORDER = [SINGLE_SELECT["Q14"][i] for i in range(1, 6)]
YES_NO_ORDER = [SINGLE_SELECT["Q17"][i] for i in range(1, 4)]


def label_for(qid, code):
    """Returns the label for one numeric code, or the bare code if unmapped."""
    table = SINGLE_SELECT.get(qid) or MULTI_SELECT.get(qid) or {}
    return table.get(int(code), f"{qid}={int(code)}")


def is_provisional(qid):
    """True when this question's labels or identity are not fully established."""
    return CONFIDENCE.get(qid) != "instrument"
