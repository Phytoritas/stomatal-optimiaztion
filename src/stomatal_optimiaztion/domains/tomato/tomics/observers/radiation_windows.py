from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import numpy as np
import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.observers.contracts import (
    RADIATION_COLUMN_USED,
    RADIATION_PRIMARY_SOURCE,
    RADIATION_THRESHOLDS_W_M2,
)

ENV_MEAN_COLUMNS = {
    "env_vpd_kpa": "day_vpd_kpa_mean",
    "env_air_temperature_c": "day_air_temp_c_mean",
    "env_co2_ppm": "day_co2_ppm_mean",
}


def _available(columns: Iterable[str], frame: pd.DataFrame) -> list[str]:
    return [column for column in columns if column in frame.columns]


def _date_string(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, errors="coerce").dt.strftime("%Y-%m-%d")


def build_radiation_intervals(
    frame: pd.DataFrame,
    *,
    thresholds_w_m2: Iterable[int | float] = RADIATION_THRESHOLDS_W_M2,
    timestamp_col: str = "timestamp",
    radiation_col: str = RADIATION_COLUMN_USED,
    interval_minutes: int = 10,
    group_cols: Iterable[str] = ("loadcell_id", "treatment"),
) -> pd.DataFrame:
    if timestamp_col not in frame.columns:
        raise KeyError(f"Missing timestamp column: {timestamp_col}")
    if radiation_col not in frame.columns:
        raise KeyError(f"Missing radiation column: {radiation_col}")

    env_cols = _available(("env_vpd_kpa", "env_air_temperature_c", "env_co2_ppm"), frame)
    group_cols_present = _available(group_cols, frame)
    columns = [timestamp_col, radiation_col, *group_cols_present, *env_cols]
    data = frame.loc[:, list(dict.fromkeys(columns))].copy()
    data[timestamp_col] = pd.to_datetime(data[timestamp_col], errors="coerce")
    data = data.dropna(subset=[timestamp_col])
    data[radiation_col] = pd.to_numeric(data[radiation_col], errors="coerce")
    data["interval_start"] = data[timestamp_col].dt.floor(f"{interval_minutes}min")

    aggregations: dict[str, tuple[str, str]] = {
        "radiation_wm2_mean": (radiation_col, "mean"),
        "radiation_wm2_max": (radiation_col, "max"),
        "sample_count": (radiation_col, "count"),
    }
    for env_col in env_cols:
        aggregations[f"{env_col}_mean"] = (env_col, "mean")

    grouped = (
        data.groupby([*group_cols_present, "interval_start"], dropna=False)
        .agg(**aggregations)
        .reset_index()
    )
    grouped["interval_end"] = grouped["interval_start"] + pd.to_timedelta(interval_minutes, unit="min")
    grouped["date"] = _date_string(grouped["interval_start"])
    grouped["interval_seconds"] = float(interval_minutes * 60)
    grouped["radiation_source_used"] = RADIATION_PRIMARY_SOURCE
    grouped["radiation_column_used"] = radiation_col

    rows: list[pd.DataFrame] = []
    for threshold in thresholds_w_m2:
        threshold_frame = grouped.copy()
        threshold_frame["threshold_w_m2"] = float(threshold)
        threshold_frame["radiation_phase"] = np.where(
            threshold_frame["radiation_wm2_max"].fillna(0.0) > float(threshold), "day", "night"
        )
        rows.append(threshold_frame)
    out = pd.concat(rows, ignore_index=True) if rows else grouped.iloc[0:0].copy()
    return out.sort_values([*group_cols_present, "threshold_w_m2", "interval_start"]).reset_index(drop=True)


def add_radiation_phase_columns(intervals: pd.DataFrame) -> pd.DataFrame:
    if intervals.empty:
        return intervals.copy()
    id_cols = [column for column in ("interval_start", "interval_end", "date", "loadcell_id", "treatment") if column in intervals]
    values = intervals[id_cols + ["threshold_w_m2", "radiation_phase"]].copy()
    values["phase_col"] = values["threshold_w_m2"].map(lambda value: f"radiation_phase_{int(value)}W")
    wide = values.pivot_table(
        index=id_cols,
        columns="phase_col",
        values="radiation_phase",
        aggfunc="first",
    ).reset_index()
    wide.columns.name = None
    numeric_cols = [
        column
        for column in (
            "radiation_wm2_mean",
            "radiation_wm2_max",
            "env_vpd_kpa_mean",
            "env_air_temperature_c_mean",
            "env_co2_ppm_mean",
        )
        if column in intervals.columns
    ]
    base = intervals[intervals["threshold_w_m2"].eq(0)][id_cols + numeric_cols].copy()
    return base.merge(wide, on=id_cols, how="left")


