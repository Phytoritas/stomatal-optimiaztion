from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import numpy as np
import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.observers.radiation_windows import add_radiation_phase_columns


def _group_columns(frame: pd.DataFrame, candidates: Iterable[str]) -> list[str]:
    return [column for column in candidates if column in frame.columns]


def build_10min_event_bridged_water_loss(
    frame: pd.DataFrame,
    radiation_intervals: pd.DataFrame | None = None,
    *,
    timestamp_col: str = "timestamp",
    weight_col: str = "loadcell_weight_kg",
    interval_minutes: int = 10,
    event_threshold_g: float = 50.0,
) -> pd.DataFrame:
    if "interval_start" in frame.columns and {"quiet_loss_rate_g_h", "event_flag"}.issubset(frame.columns):
        out = frame.copy()
        out["interval_start"] = pd.to_datetime(out["interval_start"], errors="coerce")
        out["interval_end"] = out.get(
            "interval_end", out["interval_start"] + pd.to_timedelta(interval_minutes, unit="min")
        )
        rate = np.where(
            out["event_flag"].astype(bool),
            pd.to_numeric(out.get("bridge_loss_rate_g_h", out["quiet_loss_rate_g_h"]), errors="coerce"),
            pd.to_numeric(out["quiet_loss_rate_g_h"], errors="coerce"),
        )
        out["loss_g_10min_unscaled"] = rate * interval_minutes / 60.0
        out["water_flux_source_used"] = "rate_columns"
    else:
        if timestamp_col not in frame.columns:
            raise KeyError(f"Missing timestamp column: {timestamp_col}")
        if weight_col not in frame.columns:
            raise KeyError(f"Missing loadcell weight column: {weight_col}")
        group_cols = _group_columns(frame, ("loadcell_id", "sample_id", "treatment"))
        data = frame[[timestamp_col, weight_col, *group_cols]].copy()
        data[timestamp_col] = pd.to_datetime(data[timestamp_col], errors="coerce")
        data[weight_col] = pd.to_numeric(data[weight_col], errors="coerce")
        data = data.dropna(subset=[timestamp_col]).sort_values([*group_cols, timestamp_col])
        data["interval_start"] = data[timestamp_col].dt.floor(f"{interval_minutes}min")
        data["weight_delta_g"] = data.groupby(group_cols, dropna=False)[weight_col].diff() * 1000.0 if group_cols else data[
            weight_col
        ].diff() * 1000.0
        data["positive_loss_g"] = (-data["weight_delta_g"]).clip(lower=0.0)
        data["event_flag"] = data["weight_delta_g"].abs().gt(event_threshold_g)
        group_keys = [column for column in ("loadcell_id", "treatment", "interval_start") if column in data.columns]
        out = (
            data.groupby(group_keys, dropna=False)
            .agg(
                loss_g_10min_unscaled=("positive_loss_g", "sum"),
                event_flag=("event_flag", "max"),
            )
            .reset_index()
        )
        out["interval_end"] = out["interval_start"] + pd.to_timedelta(interval_minutes, unit="min")
        out["water_flux_source_used"] = "loadcell_weight_kg_derivative"

    out["date"] = pd.to_datetime(out["interval_start"], errors="coerce").dt.strftime("%Y-%m-%d")
    out["event_type"] = np.where(out["event_flag"].fillna(False).astype(bool), "irrigation_or_drainage", "quiet")
    out["warnings"] = ""

    if radiation_intervals is not None and not radiation_intervals.empty:
        phase_wide = add_radiation_phase_columns(radiation_intervals)
        merge_cols = [column for column in ("interval_start", "loadcell_id", "treatment") if column in out.columns and column in phase_wide.columns]
        if merge_cols:
            out = out.merge(phase_wide, on=merge_cols, how="left", suffixes=("", "_radiation"))
            if "date_radiation" in out.columns:
                out = out.drop(columns=["date_radiation"])
            if "interval_end_radiation" in out.columns:
                out = out.drop(columns=["interval_end_radiation"])

    out["daily_bridge_scale_factor"] = np.nan
    out["loss_g_10min_event_bridged_calibrated"] = np.nan
    out["bridge_status"] = "uncalibrated_no_daily_total"
    return out.sort_values([column for column in ("date", "loadcell_id", "interval_start") if column in out.columns]).reset_index(
        drop=True
    )


