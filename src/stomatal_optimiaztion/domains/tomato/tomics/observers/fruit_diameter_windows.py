from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import numpy as np
import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.observers.sensor_mapping import sensor_mapping_rows


def _value_at_timestamp(
    series_frame: pd.DataFrame,
    *,
    timestamp_col: str,
    value_col: str,
    timestamp: pd.Timestamp,
    max_gap: pd.Timedelta = pd.Timedelta(minutes=30),
) -> float:
    data = series_frame[[timestamp_col, value_col]].dropna().copy()
    data[timestamp_col] = pd.to_datetime(data[timestamp_col], errors="coerce")
    data = data.dropna(subset=[timestamp_col]).sort_values(timestamp_col)
    if data.empty or pd.isna(timestamp):
        return float("nan")
    indexed = data.set_index(timestamp_col)[value_col].astype(float)
    nearest_idx = indexed.index[np.argmin(np.abs(indexed.index - timestamp))]
    if abs(nearest_idx - timestamp) > max_gap:
        return float("nan")
    return float(indexed.loc[nearest_idx])


def build_fruit_leaf_loadcell_bridge(mapping: dict[str, Any]) -> pd.DataFrame:
    return sensor_mapping_rows(mapping)


def build_fruit_leaf_radiation_windows(
    qc_frame: pd.DataFrame,
    photoperiod: pd.DataFrame,
    mapping: dict[str, Any],
    *,
    timestamp_col: str = "TIMESTAMP",
    thresholds_w_m2: Iterable[int | float] = (0, 1, 5, 10),
) -> tuple[pd.DataFrame, pd.DataFrame]:
    frame = qc_frame.copy()
    frame[timestamp_col] = pd.to_datetime(frame[timestamp_col], errors="coerce")
    fruit_rows: list[dict[str, Any]] = []
    leaf_rows: list[dict[str, Any]] = []
    photoperiod = photoperiod.copy()
    photoperiod["first_light_timestamp"] = pd.to_datetime(photoperiod["first_light_timestamp"], errors="coerce")
    photoperiod["last_light_timestamp"] = pd.to_datetime(photoperiod["last_light_timestamp"], errors="coerce")

    for threshold in thresholds_w_m2:
        threshold_photo = photoperiod[photoperiod["threshold_w_m2"].eq(float(threshold))].sort_values("date")
        next_first_by_date = dict(
            zip(threshold_photo["date"], threshold_photo["first_light_timestamp"].shift(-1), strict=False)
        )
        for _, boundary in threshold_photo.iterrows():
            first_light = boundary["first_light_timestamp"]
            last_light = boundary["last_light_timestamp"]
            date = boundary["date"]
            for sensor_col, sensor_info in mapping.get("fruit_sensor_map", {}).items():
                valid_col = f"{sensor_col}_valid"
                sensor_frame = frame[frame.get(valid_col, True).astype(bool)] if valid_col in frame.columns else frame
                start_value = _value_at_timestamp(
                    sensor_frame,
                    timestamp_col=timestamp_col,
                    value_col=sensor_col,
                    timestamp=first_light,
                )
                last_value = _value_at_timestamp(
                    sensor_frame,
                    timestamp_col=timestamp_col,
                    value_col=sensor_col,
                    timestamp=last_light,
                )
                next_first = next_first_by_date.get(date)
                next_first_value = _value_at_timestamp(
                    sensor_frame,
                    timestamp_col=timestamp_col,
                    value_col=sensor_col,
                    timestamp=next_first,
                )
                day_data = sensor_frame[
                    (sensor_frame[timestamp_col] >= first_light) & (sensor_frame[timestamp_col] <= last_light)
                ]
                night_data = sensor_frame[
                    (sensor_frame[timestamp_col] >= last_light) & (sensor_frame[timestamp_col] <= next_first)
                ]
                step = pd.to_numeric(sensor_frame.get(sensor_col), errors="coerce").diff().abs()
                endpoint_ok = pd.notna(start_value) and pd.notna(last_value)
                fruit_rows.append(
                    {
                        "date": date,
                        "threshold_w_m2": float(threshold),
                        "sensor_column": sensor_col,
                        "loadcell_id": sensor_info.get("loadcell_id"),
                        "treatment": sensor_info.get("treatment"),
                        "mapping_status": sensor_info.get("mapping_status"),
                        "radiation_day_net_mm": last_value - start_value if endpoint_ok else np.nan,
                        "radiation_night_carryover_net_mm": (
                            next_first_value - last_value if pd.notna(next_first_value) and pd.notna(last_value) else np.nan
                        ),
                        "24h_net_mm": next_first_value - start_value if pd.notna(next_first_value) and pd.notna(start_value) else np.nan,
                        "radiation_day_range_mm": (
                            float(day_data[sensor_col].max() - day_data[sensor_col].min())
                            if not day_data.empty and sensor_col in day_data
                            else np.nan
                        ),
                        "radiation_night_range_mm": (
                            float(night_data[sensor_col].max() - night_data[sensor_col].min())
                            if not night_data.empty and sensor_col in night_data
                            else np.nan
                        ),
                        "max_10min_step_mm": float(step.max(skipna=True)) if step.notna().any() else np.nan,
                        "stable_flag": bool(endpoint_ok and (step.dropna() <= 1.0).all()),
                        "sensor_level_only": True,
                        "fruit_diameter_p_values_allowed": False,
                        "fruit_diameter_allocation_calibration_target": False,
                        "qc_status": "ok" if endpoint_ok else "insufficient_valid_points_or_no_radiation_boundary",
                    }
                )

            leaf_row: dict[str, Any] = {"date": date, "threshold_w_m2": float(threshold)}
            for sensor_col, sensor_info in mapping.get("leaf_sensor_map", {}).items():
                loadcell_id = sensor_info.get("loadcell_id")
                day = frame[(frame[timestamp_col] >= first_light) & (frame[timestamp_col] <= last_light)]
                next_first = next_first_by_date.get(date)
                night = frame[(frame[timestamp_col] >= last_light) & (frame[timestamp_col] <= next_first)]
                prefix = f"leaf_temp_lc{loadcell_id}"
                leaf_row[f"{prefix}_radiation_day_mean_c"] = (
                    float(pd.to_numeric(day[sensor_col], errors="coerce").mean()) if sensor_col in day else np.nan
                )
                leaf_row[f"{prefix}_radiation_night_mean_c"] = (
                    float(pd.to_numeric(night[sensor_col], errors="coerce").mean()) if sensor_col in night else np.nan
                )
            if {
                "leaf_temp_lc4_radiation_day_mean_c",
                "leaf_temp_lc1_radiation_day_mean_c",
            }.issubset(leaf_row):
                leaf_row["delta_leaf_temp_lc4_minus_lc1_radiation_day_mean_c"] = (
                    leaf_row["leaf_temp_lc4_radiation_day_mean_c"] - leaf_row["leaf_temp_lc1_radiation_day_mean_c"]
                )
                leaf_row["delta_leaf_temp_lc4_minus_lc1_radiation_night_mean_c"] = (
                    leaf_row["leaf_temp_lc4_radiation_night_mean_c"] - leaf_row["leaf_temp_lc1_radiation_night_mean_c"]
                )
            leaf_rows.append(leaf_row)

    return pd.DataFrame(fruit_rows), pd.DataFrame(leaf_rows)


