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
| `crism_selected_sites.csv` | 3 rows | degrees east/north | legacy pre-model C1, P1 and A1 audit locations; not the accepted HW1–HW3 set |

## Completed-run arrays

Each NPY raster has shape `275 × 342` and follows the computational grid with row 0 at the north edge.

| Suffix | Unit | No-data / dry coding |
|---|---|---|
| `_current_depth_m.npy` | m | 0 for dry cells |
| `_maximum_depth_m.npy` | m | 0 for never-wet cells |
| `_arrival_years.npy` | yr since source start | `NaN` for never reached |
| `_wet_duration_years.npy` | yr | 0 for never wet |

The reporting-wet threshold is strictly greater than `0.05 m`; `0.015 m` is reserved for numerical-front arrival/duration diagnostics. Summary JSON files define the source, scenario parameters, water ledger, checkpoint results, numerical settings and completion flags.

## Accepted browser-display bundle

`data/accepted-v2/accepted_v2_manifest.json` binds the accepted `low_f64_v2` and `medium_f64_v2` summaries to their browser arrays and source/display hashes. Every `.f32` file is a little-endian float32 copy of a `275 × 342` source array for visualization only:

| Browser suffix | Meaning |
|---|---|
| `_current.f32` | final water depth |
| `_maximum.f32` | maximum water depth over the run |
| `_arrival.f32` | first arrival at the 0.015 m numerical-front threshold; NaN if unreached |
| `_duration.f32` | wet duration at the 0.015 m numerical-front threshold |

The manifest also stores HW1–HW3 coordinates, hydrology rows/columns, accepted-medium maximum depths, the `0.05 m` reporting threshold and the source-interpretation boundary. Browser arrays are not a replacement for the authoritative v2 `.npy` arrays.

## Coordinate audit

The source and CRISM coordinates are transformed to the 400 m grid in `model/run_exact_longterm.py`. Paper-map markers are projected from the audited row/column indices in `paper_english/POINT_COORDINATE_AUDIT.md`; they are not manually placed by eye.