def calibrate_to_daily_event_bridged_total(
    intervals: pd.DataFrame,
    daily_totals: pd.DataFrame | None = None,
    *,
    total_col: str = "existing_daily_event_bridged_loss_g_per_day",
) -> pd.DataFrame:
    out = intervals.copy()
    if daily_totals is None or daily_totals.empty or total_col not in daily_totals.columns:
        out["daily_bridge_scale_factor"] = np.nan
        out["loss_g_10min_event_bridged_calibrated"] = np.nan
        out["bridge_status"] = "uncalibrated_no_daily_total"
        return out

    merge_cols = [column for column in ("date", "loadcell_id", "treatment") if column in out.columns and column in daily_totals.columns]
    totals = out.groupby(merge_cols, dropna=False)["loss_g_10min_unscaled"].sum().rename("unscaled_daily_loss_g").reset_index()
    scale = totals.merge(daily_totals[merge_cols + [total_col]], on=merge_cols, how="left")
    scale["daily_bridge_scale_factor"] = scale[total_col] / scale["unscaled_daily_loss_g"].replace(0, np.nan)
    out = out.merge(scale[merge_cols + ["daily_bridge_scale_factor"]], on=merge_cols, how="left", suffixes=("", "_new"))
    if "daily_bridge_scale_factor_new" in out.columns:
        out["daily_bridge_scale_factor"] = out["daily_bridge_scale_factor_new"]
        out = out.drop(columns=["daily_bridge_scale_factor_new"])
    out["loss_g_10min_event_bridged_calibrated"] = out["loss_g_10min_unscaled"] * out["daily_bridge_scale_factor"]
    out["bridge_status"] = np.where(out["daily_bridge_scale_factor"].notna(), "calibrated_to_daily_event_total", "uncalibrated_no_daily_total")
    return out


def summarize_radiation_daynight_et(intervals: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    threshold_cols = [column for column in intervals.columns if column.startswith("radiation_phase_") and column.endswith("W")]
    value_col = (
        "loss_g_10min_event_bridged_calibrated"
        if intervals.get("loss_g_10min_event_bridged_calibrated", pd.Series(dtype=float)).notna().any()
        else "loss_g_10min_unscaled"
    )
    for threshold_col in threshold_cols:
        threshold = float(threshold_col.removeprefix("radiation_phase_").removesuffix("W"))
        group_cols = [column for column in ("date", "loadcell_id", "treatment") if column in intervals.columns]
        for keys, group in intervals.groupby(group_cols, dropna=False):
            if not isinstance(keys, tuple):
                keys = (keys,)
            row = dict(zip(group_cols, keys, strict=True))
            day = group[group[threshold_col].eq("day")]
            night = group[group[threshold_col].eq("night")]
            day_et = float(day[value_col].sum())
            night_et = float(night[value_col].sum())
            day_hours = day.shape[0] * (10.0 / 60.0)
            night_hours = night.shape[0] * (10.0 / 60.0)
            row.update(
                {
                    "threshold_w_m2": threshold,
                    "radiation_day_ET_g": day_et,
                    "radiation_night_ET_g": night_et,
                    "radiation_day_rate_g_h": day_et / day_hours if day_hours > 0 else np.nan,
                    "radiation_night_rate_g_h": night_et / night_hours if night_hours > 0 else np.nan,
                    "day_fraction_ET": day_et / (day_et + night_et) if (day_et + night_et) > 0 else np.nan,
                    "night_fraction_ET": night_et / (day_et + night_et) if (day_et + night_et) > 0 else np.nan,
                    "bridge_status": ";".join(sorted(set(group.get("bridge_status", pd.Series(["unknown"])).dropna().astype(str)))),
                    "water_flux_source_used": ";".join(
                        sorted(set(group.get("water_flux_source_used", pd.Series(["unknown"])).dropna().astype(str)))
                    ),
                }
            )
            rows.append(row)
    summary = pd.DataFrame(rows)
    if summary.empty:
        return summary
    if "treatment" not in summary.columns:
        summary["drought_control_day_ET_ratio"] = np.nan
        summary["drought_control_night_ET_ratio"] = np.nan
        return summary.reset_index(drop=True)
    control = summary[summary["treatment"].eq("Control")]
    drought = summary[summary["treatment"].eq("Drought")]
    ratio_cols = ["date", "threshold_w_m2"]
    if not control.empty and not drought.empty:
        control_mean = control.groupby(ratio_cols, dropna=False)[["radiation_day_ET_g", "radiation_night_ET_g"]].mean()
        drought_mean = drought.groupby(ratio_cols, dropna=False)[["radiation_day_ET_g", "radiation_night_ET_g"]].mean()
        ratios = drought_mean.join(control_mean, lsuffix="_drought", rsuffix="_control").reset_index()
        ratios["drought_control_day_ET_ratio"] = ratios["radiation_day_ET_g_drought"] / ratios[
            "radiation_day_ET_g_control"
        ].replace(0, np.nan)
        ratios["drought_control_night_ET_ratio"] = ratios["radiation_night_ET_g_drought"] / ratios[
            "radiation_night_ET_g_control"
        ].replace(0, np.nan)
        summary = summary.merge(
            ratios[ratio_cols + ["drought_control_day_ET_ratio", "drought_control_night_ET_ratio"]],
            on=ratio_cols,
            how="left",
        )
    else:
        summary["drought_control_day_ET_ratio"] = np.nan
        summary["drought_control_night_ET_ratio"] = np.nan
    return summary.sort_values([column for column in ("date", "loadcell_id", "threshold_w_m2") if column in summary.columns]).reset_index(
        drop=True
    )


def build_daily_wide_et_summary(daily_summary: pd.DataFrame, *, threshold_w_m2: int | float = 0) -> pd.DataFrame:
    main = daily_summary[daily_summary["threshold_w_m2"].eq(float(threshold_w_m2))].copy()
    if main.empty:
        return main
    main["radiation_total_ET_g"] = main["radiation_day_ET_g"] + main["radiation_night_ET_g"]
    main["fixed_clock_daynight_primary"] = False
    return main
