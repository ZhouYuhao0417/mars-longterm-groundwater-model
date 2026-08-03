"""Analytic long-duration groundwater hydrographs for the Mars model.

All discharge values are combined totals for the two hypothesized troughs. The
hydrologic model applies that total once at the user's original source point;
it does not infer, draw, or rasterize the trough geometry. The retention
coefficient is applied once after integrating raw groundwater release.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable

import numpy as np


DAY_SECONDS = 86_400.0
YEAR_DAYS = 365.25
YEAR_SECONDS = YEAR_DAYS * DAY_SECONDS


# Each tuple is (start fraction of T, end fraction of T, Q0 multiplier).
# The short separated pulses represent episodic fracture reactivation while Qb
# continues between pulses.
PULSE_STAGES = (
    (0.00, 0.02, 1.00),
    (0.02, 0.08, 0.35),
    (0.25, 0.28, 0.80),
    (0.55, 0.57, 0.60),
)


@dataclass(frozen=True)
class Scenario:
    key: str
    name: str
    process: str
    qb_m3s: float
    q0_m3s: float
    tau_years: float
    duration_years: float
    retention: float


SCENARIOS = {
    "low": Scenario("low", "低：弱持续基流", "constant", 100.0, 1_000.0, 1.0, 10.0, 0.4),
    "medium": Scenario("medium", "中：承压含水层衰减", "exponential", 300.0, 3_000.0, 3.0, 20.0, 0.7),
    "high": Scenario("high", "高：分阶段裂隙脉冲", "pulse", 500.0, 5_000.0, 5.0, 30.0, 1.0),
}


def discharge_m3s(
    process: str,
    time_years: float | np.ndarray,
    qb_m3s: float,
    q0_m3s: float,
    tau_years: float,
    duration_years: float,
) -> float | np.ndarray:
    """Return the raw total discharge Q(t) across both source zones."""
    t = np.asarray(time_years, dtype=float)
    active = (t >= 0.0) & (t <= duration_years)
    if process == "constant":
        q = np.full_like(t, qb_m3s)
    elif process == "exponential":
        tau = max(float(tau_years), 1e-9)
        q = qb_m3s + q0_m3s * np.exp(-np.maximum(t, 0.0) / tau)
    elif process == "pulse":
        q = np.full_like(t, qb_m3s)
        frac = np.divide(t, duration_years, out=np.zeros_like(t), where=duration_years > 0)
        for start, end, multiplier in PULSE_STAGES:
            q += np.where((frac >= start) & (frac < end), q0_m3s * multiplier, 0.0)
    else:
        raise ValueError(f"Unknown process: {process}")
    q = np.where(active, q, 0.0)
    if np.isscalar(time_years):
        return float(q)
    return q


def raw_volume_m3(
    process: str,
    time_years: float,
    qb_m3s: float,
    q0_m3s: float,
    tau_years: float,
    duration_years: float,
) -> float:
    """Exact integral of raw Q(t) from zero to time_years."""
    t = min(max(float(time_years), 0.0), max(float(duration_years), 0.0))
    if process == "constant":
        integral_q_years = qb_m3s * t
    elif process == "exponential":
        tau = max(float(tau_years), 1e-9)
        integral_q_years = qb_m3s * t + q0_m3s * tau * (1.0 - math.exp(-t / tau))
    elif process == "pulse":
        integral_q_years = qb_m3s * t
        for start, end, multiplier in PULSE_STAGES:
            overlap = max(0.0, min(t, end * duration_years) - start * duration_years)
            integral_q_years += q0_m3s * multiplier * overlap
    else:
        raise ValueError(f"Unknown process: {process}")
    return integral_q_years * YEAR_SECONDS


def water_ledger(
    process: str,
    time_years: float,
    qb_m3s: float,
    q0_m3s: float,
    tau_years: float,
    duration_years: float,
    retention: float,
) -> dict[str, float]:
    """Return raw, effective, and lumped loss volumes in cubic metres."""
    raw = raw_volume_m3(process, time_years, qb_m3s, q0_m3s, tau_years, duration_years)
    c = min(max(float(retention), 0.0), 1.0)
    effective = raw * c
    return {"raw_m3": raw, "effective_m3": effective, "loss_m3": raw - effective}


def adaptive_times(duration_years: float) -> np.ndarray:
    """Piecewise time grid used for plotting and diagnostics, never daily for decades."""
    total_days = max(float(duration_years), 0.0) * YEAR_DAYS
    if total_days == 0:
        return np.array([0.0])
    boundaries = (
        (30.0, 1.0),
        (YEAR_DAYS, 7.0),
        (5.0 * YEAR_DAYS, 30.0),
        (10.0 * YEAR_DAYS, 90.0),
        (math.inf, 180.0),
    )
    days = [0.0]
    current = 0.0
    for upper, step in boundaries:
        stop = min(total_days, upper)
        while current + step < stop - 1e-9:
            current += step
            days.append(current)
        if stop > days[-1] + 1e-9:
            days.append(stop)
        current = stop
        if current >= total_days - 1e-9:
            break
    return np.asarray(days, dtype=float) / YEAR_DAYS


def inverse_effective_volume_years(
    target_effective_m3: float,
    process: str,
    qb_m3s: float,
    q0_m3s: float,
    tau_years: float,
    duration_years: float,
    retention: float,
) -> float | None:
    """Find the first time at which the exact effective-volume integral reaches target."""
    target = max(float(target_effective_m3), 0.0)
    if target == 0:
        return 0.0
    total = raw_volume_m3(process, duration_years, qb_m3s, q0_m3s, tau_years, duration_years) * retention
    if total + 1e-6 < target or retention <= 0:
        return None
    lo, hi = 0.0, float(duration_years)
    for _ in range(70):
        mid = (lo + hi) / 2.0
        value = raw_volume_m3(process, mid, qb_m3s, q0_m3s, tau_years, duration_years) * retention
        if value < target:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


def scenario_rows() -> Iterable[dict[str, float | str]]:
    for scenario in SCENARIOS.values():
        ledger = water_ledger(
            scenario.process,
            scenario.duration_years,
            scenario.qb_m3s,
            scenario.q0_m3s,
            scenario.tau_years,
            scenario.duration_years,
            scenario.retention,
        )
        yield {
            **scenario.__dict__,
            "raw_km3": ledger["raw_m3"] / 1e9,
            "effective_km3": ledger["effective_m3"] / 1e9,
            "loss_km3": ledger["loss_m3"] / 1e9,
            "adaptive_steps": int(adaptive_times(scenario.duration_years).size - 1),
        }
