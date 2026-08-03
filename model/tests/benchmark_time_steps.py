"""比较长期加速时间步与原 600 秒结果；本脚本不修改输入数据。"""

from pathlib import Path
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT.parent / "data"
sys.path.insert(0, str(ROOT / "src"))
from two_d_diffusive_wave import DiffusiveWave2D, quantize_depth


data = np.load(DATA_ROOT / "conservative-model.npz")
expected_q = data["q25_d030"]
expected_wet = expected_q > 0
expected_stats = data["s25_d030"]

print("dt_s,runtime_s,wet_iou,quantized_mae,stored_rel_error,balance_error")
for dt_s in (900.0, 1_200.0, 1_800.0, 3_600.0, 7_200.0, 21_600.0):
    started = time.perf_counter()
    model = DiffusiveWave2D(data["z400"], data["basin"], data["inlet"])
    model.advance_constant(25_000.0, 30 * 86_400.0, dt_s=dt_s)
    elapsed = time.perf_counter() - started
    actual_q = quantize_depth(model.h)
    actual_wet = actual_q > 0
    union = np.count_nonzero(expected_wet | actual_wet)
    intersection = np.count_nonzero(expected_wet & actual_wet)
    iou = intersection / union if union else 1.0
    mae = float(np.mean(np.abs(actual_q.astype(float) - expected_q.astype(float))))
    balance = model.balance()
    stored_error = (balance.stored_m3 - expected_stats[0]) / expected_stats[0]
    print(
        f"{dt_s:.0f},{elapsed:.3f},{iou:.6f},{mae:.6f},"
        f"{stored_error:.6g},{balance.relative_error:.6g}"
    )
