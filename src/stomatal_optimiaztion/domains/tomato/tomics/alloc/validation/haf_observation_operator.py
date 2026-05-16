from __future__ import annotations

from typing import Any

import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.observers.contracts import (
    CANONICAL_2025_2C_FRUIT_DMC,
    HAF_2025_2C_LOADCELL_FLOOR_AREA_M2,
)


OBSERVATION_OPERATOR_FAMILY = "fresh_to_dry_dmc_0p056"
INVERSE_OBSERVATION_OPERATOR_FAMILY = "dry_to_fresh_dmc_0p056"
FDMC_MODE = "constant_0p056"


def _numeric_series(raw: Any, *, index: pd.Index | None = None) -> pd.Series:
    if isinstance(raw, pd.Series):
        return pd.to_numeric(raw, errors="coerce")
    if index is None:
        return pd.Series([raw], dtype="float64")
    return pd.Series(raw, index=index, dtype="float64")


def _same_shape(raw: Any, series: pd.Series) -> float | pd.Series:
    if isinstance(raw, pd.Series):
        return series
    return float(series.iloc[0])


def fresh_loadcell_to_dry_floor_area(
    fresh_g_loadcell: float | pd.Series,
    dmc: float = CANONICAL_2025_2C_FRUIT_DMC,
    effective_floor_area_per_loadcell_m2: float = HAF_2025_2C_LOADCELL_FLOOR_AREA_M2,
) -> float | pd.Series:
    values = _numeric_series(fresh_g_loadcell)
    converted = values * float(dmc) / float(effective_floor_area_per_loadcell_m2)
    return _same_shape(fresh_g_loadcell, converted)


def dry_floor_area_to_fresh_loadcell(
    dry_g_m2_floor: float | pd.Series,
    dmc: float = CANONICAL_2025_2C_FRUIT_DMC,
    effective_floor_area_per_loadcell_m2: float = HAF_2025_2C_LOADCELL_FLOOR_AREA_M2,
) -> float | pd.Series:
    values = _numeric_series(dry_g_m2_floor)
    converted = values * float(effective_floor_area_per_loadcell_m2) / float(dmc)
    return _same_shape(dry_g_m2_floor, converted)


def _first_numeric(frame: pd.DataFrame, columns: tuple[str, ...]) -> pd.Series:
    values = pd.Series(float("nan"), index=frame.index, dtype="float64")
    for column in columns:
        if column not in frame.columns:
            continue
        candidate = pd.to_numeric(frame[column], errors="coerce")
        values = values.fillna(candidate)
    return values


def _normalise_loadcell(raw: pd.Series) -> pd.Series:
    values = pd.to_numeric(raw, errors="coerce")
    if values.notna().all():
        return values.astype(int).astype(str)
    return raw.astype(str)


