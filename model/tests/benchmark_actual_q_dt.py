"""在长期情景实际流量范围内比较粗时间步与 600 s 基准。"""

from pathlib import Path
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT.parent / "data"
sys.path.insert(0, str(ROOT / "src"))
from two_d_diffusive_wave import DiffusiveWave2D, WET_THRESHOLD_M

data = np.load(DATA_ROOT / "conservative-model.npz")

print("q_m3s,dt_s,runtime_s,wet_iou,depth_rmse_m,stored_rel_difference")
for q in (500.0, 1_000.0):
    baseline = DiffusiveWave2D(
        data["z400"], data["basin"], data["inlet"], dynamic_crop=True
    )
    baseline.advance_constant(q, 30 * 86_400.0, dt_s=600.0)
    base_wet = baseline.h > WET_THRESHOLD_M
    base_stored = baseline.balance().stored_m3
    for dt_s in (1_200.0, 1_800.0, 3_600.0):
        started = time.perf_counter()
        model = DiffusiveWave2D(
            data["z400"], data["basin"], data["inlet"], dynamic_crop=True
        )
        model.advance_constant(q, 30 * 86_400.0, dt_s=dt_s)
        elapsed = time.perf_counter() - started
        wet = model.h > WET_THRESHOLD_M
        union = np.count_nonzero(base_wet | wet)
        intersection = np.count_nonzero(base_wet & wet)
        iou = intersection / union if union else 1.0
        rmse = float(np.sqrt(np.mean((model.h - baseline.h) ** 2)))
        stored_difference = (model.balance().stored_m3 - base_stored) / base_stored
        print(
            f"{q:.0f},{dt_s:.0f},{elapsed:.3f},{iou:.6f},"
            f"{rmse:.6f},{stored_difference:.6g}"
        )
