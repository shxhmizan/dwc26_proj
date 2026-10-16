# Data dictionary and audit

## Source inventory

- 01 Introduction.xlsx: 2 sheets
- 02 Field Production.xlsx: 8 sheets
- 03 Train Cases 1.xlsx: 20 sheets
- 04 Train Cases 2.xlsx: 20 sheets
- 05 Train Cases 3.xlsx: 20 sheets
- 06 Train Cases 4.xlsx: 10 sheets
- 07  Validation Cases.xlsx: 15 sheets
- 08 Test Cases.xlsx: 15 sheets
- 09 Template Deliverable.xlsx: 10 sheets

## Verified structure

- Grid cases: 100 sheets, each summary records columns plus a bounded 100-row property audit in `work/grid_summaries.json`. The typical dimensions are 53 x 55 x 31 = 90,365 cells; do not mistake sampled active-cell counts for a full-grid count.
- Partition: cases 1–70 train, 71–85 validation, 86–100 test (kickoff, slide 28).
- Production: RAMP_History remains separate from cases. Common observed history has 41 quarterly boundaries ending 2008-01-01; derived rate comparison has 40 intervals.
- Template: ten tabs with 80 required quarterly dates from 2008-04-01 to 2028-01-01, columns date/gas cumulative/oil cumulative/water cumulative.
- `-999.25` is treated as an inactive/sentinel property marker only in the documented property context; no zero is converted to missing.

## Important limitations

Grid pressure and saturation fields are static snapshots in these exports, not a time history. Coordinate units/CRS and snapshot time are not documented. Fluid/PVT region IDs are identifiers, not named formations or fault blocks. Nomenclature is retained as source material because labels can conflict with workbook column names.

## Cached provenance

All derived grids are sourced from `TestCases/*.xlsx`; cache creation occurs in `run_analysis.py`, which inspects every grid sheet. No source workbook is written.