def build_harvest_observation_frame_dmc_0p056(
    feature_frame: pd.DataFrame,
    *,
    effective_floor_area_per_loadcell_m2: float = HAF_2025_2C_LOADCELL_FLOOR_AREA_M2,
) -> pd.DataFrame:
    if feature_frame.empty:
        return pd.DataFrame()

    required = {"date", "loadcell_id", "treatment"}
    missing = sorted(required.difference(feature_frame.columns))
    if missing:
        raise ValueError(f"Observer feature frame is missing required columns: {missing}")

    frame = feature_frame.copy()
    if "threshold_w_m2" in frame.columns:
        threshold = pd.to_numeric(frame["threshold_w_m2"], errors="coerce").fillna(0.0)
        frame = frame.loc[threshold.eq(0.0)].copy()

    frame["date"] = pd.to_datetime(frame["date"]).dt.normalize()
    frame["loadcell_id"] = _normalise_loadcell(frame["loadcell_id"])
    frame["treatment"] = frame["treatment"].astype(str)
    frame = frame.sort_values(["loadcell_id", "date"]).reset_index(drop=True)

    daily_fw = _first_numeric(
        frame,
        (
            "loadcell_daily_yield_g",
            "observed_fruit_FW_g_loadcell",
            "measured_or_legacy_fresh_yield_g",
            "observed_fruit_FW_g_loadcell_legacy_yield",
        ),
    )
    cumulative_fw = _first_numeric(
        frame,
        (
            "loadcell_cumulative_yield_g",
            "individual_cumulative_yield_g",
        ),
    )
    if cumulative_fw.notna().any():
        cumulative_fw = cumulative_fw.groupby(frame["loadcell_id"]).ffill().fillna(0.0)
    else:
        cumulative_fw = daily_fw.fillna(0.0).groupby(frame["loadcell_id"]).cumsum()

    if daily_fw.notna().any():
        daily_fw = daily_fw.fillna(0.0)
    else:
        daily_fw = (
            cumulative_fw.groupby(frame["loadcell_id"])
            .diff()
            .fillna(cumulative_fw)
            .clip(lower=0.0)
        )

    observed_dw_loadcell = cumulative_fw * CANONICAL_2025_2C_FRUIT_DMC
    observed_dw_floor = observed_dw_loadcell / float(effective_floor_area_per_loadcell_m2)
    daily_dw_floor = daily_fw * CANONICAL_2025_2C_FRUIT_DMC / float(
        effective_floor_area_per_loadcell_m2
    )

    out = pd.DataFrame(
        {
            "date": frame["date"],
            "loadcell_id": frame["loadcell_id"],
            "treatment": frame["treatment"],
            "fresh_yield_available": frame.get("fresh_yield_available", True),
            "fresh_yield_source": frame.get("fresh_yield_source", ""),
            "measured_cumulative_fruit_FW_g_loadcell": cumulative_fw,
            "measured_cumulative_fruit_DW_g_m2_floor_dmc_0p056": observed_dw_floor,
            "measured_daily_increment_FW_g_loadcell": daily_fw,
            "measured_daily_increment_DW_g_m2_floor_dmc_0p056": daily_dw_floor,
            "observed_fruit_FW_g_loadcell": cumulative_fw,
            "observed_fruit_DW_g_loadcell_dmc_0p056": observed_dw_loadcell,
            "observed_fruit_DW_g_m2_floor_dmc_0p056": observed_dw_floor,
            "canonical_fruit_DMC_fraction": CANONICAL_2025_2C_FRUIT_DMC,
            "fruit_DMC_fraction": CANONICAL_2025_2C_FRUIT_DMC,
            "default_fruit_dry_matter_content": CANONICAL_2025_2C_FRUIT_DMC,
            "DMC_fixed_for_2025_2C": True,
            "DMC_sensitivity_enabled": False,
            "dry_yield_is_dmc_estimated": True,
            "direct_dry_yield_measured": False,
            "observation_operator": OBSERVATION_OPERATOR_FAMILY,
            "inverse_observation_operator": INVERSE_OBSERVATION_OPERATOR_FAMILY,
            "fdmc_mode": FDMC_MODE,
            "yield_source": frame.get("legacy_yield_bridge_provenance", ""),
            "dry_yield_source": "fresh_yield_times_canonical_DMC_0p056",
        }
    )
    return out


def observation_operator_audit(frame: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "observation_operator": OBSERVATION_OPERATOR_FAMILY,
                "inverse_observation_operator": INVERSE_OBSERVATION_OPERATOR_FAMILY,
                "observation_operator_family": OBSERVATION_OPERATOR_FAMILY,
                "observation_operator_family_inverse": INVERSE_OBSERVATION_OPERATOR_FAMILY,
                "fdmc_mode": FDMC_MODE,
                "canonical_fruit_DMC_fraction": CANONICAL_2025_2C_FRUIT_DMC,
                "DMC_fixed_for_2025_2C": True,
                "DMC_sensitivity_enabled": False,
                "dry_yield_is_dmc_estimated": True,
                "direct_dry_yield_measured": False,
                "rows": int(len(frame)),
                "non_null_cumulative_dw_rows": int(
                    frame.get(
                        "measured_cumulative_fruit_DW_g_m2_floor_dmc_0p056",
                        pd.Series(dtype=float),
                    )
                    .notna()
                    .sum()
                ),
                "status": "ok" if not frame.empty else "empty_observation_frame",
            }
        ]
    )


__all__ = [
    "FDMC_MODE",
    "INVERSE_OBSERVATION_OPERATOR_FAMILY",
    "OBSERVATION_OPERATOR_FAMILY",
    "build_harvest_observation_frame_dmc_0p056",
    "dry_floor_area_to_fresh_loadcell",
    "fresh_loadcell_to_dry_floor_area",
    "observation_operator_audit",
]
