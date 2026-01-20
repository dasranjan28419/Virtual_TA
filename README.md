# Virtual_TA

Virtual_TA contains analysis and visualizations for "Ask the Virtual TA" survey responses. The repository includes a Python script that performs simple lexicon-based sentiment analysis and generates a circular word cloud and sentiment distribution chart from survey feedback.

########################################################
Table of contents
- [Repository contents](#repository-contents)
- [Quick start](#quick-start)
- [How the analysis works (summary)](#how-the-analysis-works-summary)
- [Run the analysis (detailed)](#run-the-analysis-detailed)
- [Inputs & outputs](#inputs--outputs)
- [Notes & suggested improvements](#notes--suggested-improvements)
- [Contributing](#contributing)
- [License & contact](#license--contact)


########################################################
Repository contents
- [Ask the Virtual TA and Share your Learning Survey Report.csv](https://github.com/dasranjan28419/Virtual_TA/blob/main/Ask%20the%20Virtual%20TA%20and%20Share%20your%20Learning%20Survey%20Report.csv)  
  Raw survey CSV file used as input for analysis.
- [word_cloud_analysis.py](https://github.com/dasranjan28419/Virtual_TA/blob/main/word_cloud_analysis.py)  
  Main analysis script: loads the CSV, classifies sentiment using small lexicons, creates a sentiment bar chart and a circular word cloud, and saves the word cloud image.
- [Sentiment_Analysis_Bar_chart.png](https://github.com/dasranjan28419/Virtual_TA/blob/main/Sentiment_Analysis_Bar_chart.png)  
  An example/generated sentiment distribution chart image.
- [student_feedback_circular_wordcloud.png](https://github.com/dasranjan28419/Virtual_TA/blob/main/student_feedback_circular_wordcloud.png)  
  Generated circular word cloud image visualizing common words in feedback.
- [README.md](https://github.com/dasranjan28419/Virtual_TA/blob/main/README.md)  
  This file.


########################################################
Quick start

1. Prerequisites
   - Python 3.8+ recommended
   - Install required Python packages:
     pip install pandas numpy matplotlib wordcloud

   (Optional: create and activate a virtual environment before installing.)

2. Run the analysis (default)
   - From the repo root:
     python3 word_cloud_analysis.py

   Notes:
   - The script expects a CSV survey file. By default the script currently attempts to open:
     "Ask the Virtual TA and Share your Learning Survey Student Analysis Report (1).csv"
     but the repository includes:
     "Ask the Virtual TA and Share your Learning Survey Report.csv"
     If you get a FileNotFoundError, either:
     - Rename the CSV in the repo to match the filename used in the script, or
     - Edit the CSV path on line 16 of `word_cloud_analysis.py` to match the CSV filename in the repository.
    
########################################################

How the analysis works (summary)
- Automatic feedback column detection: the script looks for the first column whose name contains "experience" (case-insensitive) and uses it as the feedback text column.
- Sentiment classification: a small transparent lexicon is defined in the script (sets of positive and negative words). Each response is tokenized, counts of positive/negative matches are compared, and each response is labeled Positive / Neutral / Negative.
- Word cloud: the script builds a cleaned token list (removing short tokens and stopwords), generates a circular word cloud mask, maps words to deterministic colors (stable across runs), and saves the cloud image as `student_feedback_circular_wordcloud.png`.
- Sentiment bar chart: the script plots a bar chart of sentiment percentages with matplotlib. (See Notes below for saving behavior.)


########################################################
Inputs & outputs
- Input: CSV file containing survey responses. The script automatically finds the feedback column by searching for "experience" in column names; adjust the script if your feedback column uses a different name.
- Outputs:
  - student_feedback_circular_wordcloud.png — circular word cloud image (saved by the script).
  - Sentiment_Analysis_Bar_chart.png — sentiment distribution bar chart (the repo contains a version; to regenerate automatically save it from the script as described above).

########################################################
