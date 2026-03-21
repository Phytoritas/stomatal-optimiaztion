from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.knu_data import PLANTS_PER_M2


REPORTING_BASIS_FLOOR_AREA = "floor_area_g_m2"


@dataclass(frozen=True, slots=True)
class ValidationSeriesBundle:
    merged_df: pd.DataFrame
    metrics: dict[str, float | str | bool]


def to_floor_area_value(value: float, *, basis: str, plants_per_m2: float = PLANTS_PER_M2) -> float:
    key = str(basis).strip().lower()
    if key in {"floor_area", "floor_area_g_m2", "g/m^2", "g m^-2", "g/m2"}:
        return float(value)
    if key in {"per_plant", "g/plant"}:
        return float(value) * float(plants_per_m2)
    raise ValueError(f"Unsupported reporting basis {basis!r}.")


def daily_last(df: pd.DataFrame) -> pd.DataFrame:
    work = df.copy()
    work["datetime"] = pd.to_datetime(work["datetime"], errors="coerce")
    work = work.dropna(subset=["datetime"]).sort_values("datetime")
    work["date"] = work["datetime"].dt.normalize()
    return work.groupby("date", as_index=False).last()


def model_floor_area_cumulative_total_fruit(model_df: pd.DataFrame) -> pd.DataFrame:
    daily = daily_last(model_df)
    fruit = pd.to_numeric(daily.get("fruit_dry_weight_g_m2"), errors="coerce").fillna(0.0)
    harvested = pd.to_numeric(daily.get("harvested_fruit_g_m2"), errors="coerce").fillna(0.0)
    out = pd.DataFrame(
        {
            "date": daily["date"],
            "model_fruit_dry_weight_floor_area": fruit,
            "model_harvested_fruit_floor_area": harvested,
            "model_cumulative_total_fruit_dry_weight_floor_area": fruit + harvested,
        }
    )
    out["model_daily_increment_floor_area"] = (
        out["model_cumulative_total_fruit_dry_weight_floor_area"].diff().fillna(0.0).clip(lower=0.0)
    )
    return out


def observed_floor_area_yield(
    yield_df: pd.DataFrame,
    *,
    measured_column: str,
    estimated_column: str,
) -> pd.DataFrame:
    observed = pd.DataFrame(
        {
            "date": pd.to_datetime(yield_df.iloc[:, 0]).dt.normalize(),
            "measured_cumulative_total_fruit_dry_weight_floor_area": pd.to_numeric(
                yield_df[measured_column],
                errors="coerce",
            ),
            "estimated_cumulative_total_fruit_dry_weight_floor_area": pd.to_numeric(
                yield_df[estimated_column],
                errors="coerce",
            ),
        }
    )
    observed["measured_daily_increment_floor_area"] = (
        observed["measured_cumulative_total_fruit_dry_weight_floor_area"].diff().fillna(0.0)
    )
    observed["estimated_daily_increment_floor_area"] = (
        observed["estimated_cumulative_total_fruit_dry_weight_floor_area"].diff().fillna(0.0)
    )
    return observed


def merge_validation_series(
    observed_df: pd.DataFrame,
    model_daily_df: pd.DataFrame,
    *,
    model_value_column: str = "model_cumulative_total_fruit_dry_weight_floor_area",
    source_label: str,
) -> pd.DataFrame:
    merged = observed_df.merge(
        model_daily_df[["date", model_value_column, "model_daily_increment_floor_area"]],
        on="date",
        how="left",
    )
    merged = merged.rename(
        columns={
            model_value_column: f"{source_label}_cumulative_total_fruit_dry_weight_floor_area",
            "model_daily_increment_floor_area": f"{source_label}_daily_increment_floor_area",
        }
    )
    return merged


def _series_metrics(
    observed: pd.Series,
    predicted: pd.Series,
) -> dict[str, float]:
    work = pd.DataFrame({"observed": observed, "predicted": predicted}).dropna()
    if work.empty:
        return {
            "rmse": math.nan,
            "mae": math.nan,
            "bias": math.nan,
            "nrmse": math.nan,
            "r2": math.nan,
            "mape": math.nan,
        }
    error = work["predicted"] - work["observed"]
    rmse = float(np.sqrt(np.mean(np.square(error))))
    mae = float(np.mean(np.abs(error)))
    bias = float(np.mean(error))
    denom = float(work["observed"].max() - work["observed"].min())
    nrmse = rmse / denom if denom > 1e-9 else math.nan
    if work.shape[0] >= 2 and float(work["observed"].var()) > 1e-12:
        ss_res = float(np.square(error).sum())
        ss_tot = float(np.square(work["observed"] - work["observed"].mean()).sum())
        r2 = 1.0 - ss_res / ss_tot if ss_tot > 1e-12 else math.nan
    else:
        r2 = math.nan
    safe_obs = work["observed"].replace(0.0, np.nan)
    mape = float((np.abs(error) / safe_obs).dropna().mean() * 100.0) if safe_obs.notna().any() else math.nan
    return {
        "rmse": rmse,
        "mae": mae,
        "bias": bias,
        "nrmse": nrmse,
        "r2": r2,
        "mape": mape,
    }


