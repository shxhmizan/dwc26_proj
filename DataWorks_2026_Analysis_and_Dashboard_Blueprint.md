# DataWorks 2026: analysis and dashboard blueprint

Prepared for the team on 15 October 2026, using the supplied kickoff, README, and every workbook in `TestCases`.

## Recommendation

Build a **Reservoir History Matching and Forecast Decision Dashboard**. Its central question should be:

> Which reservoir descriptions reproduce the observed field behavior, what production range do they imply under stated future assumptions, and how much produced water must the operation handle?

The strongest story combines a validated machine-learning proxy, defensible history matching, a twenty-year scenario forecast, and an explanation of uncertainty. A generic production dashboard would cover only a small part of the challenge.

This blueprint distinguishes measured workbook findings from recommended analyses. The case comparisons and exploratory calculations below are completed. A trained ML proxy, optimized reservoir ensemble, final twenty-year forecast, and Power BI file have not been built.

## 1. What the challenge asks

The kickoff describes a **synthetic reservoir dataset**, despite the competition's broader real-world-data framing. Slides 25–26 state four objectives: map reservoir parameters to production responses, find parameter values that reduce mismatch with observations, reproduce historical behavior, and forecast the next twenty years. Slide 31 asks for the best ten forecast cases.

The supplied template contains ten output slots, each with 80 quarterly dates from **1 April 2008 to 1 January 2028** and cumulative gas, oil, and water production. These dates are the synthetic model's forecast horizon. The 2026 competition date does not move the model's forecast origin from 2008.

The README specifies source/model files, a PowerPoint document, a Power BI dashboard sourced from the completed template, and a seven-minute video. It specifies Power BI **2.154.1260.0, 64-bit, May 2026, or earlier**. The attached kickoff's deliverables slide places **16 October** under documentation and **20 October** under the remaining deliverables; slide 20 gives the overall submission close as **3 PM on 20 October**. Check the organizer portal for updates to those attached-deck dates. No portal verification was performed in this review.

Keep challenge materials within the permitted competition workflow. The README prohibits external publication of the materials. Its video requirement and confidentiality wording should be reconciled with the organizer before exposing raw data or detailed starter-kit content in a public video.

## 2. Dataset inventory and relationships

| Workbook | Contents verified | Analytical role |
|---|---|---|
| `01 Introduction.xlsx` | `Nomenclature`; `Uncertainty Values` with 100 cases and four parameters | Data dictionary and case-level features |
| `02 Field Production.xlsx` | `Plots`, a 41-row quarterly observed history table, and six wide tables for oil/gas/water rates and cumulative volumes | Observed targets and simulated production responses for all 100 cases |
| `03 Train Cases 1.xlsx` | Cases 1–20; 29 columns and 90,365 grid rows per case | Training reservoir properties |
| `04 Train Cases 2.xlsx` | Cases 21–40; same structure | Training reservoir properties |
| `05 Train Cases 3.xlsx` | Cases 41–60; same structure | Training reservoir properties |
| `06 Train Cases 4.xlsx` | Cases 61–70; same structure | Training reservoir properties |
| `07  Validation Cases.xlsx` | Cases 71–85; same structure | Model selection and generalization checks |
| `08 Test Cases.xlsx` | Cases 86–100; same structure | Locked final evaluation |
| `09 Template Deliverable.xlsx` | Ten sheets named Case 1–Case 10; 80 forecast dates on each | Submission format for ten selected or optimized forecast realizations |

The six grid workbooks contain **9,036,500 grid rows** altogether. Their size does not mean there are millions of independent reservoir realizations: there are **70 independent training cases**.

Join the files by a canonical integer `CaseID`: `Case 1` in the grid and uncertainty files corresponds to `Case_1` in the production tables. Keep `RAMP_History` as observed data, outside the simulated-case feature table. The ten template tabs are output slots; maintain a separate mapping to source CaseID or optimized parameters rather than assuming they require source Cases 1–10.

The README describes the test workbook as training data, but the kickoff explicitly specifies 70 train, 15 validation, and 15 test cases. Preserve that split pending clarification. All 100 response curves are accessible inside the production workbook, so accidental leakage is especially easy.

