# Long-term Martian groundwater outflow

[中文说明](README_ZH.md) · [Accepted low/medium viewer](accepted_runs.html) · [已验收低/中情景中文页](accepted_runs.html?lang=zh) · [Parameter explorer](index.html) · [参数探索器中文页](index_zh.html) · [Methods](METHODS.md) · [Data provenance](DATA_SOURCES.md) · [Data dictionary](DATA_DICTIONARY.md)

This repository is a bilingual, self-contained research release of a long-term groundwater-outflow extension to the original two-dimensional finite-volume diffusive-wave model. The spatial solver, DEM-controlled storage, lowest-saddle spill, downstream routing and open boundary are retained. Only the source hydrograph and long-duration execution strategy are extended.

The prescribed point at `75.937180°E, 18.136689°N` is one equivalent crater-side input applied after source-basin filling at the candidate low-rim outlet. Total `Q(t)` is applied once and is never replicated across source cells. This source does not represent surface flow along the northeast–southwest Nili Fossae trough and does not assume hydraulic delivery through that trough to Jezero's western-delta headwaters.

## Interactive front end

- Open [accepted_runs.html](accepted_runs.html) for the quality-gated low/medium arrays used in the manuscript; add `?lang=zh` for Chinese.
- Open [index.html](index.html) or [index_zh.html](index_zh.html) for the adjustable volume-mapped parameter explorer.
- The accepted viewer exposes maximum depth, final depth, arrival year and wet duration, water ledgers, HW1–HW3, thresholds and PNG export.
- The parameter explorer remains a scenario-communication layer and labels its high preset as legacy exploratory.

The accepted viewer reads hash-locked browser copies from `data/accepted-v2/`; authoritative `.npy` arrays and accepted summaries remain the quantitative record. The adjustable parameter explorer volume-maps older reference states and is not a substitute for accepted exact-run arrays.

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

The accepted low and medium browser assets are supplied so the manuscript state can be inspected without rerunning it. The old high run is retained only as a legacy exploratory sensitivity product because it is not a same-version, fully explicit v2 result.

## Reference scenarios

| Scenario | Hydrograph | Parameters | T | C | Publication status |
|---|---|---|---:|---:|---|
| Low | Constant baseflow | `Qb=100 m³ s⁻¹` | 10 yr | 0.4 | v2 accepted; analytical no-spill |
| Medium | Exponential | `Qb=300`, `Q0=3000 m³ s⁻¹`, `tau=3 yr` | 20 yr | 0.7 | v2 accepted; 2.660227 yr prefill + 17.339773 yr explicit routing |
| High | Staged pulses | `Qb=500`, `Q0=5000 m³ s⁻¹` | 30 yr | 1.0 | Legacy exploratory only; not a v2 manuscript result |

Only the current v2 low and medium records with `complete=true`, `paper_usable=true`, all publication gates true, closed ledgers, and no downstream time skipping enter the accepted viewer. See [EXCLUSIONS.md](EXCLUSIONS.md).

## Repository contents

- `accepted_runs.html`: bilingual exact accepted low/medium viewer;
- `index.html`, `index_zh.html`: bilingual adjustable parameter explorer;
- `model/`: exact 2-D runner, solver, hydrographs and regression tests;
- `data/accepted-v2/`: hash-locked browser copies of accepted low/medium arrays, summaries, maps and manifest;
- `data/`: canonical model input, CRISM site table, legacy completed arrays and provenance manifest;
- `paper_english/`: manuscript-ready figures, captions, methods text and coordinate audit;
- `assets/figures/`: 300 dpi English/Chinese PNG and LZW TIFF products;
- `scripts/`: repository validation, manifest generation and figure generation;
- `.github/workflows/validate.yml`: automated tests on every GitHub push or pull request.

## Interpretation limits

The implementation tests hydrologic feasibility under prescribed boundary conditions. It does not model erosion, sediment transport, freeze-thaw, three-dimensional aquifer-pressure diffusion or trough-geometry inversion. Here `C` is an effective along-path retention coefficient, not a precipitation-runoff coefficient.

## Citation and licence

Use [CITATION.cff](CITATION.cff) to cite this software release. Source code is © 2026 Zhou Yuhao and licensed under the [MIT License](LICENSE). Author-created documentation, captions, interface design and figure composition are licensed under [CC BY 4.0](LICENSES/CC-BY-4.0.txt) to the extent that the author holds the relevant rights. Underlying HRSC, CTX, CRISM and other third-party planetary content remains governed by its original source terms; see [DATA_SOURCES.md](DATA_SOURCES.md).
