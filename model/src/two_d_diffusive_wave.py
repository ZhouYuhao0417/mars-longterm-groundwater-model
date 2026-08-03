"""原火星二维扩散波求解器的可复用实现。

本文件刻意保留 2026-07-22 版本的离散格式、网格、火星重力、
Manning 系数、正性限制器和开放边界。长期模拟只能在此求解器外层
加速时间，不得用河段蓄泄或 HAND 模型替代这里的地表水动力。
"""

from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np


G = 3.721
MANNING_N = 0.0545
DX_M = 400.0
BASE_DT_S = 600.0
WET_THRESHOLD_M = 0.015


def quantize_depth(depth_m: np.ndarray, max_depth_m: float = 4000.0) -> np.ndarray:
    """使用原预计算文件完全相同的对数深度量化，仅用于回归比较。"""
    result = np.zeros(depth_m.shape, np.uint8)
    wet = depth_m > WET_THRESHOLD_M
    result[wet] = np.clip(
        np.rint(np.log1p(depth_m[wet]) / math.log1p(max_depth_m) * 255),
        1,
        255,
    ).astype(np.uint8)
    return result


@dataclass
class WaterBalance:
    supplied_m3: float
    stored_m3: float
    boundary_outflow_m3: float

    @property
    def residual_m3(self) -> float:
        return self.supplied_m3 - self.stored_m3 - self.boundary_outflow_m3

    @property
    def relative_error(self) -> float:
        if self.supplied_m3 == 0:
            return 0.0
        return self.residual_m3 / self.supplied_m3


