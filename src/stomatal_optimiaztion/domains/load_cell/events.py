"""Event detection utilities for load-cell irrigation and drainage analysis."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def label_points_by_derivative(
    df: pd.DataFrame,
    irrigation_threshold: float,
    drainage_threshold: float,
) -> pd.DataFrame:
    """Assign irrigation, drainage, or baseline labels from a derivative series."""

    if "dW_smooth_kg_s" not in df:
        raise KeyError("Input DataFrame must contain 'dW_smooth_kg_s'.")

    df_out = df.copy()
    d_w = df_out["dW_smooth_kg_s"].fillna(0.0)

    labels = pd.Series("baseline", index=df_out.index, dtype="object")
    labels[d_w >= irrigation_threshold] = "irrigation"
    labels[d_w <= drainage_threshold] = "drainage"

    df_out["label"] = labels
    return df_out


def label_points_by_derivative_hysteresis(
    df: pd.DataFrame,
    irrigation_threshold: float,
    drainage_threshold: float,
    hysteresis_ratio: float = 0.5,
    baseline_center: float | None = None,
) -> pd.DataFrame:
    """Assign labels using separate start and end thresholds."""

    if "dW_smooth_kg_s" not in df:
        raise KeyError("Input DataFrame must contain 'dW_smooth_kg_s'.")
    if hysteresis_ratio <= 0 or hysteresis_ratio > 1:
        raise ValueError("hysteresis_ratio must be in (0, 1].")

    df_out = df.copy()
    d_w = df_out["dW_smooth_kg_s"].fillna(0.0).astype(float)
    m0 = float(d_w.median()) if baseline_center is None else float(baseline_center)

    irrigation_end = m0 + hysteresis_ratio * (float(irrigation_threshold) - m0)
    drainage_end = m0 + hysteresis_ratio * (float(drainage_threshold) - m0)

    state = "baseline"
    labels: list[str] = []
    for value in d_w.to_numpy():
        if state == "baseline":
            if value >= irrigation_threshold:
                state = "irrigation"
            elif value <= drainage_threshold:
                state = "drainage"
        elif state == "irrigation":
            if value <= irrigation_end:
                state = "drainage" if value <= drainage_threshold else "baseline"
        else:
            if value >= drainage_end:
                state = "irrigation" if value >= irrigation_threshold else "baseline"
        labels.append(state)

    df_out["label"] = pd.Series(labels, index=df_out.index, dtype="object")
    return df_out


def group_events(
    df: pd.DataFrame,
    min_event_duration_sec: int = 2,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Group consecutive irrigation or drainage labels into event summaries."""

    if "label" not in df:
        raise KeyError("DataFrame must contain 'label' column before grouping.")

    weight_col = "weight_smooth_kg" if "weight_smooth_kg" in df else "weight_kg"
    if weight_col not in df:
        raise KeyError(
            "DataFrame must contain either 'weight_smooth_kg' or 'weight_kg'."
        )

    labels = df["label"].fillna("baseline")
    df_out = df.copy()
    event_ids = pd.Series(pd.NA, index=df_out.index, dtype="Int64")
    events: list[dict[str, Any]] = []

    current_type: str | None = None
    start_idx: int | None = None
    event_counter = 0
    timestamps = list(df_out.index)
    weight_series = df_out[weight_col].astype(float)

    def close_event(end_idx: int) -> None:
        nonlocal current_type, start_idx, event_counter
        if start_idx is None or current_type is None:
            return

        duration = end_idx - start_idx + 1
        if duration < min_event_duration_sec:
            current_type = None
            start_idx = None
            return

        idx_slice = slice(start_idx, end_idx + 1)
        event_counter += 1
        event_ids.iloc[idx_slice] = event_counter
        ts_start = timestamps[start_idx]
        ts_end = timestamps[end_idx]
        weight_before = (
            weight_series.iloc[start_idx - 1]
            if start_idx > 0
            else weight_series.iloc[start_idx]
        )
        mass_change = float(weight_series.iloc[end_idx] - weight_before)
        events.append(
            {
                "event_id": event_counter,
                "event_type": current_type,
                "start_time": ts_start,
                "end_time": ts_end,
                "duration_sec": duration,
                "mass_change_kg": mass_change,
            }
        )
        current_type = None
        start_idx = None

    for idx, label in enumerate(labels):
        normalized = label if label in ("irrigation", "drainage") else "baseline"
        if normalized == "baseline":
            if current_type is not None:
                close_event(idx - 1)
            continue

        if current_type is None:
            current_type = normalized
            start_idx = idx
        elif normalized != current_type:
            close_event(idx - 1)
            current_type = normalized
            start_idx = idx

    if current_type is not None and start_idx is not None:
        close_event(len(labels) - 1)

    df_out["event_id"] = event_ids
    events_df = pd.DataFrame(events)
    if events_df.empty:
        events_df = pd.DataFrame(
            columns=[
                "event_id",
                "event_type",
                "start_time",
                "end_time",
                "duration_sec",
                "mass_change_kg",
            ]
        )
    else:
        events_df = events_df.sort_values("start_time").reset_index(drop=True)

    return df_out, events_df


