"""从中情景已收敛断点验证60天稳态跳时，结果写入审计JSON。"""

from pathlib import Path
import json
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT.parent / "data"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from hydrographs import SCENARIOS, YEAR_SECONDS
from run_exact_longterm import effective_volume_between
from two_d_diffusive_wave import BASE_DT_S, DiffusiveWave2D, WET_THRESHOLD_M


def restore(data, state):
    model = DiffusiveWave2D(
        data["z400"], data["basin"], data["inlet"], state["h"], dynamic_crop=True
    )
    model.arrival_days[:] = state["arrival_days"]
    model.wet_duration_s[:] = state["wet_duration_s"]
    model.max_depth_m[:] = state["max_depth_m"]
    model.elapsed_s = float(state["elapsed_s"][0])
    model.explicit_stepped_s = model.elapsed_s
    model.supplied_m3 = float(state["supplied_m3"][0])
    model.boundary_outflow_m3 = float(state["boundary_outflow_m3"][0])
    return model


def advance_explicit(model, scenario, fill_years, days):
    target = model.elapsed_s + days * 86_400.0
    while model.elapsed_s < target - 1e-7:
        dt_s = min(BASE_DT_S, target - model.elapsed_s)
        start = fill_years + model.elapsed_s / YEAR_SECONDS
        end = fill_years + (model.elapsed_s + dt_s) / YEAR_SECONDS
        model.step(effective_volume_between(scenario, start, end) / dt_s, dt_s)


data = np.load(DATA_ROOT / "conservative-model.npz")
state = np.load(ROOT / "outputs" / "medium_state.npz")
scenario = SCENARIOS["medium"]
fill_years = float(state["fill_years"][0])

baseline = restore(data, state)
candidate = restore(data, state)
started = time.perf_counter()
advance_explicit(baseline, scenario, fill_years, 120.0)
baseline_runtime = time.perf_counter() - started

started = time.perf_counter()
advance_explicit(candidate, scenario, fill_years, 60.0)
skip_start = fill_years + candidate.elapsed_s / YEAR_SECONDS
skip_end = skip_start + 60.0 / 365.25
skip_volume = effective_volume_between(scenario, skip_start, skip_end)
candidate.advance_verified_steady(skip_volume, 60.0 * 86_400.0)
candidate_runtime = time.perf_counter() - started

baseline_wet = baseline.h > WET_THRESHOLD_M
candidate_wet = candidate.h > WET_THRESHOLD_M
intersection = int(np.count_nonzero(baseline_wet & candidate_wet))
union = int(np.count_nonzero(baseline_wet | candidate_wet))
depth_difference = candidate.h.astype(float) - baseline.h.astype(float)
report = {
    "source_state_postspill_days": float(state["elapsed_s"][0]) / 86_400.0,
    "comparison_days": 120.0,
    "candidate_explicit_days": 60.0,
    "candidate_verified_skip_days": 60.0,
    "wet_mask_iou": intersection / union if union else 1.0,
    "depth_rmse_m": float(np.sqrt(np.mean(depth_difference**2))),
    "depth_max_abs_difference_m": float(np.max(np.abs(depth_difference))),
    "stored_relative_difference": (
        candidate.balance().stored_m3 - baseline.balance().stored_m3
    )
    / baseline.balance().stored_m3,
    "baseline_new_arrival_cells": int(
        np.count_nonzero(np.isfinite(baseline.arrival_days))
        - np.count_nonzero(np.isfinite(state["arrival_days"]))
    ),
    "candidate_new_arrival_cells": int(
        np.count_nonzero(np.isfinite(candidate.arrival_days))
        - np.count_nonzero(np.isfinite(state["arrival_days"]))
    ),
    "baseline_mass_error": baseline.balance().relative_error,
    "candidate_mass_error": candidate.balance().relative_error,
    "baseline_runtime_s": baseline_runtime,
    "candidate_runtime_s": candidate_runtime,
}
report["accepted"] = bool(
    report["wet_mask_iou"] >= 0.995
    and abs(report["stored_relative_difference"]) <= 0.005
    and report["baseline_new_arrival_cells"] <= 2
    and abs(report["candidate_mass_error"]) < 1e-6
)
(ROOT / "outputs" / "steady_acceleration_validation.json").write_text(
    json.dumps(report, indent=2), encoding="utf-8"
)
print(json.dumps(report, indent=2))
