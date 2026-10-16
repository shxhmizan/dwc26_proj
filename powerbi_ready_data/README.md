# Power BI-ready data

This folder contains the prepared CSV tables for the DataWorks 2026 dashboard. Run the analysis first from the workspace root:

```bash
python3 analysis_codes/run_analysis.py
```

The script regenerates these tables from the supplied `TestCases/` workbooks. It reads the challenge inputs without modifying them.

`09_SpatialCellProperties.parquet` is generated locally and intentionally excluded from Git because it exceeds GitHub's normal per-file size limit. Generate it with `MPLCONFIGDIR=/tmp/dwc_mpl python3 analysis_codes/run_analysis.py --spatial-only` before importing the spatial page.

## Power BI configuration

1. In Power BI Desktop, select **Get data > Text/CSV** and load the numbered forecast tables plus the numbered spatial CSV tables. For `09_SpatialCellProperties.parquet`, select **Get data > Parquet**; it is intentionally Parquet because the active-cell fact table is large.
2. In Power Query, set `Date` to **Date**, `CaseID`, `SourceCaseID`, `OutputCaseID`, `I`, `J`, and `K` to **Whole number**, and production/property fields to **Decimal number**. Keep `CellID` as text.
3. Create a `Date` table covering 1998-01-01 through 2028-01-01 and mark it as the Date table.
4. Create these relationships:

| From | To | Relationship | Purpose |
|---|---|---|---|
| `Date[Date]` | `01_ForecastCumulative[Date]` | 1 to many | Filter forecast dates |
| `Date[Date]` | `03_ObservedHistoryRates[Date]` | 1 to many | Filter observed history |
| `02_OutputCaseMapping[OutputCaseID]` | `01_ForecastCumulative[OutputCaseID]` | 1 to many | Select one forecast realization |
| `04_CaseParameters[CaseID]` | `05_HistoryMatchMetrics[CaseID]` | 1 to many | Explain history-match sensitivity |
| `04_CaseParameters[CaseID]` | `02_OutputCaseMapping[SourceCaseID]` | 1 to many | Show selected realization parameters |
| `08_SpatialGeometry[CellID]` | `09_SpatialCellProperties[CellID]` | 1 to many | Attach one shared I/J/K geometry row to active cells across realizations |
| `04_CaseParameters[CaseID]` | `09_SpatialCellProperties[CaseID]` | 1 to many | Filter spatial properties by official train/validation/test partition |
| `04_CaseParameters[CaseID]` | `10_SpatialCaseSummary[CaseID]` | 1 to many | Filter case summaries |

Use single-direction filtering from dimensions to facts. Do not connect `HistoryMatchMetrics` directly to `ForecastCumulative`; use `OutputCaseMapping` as the traceability bridge.

## Step-by-step tutorial

Follow these steps in Power BI Desktop after running the spatial analysis. This creates a report from the delivered tables; it does **not** create or imply that a `.pbix` has already been supplied.

### 1. Import the data

1. Open Power BI Desktop and select **Get data**.
2. Select **Text/CSV**. In this folder, load the seven numbered CSVs plus `08_SpatialGeometry.csv`, `10_SpatialCaseSummary.csv`, `11_SpatialLayerSummary.csv`, `12_SpatialRegionSummary.csv`, and `13_SpatialPropertyRanges.csv`.
3. Select **Get data > Parquet** and load `09_SpatialCellProperties.parquet`. This is the active-cell fact table and is intentionally not converted to CSV.
4. In Power Query, set `Date` fields to **Date**; set `CaseID`, `OutputCaseID`, `SourceCaseID`, `I`, `J`, and `K` to **Whole number**; and set property/value fields to **Decimal number**. Keep `CellID` as **Text**.
5. Select **Close & Apply**.

### 2. Create the Date dimension

1. Select **Modeling > New table**.
2. Paste the following DAX, then select **Table tools > Mark as date table** and choose `Date`.

```DAX
Date = CALENDAR ( DATE ( 1998, 1, 1 ), DATE ( 2028, 1, 1 ) )
```