### Case-level uncertainty inputs

| Parameter | Observed range across all 100 cases | Physical question |
|---|---:|---|
| Fault transmissibility | 0.050109–0.149950 | How strongly can reservoir compartments communicate? |
| Porosity multiplier | 0.801219–1.494027 | How does pore storage affect sustained production? |
| Permeability multiplier | 0.520527–9.784546 | How does the flow capacity influence production response? |
| Aquifer pore volume | 53.952910–199.835200 | How much external water support can affect performance? |

These are observed design ranges, not established probability distributions or guaranteed physical bounds. The aquifer-volume column has no explicit unit. Do not assign it a unit or assume that it is a multiplier without confirmation.

### Grid information

Each case uses a **53 × 55 × 31** grid. There are **42,512 cells with positive pore volume and valid porosity**, and **47,853 excluded cells**, using an explicit analysis mask `PORV > 0 and PORO != -999.25`.

The 29 columns cover grid indices and coordinates; pore volume, porosity, directional permeability and transmissibility; NTG; fluid and PVT region identifiers; saturation endpoints; pressure; water, oil, and gas saturation; and solution/vapor ratios. Two fluid regions and two PVT regions are present. Do not interpret those identifiers as named geological formations or fault blocks without supporting metadata.

All 100 complete grid sheets were scanned. Coordinates are identical across cases. Only **PORV, PORO, PERMX, PERMY, TRANX, and TRANY** change between cases. The supplied pressure, saturations, PERMZ, TRANZ, region identifiers, and saturation endpoints do not change across cases. Active-cell NTG is 1; SGAS and RV are 0 in the supplied snapshot.

The files therefore support spatial reservoir inspection and compact feature extraction. They do not supply a pressure or saturation evolution sequence. The snapshot's time is not stated. Avoid calling it a verified initial state until confirmed.

## 3. Findings that should shape your solution

### A. Production decline and water handling are the main operating story

The observed history runs from **1 January 1998 to 1 January 2008**, with 41 quarterly observations. The first positive quarterly oil rate is **15,507.77 STB/day on 1 October 1998**. By 1 January 2008:

| Measure | Value |
|---|---:|
| Oil rate | 5,066.679 STB/day |
| Gas rate | 1,838.962 MSCF/day |
| Produced-water rate | 7,926.362 STB/day |
| Water-injection rate | 9,326.61 STB/day |
| Water cut, water / (oil + water) | 61.00% |
| Oil-rate reduction from the observed peak | 67.33% |

Water first exceeds oil in the quarterly observations on **1 April 2006**. This is the first observed crossing, not an exact continuous-time breakthrough date.

Observed cumulative production at 1 January 2008 is **38,378,316.971 STB oil**, **13,942,537.324 MSCF gas**, and **12,814,432.283 STB water**. These are starting anchors for life-to-date cumulative forecasts, subject to confirmation of the submission convention.

Interpretation: the rising water fraction makes water-handling burden and the timing of production decline useful dashboard outputs. These trends alone cannot identify whether aquifer encroachment, injected-water movement, or another mechanism dominates.

### B. Resolve a reporting-time mismatch before ranking cases

At 1 October 1998, the observed oil rate is 15,507.77 STB/day while Case 69's simulator boundary rate is zero. Comparing those rate cells directly creates a large apparent error. Yet the cumulative volume produced from 1 October 1998 to 1 January 1999 implies almost exactly **15,507.77 STB/day for both**.

Across the observed history, cumulative increments reproduce the **preceding row's observed rate** to rounding precision: maximum differences are below 0.001 STB/day for oil and water. The observed rate therefore behaves as a forward-period rate, while simulator boundary rates can describe the preceding interval.

Use common intervals:

`Quarter-average rate = (cumulative at quarter end − cumulative at quarter start) / actual days in quarter`

Compare observed and simulated quarter-average rates derived this way. Retain the last supplied instantaneous/forward rate as a distinct observation. Do not shift every series by an arbitrary quarter or smooth away operating changes.

