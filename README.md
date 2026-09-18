# Virtual_TA

This repository contains analysis, visualizations, and supporting materials for the "Ask the Virtual TA" student survey and related course-specific feedback analyses. It includes raw survey inputs, analysis scripts, generated output CSV files, figures, and documentation for multiple course sections.

## Repository structure

```text
Virtual_TA/
├── README.md
├── Ask the Virtual TA and Share your Learning Survey Report.csv
├── word_cloud_analysis.py
├── Sentiment_Analysis_Bar_chart.png
├── student_feedback_circular_wordcloud.png
├── data/
│   ├── ME 140 questions.pdf
│   ├── Student Survey Did the Virtual TA help make your learning easier and more effective.xlsx
│   ├── Virtual TA ME 140_December 20, 2025_17.07.csv
│   └── readme_1
├── docs/
│   ├── GPT Instruction Document_.docx
│   ├── vta_findings.html
│   ├── 📄 Chat Summary API - Step-by-Step Setup Guide.docx
│   └── readme_2
├── figures/
│   ├── ENGR_151/
│   │   ├── fig_vta_benefits.pdf
│   │   ├── fig_vta_benefits.png
│   │   ├── fig_vta_dose_response.pdf
│   │   ├── fig_vta_dose_response.png
│   │   ├── fig_vta_engagement.pdf
│   │   ├── fig_vta_engagement.png
│   │   ├── fig_vta_intensity_rho.pdf
│   │   ├── fig_vta_intensity_rho.png
│   │   ├── fig_vta_perceptions.pdf
│   │   ├── fig_vta_perceptions.png
│   │   └── readme_4
│   └── ME_140/
│       ├── fig_me140_benefits.pdf
│       ├── fig_me140_benefits.png
│       ├── fig_me140_dose_response.pdf
│       ├── fig_me140_dose_response.png
│       ├── fig_me140_engagement.pdf
│       ├── fig_me140_engagement.png
│       ├── fig_me140_intensity_rho.pdf
│       ├── fig_me140_intensity_rho.png
│       ├── fig_me140_perceptions.pdf
│       ├── fig_me140_perceptions.png
│       └── readme_5
├── Output_CSV/
│   ├── ENGR_151/
│   │   ├── analysis_sample_labeled.csv
│   │   ├── analysis_sample_numeric.csv
│   │   ├── analysis_summary.txt
│   │   ├── chi_square_results.csv
│   │   ├── frequency_tables.csv
│   │   ├── other_test_results.csv
│   │   ├── spearman_results.csv
│   │   └── readme_7
│   ├── ME_140/
│   │   ├── analysis_sample_labeled.csv
│   │   ├── analysis_sample_numeric.csv
│   │   ├── analysis_summary.txt
│   │   ├── chi_square_results.csv
│   │   ├── codebook_review.csv
│   │   ├── frequency_tables.csv
│   │   ├── open_text_responses.csv
│   │   ├── other_test_results.csv
│   │   ├── paper_figure_stats.txt
│   │   ├── spearman_results.csv
│   │   └── readme_8
│   └── readme_6
├── scripts/
│   ├── codebook_engr151.py
│   ├── codebook_me140.py
│   ├── make_paper_figures.py
│   ├── make_paper_figures_me140.py
│   ├── readme_9
│   ├── vta_survey_analysis.py
│   └── vta_survey_analysis_me140.py
└──
```

## Root files

- `README.md` — project overview and repository documentation.
- `Ask the Virtual TA and Share your Learning Survey Report.csv` — raw survey dataset used as an input for analysis.
- `word_cloud_analysis.py` — original Python script for lightweight sentiment analysis and word cloud generation.
- `Sentiment_Analysis_Bar_chart.png` — example sentiment chart output.
- `student_feedback_circular_wordcloud.png` — example circular word cloud output.

## Data folder

The `data/` directory contains course and survey datasets used for analysis and reporting.

- `ME 140 questions.pdf` — course questions document.
- `Student Survey Did the Virtual TA help make your learning easier and more effective.xlsx` — student survey spreadsheet.
- `Virtual TA ME 140_December 20, 2025_17.07.csv` — ME 140 survey response data.
- `readme_1` — placeholder/readme file in the data directory.

## Scripts folder

The `scripts/` directory contains the analytical and figure-generation code used for the project.

- `vta_survey_analysis.py` — primary survey analysis script for the ENGR 151/Virtual TA study.
- `vta_survey_analysis_me140.py` — survey analysis script for the ME 140 course section.
- `make_paper_figures.py` — plotting and figure generation for the main study results.
- `make_paper_figures_me140.py` — figure generation for the ME 140 analysis.
- `codebook_engr151.py` — coding/labeling workflow for ENGR 151 responses.
- `codebook_me140.py` — coding/labeling workflow for ME 140 responses.
- `readme_9` — placeholder/readme file in the scripts directory.

## Output CSV folder

The `Output_CSV/` directory contains generated analysis tables and summaries for course sections.

- `Output_CSV/ENGR_151/` — analysis artifacts for ENGR 151
  - `analysis_sample_labeled.csv`
  - `analysis_sample_numeric.csv`
  - `analysis_summary.txt`
  - `chi_square_results.csv`
  - `frequency_tables.csv`
  - `other_test_results.csv`
  - `spearman_results.csv`
- `Output_CSV/ME_140/` — analysis artifacts for ME 140
  - `analysis_sample_labeled.csv`
  - `analysis_sample_numeric.csv`
  - `analysis_summary.txt`
  - `chi_square_results.csv`
  - `codebook_review.csv`
  - `frequency_tables.csv`
  - `open_text_responses.csv`
  - `other_test_results.csv`
  - `paper_figure_stats.txt`
  - `spearman_results.csv`

## Figures folder

The `figures/` directory contains generated visualization files in both PNG and PDF formats.

- `figures/ENGR_151/` — visualizations for ENGR 151
  - `fig_vta_benefits.*`
  - `fig_vta_dose_response.*`
  - `fig_vta_engagement.*`
  - `fig_vta_intensity_rho.*`
  - `fig_vta_perceptions.*`
- `figures/ME_140/` — visualizations for ME 140
  - `fig_me140_benefits.*`
  - `fig_me140_dose_response.*`
  - `fig_me140_engagement.*`
  - `fig_me140_intensity_rho.*`
  - `fig_me140_perceptions.*`

## Docs folder

The `docs/` directory contains supporting documentation and reporting materials.

- `GPT Instruction Document_.docx` — GPT instruction document.
- `vta_findings.html` — HTML presentation or findings summary.
- `📄 Chat Summary API - Step-by-Step Setup Guide.docx` — setup guide for the chat summary API workflow.

## Quick start

### Prerequisites

- Python 3.8+
- Required packages:

```bash
pip install pandas numpy matplotlib wordcloud
```

### Run the basic sentiment analysis script

From the repository root:

```bash
python3 word_cloud_analysis.py
```

This script reads the survey CSV and generates a sentiment chart and word cloud output.

## Notes

- The repository includes multiple course-specific analysis workflows beyond the initial simple lexicon-based script.
- CSV outputs and figure outputs are organized by course section (ENGR_151 and ME_140).
- The project combines both survey analysis and figure/report generation for teaching and assessment evaluation.

## Contributing

Contributions are welcome. If you extend the analysis, please keep the repository structure organized by adding new scripts under `scripts/`, generated outputs under `Output_CSV/` and `figures/`, and supporting documentation under `docs/`.

## License

This repository is provided for research, course analysis, and educational use. Please check with the repository owner for any licensing or sharing restrictions before reusing the files externally.