def merge_close_events(
    events_df: pd.DataFrame,
    gap_threshold_sec: int = 30,
) -> pd.DataFrame:
    """Merge consecutive irrigation events separated by short gaps."""

    if events_df.empty:
        return events_df

    events_sorted = events_df.sort_values("start_time").reset_index(drop=True)
    merged: list[dict[str, Any]] = []
    current = events_sorted.iloc[0].to_dict()

    def flush_current() -> None:
        if current:
            merged.append(current.copy())

    for _, row in events_sorted.iloc[1:].iterrows():
        if current["event_type"] == "irrigation" and row["event_type"] == "irrigation":
            gap = (row["start_time"] - current["end_time"]).total_seconds()
            if gap <= gap_threshold_sec:
                current["end_time"] = max(current["end_time"], row["end_time"])
                current["mass_change_kg"] += row["mass_change_kg"]
                current["duration_sec"] = (
                    int(
                        (current["end_time"] - current["start_time"]).total_seconds()
                    )
                    + 1
                )
                continue
        flush_current()
        current = row.to_dict()

    flush_current()

    merged_df = pd.DataFrame(merged).reset_index(drop=True)
    merged_df["event_id"] = range(1, len(merged_df) + 1)
    return merged_df


def merge_close_events_with_df(
    df: pd.DataFrame,
    events_df: pd.DataFrame,
    gap_threshold_sec: int = 30,
    event_type: str = "irrigation",
    weight_col: str | None = None,
) -> tuple[pd.DataFrame, dict[int, int]]:
    """Merge close events and recompute their mass change from the weight series."""

    if events_df.empty:
        return events_df, {}
    if gap_threshold_sec < 0:
        raise ValueError("gap_threshold_sec must be >= 0.")

    required_cols = {"event_id", "event_type", "start_time", "end_time"}
    missing = required_cols - set(events_df.columns)
    if missing:
        raise KeyError(f"events_df missing required columns: {missing}")

    if weight_col is None:
        weight_col = "weight_smooth_kg" if "weight_smooth_kg" in df.columns else "weight_kg"
    if weight_col not in df.columns:
        raise KeyError(f"df must contain '{weight_col}' to recompute mass_change_kg.")

    weight_series = df[weight_col].astype(float).ffill()
    index = weight_series.index

    def position(ts: Any) -> int:
        loc = index.get_loc(ts)
        if isinstance(loc, slice):
            return int(loc.start)
        if isinstance(loc, (list, tuple, np.ndarray)):
            return int(loc[0])
        return int(loc)

    def mass_change(start_time: Any, end_time: Any) -> float:
        start_pos = position(start_time)
        end_pos = position(end_time)
        before = (
            weight_series.iloc[start_pos - 1]
            if start_pos > 0
            else weight_series.iloc[start_pos]
        )
        return float(weight_series.iloc[end_pos] - before)

    events_sorted = events_df.sort_values("start_time").reset_index(drop=True)

    merged_groups: list[dict[str, Any]] = []
    current = events_sorted.iloc[0].to_dict()
    current_old_ids: list[int] = [int(current["event_id"])]

    def flush() -> None:
        merged_groups.append(
            {
                "event_type": current["event_type"],
                "start_time": current["start_time"],
                "end_time": current["end_time"],
                "source_event_ids": current_old_ids.copy(),
            }
        )

    for _, row in events_sorted.iloc[1:].iterrows():
        row_dict = row.to_dict()
        can_merge = current["event_type"] == event_type and row_dict["event_type"] == event_type
        if can_merge:
            gap = (row_dict["start_time"] - current["end_time"]).total_seconds()
            if gap <= gap_threshold_sec:
                current["end_time"] = max(current["end_time"], row_dict["end_time"])
                current_old_ids.append(int(row_dict["event_id"]))
                continue

        flush()
        current = row_dict
        current_old_ids = [int(current["event_id"])]

    flush()

    merged_rows: list[dict[str, Any]] = []
    id_map: dict[int, int] = {}
    for new_id, group in enumerate(merged_groups, start=1):
        start_time = group["start_time"]
        end_time = group["end_time"]
        merged_rows.append(
            {
                "event_id": new_id,
                "event_type": group["event_type"],
                "start_time": start_time,
                "end_time": end_time,
                "duration_sec": int((end_time - start_time).total_seconds()) + 1,
                "mass_change_kg": mass_change(start_time, end_time),
                "source_event_ids": group["source_event_ids"],
            }
        )
        for old_id in group["source_event_ids"]:
            id_map[int(old_id)] = int(new_id)

    merged_df = pd.DataFrame(merged_rows)
    return merged_df, id_map