### C. The production tables are sparse time-axis exports

Each production table contains 11,096 populated time rows on a union of native simulator timestamps. A single simulated case has only **156–197 populated samples**, depending on the case. The observed `RAMP_History` column has 41 samples.

Most timestamps include fractional days. A row in the union is not a new observation for every case. Retain each case's nonblank values and full timestamps before aligning to common reporting dates. A blank at another case's timestamp is not a production shutdown and must not become zero. Avoid converting fractional dates to day-only keys before resolving collisions.

All finite supplied rates are nonnegative. Each supplied case/observed cumulative sequence is nondecreasing. The `RAMP_History` quarterly rates exactly match the corresponding `Field Production` rates.

### D. A useful baseline already exists

Using the 70 training cases, I compared rates derived from cumulative increments over the 40 common quarterly intervals. The exploratory score is:

`Score = sqrt(0.5 × MSE_oil / mean(observed_oil²) + 0.5 × MSE_water / mean(observed_water²))`

Each phase's normalized RMSE uses the RMS of the observed interval rates as its denominator. Gas is reported separately because it strongly duplicates oil in this dataset.

| Training case | Combined normalized score | Oil normalized RMSE | Water normalized RMSE |
|---|---:|---:|---:|
| 6 | 4.68% | 2.21% | 6.23% |
| 11 | 4.82% | 2.44% | 6.37% |
| 40 | 4.84% | 2.45% | 6.40% |
| 50 | 4.92% | 2.49% | 6.51% |
| 24 | 5.00% | 2.53% | 6.61% |

This is a historical screening benchmark, not ML test accuracy, a final ten-case selection, or evidence of twenty-year forecasting accuracy. Rankings depend on reporting conventions, phase weights, and which historical period is emphasized. An optimized proxy should improve on this benchmark while passing independent validation.

### E. Porosity is the clearest exploratory parameter signal

Among the **70 training cases**, the Spearman rank correlation between porosity multiplier and cumulative oil at 1 January 2008 is approximately **+0.993**. For cumulative water it is approximately **−0.994**. Gas cumulative has the same ranking as oil cumulative.

This supports a useful initial sensitivity plot and a hypothesis that storage differences strongly influence historical performance. It does not prove causality, universal parameter importance, or that the other inputs can be ignored. Evaluate conditional effects, parameter interactions, correlation among inputs, and out-of-case predictive performance before making those claims.

### F. Gas largely tracks oil in the supplied history

Observed gas–oil ratio stays near **363.3 scf/STB**, with an observed range of approximately 362.95–363.60 scf/STB when oil is positive. Gas rate is recorded in **MSCF/day**, so multiply its ratio to oil by 1,000 to express scf/STB.

A constant-GOR gas forecast is therefore a meaningful baseline. It is not proof that GOR remains constant for twenty years. The history-matching loss should not unintentionally give the same hydrocarbon signal twice the influence of water.

### G. There are no supplied future production labels

Every populated simulated and observed production sequence ends at 1 January 2008. The grid snapshots do not fill that future-label gap. A proxy that reproduces 1998–2008 cannot automatically be described as validated for 2008–2028.

A simple diagnostic illustrates forecast sensitivity. An exponential oil decline fitted to the preceding three years gives two-year forward WAPE of about **14.43%, 2.73%, and 6.60%** at cutoffs in January 2004, 2005, and 2006 respectively. Constant-last-rate baselines give 24.58%, 27.03%, and 16.80%. These are preliminary oil-only backtests using the supplied quarterly rate convention. They justify testing decline models and multiple cutoff dates; they do not validate a twenty-year forecast.

## 4. Recommended analysis programme