def build_fixed_clock_compat_windows(
    qc_frame: pd.DataFrame,
    mapping: dict[str, Any],
    *,
    timestamp_col: str = "TIMESTAMP",
) -> pd.DataFrame:
    frame = qc_frame.copy()
    frame[timestamp_col] = pd.to_datetime(frame[timestamp_col], errors="coerce")
    frame["date"] = frame[timestamp_col].dt.strftime("%Y-%m-%d")
    rows: list[dict[str, Any]] = []
    for date, day_frame in frame.groupby("date", dropna=False):
        day = day_frame[(day_frame[timestamp_col].dt.hour >= 6) & (day_frame[timestamp_col].dt.hour < 18)]
        night = day_frame[~day_frame.index.isin(day.index)]
        for sensor_col, sensor_info in mapping.get("fruit_sensor_map", {}).items():
            rows.append(
                {
                    "date": date,
                    "sensor_column": sensor_col,
                    "loadcell_id": sensor_info.get("loadcell_id"),
                    "treatment": sensor_info.get("treatment"),
                    "clock_day_range_mm": (
                        float(day[sensor_col].max() - day[sensor_col].min()) if not day.empty and sensor_col in day else np.nan
                    ),
                    "clock_night_range_mm": (
                        float(night[sensor_col].max() - night[sensor_col].min())
                        if not night.empty and sensor_col in night
                        else np.nan
                    ),
                    "fixed_clock_daynight_primary": False,
                    "clock_06_18_used_only_for_compatibility": True,
                }
            )
    return pd.DataFrame(rows)
