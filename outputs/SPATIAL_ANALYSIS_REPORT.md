# Reservoir spatial analysis

## What was measured

All 100 supplied case sheets were fully traversed: 9,036,500 cells in total, or 90,365 cells per case. The observed I/J/K extent is 1:53, 1:55, and 1:31. The documented active-cell rule, `PORV > 0` with finite `PORO != -999.25`, yields 42,512 active cells per case (4,251,200 property rows across cases). Geometry and active masks are identical across the cases; no duplicate `(CaseID, I, J, K)` keys were found.

`SPATIAL_DATA_AUDIT.json` records the case-level header mappings, source sheet, sentinel and missing counts, spatial ranges, coordinate completeness, saturation checks, and duplicate checks. `SPATIAL_CROSS_CASE_CONSISTENCY.json` uses aligned-cell hashes to distinguish varying from constant properties.

## Supported spatial interpretation

The selected layer maps show nonuniform active-cell footprints and heterogeneity in porosity, horizontal permeability, and pore volume. That supports comparing the spatial distribution of these exported properties between realizations. Across aligned active cells, PORV, PORO, PERMX, PERMY, TRANX, and TRANY vary by case, while PERMZ, NTG, TRANZ, FIPNUM, PVTNUM, PRESSURE, SWAT, SOIL, and SGAS are constant in the supplied exports.

This supports a realization-comparison workflow, not an interpretation of named formations, faults, wells, drilling targets, reserves, or fluid movement. Pressure and saturations are treated as static snapshots. The supplied files do not document CRS/EPSG, coordinate units, permeability/pore-volume/pressure units, whether Z is depth or elevation, or snapshot timing. Spatial views therefore use I/J/K indices and no basemap.

## Summary definitions

Layer and region tables aggregate active cells only. Total pore volume is summed. Porosity and SWAT/SOIL/SGAS are pore-volume weighted when their value is valid. Permeability statistics are distributional min/P10/P50/P90/max values; they are not effective reservoir permeability. Directional ratios are `P50(PERMX) / P50(PERMY)` and `P50(PERMX) / P50(PERMZ)` only where their denominators are positive. The optional hydrocarbon-volume proxy is deliberately not calculated or labelled as stock-tank oil in place or reserves.

Case-comparison maps join on I/J/K through `CellID`; unmatched cells are left missing, not changed to zero. Percentage differences are shown only for a nonzero reference value. Positive PERMX is mapped with log10 scaling; zeros are retained and marked separately.