| Priority | Analysis | Method | Decision or insight | Recommended visual |
|---|---|---|---|---|
| Essential | Field production evolution | Rates, cumulative volumes, water cut, GOR, decline by period | Understand the field's production stage | Oil/gas/water small multiples with a history cutoff |
| Essential | History-match quality | Common-interval phase errors, cumulative errors, residuals by period | Identify credible reservoir descriptions | Observed-versus-model overlay and case ranking |
| Essential | ML proxy validation | Compare predictions against unseen case responses | Establish whether the model generalizes across reservoirs | Per-phase error distributions and predicted-versus-simulated plots |
| Essential | Twenty-year forecast scenarios | Backtested decline/phase models with explicit operating assumptions | Assess plausible future production ranges | Forecast fan chart and end-horizon cumulative ranges |
| High | Water-handling demand | Water cut, water/oil ratio, total liquids, threshold dates | Identify when water handling may dominate operations | Water-rate and water-cut forecasts with optional capacity line |
| High | Parameter sensitivity and identifiability | Rank plots, conditional response curves, near-optimal parameter ranges | Explain drivers and which uncertainties remain unresolved | Parameter-response scatter plots and before/after ranges |
| High | Forecast robustness | Change fit window, loss weights, model family, and operating assumptions | Show which conclusions survive modelling choices | Scenario comparison and rank-stability chart |
| Optional | Reservoir spatial context | Layer and region summaries of porosity, permeability and pore volume | Explain where storage and flow capacity differ | I–J layer heatmap and vertical section |
| Optional | Economics under assumptions | Forecast volumes with user-entered prices/costs/discount rate | Translate production and water burden into conditional value | Assumption-labelled cash-flow and break-even sensitivity |

For spatial maps, use grid indices until coordinate system and units are confirmed. Use positive pore volume as an active mask and use a logarithmic color scale for positive permeability. A projected coordinate pair does not establish latitude/longitude or a real field location.

Do not identify an optimal drilling location from these files: well locations, completions, controls, and operational constraints are absent. Similarly, a pressure map is available, but a pressure-depletion time series is not.

## 5. Modelling approach that fits this dataset

### Step 1: Build clean, small analytical tables

Create separate logical tables for case parameters, grid-cell features, observed production, simulated production, validation metrics, and forecast results. Keep raw source values intact. Convert `-999.25` to a missing/inactive marker in relevant grid-property columns. Preserve true zeros in transmissibility, gas saturation, and production.

Aggregate grid features by fluid region and layer: total pore volume, pore-volume-weighted porosity, permeability distribution, vertical/horizontal permeability ratio, and transmissibility distributions. Only add features that vary across cases and improve validation. A water-filled aquifer can dominate total pore volume, so distinguish hydrocarbon-occupied and water-occupied pore volumes when explaining storage.

Do not call `sum(PORV × SOIL)` stock-tank oil in place or reserves. Reservoir pore volumes require confirmed units and fluid-volume conversion factors before comparison with surface STB production.

### Step 2: Establish baselines

Use the best supplied training realization, nearest-neighbor interpolation in standardized parameter space, and a regularized linear/quadratic response model. These are reference points for judging additional complexity.

### Step 3: Train a compact historical-response proxy

My preferred first candidate is **curve compression plus Gaussian-process regression**:

1. Align training case production to the common quarterly intervals.
2. Scale oil and water responses so one phase does not dominate.
3. Fit a low-dimensional curve representation, such as PCA, using training cases only.
4. Learn the relationship between the four uncertainty inputs and curve coefficients with regularized regression or a Gaussian process.
5. Reconstruct production curves and check nonnegative rates, monotonic cumulative volume, and residual patterns.

A Gaussian process is a candidate because the independent training set is small and it can produce predictive uncertainty. Its uncertainty is conditional on the chosen model and inputs; it is not the entire geological or twenty-year forecast uncertainty. Compare it against a tree-based regressor and simpler baselines using the validation cases. Do not assume it will win before testing.

An RNN, LSTM, autoencoder, or GNN is an optional research extension. The kickoff lists architectures as examples, not mandatory requirements. With 70 training realizations and no state evolution snapshots, a large neural model creates additional training and validation demands. Grid rows and repeated dates must never be counted as independent reservoir samples to justify it.

### Step 4: History-match within supported parameter space

Use bounded multistart search, differential evolution, or another transparent optimizer against the validated proxy. Normalize residuals by phase, examine oil–water tradeoffs, and use cumulative endpoints as a secondary check. If emphasizing recent performance, define that weighting before selecting the final solution and report its effect.

