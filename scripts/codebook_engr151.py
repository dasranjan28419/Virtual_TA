"""
=============================================================================
Codebook for the ENGR 151 (2026) Virtual TA survey export
=============================================================================

SOURCE OF TRUTH
---------------
The workbook itself: data/Student Survey Did the Virtual TA help make your
learning easier and more effective.xlsx, sheet "act_data". Every label below
was read back out of the delivered responses, so the strings here match the
data byte for byte -- including its typos ("Very HIgh", "quizes",
"evlaluating", "Checking my understanding of Class notes") and the non-
breaking space in item E16. Do not tidy them: the analysis matches on these
strings, and correcting one here silently drops a category.

WHY THIS FILE EXISTS, AND WHY IT IS NOT codebook_me140.py
---------------------------------------------------------
The two deployments used different instruments, so they need different
codebooks. Sharing one would corrupt both.

ENGR 151 is a Microsoft Forms export holding answer TEXT. It needs no
code -> label mapping at all; the labels are already in the cells. What it
needs instead, and what this file supplies, is the part the spreadsheet does
not carry: which items are multi-select, what order the ordered scales run
in, and which numeric score each ordinal label takes.

ME 140 is a Qualtrics export holding bare integers with no labels anywhere,
which is the entire reason codebook_me140.py exists.

The instruments differ in four ways that matter:

  1. ITEMS ONLY IN ENGR 151. E1 (academic level) and E17 (the FAQ question).
     ME 140 asked neither, so its script has no academic-level tests and no
     FAQ analysis.

  2. ITEMS ONLY IN ME 140. Q18 and Q19, the two open-text questions. ENGR 151
     is entirely closed-ended, which is why outputs/engr_151/ has no
     open_text_responses.csv.

  3. DIFFERENT OPTION SETS ON SHARED ITEMS.
       - E2 familiarity has four levels (Low..Very HIgh). ME 140's Q1 has
         five: it adds "None (no prior familiarity)".
       - E6 Virtual TA frequency has six options. It adds "I was not aware of
         the course chatbot", which ME 140's Q5 does not offer.
       - E18/E19 offer four answers, including BOTH "Maybe" and "Not sure /
         It depends on the design". ME 140's Q16/Q17 offer three.
       - E13, E14 and E16 are single-select here; the nearest ME 140 items
         (Q12, Q13, Q15) are not all single-select.

  4. DIFFERENT ORDINAL SCORING. Because the option sets differ, the scores
     differ too. ENGR 151 familiarity runs Low=1..Very HIgh=4; ME 140 runs
     Low=2..Very high=5. Virtual TA frequency starts at 0 here and at 1
     there. Borrowing ME 140's numbers would shift every ENGR 151 score by
     one without raising any error. See ME140_EQUIVALENT at the bottom.

ORDINAL SCORES MATCH THE WORKBOOK
---------------------------------
ORDINAL_SCORE reproduces the scoring already present in the workbook's
"cleaned_data" sheet, so this file documents that sheet rather than competing
with it. Two consequences are worth knowing:

  - The AI-use scales start at 0 ("Never"), not 1.
  - E6 maps TWO labels to 0: "Never" and "I was not aware of the course
    chatbot( Virtual TA)". A student who never knew the tool existed and a
    student who knew and declined both score zero exposure. That is the
    workbook's existing convention and the analysis inherits it, but it means
    E6's score is intensity of use, not awareness.

Because of that tie, display order and ordinal score are kept apart:
SINGLE_SELECT gives display position, ORDINAL_SCORE gives the analysis value.
=============================================================================
"""

# --- Question wording -------------------------------------------------------
# Keyed E1..E19 in workbook column order. COLUMN holds the act_data header the
# question actually lives under; these are long, so nothing else spells them out.
QUESTION_TEXT = {
    "E1":  "What is your current academic level?",
    "E2":  "How would you rate your prior familiarity with AI tools before this course?",
    "E3":  "Before this course, how often did you use AI tools for academic work?",
    "E4":  "This semester (overall, in all courses), how often did you use AI tools?",
    "E5":  "For what learning or coursework-related purposes do you typically use AI tools?",
    "E6":  "How often did you use the course chatbot (Virtual TA) this semester?",
    "E7":  "When in the semester did you use it most?",
    "E8":  "What did you use the Virtual TA for?",
    "E9":  "Typical session length with the Virtual TA (average time per session)",
    "E10": "Learning & understanding",
    "E11": "Efficiency and workload",
    "E12": "Study strategies",
    "E13": "Perceived learning outcome",
    "E14": "Depth vs superficial understanding",
    "E15": "I sometimes encountered responses from the Virtual TA that were "
           "unclear, incomplete, or incorrect.",
    "E16": "Self-reported adherence",
    "E17": "How did you use or perceive the FAQ materials provided during the course?",
    "E18": "Would you like to have a Virtual TA (or something similar) in other "
           "technical courses?",
    "E19": "Would you recommend future students in this course make active use of "
           "the Virtual TA?",
}

