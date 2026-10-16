# Run guide

Run from this workspace: `python3 analysis_codes/run_analysis.py`. Dependencies: Python 3.12, numpy, scipy, scikit-learn, matplotlib, pyarrow, joblib and the standard library. It reads only `TestCases/` and writes `work/`, `outputs/`, and `powerbi_ready_data/`. Random seed: 20261015.

For the spatial workflow alone, run `MPLCONFIGDIR=/tmp/dwc_mpl python3 analysis_codes/run_analysis.py --spatial-only`. Add `--refresh-spatial` to invalidate a valid cache deliberately. The spatial cache is automatically invalidated when source-workbook fingerprints, parser version, expected Cases 1–100, or full-extraction checks do not match. It writes a shared geometry CSV, active-cell Parquet properties, spatial summaries, audit JSON, and static selector-driven figures.
