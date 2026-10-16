# Power BI implementation specification

Use `09 Template Deliverable_COMPLETED.xlsx` as the main forecast source, as required by the README. In Power Query combine Case 1–Case 10 and unpivot only if needed into `OutputCaseID, Date, GasCumulative_MSCF, OilCumulative_STB, WaterCumulative_STB`. Supporting tables are `powerbi_forecast_long.csv`, `selected_realization_mapping.csv`, `case_parameters.csv`, `historical_case_screening.csv`, and `model_comparison_validation.csv`.

## Pages

1. **Field outlook:** history plus forecast cumulative/rate curves. Question: range and timing of oil decline/water burden. Filters: output case, phase, date.
2. **History-match evidence:** observed vs supplied-case interval rates, residual and score table. Question: why selected cases are credible?
3. **Reservoir uncertainty:** parameters versus historical/forecast outcomes, with SourceCaseID. Question: which sampled uncertainty combinations span outcomes?
4. **Water/scenario decisions:** water rate, water cut and a What-If capacity parameter labelled as an assumption. Question: when would a user-supplied handling threshold be crossed?

## Measures and safeguards

- Latest cumulative = `CALCULATE(MAX(Forecast[OilCumulative_STB]), LASTDATE('Date'[Date]))`; never sum cumulative values across dates.
- Increment = current cumulative minus previous date cumulative, by output case. Rate = Increment/days in interval.
- Water cut = water rate/(oil rate + water rate), calculated from additive rates, not averaged row ratios.
- Show one realization or percentile/median across alternatives; do not sum output cases as fields. Label spread “scenario/ensemble range”, not confidence interval.
- Rates use STB/d for oil/water and MSCF/d for gas. Cumulatives retain template units.

No verified `.pbix` is produced because Power BI Desktop is not available in this environment.

## Reservoir Spatial Analysis

Load `08_SpatialGeometry.csv` (one row per `CellID = I:J:K`) and `09_SpatialCellProperties.parquet` (one row per active `CaseID, CellID`) with a one-to-many relationship from geometry to properties. Load `10_SpatialCaseSummary.csv`, `11_SpatialLayerSummary.csv`, and `12_SpatialRegionSummary.csv` as pre-aggregated tables. Parquet avoids a very large text CSV and Power Query Desktop supports importing local Parquet files. Coordinate, pressure, permeability, and pore-volume units are unspecified; do not use a geographic basemap.

Geometry has one grid-cell row. Properties has one active-cell row per realization. The summary tables use active-cell count, total pore volume, PV-weighted porosity/saturations, and descriptive permeability percentiles. Do not sum different CaseIDs as fields. Directional permeability ratios are ratios of medians, not effective permeability.

Create a **Reservoir Spatial Analysis** page with Case, property, and K-layer slicers; an I-J Matrix (rows J, columns I) with background-colour conditional formatting as a native heatmap; a fixed-I/fixed-J Matrix using K ordering only; a layer/region summary table; and a case-comparison matrix. Continuous raster heatmaps or linked cross-section charts require an approved custom or Python/R visual. Leave missing comparisons blank, and compute percentage difference only for nonzero references.

Static verified views are in `outputs/spatial_figures/`. They use grid indices because CRS/EPSG, Z direction, and snapshot timestamp are not documented. Permeability maps use log10 only for positive values; zeros are marked separately and inactive cells are masked.