A rectangular min/max box can contain combinations far from the training designs. Track distance to training cases, inspect uncertainty, and avoid presenting such combinations as well-supported predictions. The sampled design limits are the initial domain for exploration, not license to invent physical limits.

Retain multiple good solutions. History matching may be non-unique: similar production histories can come from different combinations of storage, communication, and aquifer support. Show the set of parameters that remains plausible rather than claiming a uniquely recovered geology.

An optimized proxy response is **surrogate-predicted**. If the organizers provide a numerical simulator, verify shortlisted parameter sets there. The supplied Excel grids alone are not a runnable simulator deck with complete PVT, controls, and well definitions.

### Step 5: Add a forecast model suited to the available labels

If future simulator outputs or a runnable simulator become available, use them to test production beyond the history period. With the present files, the practical path is a **conditional forecast ensemble**:

- Fit decline behavior to appropriate late-history segments of the accepted realizations and observed field history. Compare exponential and bounded hyperbolic/terminal-decline variants through backtesting.
- Model water cut or water/oil ratio jointly with total liquid or oil production, with valid bounds and phase consistency. Do not extrapolate water independently without checking the resulting liquid balance.
- Use constant GOR as a gas baseline and add alternate GOR scenarios only with an explicit rationale.
- Keep the future development schedule explicit: no additional wells, no inferred workovers, and no unmodelled change in injection strategy in the base scenario. The files do not supply enough controls to estimate the causal impact of changing injection.
- Vary accepted parameters, decline windows, forecast model family, and stated operating assumptions to express uncertainty.
- Generate rates on a suitable time grid, integrate using actual elapsed days, and export cumulative values on the template's exact dates.

Do not set twenty-year production to zero merely because an unconstrained regression becomes negative. Use an appropriate constrained model. If production stops at an economic limit, expose the economic assumptions and leave the stopping rule visible.

Distinguish **cumulative since the original production start** from **incremental production during 2008–2028**. The template labels say cumulative, so the recommended working convention is to carry forward the observed 1 January 2008 baseline and add future volumes, while confirming this with the organizer. Do not silently reset cumulative totals to zero.

### Step 6: Validate two separate capabilities

**Case generalization:** train on Cases 1–70, choose settings with Cases 71–85, and evaluate once on Cases 86–100 after the design is fixed. Keep all timestamps from a case in the same partition. Fit scaling, feature selection, and PCA only on training data.

**Time extrapolation:** repeat pseudo-forecast exercises at historical cutoffs, such as 2004, 2005, and 2006. Estimate all forecast parameters using only data available by each cutoff. Report errors by forecast lead time. Do not use later observations to choose the decline start or normalize a pre-cutoff training model.

Report MAE/RMSE in actual phase units, a clearly defined normalized error, WAPE where appropriate, cumulative endpoint error, and uncertainty coverage. Avoid MAPE around zero production. Do not report `100 − error%` as model accuracy.

Neither good case generalization over the historical period nor a two-year backtest proves a twenty-year forecast. Show both capabilities and their limits separately.

### Step 7: Select ten defensible output realizations

Start from a larger pool of near-optimal histories. Screen for physical consistency and supported parameter combinations, then select ten that retain meaningful variation in parameters and forecast outcomes. Explain whether the deliverable cases are original simulations, optimized proxy realizations, or forecast scenarios. Keep a traceable mapping for every output tab.

Do not choose the ten highest oil forecasts or ten nearly identical fitted curves. If probabilistic weights cannot be justified, call the spread an **ensemble/scenario range**. Do not label ten selected curves a calibrated confidence interval.

When using petroleum exceedance notation, P90 is the lower production estimate, P50 the median, and P10 the higher estimate. These correspond to the 10th, 50th, and 90th ordinary quantiles respectively. Keep this convention visible. Compute cumulative-volume quantiles from complete trajectories; integrating a pointwise percentile rate curve generally does not give the same percentile of cumulative volume. Forecast quantiles do not constitute a formal reserves classification.

