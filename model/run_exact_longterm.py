"""在原二维扩散波内核上运行长期地下水情景。

源坑蓄水阶段使用 Q(t) 的解析积分直接跳到溢流时刻；天然溢流以后
严格使用原模型 600 s 有限体积步长。程序支持断点续算，绝不以更换
地表算法换取速度。
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sys
import time

import numpy as np
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent
DATA_ROOT = ROOT.parent / "data"
sys.path.insert(0, str(ROOT / "src"))

from hydrographs import (
    PULSE_STAGES,
    SCENARIOS,
    YEAR_DAYS,
    YEAR_SECONDS,
    inverse_effective_volume_years,
    discharge_m3s,
    raw_volume_m3,
    water_ledger,
)
from two_d_diffusive_wave import BASE_DT_S, DiffusiveWave2D, WET_THRESHOLD_M


LON_MIN = 75.5005961564
LAT_MAX = 18.8499485731
DDEG_200M = 0.003374120972


def point_to_400m(lat: float, lon: float, shape: tuple[int, int]) -> tuple[int, int]:
    x_200 = (lon - LON_MIN) / DDEG_200M - 0.5
    y_200 = (LAT_MAX - lat) / DDEG_200M - 0.5
    row = int(np.clip(np.rint(y_200 / 2), 0, shape[0] - 1))
    col = int(np.clip(np.rint(x_200 / 2), 0, shape[1] - 1))
    return row, col


def read_sites(path: Path, shape: tuple[int, int]) -> list[dict]:
    sites = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            lat = float(row["num_lat_n"])
            lon = float(row["num_lon_e"])
            grid_row, grid_col = point_to_400m(lat, lon, shape)
            sites.append(
                {
                    "site": row["site"],
                    "interpretation": row["interpretation"],
                    "lon_e": lon,
                    "lat_n": lat,
                    "row_400m": grid_row,
                    "col_400m": grid_col,
                }
            )
    return sites


def reservoir_state(
    data,
    effective_volume_m3: float,
    scenario,
    current_years: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """由 DEM 高程-面积-容积关系计算源坑水深、到达和持续时间。"""
    z = np.asarray(data["z400"], dtype=np.float32)
    basin = np.asarray(data["basin"], dtype=bool)
    capacity = float(data["storage"][0])
    target = min(max(float(effective_volume_m3), 0.0), capacity)
    depth = np.zeros_like(z, np.float32)
    arrival = np.full(z.shape, np.nan, np.float32)
    duration = np.zeros(z.shape, np.float32)
    if target <= 0:
        return depth, arrival, duration

    basin_z = z[basin].astype(np.float64)
    lo = float(basin_z.min())
    hi = float(data["spill"][0])
    cell_area = 400.0 * 400.0
    for _ in range(45):
        level = (lo + hi) / 2
        volume = float(np.maximum(level - basin_z, 0).sum() * cell_area)
        if volume < target:
            lo = level
        else:
            hi = level
    level = (lo + hi) / 2
    depth[basin] = np.maximum(level - basin_z, 0).astype(np.float32)

    sorted_z = np.sort(basin_z)
    prefix = np.concatenate(([0.0], np.cumsum(sorted_z)))
    wet_indices = np.flatnonzero(basin & (depth > WET_THRESHOLD_M))
    for flat_index in wet_indices:
        row, col = divmod(int(flat_index), z.shape[1])
        threshold_level = float(z[row, col]) + WET_THRESHOLD_M
        count = int(np.searchsorted(sorted_z, threshold_level, side="left"))
        required_m3 = max(
            (count * threshold_level - prefix[count]) * cell_area,
            0.0,
        )
        arrival_year = inverse_effective_volume_years(
            required_m3,
            scenario.process,
            scenario.qb_m3s,
            scenario.q0_m3s,
            scenario.tau_years,
            scenario.duration_years,
            scenario.retention,
        )
        if arrival_year is not None and arrival_year <= current_years:
            arrival[row, col] = arrival_year
            duration[row, col] = current_years - arrival_year
    return depth, arrival, duration


def save_state(path: Path, model: DiffusiveWave2D, fill_years: float) -> None:
    np.savez_compressed(
        path,
        h=model.h,
        arrival_days=model.arrival_days,
        wet_duration_s=model.wet_duration_s,
        max_depth_m=model.max_depth_m,
        elapsed_s=np.array([model.elapsed_s]),
        explicit_stepped_s=np.array([model.explicit_stepped_s]),
        steady_skipped_s=np.array([model.steady_skipped_s]),
        steady_validations_passed=np.array([model.steady_validations_passed]),
        steady_validations_failed=np.array([model.steady_validations_failed]),
        supplied_m3=np.array([model.supplied_m3]),
        boundary_outflow_m3=np.array([model.boundary_outflow_m3]),
        fill_years=np.array([fill_years]),
    )


def load_state(path: Path, data: np.lib.npyio.NpzFile) -> tuple[DiffusiveWave2D, float]:
    state = np.load(path)
    model = DiffusiveWave2D(
        data["z400"],
        data["basin"],
        data["inlet"],
        initial_depth_m=state["h"],
        dynamic_crop=True,
    )
    model.arrival_days[:] = state["arrival_days"]
    model.wet_duration_s[:] = state["wet_duration_s"]
    model.max_depth_m[:] = state["max_depth_m"]
    model.elapsed_s = float(state["elapsed_s"][0])
    model.explicit_stepped_s = (
        float(state["explicit_stepped_s"][0])
        if "explicit_stepped_s" in state
        else model.elapsed_s
    )
    model.steady_skipped_s = (
        float(state["steady_skipped_s"][0]) if "steady_skipped_s" in state else 0.0
    )
    model.steady_validations_passed = (
        int(state["steady_validations_passed"][0])
        if "steady_validations_passed" in state
        else 0
    )
    model.steady_validations_failed = (
        int(state["steady_validations_failed"][0])
        if "steady_validations_failed" in state
        else 0
    )
    model.supplied_m3 = float(state["supplied_m3"][0])
    model.boundary_outflow_m3 = float(state["boundary_outflow_m3"][0])
    return model, float(state["fill_years"][0])


def effective_volume_between(scenario, start_years: float, end_years: float) -> float:
    return scenario.retention * (
        raw_volume_m3(
            scenario.process,
            end_years,
            scenario.qb_m3s,
            scenario.q0_m3s,
            scenario.tau_years,
            scenario.duration_years,
        )
        - raw_volume_m3(
            scenario.process,
            start_years,
            scenario.qb_m3s,
            scenario.q0_m3s,
            scenario.tau_years,
            scenario.duration_years,
        )
    )


def clone_model(model: DiffusiveWave2D, data) -> DiffusiveWave2D:
    clone = DiffusiveWave2D(
        data["z400"],
        data["basin"],
        data["inlet"],
        initial_depth_m=model.h,
        dynamic_crop=True,
    )
    clone.arrival_days[:] = model.arrival_days
    clone.wet_duration_s[:] = model.wet_duration_s
    clone.max_depth_m[:] = model.max_depth_m
    clone.elapsed_s = model.elapsed_s
    clone.explicit_stepped_s = model.explicit_stepped_s
    clone.steady_skipped_s = model.steady_skipped_s
    clone.steady_validations_passed = model.steady_validations_passed
    clone.steady_validations_failed = model.steady_validations_failed
    clone.supplied_m3 = model.supplied_m3
    clone.boundary_outflow_m3 = model.boundary_outflow_m3
    return clone


def advance_exact_interval(
    model: DiffusiveWave2D,
    scenario,
    fill_years: float,
    duration_s: float,
) -> None:
    target_s = model.elapsed_s + max(float(duration_s), 0.0)
    while model.elapsed_s + 1e-7 < target_s:
        dt_s = min(BASE_DT_S, target_s - model.elapsed_s)
        start_years = fill_years + model.elapsed_s / YEAR_SECONDS
        end_years = fill_years + (model.elapsed_s + dt_s) / YEAR_SECONDS
        effective_q = effective_volume_between(scenario, start_years, end_years) / dt_s
        model.step(effective_q, dt_s)


def next_forcing_boundary_years(scenario, current_years: float, target_years: float) -> float:
    """稳态跳时不得跨越脉冲边界；指数过程每段最多变化10%。"""
    if scenario.process == "pulse":
        boundaries = {0.0, scenario.duration_years, target_years}
        for start, end, _ in PULSE_STAGES:
            boundaries.add(start * scenario.duration_years)
            boundaries.add(end * scenario.duration_years)
        later = [value for value in boundaries if value > current_years + 1e-10]
        return min(later) if later else target_years
    if scenario.process == "constant":
        return target_years

    upper = min(target_years, current_years + 1.0)
    q_start = scenario.retention * discharge_m3s(
        scenario.process,
        current_years,
        scenario.qb_m3s,
        scenario.q0_m3s,
        scenario.tau_years,
        scenario.duration_years,
    )
    if q_start <= 0:
        return upper
    q_upper = scenario.retention * discharge_m3s(
        scenario.process,
        upper,
        scenario.qb_m3s,
        scenario.q0_m3s,
        scenario.tau_years,
        scenario.duration_years,
    )
    if abs(q_upper - q_start) / q_start <= 0.10:
        return upper
    lo, hi = current_years, upper
    for _ in range(50):
        mid = (lo + hi) / 2
        q_mid = scenario.retention * discharge_m3s(
            scenario.process,
            mid,
            scenario.qb_m3s,
            scenario.q0_m3s,
            scenario.tau_years,
            scenario.duration_years,
        )
        if abs(q_mid - q_start) / q_start <= 0.10:
            lo = mid
        else:
            hi = mid
    return lo


def save_outputs(
    output_dir: Path,
    scenario,
    model: DiffusiveWave2D | None,
    data,
    fill_years: float | None,
    current_years: float,
    requested_years: float,
) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    storage_capacity = float(data["storage"][0])
    ledger = water_ledger(
        scenario.process,
        current_years,
        scenario.qb_m3s,
        scenario.q0_m3s,
        scenario.tau_years,
        scenario.duration_years,
        scenario.retention,
    )
    reservoir_m3 = min(ledger["effective_m3"], storage_capacity)
    reservoir_depth, reservoir_arrival, reservoir_duration = reservoir_state(
        data, ledger["effective_m3"], scenario, current_years
    )
    if model is None:
        depth = reservoir_depth
        max_depth = reservoir_depth.copy()
        arrival_years = reservoir_arrival
        duration_years = reservoir_duration
        downstream_balance = None
        downstream_stored = 0.0
        boundary_outflow = 0.0
    else:
        depth = model.h.copy()
        depth[np.asarray(data["basin"], dtype=bool)] = reservoir_depth[
            np.asarray(data["basin"], dtype=bool)
        ]
        max_depth = model.max_depth_m.copy()
        max_depth[np.asarray(data["basin"], dtype=bool)] = reservoir_depth[
            np.asarray(data["basin"], dtype=bool)
        ]
        arrival_years = np.where(
            np.isfinite(model.arrival_days),
            float(fill_years) + model.arrival_days / YEAR_DAYS,
            np.nan,
        ).astype(np.float32)
        duration_years = (model.wet_duration_s / YEAR_SECONDS).astype(np.float32)
        basin = np.asarray(data["basin"], dtype=bool)
        arrival_years[basin] = reservoir_arrival[basin]
        duration_years[basin] = reservoir_duration[basin]
        downstream_balance = model.balance()
        downstream_stored = downstream_balance.stored_m3
        boundary_outflow = downstream_balance.boundary_outflow_m3

    np.save(output_dir / f"{scenario.key}_current_depth_m.npy", depth)
    np.save(output_dir / f"{scenario.key}_maximum_depth_m.npy", max_depth)
    np.save(output_dir / f"{scenario.key}_arrival_years.npy", arrival_years)
    np.save(output_dir / f"{scenario.key}_wet_duration_years.npy", duration_years)

    sites = read_sites(DATA_ROOT / "crism_selected_sites.csv", depth.shape)
    covered = 0
    for site in sites:
        row, col = site["row_400m"], site["col_400m"]
        arrival = float(arrival_years[row, col])
        site.update(
            {
                "reached": bool(np.isfinite(arrival)),
                "arrival_years": arrival if np.isfinite(arrival) else None,
                "current_depth_m": float(depth[row, col]),
                "maximum_depth_m": float(max_depth[row, col]),
                "wet_duration_years": float(duration_years[row, col]),
            }
        )
        covered += int(site["reached"])

    residual_m3 = (
        ledger["effective_m3"]
        - reservoir_m3
        - downstream_stored
        - boundary_outflow
    )
    is_complete = abs(current_years - requested_years) < 1e-9
    summary = {
        "model": "original_2d_finite_volume_diffusive_wave",
        "spatial_solver_changed": False,
        "scenario": scenario.__dict__,
        "requested_years": requested_years,
        "completed_years": current_years,
        "complete": is_complete,
        "paper_usable": bool(
            is_complete
            and (downstream_balance is None or abs(downstream_balance.relative_error) < 1e-6)
        ),
        "source": {
            "lon_e": 75.937180,
            "lat_n": 18.136689,
            "meaning": "combined_total_for_two_conceptual_troughs_applied_once",
            "geometry_drawn": False,
        },
        "source_fill_years": fill_years,
        "water_ledger_km3": {
            "raw_release": ledger["raw_m3"] / 1e9,
            "effective_after_c": ledger["effective_m3"] / 1e9,
            "loss_one_minus_c": ledger["loss_m3"] / 1e9,
            "source_basin_storage": reservoir_m3 / 1e9,
            "downstream_surface_storage": downstream_stored / 1e9,
            "open_boundary_outflow": boundary_outflow / 1e9,
            "unresolved_if_partial": residual_m3 / 1e9,
        },
        "outputs": {
            "covered_sites": covered,
            "site_count": len(sites),
            "maximum_depth_m": float(max_depth.max()),
            "wet_cells_current": int(np.count_nonzero(depth > WET_THRESHOLD_M)),
            "wet_cells_ever": int(np.count_nonzero(max_depth > WET_THRESHOLD_M)),
        },
        "checkpoints": sites,
        "numerics": {
            "grid_m": 400.0,
            "surface_dt_s": BASE_DT_S,
            "mars_gravity_m_s2": 3.721,
            "manning_n": 0.0545,
            "dynamic_computational_window": True,
            "source_prefill_integrated_analytically": True,
            "downstream_time_skipping": bool(
                model is not None and model.steady_skipped_s > 0
            ),
            "explicit_surface_years": (
                model.explicit_stepped_s / YEAR_SECONDS if model is not None else 0.0
            ),
            "verified_steady_skipped_years": (
                model.steady_skipped_s / YEAR_SECONDS if model is not None else 0.0
            ),
            "steady_skip_criteria": {
                "two_consecutive_blocks": True,
                "block_days": 30.0,
                "storage_relative_change_max": 0.001,
                "new_arrival_cells_max": 2,
                "boundary_outflow_fraction_min": 0.98,
                "exponential_q_change_per_skip_max": 0.10,
                "pulse_boundaries_never_crossed": True
            },
            "steady_shadow_validations_passed": (
                model.steady_validations_passed if model is not None else 0
            ),
            "steady_shadow_validations_failed": (
                model.steady_validations_failed if model is not None else 0
            ),
            "downstream_mass_error": (
                downstream_balance.relative_error if downstream_balance else 0.0
            ),
        },
    }
    (output_dir / f"{scenario.key}_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    z = np.asarray(data["z400"], dtype=float)
    lo, hi = np.percentile(z, (2, 98))
    gray = np.clip((z - lo) / (hi - lo), 0, 1)
    rgb = np.repeat((gray[..., None] * 175 + 35).astype(np.uint8), 3, axis=2)
    wet = depth > WET_THRESHOLD_M
    intensity = np.zeros(depth.shape, np.float32)
    intensity[wet] = np.clip(np.log1p(depth[wet]) / np.log1p(4000.0), 0.08, 1)
    rgb[..., 0] = np.where(wet, rgb[..., 0] * (1 - 0.70 * intensity), rgb[..., 0]).astype(np.uint8)
    rgb[..., 1] = np.where(wet, rgb[..., 1] * (1 - 0.35 * intensity) + 90 * intensity, rgb[..., 1]).astype(np.uint8)
    rgb[..., 2] = np.where(wet, rgb[..., 2] * (1 - 0.15 * intensity) + 150 * intensity, rgb[..., 2]).astype(np.uint8)
    preview = Image.fromarray(rgb).resize((1368, 1100), Image.Resampling.NEAREST)
    if not is_complete:
        draw = ImageDraw.Draw(preview, "RGBA")
        draw.rectangle((0, 0, 1368, 62), fill=(125, 0, 0, 220))
        try:
            font = ImageFont.truetype("arial.ttf", 32)
        except OSError:
            font = ImageFont.load_default()
        draw.text((22, 14), "PARTIAL RUN - DO NOT CITE", fill=(255, 255, 255, 255), font=font)
    preview.save(output_dir / f"{scenario.key}_map.png")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", choices=SCENARIOS, default="medium")
    parser.add_argument("--run-name", help="自定义参数的输出前缀；省略时自动生成")
    parser.add_argument("--process", choices=("constant", "exponential", "pulse"))
    parser.add_argument("--qb", type=float, help="两条概念沟槽合计基流 Qb，m3/s")
    parser.add_argument("--q0", type=float, help="合计初始或脉冲流量 Q0，m3/s")
    parser.add_argument("--tau-years", type=float)
    parser.add_argument("--duration-years", type=float)
    parser.add_argument("--retention", type=float, help="沿程有效保留系数 C，0-1")
    parser.add_argument("--until-years", type=float)
    parser.add_argument(
        "--max-postspill-days",
        type=float,
        help="本次最多新增计算多少个溢流后物理日；省略则算到目标时刻",
    )
    parser.add_argument("--progress-days", type=float, default=10.0)
    parser.add_argument(
        "--acceleration",
        choices=("verified", "off"),
        default="verified",
        help="verified 仅在连续收敛后跳过稳态段；off 全程600秒显式",
    )
    parser.add_argument("--fresh", action="store_true")
    args = parser.parse_args()

    scenario = SCENARIOS[args.scenario]
    has_overrides = any(
        value is not None
        for value in (
            args.process,
            args.qb,
            args.q0,
            args.tau_years,
            args.duration_years,
            args.retention,
        )
    )
    scenario = replace(
        scenario,
        process=scenario.process if args.process is None else args.process,
        qb_m3s=scenario.qb_m3s if args.qb is None else max(args.qb, 0.0),
        q0_m3s=scenario.q0_m3s if args.q0 is None else max(args.q0, 0.0),
        tau_years=(
            scenario.tau_years if args.tau_years is None else max(args.tau_years, 1e-9)
        ),
        duration_years=(
            scenario.duration_years
            if args.duration_years is None
            else max(args.duration_years, 0.0)
        ),
        retention=(
            scenario.retention
            if args.retention is None
            else min(max(args.retention, 0.0), 1.0)
        ),
    )
    if args.run_name:
        safe_name = "".join(
            character for character in args.run_name if character.isalnum() or character in "-_"
        )
        if not safe_name:
            raise ValueError("run-name 必须包含字母、数字、连字符或下划线")
        scenario = replace(scenario, key=safe_name)
    elif has_overrides:
        signature = json.dumps(
            {
                "process": scenario.process,
                "qb": scenario.qb_m3s,
                "q0": scenario.q0_m3s,
                "tau": scenario.tau_years,
                "duration": scenario.duration_years,
                "retention": scenario.retention,
            },
            sort_keys=True,
        )
        suffix = hashlib.sha256(signature.encode("utf-8")).hexdigest()[:8]
        scenario = replace(scenario, key=f"{scenario.key}_custom_{suffix}")
    requested_years = min(
        scenario.duration_years if args.until_years is None else max(args.until_years, 0.0),
        scenario.duration_years,
    )
    data = np.load(DATA_ROOT / "conservative-model.npz")
    storage_capacity = float(data["storage"][0])
    fill_years = inverse_effective_volume_years(
        storage_capacity,
        scenario.process,
        scenario.qb_m3s,
        scenario.q0_m3s,
        scenario.tau_years,
        scenario.duration_years,
        scenario.retention,
    )
    output_dir = ROOT / "outputs"
    output_dir.mkdir(exist_ok=True)
    state_path = output_dir / f"{scenario.key}_state.npz"

    if fill_years is None or requested_years <= fill_years:
        summary = save_outputs(
            output_dir, scenario, None, data, fill_years, requested_years, requested_years
        )
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return

    if state_path.exists() and not args.fresh:
        model, saved_fill = load_state(state_path, data)
        if abs(saved_fill - fill_years) > 1e-8:
            raise RuntimeError("断点文件与当前情景的源坑溢流时刻不一致")
    else:
        model = DiffusiveWave2D(
            data["z400"], data["basin"], data["inlet"], dynamic_crop=True
        )

    target_postspill_s = (requested_years - fill_years) * YEAR_SECONDS
    if args.max_postspill_days is not None:
        target_postspill_s = min(
            target_postspill_s,
            model.elapsed_s + max(args.max_postspill_days, 0.0) * 86_400.0,
        )
    next_progress_s = model.elapsed_s + max(args.progress_days, 0.1) * 86_400.0
    stability_block_s = 30.0 * 86_400.0
    next_stability_s = model.elapsed_s + stability_block_s
    previous_stored = model.balance().stored_m3
    previous_arrived = int(np.count_nonzero(np.isfinite(model.arrival_days)))
    previous_supplied = model.supplied_m3
    previous_outflow = model.boundary_outflow_m3
    stable_blocks = 0
    wall_start = time.perf_counter()
    while model.elapsed_s + 1e-7 < target_postspill_s:
        dt_s = min(BASE_DT_S, target_postspill_s - model.elapsed_s)
        start_years = fill_years + model.elapsed_s / YEAR_SECONDS
        end_years = fill_years + (model.elapsed_s + dt_s) / YEAR_SECONDS
        effective_q = effective_volume_between(scenario, start_years, end_years) / dt_s
        model.step(effective_q, dt_s)
        if model.elapsed_s + 1e-7 >= next_stability_s:
            balance = model.balance()
            arrived = int(np.count_nonzero(np.isfinite(model.arrival_days)))
            block_input = model.supplied_m3 - previous_supplied
            block_out = model.boundary_outflow_m3 - previous_outflow
            storage_change = abs(balance.stored_m3 - previous_stored) / max(
                previous_stored, 1.0
            )
            new_arrivals = max(arrived - previous_arrived, 0)
            out_fraction = block_out / block_input if block_input > 0 else 1.0
            if (
                storage_change <= 0.001
                and new_arrivals <= 2
                and out_fraction >= 0.98
            ):
                stable_blocks += 1
            else:
                stable_blocks = 0
            previous_stored = balance.stored_m3
            previous_arrived = arrived
            previous_supplied = model.supplied_m3
            previous_outflow = model.boundary_outflow_m3
            next_stability_s += stability_block_s

            if args.acceleration == "verified" and stable_blocks >= 2:
                shadow = clone_model(model, data)
                validation_start_stored = model.balance().stored_m3
                validation_start_arrived = int(
                    np.count_nonzero(np.isfinite(model.arrival_days))
                )
                validation_s = min(
                    30.0 * 86_400.0, target_postspill_s - model.elapsed_s
                )
                advance_exact_interval(shadow, scenario, fill_years, validation_s)
                base_wet = model.h > WET_THRESHOLD_M
                shadow_wet = shadow.h > WET_THRESHOLD_M
                union = int(np.count_nonzero(base_wet | shadow_wet))
                wet_iou = (
                    int(np.count_nonzero(base_wet & shadow_wet)) / union
                    if union
                    else 1.0
                )
                shadow_stored = shadow.balance().stored_m3
                shadow_storage_change = abs(
                    shadow_stored - validation_start_stored
                ) / max(validation_start_stored, 1.0)
                shadow_new_arrivals = max(
                    int(np.count_nonzero(np.isfinite(shadow.arrival_days)))
                    - validation_start_arrived,
                    0,
                )
                depth_rmse = float(
                    np.sqrt(
                        np.mean(
                            (shadow.h.astype(np.float64) - model.h.astype(np.float64))
                            ** 2
                        )
                    )
                )
                validation_ok = (
                    wet_iou >= 0.995
                    and shadow_storage_change <= 0.005
                    and shadow_new_arrivals <= 2
                    and depth_rmse <= 0.10
                )
                if validation_ok:
                    shadow.steady_validations_passed += 1
                    model = shadow
                    current_years = fill_years + model.elapsed_s / YEAR_SECONDS
                    target_years = fill_years + target_postspill_s / YEAR_SECONDS
                    skip_to_years = next_forcing_boundary_years(
                        scenario, current_years, target_years
                    )
                    skip_s = (skip_to_years - current_years) * YEAR_SECONDS
                    if skip_s >= 7 * 86_400.0:
                        skip_volume = effective_volume_between(
                            scenario, current_years, skip_to_years
                        )
                        model.advance_verified_steady(skip_volume, skip_s)
                        save_state(state_path, model, fill_years)
                        print(
                            f"shadow validation passed: iou={wet_iou:.6f}, "
                            f"new={shadow_new_arrivals}, rmse={depth_rmse:.4f} m; "
                            f"steady skip {skip_s / 86_400:.1f} d to "
                            f"post-spill {model.elapsed_s / 86_400:.1f} d; "
                            f"mass_error={model.balance().relative_error:.3g}",
                            flush=True,
                        )
                else:
                    model.steady_validations_failed += 1
                    print(
                        f"shadow validation rejected: iou={wet_iou:.6f}, "
                        f"new={shadow_new_arrivals}, storage={shadow_storage_change:.4g}, "
                        f"rmse={depth_rmse:.4f} m",
                        flush=True,
                    )
                stable_blocks = 0
                previous_stored = model.balance().stored_m3
                previous_arrived = int(
                    np.count_nonzero(np.isfinite(model.arrival_days))
                )
                previous_supplied = model.supplied_m3
                previous_outflow = model.boundary_outflow_m3
                next_stability_s = model.elapsed_s + stability_block_s
        if model.elapsed_s + 1e-7 >= next_progress_s:
            save_state(state_path, model, fill_years)
            balance = model.balance()
            print(
                f"post-spill {model.elapsed_s / 86_400:.1f} d; "
                f"wet={np.count_nonzero(model.h > WET_THRESHOLD_M)}; "
                f"stored={balance.stored_m3 / 1e9:.3f} km3; "
                f"mass_error={balance.relative_error:.3g}; "
                f"wall={time.perf_counter() - wall_start:.1f} s",
                flush=True,
            )
            progress_step_s = max(args.progress_days, 0.1) * 86_400.0
            while next_progress_s <= model.elapsed_s + 1e-7:
                next_progress_s += progress_step_s

    save_state(state_path, model, fill_years)
    completed_years = fill_years + model.elapsed_s / YEAR_SECONDS
    summary = save_outputs(
        output_dir,
        scenario,
        model,
        data,
        fill_years,
        completed_years,
        requested_years,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
