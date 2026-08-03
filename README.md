# Long-term Martian groundwater outflow

[中文说明](README_ZH.md) · [Interactive English page](index.html) · [中文交互页](index_zh.html) · [Methods](METHODS.md) · [Data provenance](DATA_SOURCES.md) · [Data dictionary](DATA_DICTIONARY.md)

This repository is a bilingual, self-contained research release of a long-term groundwater-outflow extension to the original two-dimensional finite-volume diffusive-wave model. The spatial solver, DEM-controlled storage, lowest-saddle spill, downstream routing and open boundary are retained. Only the source hydrograph and long-duration execution strategy are extended.

The model does not infer or draw the two troughs. The investigator-specified point at `75.937180°E, 18.136689°N` is one equivalent source for their combined conceptual discharge. Total `Q(t)` is applied once; it is never replicated across source cells.

## Interactive front end

- Open [index.html](index.html) for the English interface.
- Open [index_zh.html](index_zh.html) for the Chinese interface.
- Each page switches directly to the other language.
- Both pages are single-file applications with no network requests, external fonts or map services.
- Paper-figure mode, PNG export and parameter-JSON download work locally and on GitHub Pages.

The interactive map is a scenario-communication layer that volume-maps precomputed reference states. It is not a substitute for the exact-run arrays in `data/completed-runs/`.

## Reproduce and validate

Python 3.12 is the reference environment.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
python scripts/validate_repository.py
```

Run an exact low scenario:

```bash
python model/run_exact_longterm.py --scenario low --fresh
```

Run a custom 30-year exponential scenario:

```bash
python model/run_exact_longterm.py --scenario medium --process exponential --qb 300 --q0 3000 --tau-years 3 --duration-years 30 --retention 0.7 --until-years 30 --run-name custom-exp-30y
```

The high run is computationally expensive. Completed low/high maps, per-cell arrays, summaries and numerical audits are supplied so that the published state can be inspected without rerunning it.

## Reference scenarios

| Scenario | Hydrograph | Parameters | T | C | Publication status |
|---|---|---|---:|---:|---|
| Low | Constant baseflow | `Qb=100 m³ s⁻¹` | 10 yr | 0.4 | Complete; usable |
| Medium | Exponential | `Qb=300`, `Q0=3000 m³ s⁻¹`, `tau=3 yr` | 20 yr | 0.7 | Incomplete; excluded from spatial claims |
| High | Staged pulses | `Qb=500`, `Q0=5000 m³ s⁻¹` | 30 yr | 1.0 | Complete; usable |

Only results with both `complete=true` and `paper_usable=true` enter quantitative maps. See [EXCLUSIONS.md](EXCLUSIONS.md).

## Repository contents

- `index.html`, `index_zh.html`: bilingual interactive front end;
- `model/`: exact 2-D runner, solver, hydrographs and regression tests;
- `data/`: canonical model input, CRISM site table, completed arrays and provenance manifest;
- `paper_english/`: manuscript-ready figures, captions, methods text and coordinate audit;
- `assets/figures/`: 300 dpi English/Chinese PNG and LZW TIFF products;
- `scripts/`: repository validation, manifest generation and figure generation;
- `.github/workflows/validate.yml`: automated tests on every GitHub push or pull request.

## Interpretation limits

The implementation tests hydrologic feasibility under prescribed boundary conditions. It does not model erosion, sediment transport, freeze-thaw, three-dimensional aquifer-pressure diffusion or trough-geometry inversion. Here `C` is an effective along-path retention coefficient, not a precipitation-runoff coefficient.

## Citation and licence

Use [CITATION.cff](CITATION.cff) to cite this software release. Source code is © 2026 Zhou Yuhao and licensed under the [MIT License](LICENSE). Author-created documentation, captions, interface design and figure composition are licensed under [CC BY 4.0](LICENSES/CC-BY-4.0.txt) to the extent that the author holds the relevant rights. Underlying HRSC, CTX, CRISM and other third-party planetary content remains governed by its original source terms; see [DATA_SOURCES.md](DATA_SOURCES.md).
