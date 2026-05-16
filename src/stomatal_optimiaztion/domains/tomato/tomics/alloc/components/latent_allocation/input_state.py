from __future__ import annotations

import math
from typing import Any, Mapping

import numpy as np
import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.latent_allocation.contracts import (
    as_dict,
)


REQUIRED_PRODUCTION_METADATA = {
    "production_ready_for_latent_allocation": True,
    "production_export_completed": True,
    "row_cap_applied": False,
    "chunk_aggregation_used": True,
    "fixed_clock_daynight_primary": False,
    "radiation_column_used": "env_inside_radiation_wm2",
    "dataset1_radiation_directly_usable": True,
}


def _truthy(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and math.isfinite(float(value)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "y"}
    return False


def check_production_preconditions(
    metadata: Mapping[str, Any],
    config: Mapping[str, Any],
) -> tuple[bool, dict[str, Any]]:
    latent_cfg = as_dict(config.get("latent_allocation"))
    require_production = bool(latent_cfg.get("require_production_observer_export", True))
    require_no_cap = bool(latent_cfg.get("require_row_cap_absent", True))
    require_radiation = bool(latent_cfg.get("require_radiation_defined_daynight", True))

    checks: dict[str, Any] = {}
    if require_production:
        checks["production_ready_for_latent_allocation"] = (
            _truthy(metadata.get("production_ready_for_latent_allocation")) is True
        )
        checks["production_export_completed"] = _truthy(metadata.get("production_export_completed")) is True
        checks["chunk_aggregation_used"] = _truthy(metadata.get("chunk_aggregation_used")) is True
    if require_no_cap:
        checks["row_cap_applied"] = metadata.get("row_cap_applied") is False
    if require_radiation:
        checks["fixed_clock_daynight_primary"] = metadata.get("fixed_clock_daynight_primary") is False
        checks["radiation_column_used"] = metadata.get("radiation_column_used") == "env_inside_radiation_wm2"
        checks["dataset1_radiation_directly_usable"] = (
            metadata.get("dataset1_radiation_directly_usable") is True
        )

    passed = all(bool(value) for value in checks.values())
    return passed, {
        "production_observer_precondition_passed": passed,
        "precondition_checks": checks,
        "precondition_failure_reasons": [
            key for key, value in checks.items() if not bool(value)
        ],
    }


def _coalesce(frame: pd.DataFrame, candidates: tuple[str, ...], *, default: object = np.nan) -> pd.Series:
    result = pd.Series(default, index=frame.index)
    for column in candidates:
        if column in frame.columns:
            values = frame[column]
            result = result.where(result.notna(), values)
    return result


def _bool_series(frame: pd.DataFrame, column: str, *, default: bool = False) -> pd.Series:
    if column not in frame.columns:
        return pd.Series(default, index=frame.index)
    return frame[column].fillna(default).map(_truthy)


def _numeric_series(frame: pd.DataFrame, column: str, *, default: float = np.nan) -> pd.Series:
    if column not in frame.columns:
        return pd.Series(default, index=frame.index, dtype=float)
    return pd.to_numeric(frame[column], errors="coerce")


def _lai_proxy(frame: pd.DataFrame, config: Mapping[str, Any]) -> tuple[pd.Series, pd.Series]:
    latent_cfg = as_dict(config.get("latent_allocation"))
    lai_cfg = as_dict(latent_cfg.get("lai"))
    lai_available = bool(lai_cfg.get("lai_available", False))
    proxy_allowed = bool(lai_cfg.get("lai_proxy_allowed", False))
    if lai_available or not proxy_allowed:
        return (
            pd.Series(False, index=frame.index),
            pd.Series(np.nan, index=frame.index, dtype=float),
        )

    source = _numeric_series(frame, "source_proxy_MJ_CO2_T")
    positive = source[source > 0]
    scale = float(positive.quantile(0.75)) if not positive.empty else 1.0
    if not math.isfinite(scale) or scale <= 0.0:
        scale = 1.0
    target = float(lai_cfg.get("target_lai", 3.0))
    proxy = (source / scale * target).clip(lower=0.0, upper=target)
    return source.notna(), proxy


def build_latent_allocation_input_state(
    feature_frame: pd.DataFrame,
    metadata: dict[str, Any],
    config: dict[str, Any],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    passed, precondition_meta = check_production_preconditions(metadata, config)
    if not passed:
        empty = pd.DataFrame(
            columns=[
                "date",
                "loadcell_id",
                "treatment",
                "threshold_w_m2",
                "direct_partition_observation_available",
                "allocation_validation_basis",
            ]
        )
        return empty, precondition_meta | {"latent_allocation_ready": False}

    frame = feature_frame.copy()
    if frame.empty:
        return frame, precondition_meta | {"latent_allocation_ready": False, "input_row_count": 0}

    input_state = pd.DataFrame(index=frame.index)
    input_state["date"] = frame["date"].astype(str) if "date" in frame.columns else ""
    input_state["loadcell_id"] = frame.get("loadcell_id", pd.Series(np.nan, index=frame.index))
    input_state["treatment"] = frame.get("treatment", pd.Series("", index=frame.index)).astype(str)
    input_state["threshold_w_m2"] = pd.to_numeric(
        frame.get("threshold_w_m2", pd.Series(0, index=frame.index)),
        errors="coerce",
    ).fillna(0.0)

    numeric_columns = [
        "radiation_day_ET_g",
        "radiation_night_ET_g",
        "radiation_total_ET_g",
        "day_fraction_ET",
        "night_fraction_ET",
        "day_radiation_integral_MJ_m2",
        "day_radiation_mean_wm2",
        "RZI_main",
        "RZI_theta_paired",
        "RZI_theta_group",
        "tensiometer_coverage_fraction",
        "apparent_canopy_conductance",
        "source_proxy_MJ_CO2_T",
    ]
    for column in numeric_columns:
        input_state[column] = _numeric_series(frame, column)

    input_state["day_vpd_kpa_mean"] = pd.to_numeric(
        _coalesce(frame, ("day_vpd_kpa_mean", "day_vpd_kpa_mean_y", "day_vpd_kpa_mean_x")),
        errors="coerce",
    )
    input_state["RZI_main"] = input_state["RZI_main"].fillna(0.0).clip(lower=0.0, upper=1.0)
    input_state["radiation_total_ET_g"] = input_state["radiation_total_ET_g"].fillna(
        input_state["radiation_day_ET_g"].fillna(0.0) + input_state["radiation_night_ET_g"].fillna(0.0)
    )

    input_state["RZI_main_source"] = frame.get("RZI_main_source", pd.Series("not_available", index=frame.index))
    input_state["tensiometer_available"] = _bool_series(frame, "tensiometer_available")
    input_state["apparent_canopy_conductance_available"] = _bool_series(
        frame,
        "apparent_canopy_conductance_available",
        default=bool(metadata.get("apparent_canopy_conductance_available", False)),
    )
    input_state["source_proxy_MJ_CO2_T_available"] = _bool_series(
        frame,
        "source_proxy_MJ_CO2_T_available",
    ) | input_state["source_proxy_MJ_CO2_T"].notna()

    for column in frame.columns:
        if column.startswith("leaf_temp_") or column.startswith("delta_leaf_temp_"):
            input_state[column] = frame[column]
        if column in {
            "sensor_column",
            "mapping_status",
            "radiation_day_net_mm",
            "radiation_night_carryover_net_mm",
            "24h_net_mm",
            "stable_flag",
            "qc_status",
        }:
            input_state[column] = frame[column]
        if column.startswith("dataset3_") or column.startswith("Dataset3_") or column in {
            "stem_diameter_mean",
            "flower_cluster_height_mean",
            "flowering_date_min",
            "flowering_date_max",
            "flower_cluster_no_mean",
        }:
            input_state[column] = frame[column]

    input_state["LAI_available"] = False
    lai_proxy_available, lai_proxy_value = _lai_proxy(input_state, config)
    input_state["LAI_proxy_available"] = lai_proxy_available
    input_state["LAI_proxy_value"] = lai_proxy_value

    input_state["direct_partition_observation_available"] = False
    input_state["allocation_validation_basis"] = "latent_inference_from_observer_features"
    input_state["fruit_diameter_diagnostic_only"] = True
    input_state["fruit_diameter_p_values_allowed"] = False
    input_state["fruit_diameter_allocation_calibration_target"] = False
    input_state["fruit_diameter_model_promotion_target"] = False
    input_state["event_bridged_ET_calibration_status"] = metadata.get(
        "event_bridged_ET_calibration_status",
        "unknown",
    )
    input_state["Dataset3_mapping_confidence"] = metadata.get(
        "Dataset3_mapping_confidence",
        frame.get("Dataset3_mapping_confidence", pd.Series("unknown", index=frame.index)).iloc[0]
        if "Dataset3_mapping_confidence" in frame.columns and not frame.empty
        else "unknown",
    )
    input_state = input_state.sort_values(
        [column for column in ("date", "loadcell_id", "threshold_w_m2") if column in input_state.columns]
    ).reset_index(drop=True)
    return input_state, precondition_meta | {
        "latent_allocation_ready": True,
        "input_row_count": int(input_state.shape[0]),
        "LAI_proxy_used": bool(input_state["LAI_proxy_available"].any()),
        "event_bridged_ET_calibration_status": input_state["event_bridged_ET_calibration_status"].iloc[0],
    }


__all__ = [
    "REQUIRED_PRODUCTION_METADATA",
    "build_latent_allocation_input_state",
    "check_production_preconditions",
]