# --- act_data column header for each question -------------------------------
COLUMN = {
    "E1":  "What is your current academic level?",
    "E2":  "How would you rate your prior familiarity with AI tools (ChatGPT, Gemini, "
           "Copilot, etc.) before this course?",
    "E3":  "Before this course, how often did you use AI tools for academic work?",
    "E4":  "This semester (overall, in all courses), how often did you use AI tools "
           "(any, including the Virtual TA)?",
    "E5":  "For what learning or coursework-related purposes do you typically use AI "
           "tools? (Select all that apply.)",
    "E6":  "How often did you use the course chatbot (Virtual TA) this semester?",
    "E7":  "When in the semester did you use it most?",
    "E8":  "What did you use the Virtual TA for? (Select all that apply.)",
    "E9":  "Typical session length with the Virtual TA (average time per session):",
    "E10": "Learning & understanding (select all that apply).",
    "E11": "Efficiency and workload (select all that apply)",
    "E12": "Study Strategies",
    "E13": "Perceived learning outcome",
    "E14": "Depth vs superficial understanding",
    "E15": "I sometimes encountered responses from the Virtual TA that were unclear, "
           "incomplete, or incorrect.",
    "E16": "Self-reported adherence.",
    "E17": "How did you use or perceive the FAQ materials provided during the course, "
           "which were generated from questions students asked to the VTA? "
           "(Select all that apply)",
    "E18": "Would you like to have a Virtual TA (or something similar) in other "
           "technical courses?",
    "E19": "Would you recommend future students in this course make active use of the "
           "Virtual TA?",
}

# --- cleaned_data columns that already carry a scored version ---------------
CLEAN_COLUMN = {
    "E1":  ("Level",            "Level_ord"),
    "E2":  ("Familiarity",      "Familiarity_ord"),
    "E3":  ("AI_before",        "AI_before_ord"),
    "E6":  ("VTA_semester_use", "VTA_freq/intensity"),
    "E8":  ("VTA_Usage",        None),
    "E9":  ("VTA_session_len",  "VTA_session_len_ord"),
}

# --- Short names used for output columns and figure axes --------------------
SHORT_NAME = {
    "E1":  "academic_level",    "E2":  "AI_familiarity",
    "E3":  "AI_before",         "E4":  "AI_semester",
    "E5":  "AI_purposes",       "E6":  "VTA_freq",
    "E7":  "VTA_timing",        "E8":  "VTA_purposes",
    "E9":  "VTA_session_len",   "E10": "learning",
    "E11": "efficiency",        "E12": "study_strategy",
    "E13": "perceived_outcome", "E14": "depth",
    "E15": "quality_concern",   "E16": "adherence",
    "E17": "faq",               "E18": "want_elsewhere",
    "E19": "recommend",
}

# --- Single-select: display position -> label -------------------------------
# The position is OUR display order, not a code stored in the export; the
# workbook holds the text. For ordinal items, use ORDINAL_SCORE for analysis.
SINGLE_SELECT = {
    "E1": {1: "Sophomore", 2: "Junior", 3: "Senior"},

    # Four levels only, and the workbook's "Very HIgh" typo is load-bearing.
    "E2": {1: "Low", 2: "Moderate", 3: "High", 4: "Very HIgh"},

    "E3": {1: "Never", 2: "A few times per semester", 3: "A few times per month",
           4: "A few times per week", 5: "Daily or almost daily"},

    "E4": {1: "Never", 2: "A few times per semester", 3: "A few times per month",
           4: "A few times per week", 5: "Daily or almost daily"},

    # Six options: the awareness option has no ME 140 counterpart.
    "E6": {1: "Never",
           2: "I was not aware of the course chatbot( Virtual TA)",
           3: "1-2 times total",
           4: "A few times per month",
           5: "1-2 times per week",
           6: "3+ times per week"},

    "E7": {1: "Mostly at the beginning of the course",
           2: "Mostly in the middle of the course",
           3: "Mostly near exams / deadlines",
           4: "Consistently throughout the semester",
           5: "I only tried it once or twice"},

    "E9": {1: "Less than 5 minutes", 2: "5-15 minutes", 3: "15-30 minutes",
           4: "30-60 minutes",       5: "More than 60 minutes"},

    "E12": {1: "I used the Virtual TA mainly after trying problems on my own.",
            2: "I used the Virtual TA mainly before trying problems on my own.",
            3: "Using Virtual TA encouraged me to attempt more challenging problems.",
            4: "Using the Virtual TA made me more likely to postpone starting "
               "homework (procrastinate).",
            5: "I sometimes accepted the Virtual TA's answers without critically "
               "evlaluating them."},

    "E13": {1: "The Virtual TA helped me perform better on homework.",
            2: "The Virtual TA helped me perform better on quizzes and exams.",
            3: "Without the Virtual TA, I think my final grade would have been lower.",
            4: "Even if my grade did not change, I feel I learned concepts more "
               "solidly because of the Virtual TA."},

    "E14": {1: "Sometimes the Virtual TA's help made me feel like I understood more "
               "than I actually did.",
            2: "The Virtual TA encouraged me to ask \"why\" and not just \"what is "
               "the answer\".",
            3: "Using the Virtual TA changed how I think about problem solving "
               "(eg. more step-by-step reasoning, asking better questions).",
            4: "I worry that relying on AI tools might weaken my ability to solve "
               "problems independently in the long term."},

    "E15": {1: "Strongly disagree", 2: "Disagree", 3: "Neutral",
            4: "Agree", 5: "Strongly agree"},

    # The fourth option carries a non-breaking space before "not". Written as an
    # escape so it survives editors that would silently convert it to a space.
    "E16": {1: "I always used the Virtual TA in ways that I believe are consistent "
               "with the course rules.",
            2: "I have used AI mainly to check or improve work I already did myself.",
            3: "I have used AI to generate solutions that I submitted with minimal "
               "modification.",
            4: "I sometimes used the Virtual TA (or other AI tools) in ways that I "
               "suspect the instructor might not approve of."},

    # Four options, not three: this instrument offers "Maybe" as well as
    # "Not sure / It depends on the design".
    "E18": {1: "Yes", 2: "No", 3: "Maybe",
            4: "Not sure / It depends on the design"},
    "E19": {1: "Yes", 2: "No", 3: "Maybe",
            4: "Not sure / It depends on the design"},
}