3. In Model view, connect `Date[Date]` to `01_ForecastCumulative[Date]` and `03_ObservedHistoryRates[Date]`. Use one-to-many, single-direction relationships.

### 3. Build the model relationships

1. Open **Model view**.
2. Create the relationships in the table above, especially `08_SpatialGeometry[CellID]` (one) to `09_SpatialCellProperties[CellID]` (many).
3. Connect `04_CaseParameters[CaseID]` (one) to each spatial case-level table and to `09_SpatialCellProperties[CaseID]` (many).
4. Keep filters single direction, from the dimension/geometry table to the fact table. Do not directly relate alternative forecast cases to spatial cases as though they are additive fields.

### 4. Build the Reservoir Spatial Analysis page

1. Add a new report page named **Reservoir Spatial Analysis**.
2. Add slicers for `04_CaseParameters[CaseID]`, `11_SpatialLayerSummary[K]`, and a disconnected property selector if you need one visual to switch measures. A simple first version can use separate measures/visuals for PORO, PERMX, PORV, SOIL, and SWAT.
3. Add a **Matrix** visual for the I-J heatmap. Put `08_SpatialGeometry[J]` in **Rows**, `08_SpatialGeometry[I]` in **Columns**, and one selected property measure in **Values**.
4. In the Matrix formatting pane, apply **Cell elements > Background color > fx** to the value. Choose a colour scale. This is the native heatmap method; it uses grid indices, not a geographic map.
5. Add a second Matrix for a vertical section. Filter it to one I or J index, use the other horizontal index in Columns, put `08_SpatialGeometry[K]` in Rows, and use the same property measure in Values. Label the K axis “K index (ordering only)”; do not label it depth or elevation.
6. Add a table or column chart from `11_SpatialLayerSummary` and `12_SpatialRegionSummary` for active-cell count, total pore volume, PV-weighted porosity, and permeability P50/P10/P90.

### 5. Add safe property measures

Create one measure per displayed property. For example:

```DAX
Selected Porosity = AVERAGE ( '09_SpatialCellProperties'[PORO] )

Selected PERMX = AVERAGE ( '09_SpatialCellProperties'[PERMX] )

Total Pore Volume = SUM ( '09_SpatialCellProperties'[PORV] )
```

`Selected Porosity` and `Selected PERMX` describe the selected cell(s); they are not effective-reservoir properties. For layer/region cards, prefer the precomputed PV-weighted and percentile fields in the summary tables. Do not sum values across CaseIDs.

### 6. Add a case-comparison view

1. Create two disconnected Case selector tables, one for the reference case and one for the comparison case, so a user can choose both independently.
2. Build comparison measures by filtering `09_SpatialCellProperties` for each selected CaseID while retaining the shared `CellID` context.
3. Define absolute difference as comparison minus reference.
4. Define percentage difference only if the reference value is not blank and is nonzero. Return `BLANK()` for unmatched or zero-reference cells; never replace them with zero difference.
5. Display the difference in another I-J Matrix with a diverging conditional colour scale centred on zero.

### 7. Validate before presenting

1. Select Case 1 and K 1. Compare the Matrix footprint and values against `../outputs/spatial_figures/heatmaps_case_1_k_1.png`.
2. Change CaseID, K, property, and fixed section index one at a time. Confirm the Matrix values change rather than only the title/slicer state.
3. Check `10_SpatialCaseSummary.csv`: each case should show 90,365 total cells, 42,512 active cells, and zero duplicate spatial keys for this delivered extraction.
4. Confirm no geographic basemap is used and that unspecified source units are labelled as such.
5. Review `../outputs/SPATIAL_DATA_AUDIT.json` and `../outputs/SPATIAL_CROSS_CASE_CONSISTENCY.json` before describing spatial patterns.

## Tables and functions