def _offset_adjusted(series: pd.Series) -> pd.Series:
    clean = pd.to_numeric(series, errors="coerce")
    first = clean.dropna().iloc[0] if clean.dropna().shape[0] > 0 else 0.0
    return clean - float(first)


def compute_validation_bundle(
    observed_df: pd.DataFrame,
    *,
    candidate_series: pd.Series,
    candidate_label: str,
    unit_declared_in_observation_file: str,
) -> ValidationSeriesBundle:
    merged = observed_df.copy()
    merged[f"{candidate_label}_cumulative_total_fruit_dry_weight_floor_area"] = pd.to_numeric(
        candidate_series,
        errors="coerce",
    )
    merged["measured_offset_adjusted"] = _offset_adjusted(
        merged["measured_cumulative_total_fruit_dry_weight_floor_area"]
    )
    merged[f"{candidate_label}_offset_adjusted"] = _offset_adjusted(
        merged[f"{candidate_label}_cumulative_total_fruit_dry_weight_floor_area"]
    )
    merged[f"{candidate_label}_daily_increment_floor_area"] = (
        merged[f"{candidate_label}_cumulative_total_fruit_dry_weight_floor_area"].diff().fillna(0.0)
    )
    raw_metrics = _series_metrics(
        merged["measured_cumulative_total_fruit_dry_weight_floor_area"],
        merged[f"{candidate_label}_cumulative_total_fruit_dry_weight_floor_area"],
    )
    offset_metrics = _series_metrics(
        merged["measured_offset_adjusted"],
        merged[f"{candidate_label}_offset_adjusted"],
    )
    increment_error = (
        merged[f"{candidate_label}_daily_increment_floor_area"] - merged["measured_daily_increment_floor_area"]
    ).abs()
    final_window_error = (
        merged[f"{candidate_label}_offset_adjusted"].iloc[-1] - merged["measured_offset_adjusted"].iloc[-1]
    )
    metrics = {
        "reporting_basis": REPORTING_BASIS_FLOOR_AREA,
        "unit_declared_in_observation_file": unit_declared_in_observation_file,
        "yield_rmse_raw": raw_metrics["rmse"],
        "yield_rmse_offset_adjusted": offset_metrics["rmse"],
        "yield_mae_raw": raw_metrics["mae"],
        "yield_mae_offset_adjusted": offset_metrics["mae"],
        "yield_bias_raw": raw_metrics["bias"],
        "yield_bias_offset_adjusted": offset_metrics["bias"],
        "yield_nrmse_raw": raw_metrics["nrmse"],
        "yield_nrmse_offset_adjusted": offset_metrics["nrmse"],
        "yield_r2_raw": raw_metrics["r2"],
        "yield_r2_offset_adjusted": offset_metrics["r2"],
        "yield_mape_offset_adjusted": offset_metrics["mape"],
        "peak_daily_increment_error": float(increment_error.max()),
        "final_window_error": float(final_window_error),
        "offset_adjustment_applied": bool(
            abs(float(merged["measured_cumulative_total_fruit_dry_weight_floor_area"].iloc[0])) > 1e-9
        ),
    }
    return ValidationSeriesBundle(merged_df=merged, metrics=metrics)


def canopy_collapse_days(
    df: pd.DataFrame,
    *,
    lai_floor: float = 2.0,
    leaf_floor: float = 0.18,
) -> int:
    if df.empty:
        return 0
    work = df.copy()
    work["date"] = pd.to_datetime(work["datetime"]).dt.normalize()
    active = (pd.to_numeric(work.get("active_trusses"), errors="coerce").fillna(0.0) > 0.0) | (
        pd.to_numeric(work.get("fruit_dry_weight_g_m2"), errors="coerce").fillna(0.0) > 0.0
    )
    collapse = active & (
        (pd.to_numeric(work.get("LAI"), errors="coerce").fillna(0.0) < lai_floor)
        | (pd.to_numeric(work.get("alloc_frac_leaf"), errors="coerce").fillna(0.0) < leaf_floor)
    )
    return int(collapse.groupby(work["date"]).any().sum())


__all__ = [
    "REPORTING_BASIS_FLOOR_AREA",
    "ValidationSeriesBundle",
    "canopy_collapse_days",
    "compute_validation_bundle",
    "daily_last",
    "merge_validation_series",
    "model_floor_area_cumulative_total_fruit",
    "observed_floor_area_yield",
    "to_floor_area_value",
]
