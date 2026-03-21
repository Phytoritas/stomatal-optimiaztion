from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import pandas as pd


def _clamp(value: float, low: float, high: float) -> float:
    return float(min(max(float(value), low), high))


def esat_kpa_from_t_c(t_air_c: float) -> float:
    return float(0.61078 * math.exp((17.2694 * float(t_air_c)) / (float(t_air_c) + 237.29)))


def vpd_kpa_from_t_rh(t_air_c: float, rh_percent: float) -> float:
    esat = esat_kpa_from_t_c(t_air_c)
    return max(esat * (1.0 - _clamp(rh_percent, 0.0, 100.0) / 100.0), 0.0)


@dataclass(frozen=True, slots=True)
class ThetaProxyScenario:
    name: str
    center: float
    lower_trigger: float
    upper_target: float
    day_depletion_per_day: float
    night_recovery_per_day: float
    drain_per_day: float
    saturation_start: float


DEFAULT_SCENARIOS: dict[str, ThetaProxyScenario] = {
    "dry": ThetaProxyScenario(
        name="dry",
        center=0.50,
        lower_trigger=0.46,
        upper_target=0.56,
        day_depletion_per_day=0.12,
        night_recovery_per_day=0.035,
        drain_per_day=0.060,
        saturation_start=0.78,
    ),
    "moderate": ThetaProxyScenario(
        name="moderate",
        center=0.65,
        lower_trigger=0.60,
        upper_target=0.71,
        day_depletion_per_day=0.10,
        night_recovery_per_day=0.040,
        drain_per_day=0.075,
        saturation_start=0.80,
    ),
    "wet": ThetaProxyScenario(
        name="wet",
        center=0.80,
        lower_trigger=0.75,
        upper_target=0.83,
        day_depletion_per_day=0.085,
        night_recovery_per_day=0.030,
        drain_per_day=0.100,
        saturation_start=0.82,
    ),
}


def _demand_index(frame: pd.DataFrame) -> pd.Series:
    vpd = pd.Series(
        [vpd_kpa_from_t_rh(t_air_c, rh) for t_air_c, rh in zip(frame["T_air_C"], frame["RH_percent"], strict=False)],
        index=frame.index,
        dtype=float,
    )
    par_norm = pd.to_numeric(frame["PAR_umol"], errors="coerce").fillna(0.0) / 1200.0
    vpd_norm = vpd / 3.0
    demand = 0.65 * par_norm.clip(lower=0.0, upper=1.5) + 0.35 * vpd_norm.clip(lower=0.0, upper=1.5)
    return demand.clip(lower=0.0, upper=1.0)


def _rootzone_temp_stress(frame: pd.DataFrame) -> pd.Series:
    t_air = pd.to_numeric(frame["T_air_C"], errors="coerce").fillna(20.0)
    heat = ((t_air - 28.0) / 8.0).clip(lower=0.0, upper=1.0)
    cold = ((16.0 - t_air) / 6.0).clip(lower=0.0, upper=1.0)
    return (0.7 * heat + 0.3 * cold).clip(lower=0.0, upper=1.0)


