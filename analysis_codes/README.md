# DataWorks 2026 analysis code

This folder contains the reproducible local workflow used to produce the files in `../outputs/`.

## Requirements

- Python 3.12 or compatible Python 3 version
- Packages listed in `requirements.txt`

Install the packages in your preferred isolated environment:

```bash
python3 -m pip install -r analysis_codes/requirements.txt
```

## Run

From the challenge workspace root (`dwc26 2`), run:

```bash
python3 analysis_codes/run_analysis.py
```

The script reads only the supplied Excel files in `TestCases/`. It does not modify them.

During execution it prints eight timestamped progress stages, including data loading, cached grid-audit handling, model comparison, history matching, forecast export, and completion. This makes long runs easy to monitor from a terminal or notebook cell.

It writes intermediate cached grid summaries to `work/` and final deliverables to `outputs/`:

- `09 Template Deliverable_COMPLETED.xlsx`
- `selected_proxy.joblib`
- model validation and frozen test metrics
- history-match, forecast, and Power BI-ready CSV tables
- Markdown reports and the dashboard specification

## Reproducibility notes

The random seed is fixed at `20261015`. The model is trained on Cases 1–70, selected using Cases 71–85, then evaluated once on Cases 86–100. The script reads Excel workbooks through their OOXML contents, so it does not require `openpyxl`.

The completed template is a conditional 2008–2028 forecast extrapolation. The supplied files contain no future simulator labels or runnable numerical simulator, so forecast uncertainty must be interpreted as scenario/ensemble spread rather than a calibrated probability interval.
