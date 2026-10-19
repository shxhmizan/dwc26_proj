<div align="center">

# ExxonMobil DataWorks Challenge 2026

### Machine Learning-Assisted History Matching & Production Forecasting

**A reproducible analytics workflow for reservoir history matching, production forecasting, and uncertainty-aware decision support.**

![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Machine Learning](https://img.shields.io/badge/Machine%20Learning-Scikit--learn-F7931E?style=for-the-badge&logo=scikitlearn&logoColor=white)
![Analytics](https://img.shields.io/badge/Analytics-Reservoir%20Engineering-0F766E?style=for-the-badge)
![Dashboard](https://img.shields.io/badge/Dashboard-Power%20BI-F2C811?style=for-the-badge&logo=powerbi&logoColor=black)

</div>

---

## Project Overview

This project explores how machine learning and analytical modelling can support **reservoir history matching** and **conditional production forecasting**. The workflow compares simulated production histories with observed field behaviour, screens candidate reservoir cases, builds a machine-learning proxy, and prepares forecast and validation outputs for a Power BI decision-support dashboard.

The dashboard concept connects four questions:

- **What could future field production look like?** Compare historical trends with alternative production scenarios.
- **How well do candidate cases match observed history?** Inspect model performance and history-matching evidence.
- **Which uncertain parameters are associated with different outcomes?** Explore reservoir uncertainty and sensitivity.
- **What operational risks deserve attention?** Track production decline and produced-water handling scenarios.

> **Important interpretation note:** Forecasts are conditional extrapolations, not guaranteed outcomes. Scenario spread should not be interpreted as a calibrated confidence interval or reserves estimate.

## Dashboard Preview

The screenshots below show the four dashboard views prepared for the project.

### 01 · Field Performance & Production Forecast

![Field Performance & Production Forecast](Dashboard%20Pictures/Field%20Performance%20%26%20Production%20Forecast.png)

*Compare field production performance and forecast scenarios to understand potential changes in oil, gas, and water production over the forecast horizon.*

### 02 · History Matching & Model Comparison

![History Matching & Model Comparison](Dashboard%20Pictures/History%20Matching%20%26%20Model%20Comparison.png)

*Review how candidate cases and proxy models reproduce observed production behaviour. Use the comparison to understand model fit rather than treating historical fit as proof of future accuracy.*

### 03 · Reservoir Uncertainty & Sensitivity

![Reservoir Uncertainty & Sensitivity](Dashboard%20Pictures/Reservoir%20Uncertainty%20%26%20Sensitivity.png)

*Explore how alternative reservoir parameter combinations relate to the range of historical matches and forecast scenarios.*

### 04 · Operations & Reservoir Risk

![Operations & Reservoir Risk](Dashboard%20Pictures/Operations%20%26%20Reservoir%20Risk.png)

*Bring production decline and produced-water trends into focus to support scenario-based operational discussion.*

---

## Methodology at a Glance

```text
Supplied Excel workbooks
          ↓
Data extraction & quality checks
          ↓
Case screening and production-history comparison
          ↓
Machine-learning proxy and history matching
          ↓
Conditional forecast scenarios
          ↓
Validation outputs, reports and Power BI-ready tables
```

### Main analytical components

| Component | Purpose |
|---|---|
| Data preparation and audit | Extract production and uncertainty inputs and check the supplied reservoir-grid data. |
| Proxy modelling | Learn relationships between the four uncertainty inputs and historical production responses. |
| History matching | Search for candidate parameter combinations that reduce mismatch with observed production history. |
| Forecast scenarios | Continue selected cases into a conditional 2008–2028 forecast using documented decline assumptions. |
| Dashboard-ready outputs | Export model results, validation tables, and supporting datasets for visualization in Power BI. |

The analysis workflow uses a fixed random seed (`20261015`). The documented split is **Cases 1–70 for training, 71–85 for model selection, and 86–100 for the final test evaluation**. The selected historical proxy is `ExtraTrees`, chosen on the validation cases before the held-out test set is evaluated.

## Technology Stack

- **Python** — analysis workflow and reproducible processing
- **NumPy & SciPy** — numerical analysis and optimization
- **scikit-learn** — machine-learning proxy and validation
- **Matplotlib** — static spatial-analysis figures
- **Jupyter Notebook** — interactive review of the analysis workflow
- **Power BI** — planned dashboard layer using the exported forecast template and supporting tables
- **CSV, Excel & Markdown** — model outputs, data handoff, and documentation

## Repository Structure

```text
.
├── Dashboard Pictures/       # Dashboard screenshots
├── analysis_codes/           # Analysis scripts, notebook and dependencies
├── outputs/                  # Forecast template, validation data and reports
├── powerbi_ready_data/       # Tables prepared for Power BI
├── DataWorks_2026_Analysis_and_Dashboard_Blueprint.md
└── README.md
```

Key files:

- `analysis_codes/run_analysis.py` — main reproducible analysis workflow
- `analysis_codes/run_analysis.ipynb` — notebook for reviewing the workflow
- `outputs/09 Template Deliverable_COMPLETED.xlsx` — populated forecast deliverable
- `outputs/EXECUTIVE_ANALYSIS_REPORT.md` — summary of findings and analytical limitations
- `outputs/POWER_BI_SPECIFICATION.md` — recommended dashboard pages, measures, and safeguards
- `outputs/DATA_DICTIONARY_AND_AUDIT.md` — data definitions and audit notes
- `outputs/SPATIAL_ANALYSIS_REPORT.md` — reservoir-grid spatial-analysis notes

## Run the Analysis

### 1. Requirements

- Python 3.12 or a compatible Python 3 version
- The source Excel workbooks supplied with the challenge, placed in the expected `TestCases/` directory
- Python packages listed in `analysis_codes/requirements.txt`

### 2. Install dependencies

Run this command from the workspace root:

```bash
python3 -m pip install -r analysis_codes/requirements.txt
```

### 3. Execute the workflow

```bash
python3 analysis_codes/run_analysis.py
```

The script reads the supplied test-case workbooks and writes generated deliverables to `outputs/`, Power BI-ready tables to `powerbi_ready_data/`, and intermediate cache files to `work/`.

For spatial analysis only:

```bash
MPLCONFIGDIR=/tmp/dwc_mpl python3 analysis_codes/run_analysis.py --spatial-only
```

Add `--refresh-spatial` to deliberately invalidate and rebuild the spatial cache.

See [`analysis_codes/README.md`](analysis_codes/README.md) and [`outputs/RUN_GUIDE.md`](outputs/RUN_GUIDE.md) for additional run details.

## Results & Limitations

The accompanying analysis report documents the selected proxy, history-match results, validation workflow, and forecast assumptions. Interpret the results with these boundaries in mind:

- The 2008–2028 production curves are **conditional extrapolations** based on late-history decline assumptions.
- Forecast variation represents a **scenario/ensemble range**, not a calibrated probability interval.
- Historical matching scores measure fit to supplied history; they are **not future forecast accuracy**.
- The supplied data do not include future simulator labels or a runnable numerical simulator, so optimized proxy curves are not numerical-simulator realizations.
- The analysis report notes that the completed Power BI `.pbix` file is not included in this repository.

For full details, read [`outputs/EXECUTIVE_ANALYSIS_REPORT.md`](outputs/EXECUTIVE_ANALYSIS_REPORT.md) and [`outputs/POWER_BI_SPECIFICATION.md`](outputs/POWER_BI_SPECIFICATION.md).

## Challenge Deliverables Context

The challenge brief calls for source code and model files, a PowerPoint document, a Power BI dashboard, and a seven-minute video. Refer to the official challenge instructions and organizer updates for the final requirements and deadlines.

---

## Data Use Notice

The original challenge README states that the datasets and starter kit are provided exclusively for the DataWorks Challenge 2026 and **must not be published externally**. Keep source workbooks, restricted challenge materials, and any derived content within the usage permitted by the organizers. Confirm publication permissions before making this repository or its contents public.

<div align="center">

**DataWorks Challenge 2026 · Reservoir Analytics · Machine Learning · Forecast Scenarios**

</div>
