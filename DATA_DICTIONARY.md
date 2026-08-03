# Data dictionary

## Canonical inputs

| File / variable | Shape | Unit / coding | Meaning |
|---|---:|---|---|
| `conservative-model.npz:z400` | 275 × 342 | m | 400 m hydrodynamic DEM |
| `basin` | 275 × 342 | 0/1 | source-depression mask |
| `inlet` | 275 × 342 | 0/1 | source weights support; normalized in the solver |
| `spill` | 1 | m | lowest natural saddle elevation |
| `storage` | 1 | m³ | source storage to the spill elevation |
| `outlet` | 2 | row, column | natural spillway cell |
| `z200` | 550 × 684 | m, int16 | display-resolution elevation |
| `precision200` | 550 × 684 | categorical | contributing terrain-source class |
| `q*_d*`, `s*_d*` | 275 × 342 / 3 | quantized depth / m³ | legacy 2-D regression anchors |
| `crism_selected_sites.csv` | 3 rows | degrees east/north | prescribed C1, P1 and A1 locations |

## Completed-run arrays

Each NPY raster has shape `275 × 342` and follows the computational grid with row 0 at the north edge.

| Suffix | Unit | No-data / dry coding |
|---|---|---|
| `_current_depth_m.npy` | m | 0 for dry cells |
| `_maximum_depth_m.npy` | m | 0 for never-wet cells |
| `_arrival_years.npy` | yr since source start | `NaN` for never reached |
| `_wet_duration_years.npy` | yr | 0 for never wet |

The wet threshold is `0.05 m`. Summary JSON files define the source, scenario parameters, water ledger, checkpoint results, numerical settings and completion flags.

## Coordinate audit

The source and CRISM coordinates are transformed to the 400 m grid in `model/run_exact_longterm.py`. Paper-map markers are projected from the audited row/column indices in `paper_english/POINT_COORDINATE_AUDIT.md`; they are not manually placed by eye.