def build_photoperiod_table(
    intervals: pd.DataFrame,
    *,
    dataset1_radiation_directly_usable: bool = True,
    fallback_required: bool = False,
    fallback_source_if_required: str | None = None,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for (date, threshold), group in intervals.groupby(["date", "threshold_w_m2"], dropna=False):
        deduped = group.sort_values("interval_start").drop_duplicates("interval_start")
        day = deduped[deduped["radiation_phase"].eq("day")]
        night = deduped[deduped["radiation_phase"].eq("night")]
        first_light = day["interval_start"].min() if not day.empty else pd.NaT
        last_light = day["interval_start"].max() if not day.empty else pd.NaT
        if pd.isna(first_light) or pd.isna(last_light):
            photoperiod_seconds = 0.0
        else:
            photoperiod_seconds = float((last_light - first_light).total_seconds() + 600)
        rows.append(
            {
                "date": date,
                "threshold_w_m2": float(threshold),
                "first_light_timestamp": first_light,
                "last_light_timestamp": last_light,
                "photoperiod_seconds": photoperiod_seconds,
                "day_interval_count": int(day.shape[0]),
                "night_interval_count": int(night.shape[0]),
                "radiation_source_used": RADIATION_PRIMARY_SOURCE,
                "radiation_column_used": RADIATION_COLUMN_USED,
                "dataset1_radiation_directly_usable": dataset1_radiation_directly_usable,
                "fallback_required": fallback_required,
                "fallback_source_if_required": fallback_source_if_required,
            }
        )
    return pd.DataFrame(rows).sort_values(["date", "threshold_w_m2"]).reset_index(drop=True)


def build_radiation_daily_summary(intervals: pd.DataFrame) -> pd.DataFrame:
    if intervals.empty:
        return pd.DataFrame()
    work = intervals.copy()
    work["radiation_energy_MJ_m2"] = work["radiation_wm2_mean"].fillna(0.0) * work["interval_seconds"] / 1_000_000
    group_cols = [column for column in ("date", "loadcell_id", "treatment", "threshold_w_m2") if column in work.columns]
    rows: list[dict[str, Any]] = []
    for keys, group in work.groupby(group_cols, dropna=False):
        if not isinstance(keys, tuple):
            keys = (keys,)
        row = dict(zip(group_cols, keys, strict=True))
        for phase in ("day", "night"):
            phase_group = group[group["radiation_phase"].eq(phase)]
            row[f"{phase}_interval_count"] = int(phase_group.shape[0])
            row[f"{phase}_radiation_integral_MJ_m2"] = float(phase_group["radiation_energy_MJ_m2"].sum())
            row[f"{phase}_radiation_mean_wm2"] = float(phase_group["radiation_wm2_mean"].mean()) if not phase_group.empty else np.nan
            for env_col, out_col in ENV_MEAN_COLUMNS.items():
                source_col = f"{env_col}_mean"
                if source_col in phase_group.columns:
                    row[out_col.replace("day_", f"{phase}_")] = (
                        float(phase_group[source_col].mean()) if not phase_group.empty else np.nan
                    )
        co2 = row.get("day_co2_ppm_mean")
        temp = row.get("day_air_temp_c_mean")
        integral = row.get("day_radiation_integral_MJ_m2")
        if pd.notna(co2) and pd.notna(temp) and pd.notna(integral):
            row["source_proxy_MJ_CO2_T"] = float(integral) * (float(co2) / 400.0) * np.exp(
                -((float(temp) - 25.0) / 12.0) ** 2
            )
            row["source_proxy_MJ_CO2_T_available"] = True
        else:
            row["source_proxy_MJ_CO2_T"] = np.nan
            row["source_proxy_MJ_CO2_T_available"] = False
        row["radiation_source_used"] = RADIATION_PRIMARY_SOURCE
        row["radiation_column_used"] = RADIATION_COLUMN_USED
        rows.append(row)
    return pd.DataFrame(rows).sort_values(group_cols).reset_index(drop=True)


def add_clock_compatibility_audit(
    frame: pd.DataFrame,
    *,
    timestamp_col: str = "TIMESTAMP",
    day_start_hour: int = 6,
    day_end_hour: int = 18,
) -> pd.DataFrame:
    out = frame.copy()
    out[timestamp_col] = pd.to_datetime(out[timestamp_col], errors="coerce")
    hour = out[timestamp_col].dt.hour
    out["clock_06_18_phase"] = np.where((hour >= day_start_hour) & (hour < day_end_hour), "day", "night")
    out["fixed_clock_daynight_primary"] = False
    out["clock_06_18_used_only_for_compatibility"] = True
    return out

