# Executive analysis report

## Evidence-backed result

The supplied data support a history-matching workflow and a **conditional** 20-year extrapolation; they do not include future simulator labels or a runnable simulator. The selected historical proxy is `extra_trees`, chosen using only cases 71–85 after training on cases 1–70. The test set (86–100) was evaluated once after model selection.

The best supplied training history match is Case 6: combined oil/water normalized interval-rate score 4.68%, oil 2.21%, water 6.23%. This is a screening mismatch, not a future forecast accuracy.

At 2008-01-01, observed anchor cumulatives are gas 13,942,537.324 MSCF, oil 38,378,316.971 STB, water 12,814,432.283 STB. Last common interval rates are oil 5,246.80 STB/d, water 7,782.27 STB/d, gas 1,905.58 MSCF/d.

## Method and boundaries

- Active grid mask: `PORV > 0 and PORO != -999.25`; zeros remain valid. Every grid sheet header and its first 100 data rows were audited and reduced to `work/grid_summaries.json`; this bounded audit is not an exact full-grid active-cell count.
- Production comparison uses cumulative increments over the 40 observed reporting intervals; this prevents boundary-rate timing conventions from being mistaken for mismatch. Sparse native timestamps are retained in extraction and no time shift is applied.
- Proxy inputs are the four uncertainty values only. Grid features were audited but excluded from the fitted proxy because the workbook’s changing property fields are generated from the same uncertain descriptions and the sample has only 70 independent cases.
- History matching uses a training-only proxy and bounded differential-evolution searches. Optimized curves are marked surrogate predictions and are not exported as numerical-simulator realizations.
- Forecast tabs use ten diverse, credible supplied cases and a conditional exponential decline continuation fitted to each case’s late history. Gas uses each case’s late-history gas/oil relation. Water follows its own late-history exponential continuation. No changing wells, injection, workovers, economics, or capacity are inferred.

## Forecast limitation

Eight-quarter rolling oil backtests at three cutoffs are in `rolling_oil_decline_backtests.csv`. Forecast spread is a scenario/ensemble range, not calibrated probability or reserves. Backtesting and model metrics concern historical curves, while 2008–2028 remains extrapolation. Confirm with organizers whether the required cumulative convention should anchor to observed 2008-01-01 field totals; that convention is used here.

See `DATA_DICTIONARY_AND_AUDIT.md`, `POWER_BI_SPECIFICATION.md`, and CSV deliverables for details.