def apply_theta_substrate_proxy(
    forcing_df: pd.DataFrame,
    *,
    mode: str,
    scenario: str,
    theta_min_hard: float = 0.40,
    theta_max_hard: float = 0.85,
    saturation_weight: float = 0.65,
    temperature_weight: float = 0.35,
    hysteresis_band: float = 0.02,
) -> pd.DataFrame:
    key = str(mode).strip().lower()
    scenario_key = str(scenario).strip().lower()
    if scenario_key not in DEFAULT_SCENARIOS:
        ordered = ", ".join(sorted(DEFAULT_SCENARIOS))
        raise ValueError(f"Unsupported theta proxy scenario {scenario!r}; expected one of: {ordered}.")
    if key not in {"flat_constant", "bucket_irrigated", "bucket_irrigated_hysteretic"}:
        raise ValueError(
            f"Unsupported theta proxy mode {mode!r}; expected 'flat_constant', 'bucket_irrigated', or 'bucket_irrigated_hysteretic'."
        )

    scenario_cfg = DEFAULT_SCENARIOS[scenario_key]
    frame = forcing_df.copy()
    frame["datetime"] = pd.to_datetime(frame["datetime"], errors="coerce")
    if frame["datetime"].isna().any():
        raise ValueError("theta proxy forcing requires parseable datetime values.")
    frame = frame.sort_values("datetime").reset_index(drop=True)
    frame["vpd_kpa"] = _demand_index(frame) * 3.0
    frame["demand_index"] = _demand_index(frame)
    frame["rootzone_temperature_stress"] = _rootzone_temp_stress(frame)
    frame["theta_proxy_mode"] = key
    frame["theta_proxy_scenario"] = scenario_cfg.name

    if key == "flat_constant":
        frame["theta_substrate"] = scenario_cfg.center
        frame["rootzone_saturation"] = frame["theta_substrate"].map(
            lambda theta: _clamp((theta - scenario_cfg.saturation_start) / max(theta_max_hard - scenario_cfg.saturation_start, 1e-6), 0.0, 1.0)
        )
        frame["rootzone_multistress"] = (
            saturation_weight * frame["rootzone_saturation"]
            + temperature_weight * frame["rootzone_temperature_stress"]
        ).clip(lower=0.0, upper=1.0)
        return frame

    theta_values: list[float] = []
    saturation_values: list[float] = []
    multistress_values: list[float] = []
    irrigation_flags: list[int] = []
    irrigation_on = False
    theta = scenario_cfg.center
    for idx, row in frame.iterrows():
        dt_days = 1.0 / 1440.0 if idx == 0 else max(
            (row["datetime"] - frame.loc[idx - 1, "datetime"]).total_seconds() / 86400.0,
            1.0 / 86400.0,
        )
        demand = float(row["demand_index"])
        par = float(row["PAR_umol"])
        day_factor = 1.0 if par > 10.0 else 0.35
        theta -= scenario_cfg.day_depletion_per_day * demand * day_factor * dt_days

        hour = int(pd.Timestamp(row["datetime"]).hour)
        if par <= 10.0:
            theta += scenario_cfg.night_recovery_per_day * max(scenario_cfg.center - theta, 0.0) * dt_days

        if key == "bucket_irrigated":
            pulse_window = hour in {6, 7, 8, 12, 13}
            if pulse_window and theta < scenario_cfg.lower_trigger:
                theta += 3.0 * max(scenario_cfg.upper_target - theta, 0.0) * dt_days * 24.0
                irrigation = 1
            else:
                irrigation = 0
        else:
            lower_start = scenario_cfg.lower_trigger
            upper_stop = min(scenario_cfg.upper_target + hysteresis_band, theta_max_hard)
            if theta <= lower_start:
                irrigation_on = True
            elif theta >= upper_stop:
                irrigation_on = False
            if irrigation_on and hour in {6, 7, 8, 12, 13, 14}:
                theta += 3.2 * max(scenario_cfg.upper_target - theta, 0.0) * dt_days * 24.0
                irrigation = 1
            else:
                irrigation = 0

        saturation = _clamp(
            (theta - scenario_cfg.saturation_start) / max(theta_max_hard - scenario_cfg.saturation_start, 1e-6),
            0.0,
            1.0,
        )
        theta -= scenario_cfg.drain_per_day * saturation * dt_days
        theta = _clamp(theta, theta_min_hard, theta_max_hard)

        multistress = _clamp(
            saturation_weight * saturation + temperature_weight * float(row["rootzone_temperature_stress"]),
            0.0,
            1.0,
        )
        theta_values.append(theta)
        saturation_values.append(saturation)
        multistress_values.append(multistress)
        irrigation_flags.append(irrigation)

    frame["theta_substrate"] = theta_values
    frame["rootzone_saturation"] = saturation_values
    frame["rootzone_multistress"] = multistress_values
    frame["irrigation_recharge_flag"] = irrigation_flags
    return frame


def theta_proxy_summary(frame: pd.DataFrame) -> dict[str, Any]:
    return {
        "theta_min": float(pd.to_numeric(frame["theta_substrate"], errors="coerce").min()),
        "theta_max": float(pd.to_numeric(frame["theta_substrate"], errors="coerce").max()),
        "theta_mean": float(pd.to_numeric(frame["theta_substrate"], errors="coerce").mean()),
        "multistress_mean": float(pd.to_numeric(frame["rootzone_multistress"], errors="coerce").mean()),
        "saturation_mean": float(pd.to_numeric(frame["rootzone_saturation"], errors="coerce").mean()),
        "proxy_mode": str(frame["theta_proxy_mode"].iloc[0]),
        "proxy_scenario": str(frame["theta_proxy_scenario"].iloc[0]),
    }


__all__ = [
    "DEFAULT_SCENARIOS",
    "ThetaProxyScenario",
    "apply_theta_substrate_proxy",
    "esat_kpa_from_t_c",
    "theta_proxy_summary",
    "vpd_kpa_from_t_rh",
]