| File | Grain | Function in dashboard |
|---|---|---|
| `01_ForecastCumulative.csv` | Output case and forecast quarter | Main forecast fact table. Contains cumulative gas (MSCF), oil (STB), and water (STB) for ten conditional scenarios. Use it for field outlook and scenario comparison. |
| `02_OutputCaseMapping.csv` | One row per output case | Maps each required template tab to the supplied source case and its historical score. Supports traceability and slicers. |
| `03_ObservedHistoryRates.csv` | Historical quarter | Observed oil, water, and gas interval-average rates plus calculated water cut. Use it to contrast 1998–2008 history against forecast. |
| `04_CaseParameters.csv` | One row per simulation case | Four uncertainty parameters and the train/validation/test partition. Use for sensitivity, coverage, and selected-case parameter views. |
| `05_HistoryMatchMetrics.csv` | One row per simulation case | Oil, water, gas MAE/RMSE/normalized RMSE and combined oil-water history-match score. Use for ranking and residual-quality views. |
| `06_ProxyModelValidation.csv` | One row per candidate model | Validation-only model comparison. Use for technical evidence, not for field forecast aggregation. |
| `07_SurrogateHistoryMatches.csv` | One row per water-loss weighting | Bounded optimized parameter combinations from the surrogate search. Use to illustrate non-uniqueness and sensitivity to the loss weights. |
| `08_SpatialGeometry.csv` | One row per CellID / I-J-K grid cell | Shared grid geometry and source provenance. X/Y/Z are retained but their CRS, units, and Z direction are unspecified. Do not use a map visual. |
| `09_SpatialCellProperties.parquet` | One active cell per CaseID and CellID | Large spatial fact table: reservoir properties, regions, saturations, pressure, and source sheet. Inactive cells are absent by design; use geometry for the visible grid footprint. |
| `10_SpatialCaseSummary.csv` | One case | Full-grid counts, sentinel/missing checks, ranges, pore volume, PV-weighted summaries, and descriptive permeability distributions. |
| `11_SpatialLayerSummary.csv` | One case and K layer | Active-cell, pore-volume, PV-weighted, and directional permeability summary by grid layer. |
| `12_SpatialRegionSummary.csv` | One case and FIPNUM/PVTNUM combination | Corresponding active-cell and pore-volume summary by source region identifiers. |
| `13_SpatialPropertyRanges.csv` | One case and property | Valid active-property min/max and count; use for diagnostics rather than reservoir aggregation. |

## Recommended measures

The forecast table stores cumulative volumes. Never sum cumulative values over time or across output cases.

```DAX
Latest Oil Cumulative STB =
MAX ( '01_ForecastCumulative'[OilCumulative_STB] )

Oil Increment STB =
VAR CurrentValue = MAX ( '01_ForecastCumulative'[OilCumulative_STB] )
VAR PreviousValue =
    CALCULATE (
        MAX ( '01_ForecastCumulative'[OilCumulative_STB] ),
        DATEADD ( 'Date'[Date], -1, QUARTER )
    )
RETURN
    CurrentValue - PreviousValue
```

For water cut, derive oil and water rates from same-case cumulative increments and calculate `WaterRate / (OilRate + WaterRate)`. Do not average row-level water-cut ratios. When comparing scenarios, choose one output case or calculate a median/quantile across cases; do not sum alternative cases as if they are additive fields.

The scenario range is not a calibrated probability interval or a reserves classification. A water-capacity line must be a labelled What-If input because no facility capacity was supplied.

## Reservoir Spatial Analysis page

Add CaseID, property, and K slicers. Use a native **Matrix** with J as rows, I as columns, and a selected property measure as Values; apply background conditional formatting as the I-J heatmap. Use a second Matrix for a fixed-I or fixed-J section with K as the ordered axis; K is not assumed to be physical depth. Pair this with layer/region summary visuals and a case-comparison matrix.

Do not sum values across alternative CaseIDs. Porosity and saturation summary columns are pore-volume weighted; permeability columns are descriptive distributions, not effective permeability. For comparison, join through `CellID`, leave unmatched cells blank, and calculate percentage change only where the reference denominator is nonzero. Positive PERMX maps may use log10 scaling; zero permeability is meaningful and must not be converted to missing.

The source does not document coordinate reference system, units, Z interpretation, or pressure/saturation snapshot time. Use grid-index displays and label units as unspecified. See `../outputs/POWER_BI_SPECIFICATION.md` for the complete visual design and compatibility notes.
