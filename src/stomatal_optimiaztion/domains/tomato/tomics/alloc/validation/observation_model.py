from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd


REPORTING_BASIS_FLOOR_AREA = "floor_area_g_m2"


@dataclass(frozen=True, slots=True)
class ValidationSeriesBundle:
    merged_df: pd.DataFrame
    metrics: dict[str, float | str | bool]


def _series_metrics(observed: pd.Series, predicted: pd.Series) -> dict[str, float]:
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
    nonnull = clean.dropna()
    first = nonnull.iloc[0] if not nonnull.empty else 0.0
    return clean - float(first)


def _threshold_crossing_days(
    series: pd.Series,
    dates: pd.Series,
    *,
    fractions: tuple[float, ...] = (0.10, 0.25, 0.50, 0.75, 0.90),
) -> list[float]:
    clean = pd.to_numeric(series, errors="coerce")
    valid = pd.DataFrame({"date": pd.to_datetime(dates), "value": clean}).dropna()
    if valid.empty:
        return []
    final_value = float(valid["value"].iloc[-1])
    if final_value <= 1e-9:
        return []
    start_date = pd.Timestamp(valid["date"].iloc[0]).normalize()
    day_offsets: list[float] = []
    for frac in fractions:
        threshold = final_value * frac
        reached = valid[valid["value"] >= threshold]
        if reached.empty:
            continue
        first_date = pd.Timestamp(reached["date"].iloc[0]).normalize()
        day_offsets.append(float((first_date - start_date).days))
    return day_offsets


def harvest_timing_mae_days(
    *,
    observed_series: pd.Series,
    predicted_series: pd.Series,
    dates: pd.Series,
) -> float:
    observed_offsets = _threshold_crossing_days(observed_series, dates)
    predicted_offsets = _threshold_crossing_days(predicted_series, dates)
    paired = list(zip(observed_offsets, predicted_offsets, strict=False))
    if not paired:
        return math.nan
    return float(np.mean([abs(pred - obs) for obs, pred in paired]))


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


def compute_validation_bundle(
    observed_df: pd.DataFrame,
    *,
    candidate_series: pd.Series,
    candidate_daily_increment_series: pd.Series | None = None,
    candidate_label: str,
    unit_declared_in_observation_file: str,
) -> ValidationSeriesBundle:
    merged = observed_df.copy()
    cumulative_column = f"{candidate_label}_cumulative_total_fruit_dry_weight_floor_area"
    merged[cumulative_column] = pd.to_numeric(candidate_series, errors="coerce")
    merged["measured_offset_adjusted"] = _offset_adjusted(
        merged["measured_cumulative_total_fruit_dry_weight_floor_area"]
    )
    merged[f"{candidate_label}_offset_adjusted"] = _offset_adjusted(merged[cumulative_column])
    if candidate_daily_increment_series is None:
        merged[f"{candidate_label}_daily_increment_floor_area"] = pd.to_numeric(merged[cumulative_column], errors="coerce").diff()
    else:
        merged[f"{candidate_label}_daily_increment_floor_area"] = pd.to_numeric(
            candidate_daily_increment_series,
            errors="coerce",
        )

    raw_metrics = _series_metrics(
        merged["measured_cumulative_total_fruit_dry_weight_floor_area"],
        merged[cumulative_column],
    )
    offset_metrics = _series_metrics(
        merged["measured_offset_adjusted"],
        merged[f"{candidate_label}_offset_adjusted"],
    )
    increment_metrics = _series_metrics(
        merged["measured_daily_increment_floor_area"],
        merged[f"{candidate_label}_daily_increment_floor_area"],
    )
    increment_error = (
        merged[f"{candidate_label}_daily_increment_floor_area"] - merged["measured_daily_increment_floor_area"]
    ).abs()
    increment_error = pd.to_numeric(increment_error, errors="coerce")
    if merged.empty:
        final_bias = math.nan
        observed_final = math.nan
        final_bias_pct = math.nan
        final_window_error = math.nan
        offset_adjustment_applied = False
    else:
        final_bias = float(
            pd.to_numeric(merged[cumulative_column], errors="coerce").iloc[-1]
            - pd.to_numeric(merged["measured_cumulative_total_fruit_dry_weight_floor_area"], errors="coerce").iloc[-1]
        )
        observed_final = float(
            pd.to_numeric(merged["measured_cumulative_total_fruit_dry_weight_floor_area"], errors="coerce").iloc[-1]
        )
        final_bias_pct = final_bias / observed_final * 100.0 if abs(observed_final) > 1e-9 else math.nan
        final_window_error = float(
            merged[f"{candidate_label}_offset_adjusted"].iloc[-1] - merged["measured_offset_adjusted"].iloc[-1]
        )
        offset_adjustment_applied = bool(
            abs(float(pd.to_numeric(merged["measured_cumulative_total_fruit_dry_weight_floor_area"], errors="coerce").iloc[0])) > 1e-9
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
        "peak_daily_increment_error": float(increment_error.max()) if increment_error.notna().any() else math.nan,
        "final_window_error": final_window_error,
        "offset_adjustment_applied": offset_adjustment_applied,
        "rmse_cumulative_raw": raw_metrics["rmse"],
        "rmse_cumulative_offset": offset_metrics["rmse"],
        "mae_cumulative_offset": offset_metrics["mae"],
        "r2_cumulative_offset": offset_metrics["r2"],
        "rmse_daily_increment": increment_metrics["rmse"],
        "mae_daily_increment": increment_metrics["mae"],
        "harvest_timing_mae_days": harvest_timing_mae_days(
            observed_series=merged["measured_offset_adjusted"],
            predicted_series=merged[f"{candidate_label}_offset_adjusted"],
            dates=merged["date"],
        ),
        "final_cumulative_bias": final_bias,
        "final_cumulative_bias_pct": final_bias_pct,
    }
    return ValidationSeriesBundle(merged_df=merged, metrics=metrics)