# --- Multi-select: display position -> label --------------------------------
# Stored semicolon-delimited in the workbook.
MULTI_SELECT = {
    "E5": {1: "Explaining difficult concepts",
           2: "Checking my homework or solutions",
           3: "Generating code or troubleshooting code",
           4: "Drafting written assignments",
           5: "Brainstorming ideas",
           6: "Creating study notes / summaries",
           7: "Preparing for midterms/exams",
           8: "Checking my understanding of Class notes",
           9: "I use Ai mainly for non-academic tasks",
           10: "I generally do not use AI tools"},

    "E8": {1: "Clarifying lecture concepts",
           2: "Clarifying homework problems before attempting them",
           3: "Checking or debugging my homework solutions",
           4: "Understanding solutions after homework was graded",
           5: "Preparing for quizes",
           6: "Preparing for midterms",
           7: "Preparing for final exam",
           8: "Clarifying Lab instructions or lab analysis",
           9: "Just curious / playing with it."},

    "E10": {1: "The Virtual TA helped me understand course concepts more deeply",
            2: "The Virtual TA helped me make connections across topics",
            3: "Using the Virtual TA made me more confident in this subject",
            4: "The Virtual TA didn't affect my learning"},

    "E11": {1: "The Virtual TA helped me complete my homework or studying more "
               "efficiently",
            2: "The Virtual TA reduced the amount of time I felt stuck on problems.",
            3: "The Virtual TA saved me time overall in this course.",
            4: "Because of the Virtual TA, I can spend less time using other "
               "resources (office hours, peers, internet, etc)",
            5: "None of the Above"},

    # E17 has no ME 140 counterpart: ME 140 did not ask about FAQ materials.
    "E17": {1: "The FAQ helped me understand the topic better.",
            2: "The FAQ clarified common points of confusion related to the topic.",
            3: "The FAQ included questions I wanted to ask but had not asked myself.",
            4: "The FAQ introduced questions or perspectives I had not previously "
               "considered.",
            5: "The FAQ helped me prepare for homework, labs, quizzes, or exams.",
            6: "The FAQ was useful as a quick review or study resource.",
            7: "Most of the FAQ content was too basic because I already understood "
               "those concepts.",
            8: "I reviewed the FAQ only briefly and did not use it much.",
            9: "I was not aware of the FAQ or did not use it."},
}

# --- Ordinal scoring, reproducing the workbook's cleaned_data sheet ----------
# label -> score. Note the 0-based AI-use scales and the E6 tie described in
# the header. Rank-based tests (Spearman, Mann-Whitney, Kruskal-Wallis) run on
# these values.
ORDINAL_SCORE = {
    "E2": {"Low": 1, "Moderate": 2, "High": 3, "Very HIgh": 4},

    "E3": {"Never": 0, "A few times per semester": 1, "A few times per month": 2,
           "A few times per week": 3, "Daily or almost daily": 4},

    "E4": {"Never": 0, "A few times per semester": 1, "A few times per month": 2,
           "A few times per week": 3, "Daily or almost daily": 4},

    # Both zero-exposure answers score 0; see the header note.
    "E6": {"Never": 0,
           "I was not aware of the course chatbot( Virtual TA)": 0,
           "1-2 times total": 1,
           "A few times per month": 2,
           "1-2 times per week": 3,
           "3+ times per week": 4},

    "E9": {"Less than 5 minutes": 1, "5-15 minutes": 2, "15-30 minutes": 3,
           "30-60 minutes": 4, "More than 60 minutes": 5},

    "E15": {"Strongly disagree": 1, "Disagree": 2, "Neutral": 3,
            "Agree": 4, "Strongly agree": 5},
}

