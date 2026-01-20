# Virtual_TA

Virtual_TA contains analysis and visualizations for "Ask the Virtual TA" survey responses. The repository includes a Python script that performs simple lexicon-based sentiment analysis and generates a circular word cloud and sentiment distribution chart from survey feedback.

Table of contents
- [Repository contents](#repository-contents)
- [Quick start](#quick-start)
- [How the analysis works (summary)](#how-the-analysis-works-summary)
- [Run the analysis (detailed)](#run-the-analysis-detailed)
- [Inputs & outputs](#inputs--outputs)
- [Notes & suggested improvements](#notes--suggested-improvements)
- [Contributing](#contributing)
- [License & contact](#license--contact)

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

How the analysis works (summary)
- Automatic feedback column detection: the script looks for the first column whose name contains "experience" (case-insensitive) and uses it as the feedback text column.
- Sentiment classification: a small transparent lexicon is defined in the script (sets of positive and negative words). Each response is tokenized, counts of positive/negative matches are compared, and each response is labeled Positive / Neutral / Negative.
- Word cloud: the script builds a cleaned token list (removing short tokens and stopwords), generates a circular word cloud mask, maps words to deterministic colors (stable across runs), and saves the cloud image as `student_feedback_circular_wordcloud.png`.
- Sentiment bar chart: the script plots a bar chart of sentiment percentages with matplotlib. (See Notes below for saving behavior.)

Run the analysis (detailed / headless environment)
- To run on a normal desktop (show plots interactively):
  python3 word_cloud_analysis.py

- To run on a headless CI server (no display) and ensure images are written:
  1. Set matplotlib backend to 'Agg' (non-interactive) by editing the top of `word_cloud_analysis.py`:
     import matplotlib
     matplotlib.use('Agg')
     import matplotlib.pyplot as plt
  2. Optionally modify the script to save the sentiment bar chart (it currently calls plt.show()). Add after plotting the bar chart:
     plt.savefig('Sentiment_Analysis_Bar_chart.png', bbox_inches='tight')
  3. Then run:
     python3 word_cloud_analysis.py
  After running the script you should have `student_feedback_circular_wordcloud.png` (the script already saves this) and, if you add the save call, `Sentiment_Analysis_Bar_chart.png`.

Inputs & outputs
- Input: CSV file containing survey responses. The script automatically finds the feedback column by searching for "experience" in column names; adjust the script if your feedback column uses a different name.
- Outputs:
  - student_feedback_circular_wordcloud.png — circular word cloud image (saved by the script).
  - Sentiment_Analysis_Bar_chart.png — sentiment distribution bar chart (the repo contains a version; to regenerate automatically save it from the script as described above).

Notes & suggested improvements
- Filename mismatch: The script expects a slightly different CSV filename than the one in this repository. Either rename the CSV or update the filename on line 16 in `word_cloud_analysis.py`.
- Requirements file: add a `requirements.txt` with pinned versions, e.g.:
  pandas>=1.3
  numpy>=1.19
  matplotlib>=3.4
  wordcloud>=1.8
- CLI / args: make `word_cloud_analysis.py` accept command-line arguments (input path, output paths, max_words, stopwords file) to be more flexible.
- Unit tests: consider adding tests for the tokenizer and sentiment classification (pytest).
- Documentation: expand `docs/` with a short data dictionary (explain CSV columns) and processing steps to make the analysis reproducible.
- Privacy: if the CSV contains personally identifying information, remove or anonymize it before publishing.
- Reproducibility: add a deterministic random seed or make color mapping deterministic (the script already uses a stable hash-based color function).
- Packaging: create a small CLI wrapper (click/argparse) or a Jupyter notebook showing step-by-step usage and visual outputs.

Contributing
- If you'd like to contribute improvements (fix filename, save charts automatically, or parameterize the script), please:
  1. Fork the repository.
  2. Create a branch with a descriptive name.
  3. Open a pull request describing the changes and why they are needed.

License & contact
- No license file is present in the repository. If you want this project to be open-source, add a LICENSE (e.g., MIT) to clarify reuse permissions.
- Maintainer / contact: GitHub user `dasranjan28419`.

If you want, I can:
- Propose a ready-to-paste improved `README.md` (this file) into the repository (I can create the file block for you to paste or, with your confirmation, push it to the repo).
- Create a small patch to `word_cloud_analysis.py` to accept an input CSV path and to save the bar chart automatically.
- Add a `requirements.txt` and a simple `run_analysis.sh` script for convenience.

Which would you like me to do next?
