"""Time aggregation utilities for load-cell pipeline outputs."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def resample_flux_timeseries(df_1s: pd.DataFrame, rule: str) -> pd.DataFrame:
    """Resample per-second flux outputs to a coarser time step."""

    if not isinstance(df_1s.index, pd.DatetimeIndex):
        raise TypeError("df_1s must have a DateTimeIndex for resampling.")
    if df_1s.empty:
        return pd.DataFrame()

    required = {"irrigation_kg_s", "drainage_kg_s", "transpiration_kg_s"}
    missing = required - set(df_1s.columns)
    if missing:
        raise KeyError(f"df_1s missing required flux columns: {missing}")

    grouped = df_1s.resample(rule)
    out = pd.DataFrame(index=grouped.size().index)
    out.index.name = "timestamp"

    n_samples = grouped.size().astype("int64")
    out["n_samples"] = n_samples

    out["irrigation_kg"] = grouped["irrigation_kg_s"].sum(min_count=1).fillna(0.0)
    out["drainage_kg"] = grouped["drainage_kg_s"].sum(min_count=1).fillna(0.0)
    out["transpiration_kg"] = grouped["transpiration_kg_s"].sum(min_count=1).fillna(
        0.0
    )

    denom = n_samples.replace(0, np.nan).astype(float)
    out["irrigation_kg_s"] = (out["irrigation_kg"] / denom).fillna(0.0)
    out["drainage_kg_s"] = (out["drainage_kg"] / denom).fillna(0.0)
    out["transpiration_kg_s"] = (out["transpiration_kg"] / denom).fillna(0.0)

    out["cum_irrigation_kg"] = out["irrigation_kg"].cumsum()
    out["cum_drainage_kg"] = out["drainage_kg"].cumsum()
    out["cum_transpiration_kg"] = out["transpiration_kg"].cumsum()

    for col in [
        "weight_raw_kg",
        "weight_kg",
        "weight_smooth_kg",
        "reconstructed_weight_kg",
        "water_balance_error_before_fix_kg",
        "water_balance_error_kg",
    ]:
        if col in df_1s.columns:
            out[f"{col}_end"] = grouped[col].last()

    if "water_balance_error_kg" in df_1s.columns:
        out["water_balance_error_kg_mean_abs"] = (
            df_1s["water_balance_error_kg"].abs().resample(rule).mean()
        )

    if "is_interpolated" in df_1s.columns:
        out["interpolated_frac"] = df_1s["is_interpolated"].resample(rule).mean()
    if "is_outlier" in df_1s.columns:
        out["outlier_frac"] = df_1s["is_outlier"].resample(rule).mean()
    if "transpiration_scale" in df_1s.columns:
        out["transpiration_scale"] = grouped["transpiration_scale"].last()

    for col in [
        "irrigation_time_sec",
        "drainage_time_sec",
        "irrigation_time_sec_raw",
        "drainage_time_sec_raw",
    ]:
        if col in df_1s.columns:
            out[col] = df_1s[col].resample(rule).sum().fillna(0.0)
            out[col] = out[col].astype("int64")
            out[col.replace("_sec", "_frac")] = (out[col] / denom).fillna(0.0)

    for col in ["substrate_ec_ds", "substrate_moisture_percent"]:
        if col in df_1s.columns:
            out[col] = df_1s[col].resample(rule).mean()

    return out


def daily_summary(
    df_1s: pd.DataFrame,
    events_df: pd.DataFrame | None = None,
    metadata: dict[str, Any] | None = None,
) -> pd.DataFrame:
    """Build 1-day summary rows from per-second results."""

    if not isinstance(df_1s.index, pd.DatetimeIndex):
        raise TypeError("df_1s must have a DateTimeIndex for resampling.")
    if df_1s.empty:
        return pd.DataFrame()

    day_rule = "1D"
    out = pd.DataFrame(index=df_1s.resample(day_rule).size().index)
    out.index.name = "day"

    out["n_samples"] = df_1s.resample(day_rule).size().astype("int64")
    index_series = df_1s.index.to_series()
    out["start_time"] = index_series.resample(day_rule).min()
    out["end_time"] = index_series.resample(day_rule).max()

    if "irrigation_kg_s" in df_1s.columns:
        out["total_irrigation_kg"] = df_1s["irrigation_kg_s"].resample(day_rule).sum()
    if "drainage_kg_s" in df_1s.columns:
        out["total_drainage_kg"] = df_1s["drainage_kg_s"].resample(day_rule).sum()
    if "transpiration_kg_s" in df_1s.columns:
        out["total_transpiration_kg"] = (
            df_1s["transpiration_kg_s"].resample(day_rule).sum()
        )

    if "water_balance_error_kg" in df_1s.columns:
        out["final_balance_error_kg"] = (
            df_1s["water_balance_error_kg"].resample(day_rule).last()
        )
        out["mean_abs_balance_error_kg"] = (
            df_1s["water_balance_error_kg"].abs().resample(day_rule).mean()
        )

    if "is_interpolated" in df_1s.columns:
        out["interpolated_frac"] = df_1s["is_interpolated"].resample(day_rule).mean()
    if "is_outlier" in df_1s.columns:
        out["outlier_frac"] = df_1s["is_outlier"].resample(day_rule).mean()
    if "transpiration_scale" in df_1s.columns:
        out["transpiration_scale"] = (
            df_1s["transpiration_scale"].resample(day_rule).last()
        )

    for col in [
        "irrigation_time_sec",
        "drainage_time_sec",
        "irrigation_time_sec_raw",
        "drainage_time_sec_raw",
    ]:
        if col in df_1s.columns:
            out[col] = df_1s[col].resample(day_rule).sum().fillna(0.0).astype("int64")

    if "irrigation_time_sec" not in out.columns and "label" in df_1s.columns:
        labels = df_1s["label"].fillna("baseline").astype(str)
        out["irrigation_time_sec_raw"] = (
            (labels == "irrigation").resample(day_rule).sum().fillna(0.0).astype("int64")
        )
        out["drainage_time_sec_raw"] = (
            (labels == "drainage").resample(day_rule).sum().fillna(0.0).astype("int64")
        )

    denom_day = out["n_samples"].replace(0, np.nan).astype(float)
    for col in [
        "irrigation_time_sec",
        "drainage_time_sec",
        "irrigation_time_sec_raw",
        "drainage_time_sec_raw",
    ]:
        if col in out.columns:
            out[col.replace("_sec", "_frac")] = (out[col] / denom_day).fillna(0.0)

    for col in ["substrate_ec_ds", "substrate_moisture_percent"]:
        if col in df_1s.columns:
            out[col] = df_1s[col].resample(day_rule).mean()

    out["irrigation_event_count"] = 0
    out["drainage_event_count"] = 0
    if (
        events_df is not None
        and isinstance(events_df, pd.DataFrame)
        and not events_df.empty
        and {"start_time", "event_type"}.issubset(events_df.columns)
    ):
        events = events_df.copy()
        events["day"] = pd.to_datetime(events["start_time"], errors="coerce").dt.floor(
            "D"
        )
        counts = (
            events.dropna(subset=["day"])
            .groupby(["day", "event_type"])
            .size()
            .unstack(fill_value=0)
        )
        if "irrigation" in counts.columns:
            out["irrigation_event_count"] = (
                out.index.map(counts["irrigation"]).fillna(0).astype(int)
            )
        if "drainage" in counts.columns:
            out["drainage_event_count"] = (
                out.index.map(counts["drainage"]).fillna(0).astype(int)
            )

    if metadata:
        if "irrigation_threshold" in metadata:
            out["irrigation_threshold"] = float(metadata["irrigation_threshold"])
        if "drainage_threshold" in metadata:
            out["drainage_threshold"] = float(metadata["drainage_threshold"])

    return out