def resolve_validation_series_columns(
    validation_df: pd.DataFrame,
    *,
    source_label: str,
) -> tuple[str, str, str]:
    prefixes = [source_label]
    if source_label == "workbook_estimated":
        prefixes.append("estimated")
    elif source_label not in {"measured", "estimated", "model"}:
        prefixes.append("model")

    for prefix in prefixes:
        cumulative_column = f"{prefix}_cumulative_total_fruit_dry_weight_floor_area"
        offset_column = f"{prefix}_offset_adjusted"
        increment_column = f"{prefix}_daily_increment_floor_area"
        if {
            cumulative_column,
            offset_column,
            increment_column,
        }.issubset(validation_df.columns):
            return cumulative_column, offset_column, increment_column
    raise KeyError(
        "Could not resolve validation series columns "
        f"for source_label={source_label!r} in columns={list(validation_df.columns)!r}."
    )


def validation_overlay_frame(
    validation_df: pd.DataFrame,
    *,
    source_label: str,
) -> pd.DataFrame:
    cumulative_column, offset_column, increment_column = resolve_validation_series_columns(
        validation_df,
        source_label=source_label,
    )
    date_column = "date" if "date" in validation_df.columns else validation_df.columns[0]
    return pd.DataFrame(
        {
            "datetime": pd.to_datetime(validation_df[date_column]),
            "cumulative_total_fruit_floor_area": pd.to_numeric(validation_df[cumulative_column], errors="coerce"),
            "offset_adjusted_cumulative_total_fruit_floor_area": pd.to_numeric(
                validation_df[offset_column],
                errors="coerce",
            ),
            "daily_increment_floor_area": pd.to_numeric(validation_df[increment_column], errors="coerce"),
        }
    )


__all__ = [
    "REPORTING_BASIS_FLOOR_AREA",
    "ValidationSeriesBundle",
    "compute_validation_bundle",
    "harvest_timing_mae_days",
    "merge_validation_series",
    "resolve_validation_series_columns",
    "validation_overlay_frame",
]
