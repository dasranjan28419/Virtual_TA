# ============================================================
# Sentiment Analysis + Circular Word Cloud for Survey Feedback
# ============================================================

import pandas as pd
import re
import numpy as np
import matplotlib.pyplot as plt
from wordcloud import WordCloud
import matplotlib
import hashlib

# ------------------------------------------------------------
# 1. Load dataset
# ------------------------------------------------------------
df = pd.read_csv(
    "Ask the Virtual TA and Share your Learning Survey Report.csv"
)

# Automatically detect the feedback column
feedback_col = [c for c in df.columns if "experience" in c.lower()][0]

# ------------------------------------------------------------
# 2. Sentiment lexicons (transparent & reviewer-friendly)
# ------------------------------------------------------------
positive_words = {
    "good", "helpful", "useful", "great", "easy", "clear",
    "understand", "excellent", "positive", "beneficial", "nice",
    "better", "accurate", "interesting"
}

negative_words = {
    "bad", "confusing", "difficult", "hard", "poor",
    "useless", "slow", "problem", "issue", "wrong"
}

# ------------------------------------------------------------
# 3. Stopwords (prepositions & fillers)
# ------------------------------------------------------------
stopwords = {
    "the", "and", "that", "this", "with", "for", "was", "were", "are",
    "but", "have", "has", "had", "from", "they", "them", "their",
    "you", "your", "would", "could", "should", "about", "into",
    "than", "then", "when", "while", "very", "more", "also",
    "like", "just", "think", "really", "much"
}

# ------------------------------------------------------------
# 4. Tokenization
# ------------------------------------------------------------
def tokenize(text):
    return re.findall(r"\b[a-zA-Z]{3,}\b", str(text).lower())

# ------------------------------------------------------------
# 5. Sentiment classification per student
# ------------------------------------------------------------
def classify_sentiment(text):
    words = tokenize(text)
    pos = sum(1 for w in words if w in positive_words)
    neg = sum(1 for w in words if w in negative_words)

    if pos > neg:
        return "Positive"
    elif neg > pos:
        return "Negative"
    else:
        return "Neutral"

df["sentiment"] = df[feedback_col].apply(classify_sentiment)

# ------------------------------------------------------------
# 6. Sentiment percentage analysis
# ------------------------------------------------------------
sentiment_percent = (
    df["sentiment"]
    .value_counts(normalize=True)
    .mul(100)
    .reindex(["Positive", "Neutral", "Negative"])
    .fillna(0)
)

# ------------------------------------------------------------
# 7. Bar chart: Sentiment distribution
# ------------------------------------------------------------
plt.figure(figsize=(6, 4))
plt.bar(sentiment_percent.index, sentiment_percent.values)
plt.ylabel("Percentage of Responses")
plt.title("Sentiment Distribution of Student Feedback")
plt.ylim(0, 100)
plt.show()

# ------------------------------------------------------------
# 8. Text preprocessing for word cloud
# ------------------------------------------------------------
def preprocess(text):
    return [w for w in tokenize(text) if w not in stopwords]

all_text = " ".join(
    word
    for response in df[feedback_col]
    for word in preprocess(response)
)

# ------------------------------------------------------------
# 9. Circular mask
# ------------------------------------------------------------
def circular_mask(diameter=700):
    x, y = np.ogrid[:diameter, :diameter]
    center = diameter / 2
    mask = (x - center) ** 2 + (y - center) ** 2 > (center ** 2)
    return mask.astype(int) * 255

mask = circular_mask(700)

# ------------------------------------------------------------
# 10. Deterministic multi-color mapping (stable across runs)
# ------------------------------------------------------------
PALETTE = [
    "#1f77b4",  # blue
    "#ff7f0e",  # orange
    "#2ca02c",  # green
    "#d62728",  # red
    "#9467bd",  # purple
    "#8c564b",  # brown
]

def stable_color_func(word, font_size, position, orientation,
                      random_state=None, **kwargs):
    digest = int(hashlib.md5(word.encode()).hexdigest(), 16)
    return PALETTE[digest % len(PALETTE)]

# ------------------------------------------------------------
# 11. Font (consistent across figures)
# ------------------------------------------------------------
font_path = matplotlib.font_manager.findfont("DejaVu Sans")

# ------------------------------------------------------------
# 12. Generate circular word cloud
# ------------------------------------------------------------
wc_circle = WordCloud(
    width=700,
    height=700,
    background_color="white",
    mask=mask,
    max_words=80,
    margin=4,
    font_path=font_path,
    color_func=stable_color_func,
    contour_width=2,
    contour_color="black"
).generate(all_text)

# ------------------------------------------------------------
# 13. Display circular word cloud
# ------------------------------------------------------------
plt.figure(figsize=(8, 8))
plt.imshow(wc_circle, interpolation="bilinear")
plt.axis("off")
plt.title("Student Feedback – Circular Word Cloud")
plt.show()

# ------------------------------------------------------------
# 14. Save figure (publication-ready)
# ------------------------------------------------------------
wc_circle.to_file("student_feedback_circular_wordcloud.png")
