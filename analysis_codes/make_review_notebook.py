#!/usr/bin/env python3
"""Create a documented Jupyter version of run_analysis.py without duplicating logic."""
import json
from pathlib import Path

HERE = Path(__file__).parent
SOURCE = HERE / "run_analysis.py"
DESTINATION = HERE / "run_analysis.ipynb"

SECTIONS = [
    ("from __future__", "# 1. Imports and reproducibility\n\n**Data used:** no challenge data is read in this section.\n\n**Analysis performed:** imports the OOXML-reader, numerical, optimisation, machine-learning, and file-output libraries. The fixed random seed makes model fitting repeatable."),
    ("def excel_date", "# 2. Spreadsheet helpers\n\n**Data used:** cells from all supplied `.xlsx` workbooks in `TestCases/`, including Excel date serials, shared text strings, worksheet references, and grid-cell rows.\n\n**Analysis performed:** decodes Excel serial dates and column references, then provides a read-only custom `XLSX` reader. This lets the workflow inspect large workbooks without requiring `openpyxl` or modifying the source files."),
    ("def table", "# 3. Table extraction and source parsing\n\n**Data used:** `01 Introduction.xlsx` for the four uncertainty parameters and `02 Field Production.xlsx` for observed `RAMP_History` plus 100 simulated gas, oil, and water cumulative/rate tables.\n\n**Analysis performed:** converts worksheets into compact in-memory tables, assigns the 70/15/15 case partition, preserves dates and missing values, and keeps observed field history separate from simulated cases."),
    ("def qtr_rates", "# 4. Reporting-time convention\n\n**Data used:** observed and simulated cumulative gas, oil, and water production from `02 Field Production.xlsx` at common quarterly reporting dates.\n\n**Analysis performed:** derives interval-average rates as cumulative-volume change divided by elapsed days. This creates comparable oil, water, and gas responses without arbitrarily shifting sparse simulator timestamps or directly comparing unlike boundary-rate conventions."),
    ("def metrics", "# 5. Evaluation metrics\n\n**Data used:** the 40 quarterly interval-average oil, water, and gas rate values for an observed or simulated/predicted case.\n\n**Analysis performed:** calculates MAE, RMSE, normalized RMSE, and a combined oil-water history-match score. Gas remains a separate diagnostic so a near-redundant hydrocarbon signal is not double-counted in the matching objective."),
    ("def model_suite", "# 6. Leakage-safe proxy model comparison\n\n**Data used:** four uncertainty inputs—fault transmissibility, porosity multiplier, permeability multiplier, and aquifer pore volume—from `01 Introduction.xlsx`; production-response curves from `02 Field Production.xlsx`.\n\n**Analysis performed:** trains Ridge-quadratic, Extra Trees, and nearest-neighbour proxy models on Cases 1–70 only. It compares their predictions against Cases 71–85 to select a compact model before the separate Case 86–100 test evaluation."),
    ("def exp_forecast", "# 7. Conditional decline forecast\n\n**Data used:** late-history interval rates from the observed field and selected supplied simulation cases, ending on 2008-01-01.\n\n**Analysis performed:** fits a constrained exponential continuation for oil and water and applies each realization's historical gas/oil relationship to gas. It creates a 2008–2028 conditional scenario extrapolation; it does not claim future simulator validation."),
    ("def fill_template", "# 8. Template writer\n\n**Data used:** `09 Template Deliverable.xlsx` and calculated quarterly cumulative gas, oil, and water forecast trajectories for ten selected output realizations.\n\n**Analysis performed:** copies the official template and writes only numerical forecast values into its existing ten sheets, preserving the required date layout, column order, and formatting. It then supports reopening the export for quality checks."),
    ("def main", "# 9. End-to-end workflow\n\n**Data used:** every challenge workbook: nomenclature/uncertainty values, field production, all train/validation/test grid-case workbooks, and the submission template.\n\n**Analysis performed:** fully traverses all 100 grid sheets through the reusable strict-header spatial extractor; validates active masks, duplicate keys, sentinels, coordinates, saturation checks, and cache provenance; produces shared geometry, active-cell Parquet properties, summaries, and selector-driven figures; then runs the separate production modelling workflow without using test outcomes for spatial feature selection."),
]

def markdown(text):
    return {"cell_type": "markdown", "metadata": {}, "source": [line + "\n" for line in text.splitlines()]}

def code(text):
    return {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": [line + "\n" for line in text.splitlines()]}

def main():
    source = SOURCE.read_text()
    starts = [(source.index(token), title) for token, title in SECTIONS if token in source]
    starts.sort()
    cells = [markdown("""# DataWorks 2026 analysis notebook

This is the documented notebook form of `run_analysis.py`. It follows the setup, run instructions, data boundaries, outputs, and reproducibility rules in `README.md`.

## Requirements

- Python 3.12 or compatible Python 3 version
- Packages in `analysis_codes/requirements.txt`

Install dependencies from the challenge workspace root:

```bash
python3 -m pip install -r analysis_codes/requirements.txt
```

## Run

Run the cells from top to bottom while the current working directory is the challenge workspace root (`dwc26 2`). The workflow reads only `TestCases/` and does not modify any supplied workbook. It prints eight timestamped progress stages.

Intermediate cached grid summaries are written to `work/`; final reports, model artifacts, validation tables, forecast tables, and `09 Template Deliverable_COMPLETED.xlsx` are written to `outputs/`. Power BI-ready CSV tables are written to `powerbi_ready_data/`.

## Reproducibility and forecast boundary

The random seed is `20261015`. Cases 1–70 train the model, Cases 71–85 select it, and Cases 86–100 provide a held-out final evaluation. The 2008–2028 result is a conditional scenario extrapolation because no future simulator labels or runnable numerical simulator are supplied; its spread is not a calibrated probability interval.
""")]
    for i, (position, title) in enumerate(starts):
        end = starts[i + 1][0] if i + 1 < len(starts) else len(source)
        cells.extend([markdown(title), code(source[position:end].rstrip())])
    notebook = {
        "cells": cells,
        "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}, "language_info": {"name": "python", "version": "3.12"}},
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    DESTINATION.write_text(json.dumps(notebook, indent=2))
    print(f"Wrote {DESTINATION}")

if __name__ == "__main__":
    main()