class DiffusiveWave2D:
    """有状态的二维有限体积扩散波模型，支持随时间变化的合计流量。"""

    def __init__(
        self,
        elevation_m: np.ndarray,
        source_basin: np.ndarray,
        outlet_inlet_mask: np.ndarray,
        initial_depth_m: np.ndarray | None = None,
        dynamic_crop: bool = False,
    ) -> None:
        self.z = np.asarray(elevation_m, dtype=np.float32)
        self.basin = np.asarray(source_basin, dtype=bool)
        self.inlet = np.asarray(outlet_inlet_mask, dtype=bool)
        if self.z.shape != self.basin.shape or self.z.shape != self.inlet.shape:
            raise ValueError("DEM、源坑和出口掩膜的形状必须一致")
        if not self.inlet.any():
            raise ValueError("自然溢流出口掩膜为空")

        self.h = (
            np.zeros_like(self.z, np.float32)
            if initial_depth_m is None
            else np.asarray(initial_depth_m, dtype=np.float32).copy()
        )
        if self.h.shape != self.z.shape:
            raise ValueError("初始水深与 DEM 形状不一致")

        self.area_m2 = DX_M * DX_M
        self.weights = self.inlet.astype(np.float32)
        self.weights /= self.weights.sum()
        self.active = ~self.basin
        self.edge = np.zeros_like(self.h, bool)
        self.edge[0] = self.edge[-1] = True
        self.edge[:, 0] = self.edge[:, -1] = True
        self.arrival_days = np.full(self.z.shape, np.inf, np.float32)
        self.wet_duration_s = np.zeros(self.z.shape, np.float64)
        self.elapsed_s = 0.0
        self.explicit_stepped_s = 0.0
        self.steady_skipped_s = 0.0
        self.steady_validations_passed = 0
        self.steady_validations_failed = 0
        self.supplied_m3 = 0.0
        self.boundary_outflow_m3 = 0.0
        self.max_depth_m = self.h.copy()
        self.dynamic_crop = bool(dynamic_crop)
        seed_mask = self.inlet | (self.h > 0)
        inlet_y, inlet_x = np.where(seed_mask)
        margin = 4
        self._crop = [
            max(0, int(inlet_y.min()) - margin),
            min(self.z.shape[0], int(inlet_y.max()) + margin + 1),
            max(0, int(inlet_x.min()) - margin),
            min(self.z.shape[1], int(inlet_x.max()) + margin + 1),
        ]
        self._pairs = (
            (0, 1, DX_M, DX_M),
            (1, 0, DX_M, DX_M),
            (1, 1, DX_M * math.sqrt(2), DX_M / math.sqrt(2)),
            (1, -1, DX_M * math.sqrt(2), DX_M / math.sqrt(2)),
        )

    def _active_window(self) -> tuple[slice, slice]:
        """返回包含全部水体和一圈干网格的计算窗口。"""
        if not self.dynamic_crop:
            return slice(0, self.z.shape[0]), slice(0, self.z.shape[1])
        while True:
            y0, y1, x0, x1 = self._crop
            view = self.h[y0:y1, x0:x1]
            touches = (
                np.any(view[0] > 0)
                or np.any(view[-1] > 0)
                or np.any(view[:, 0] > 0)
                or np.any(view[:, -1] > 0)
            )
            if not touches:
                break
            expanded = [
                max(0, y0 - 4),
                min(self.z.shape[0], y1 + 4),
                max(0, x0 - 4),
                min(self.z.shape[1], x1 + 4),
            ]
            if expanded == self._crop:
                break
            self._crop = expanded
        y0, y1, x0, x1 = self._crop
        return slice(y0, y1), slice(x0, x1)

    def step(self, total_discharge_m3s: float, dt_s: float = BASE_DT_S) -> None:
        """推进一个显式步长；Q 是两条概念沟槽合计值，只施加一次。"""
        q = max(float(total_discharge_m3s), 0.0)
        dt = float(dt_s)
        if dt <= 0:
            raise ValueError("时间步长必须为正")

        window = self._active_window()
        h = self.h[window]
        z = self.z[window]
        weights = self.weights[window]
        active = self.active[window]
        edge = self.edge[window]
        arrival_days = self.arrival_days[window]
        wet_duration_s = self.wet_duration_s[window]
        max_depth_m = self.max_depth_m[window]

        h += weights * (q * dt / self.area_m2)
        self.supplied_m3 += q * dt
        eta = z + h
        links = []
        outgoing = np.zeros_like(h, np.float32)

        for dy, dx, distance, width in self._pairs:
            if dx >= 0:
                a = (
                    slice(0, z.shape[0] - dy or None),
                    slice(0, z.shape[1] - dx or None),
                )
                b = (slice(dy, None), slice(dx, None))
            else:
                a = (slice(0, z.shape[0] - dy), slice(-dx, None))
                b = (slice(dy, None), slice(0, z.shape[1] + dx))
            valid = active[a] & active[b]
            surface_difference = eta[a] - eta[b]
            hydraulic_depth = np.maximum(
                np.maximum(eta[a], eta[b]) - np.maximum(z[a], z[b]),
                0,
            )
            slope = np.abs(surface_difference) / distance
            unit_flux = np.where(
                (hydraulic_depth > 0.003) & valid,
                (hydraulic_depth ** (5 / 3)) * np.sqrt(slope) / MANNING_N,
                0,
            )
            unit_flux = np.minimum(
                unit_flux,
                hydraulic_depth * np.sqrt(G * hydraulic_depth),
            )
            rate = np.sign(surface_difference) * unit_flux * width
            equalize = np.abs(surface_difference) * self.area_m2 / (2 * dt)
            rate = np.sign(rate) * np.minimum(np.abs(rate), equalize)
            links.append((a, b, rate))
            outgoing[a] += np.maximum(rate, 0)
            outgoing[b] += np.maximum(-rate, 0)

        factor = np.minimum(
            1.0,
            np.divide(
                h * self.area_m2 * 0.48,
                dt * outgoing,
                out=np.ones_like(h),
                where=outgoing > 0,
            ),
        ).astype(np.float32)
        for a, b, rate in links:
            limited_rate = np.where(rate >= 0, rate * factor[a], rate * factor[b])
            depth_change = limited_rate * dt / self.area_m2
            h[a] -= depth_change
            h[b] += depth_change

        np.maximum(h, 0, out=h)
        edge_volume = float(h[edge].sum(dtype=np.float64) * self.area_m2)
        self.boundary_outflow_m3 += edge_volume
        h[edge] = 0

        self.elapsed_s += dt
        self.explicit_stepped_s += dt
        newly_wet = (h > WET_THRESHOLD_M) & ~np.isfinite(arrival_days)
        arrival_days[newly_wet] = self.elapsed_s / 86_400.0
        wet_duration_s[h > WET_THRESHOLD_M] += dt
        np.maximum(max_depth_m, h, out=max_depth_m)

    def advance_verified_steady(
        self,
        effective_volume_m3: float,
        duration_s: float,
    ) -> None:
        """跨越已验证稳态段，同时保持严格水量账本和淹没持续时间。

        调用方必须先确认域内储水、首次湿润像元和边界出流均已连续
        收敛。稳态期间地表储水不变，因此新增有效水全部记入开放边界
        外排；当前湿润像元的持续时间按完整物理时段累加。
        """
        duration = max(float(duration_s), 0.0)
        volume = max(float(effective_volume_m3), 0.0)
        if duration == 0:
            return
        self.supplied_m3 += volume
        self.boundary_outflow_m3 += volume
        self.wet_duration_s[self.h > WET_THRESHOLD_M] += duration
        self.elapsed_s += duration
        self.steady_skipped_s += duration

    def advance_constant(
        self,
        total_discharge_m3s: float,
        duration_s: float,
        dt_s: float = BASE_DT_S,
    ) -> None:
        """用原 600 秒步长推进一段恒定流量，末步可缩短。"""
        remaining = max(float(duration_s), 0.0)
        while remaining > 1e-9:
            step_s = min(float(dt_s), remaining)
            self.step(total_discharge_m3s, step_s)
            remaining -= step_s

    def balance(self) -> WaterBalance:
        return WaterBalance(
            supplied_m3=self.supplied_m3,
            stored_m3=float(self.h.sum(dtype=np.float64) * self.area_m2),
            boundary_outflow_m3=self.boundary_outflow_m3,
        )