## 6. Power BI design

Build four main pages. Keep data quality and detailed geology as drill-through views or an optional fifth page.

| Page | Question answered | Core content | Interaction |
|---|---|---|---|
| 1. Field outlook | What is the production outlook and main operational burden? | Observed history, forecast cutoff, oil/gas/water forecasts, cumulative forecast range, water cut | Phase, horizon, and realization selectors |
| 2. History-match evidence | Why should we trust the selected cases? | Observed versus predicted interval rates, cumulative comparison, residuals, case ranking, validation errors | Select a case to update its curves, parameter values, and error breakdown |
| 3. Reservoir uncertainty | What drives the range, and what remains uncertain? | Parameter-response plots, accepted versus original parameter ranges, interaction plots, optional layer heatmap | Select parameter, output metric, region, or layer |
| 4. Water and scenario decisions | When does water handling become limiting, and which conclusions are robust? | Water cut, total liquids, water-rate forecast, scenario comparisons, conditional capacity crossing date | User-entered water capacity and explicitly assumed operating/economic scenarios |

The first page should be understandable without knowing ML terminology. The second should supply evidence for technical judges. The third should connect reservoir properties to outcomes. The fourth should show the operational consequence of the forecast.

Recommended headline measures are: latest observed oil rate and water cut; forecast incremental oil and water volumes for the selected horizon; forecast cumulative gas; validated historical error; and the range of water-capacity crossing dates **only when a capacity assumption is supplied**. Avoid a KPI count that overwhelms the production curves.

Use solid observed curves, visibly different simulated/forecast lines, and a vertical history cutoff at 1 January 2008. Label scenario bands by their actual meaning. Display units beside axes and metrics. Add tooltips containing CaseID, interval dates, source type, model version, and assumptions.

### Data model and calculations

Use the completed template as the main forecast source, as the README requires. In Power Query, combine the ten tabs into a long table with:

`OutputCaseID, Date, GasCumulative_MSCF, OilCumulative_STB, WaterCumulative_STB`

Keep date and case dimensions plus supporting history, case-parameter, and model-metric tables if the organizers permit supporting sources. If the template must be the sole physical workbook, confirm whether additional supporting sheets are allowed before modifying its structure. Preserve the required ten output tabs and their values.

| Measure | Correct calculation |
|---|---|
| Water cut | Water rate / (oil rate + water rate), blank if total liquid is zero |
| Water/oil ratio | Water rate / oil rate, with zero-oil handling |
| GOR in scf/STB | 1,000 × gas rate in MSCF/day / oil rate in STB/day |
| Quarter-average production rate | Difference between adjacent cumulative values / actual days |
| Forecast incremental volume | Selected end cumulative − cumulative at forecast origin |
| Latest cumulative volume | Last relevant cumulative observation, not sum of cumulative rows |
| Annual production volume | Cumulative at year end − cumulative at year start |
| Water per unit oil | Period water volume / period oil volume |

Cases are alternative descriptions of the **same field**. Never add production from ten cases as if they were ten assets. Display the selected case, a justified weighted ensemble statistic, or clearly defined quantiles. Likewise, do not average percentages across unequal periods when a ratio of aggregate volumes answers the question.

Do not label surface water injection divided by surface liquid production as voidage replacement. Reservoir-condition conversions and PVT information are required for a defensible voidage calculation.

## 7. Data issues and questions to resolve

| Issue | Action |
|---|---|
| `-999.25` sentinels | Mask by property and use positive PORV/valid PORO for the active-cell analysis; preserve real zeros |
| Sparse case timestamps and fractional days | Reshape per case, retain valid samples, then align or integrate |
| Observed/simulator rate timing | Use common cumulative increments; document the demonstrated forward-period convention |
| Nomenclature conflicts | `SWCR` is described as critical gas in the dictionary but critical water in the case headers; several following descriptions appear shifted. Confirm definitions before using them physically |
| Missing property units and snapshot time | Confirm PORV, pressure, permeability, coordinates, aquifer-volume units, and the timestamp represented by state columns |
| Test-file description conflicts with kickoff | Preserve the 70/15/15 split; obtain organizer clarification if needed |
| All case outputs are visible in one workbook | Enforce splits in code before fitting any transforms or models |
| No future simulation targets | Clearly distinguish historical proxy accuracy from assumption-dependent twenty-year extrapolation |
| Ten output cases are not explicitly mapped | Clarify whether original cases, optimized parameter sets, or representative forecast scenarios are expected |
| No costs, prices, capacities, well controls, or complete PVT tables | Use only clearly labelled external assumptions for scenario economics; avoid unsupported operating recommendations |
| No demonstrated probability distribution for uncertainty parameters | Do not treat min/max design limits or selected case counts as calibrated probabilities |