# --- Confidence and evidence ------------------------------------------------
# "delivered data" = label read directly out of the responses, so it cannot
# disagree with what the analysis matches on. Every ENGR 151 item qualifies:
# unlike ME 140, no option order had to be inferred from an instrument PDF.
CONFIDENCE = {q: "delivered data" for q in QUESTION_TEXT}

_DELIVERED = ("Labels read verbatim from the delivered responses in "
              "data/...effective.xlsx, sheet act_data.")

EVIDENCE = {q: _DELIVERED for q in QUESTION_TEXT}
EVIDENCE["E2"] = (_DELIVERED + " Four levels, no 'None' option; the workbook's "
                  "'Very HIgh' spelling is retained deliberately. Scored 1-4 to "
                  "match cleaned_data.Familiarity_ord.")
EVIDENCE["E6"] = (_DELIVERED + " Six options. 'I was not aware of the course "
                  "chatbot' has no ME 140 counterpart and, following "
                  "cleaned_data, scores 0 alongside 'Never'.")
EVIDENCE["E17"] = (_DELIVERED + " FAQ item; ME 140 did not ask this question.")
EVIDENCE["E18"] = _DELIVERED + " Four options, including both 'Maybe' and 'Not sure'."
EVIDENCE["E19"] = _DELIVERED + " Four options, including both 'Maybe' and 'Not sure'."

# Ordinal items: the score is a rank, so rank-based tests are valid.
ORDINAL = list(ORDINAL_SCORE.keys())

MULTISELECT_QS = list(MULTI_SELECT.keys())
MULTISELECT_COLS = [COLUMN[q] for q in MULTISELECT_QS]
LIKERT_ORDER = [SINGLE_SELECT["E15"][i] for i in range(1, 6)]
YES_NO_ORDER = [SINGLE_SELECT["E19"][i] for i in range(1, 5)]

# act_data columns 0-5 are the form's own bookkeeping, not survey answers.
NON_QUESTION_COLS = ["ID", "Start time", "Completion time", "Email", "Name",
                     "Last modified time"]

# --- Crosswalk to the ME 140 instrument -------------------------------------
# Provided for documentation, NOT for pooling the cohorts. Even where an item
# maps cleanly, the option sets and ordinal scores differ (see header point 4),
# so any pooled or cross-cohort comparison has to harmonise the scales first.
ME140_EQUIVALENT = {
    "E1":  None,   # academic level: not asked in ME 140
    "E2":  "Q1",   # option sets differ: ME 140 adds "None"
    "E3":  "Q2",
    "E4":  "Q3",
    "E5":  "Q4",
    "E6":  "Q5",   # option sets differ: ENGR 151 adds the awareness option
    "E7":  "Q6",
    "E8":  "Q7",
    "E9":  "Q8",
    "E10": "Q9",
    "E11": "Q10",
    "E12": "Q11",
    "E13": "Q12",
    "E14": "Q13",
    "E15": "Q14",  # ENGR 151 says "Neutral", ME 140 "Neither agree nor disagree"
    "E16": "Q15",
    "E17": None,   # FAQ: not asked in ME 140
    "E18": "Q16",  # ENGR 151 offers four answers, ME 140 three
    "E19": "Q17",  # ENGR 151 offers four answers, ME 140 three
}

# ME 140 items with no ENGR 151 counterpart: Q18 and Q19, the open-text pair.
# ENGR 151 is entirely closed-ended.
ME140_ONLY = ["Q18", "Q19"]


def label_for(qid, position):
    """Returns the label at one display position, or a marker if unmapped."""
    table = SINGLE_SELECT.get(qid) or MULTI_SELECT.get(qid) or {}
    return table.get(int(position), f"{qid}@{int(position)}")


def score_for(qid, label):
    """Returns the ordinal score for a label, or None if the item is not ordinal."""
    return ORDINAL_SCORE.get(qid, {}).get(label)


def is_provisional(qid):
    """True when this question's labels or identity are not fully established."""
    return CONFIDENCE.get(qid) != "delivered data"


def options(qid):
    """Every label for a question, in display order."""
    table = SINGLE_SELECT.get(qid) or MULTI_SELECT.get(qid) or {}
    return [table[k] for k in sorted(table)]
