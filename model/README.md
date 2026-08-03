# Exact two-dimensional runner

This directory contains the finite-volume diffusive-wave runner used for the completed low and high spatial results. Canonical inputs are stored once at repository root in `data/`.

## Run

From the repository root:

```bash
python -m pip install -r requirements.txt
python model/run_exact_longterm.py --scenario low --fresh
python model/run_exact_longterm.py --scenario high --fresh
```

The high scenario is computationally expensive and supports restart files in `model/outputs/`. Existing completed summaries, maps and numerical arrays are supplied in `data/completed-runs/`.

## Tests

```bash
python -m unittest discover -s model/tests -p "test_*.py" -v
```

The long-term extension changes the source hydrograph and execution strategy only. It retains the original 400 m two-dimensional solver, analytical source-depression prefill, 600 s explicit surface-flow step, dynamic dry-domain cropping and verified steady-state skipping.