## 8. Scope and execution priorities

The highest-value sequence is:

1. Freeze data definitions, case splits, and interval alignment. Reproduce the baseline ranking.
2. Build and validate the compact proxy. Show why it improves over simple alternatives.
3. History-match an ensemble and document non-unique parameter solutions.
4. Backtest forecasting models and create the conditional twenty-year forecast ensemble.
5. Populate the exact ten-tab cumulative template and verify every output date, unit, and cumulative progression.
6. Build the four dashboard pages around the same exported results.
7. Make the slides and seven-minute video tell the same story and use consistent figures.

Possible team workstreams are data quality/engineering, proxy modelling/history matching, forecasting/uncertainty, and Power BI/storytelling. Agree on keys, units, and forecast-origin conventions before splitting the work.

Given the attached 16 October documentation date, prioritize a clear problem definition, dataset interpretation, timing correction, baseline results, proposed methodology, and honest limitations immediately. Do not label planned model performance as completed results. Then update the remaining deliverables according to the current organizer instructions.

If time becomes tight, finish the validated historical proxy, a transparent forecast baseline, uncertainty/scenario comparisons, and four coherent pages. Add 3D graphics, complex neural networks, and economics only after the required outputs are correct.

## 9. Evidence and references

Local sources reviewed:

- `README.md`: topic, deliverables, Power BI version, dashboard source, video instructions, confidentiality.
- `DataWorks 2026 - Kick Off.pptx`: slides 20, 24–32, and 34–35; SmartArt text in the problem, objectives, and workflow slides was included in the review.
- `01 Introduction.xlsx`: both sheets, including the complete 100-case uncertainty table.
- `02 Field Production.xlsx`: observed table and all six numeric production tables, including every case and the observed column.
- `03 Train Cases 1.xlsx` through `08 Test Cases.xlsx`: all 100 grid sheets, all 29 numeric columns, all 90,365 data rows per sheet.
- `09 Template Deliverable.xlsx`: all ten sheet layouts and date sequences.

The audit checked numeric completeness, sentinel patterns, active-cell counts, grid consistency, changing versus constant properties, nonnegative rates, monotonic cumulative sequences, date ranges, and reporting-interval consistency. It did not validate the data against a simulator, an external field system, or a full physical model. Grid saturation sums equal one in the analysed active cells, but this is not a full material-balance verification.

Method references used to check the recommendations:

- [SLB: history matching](https://glossary.slb.com/en/terms/h/history_matching) describes matching historical behavior while respecting reservoir properties.
- [Scikit-learn: common pitfalls and data leakage](https://scikit-learn.org/stable/common_pitfalls.html) supports fitting preprocessing only on training data.
- [Scikit-learn: grouped cross-validation](https://scikit-learn.org/stable/modules/cross_validation.html) explains keeping related samples together when measuring generalization.
- [Scikit-learn: Gaussian processes](https://scikit-learn.org/stable/modules/gaussian_process.html) documents probabilistic regression and its dimensionality limitations.
- [SLB: oil formation volume factor](https://glossary.slb.com/en/Terms/o/oil_formation_volume_factor.aspx) explains the reservoir/surface volume distinction.
- [SPE: probabilistic and deterministic methods](https://jpt.spe.org/probabilistic-and-deterministic-methods-applicability-unconventional-reservoirs) describes petroleum exceedance notation. This blueprint does not make a reserves classification.
