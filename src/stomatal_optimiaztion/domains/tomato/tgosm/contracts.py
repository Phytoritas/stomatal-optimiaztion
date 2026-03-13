from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class OptimizationRequest:
    theta_substrate: float
    water_supply_stress: float
    vpd_kpa: float
    co2_air_ppm: float
    fruit_sink_strength: float
    vegetative_sink_strength: float
    current_g_w: float


@dataclass(frozen=True, slots=True)
class OptimizationResult:
    g_w_opt: float
    lambda_wue: float
    objective_value: float


def clamp_nonnegative(value: float) -> float:
    if value < 0:
        return 0.0
    return value
