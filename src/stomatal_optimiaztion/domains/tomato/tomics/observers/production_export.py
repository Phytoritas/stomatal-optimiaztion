from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.observers.contracts import (
    RADIATION_COLUMN_USED,
    RADIATION_PRIMARY_SOURCE,
    RADIATION_THRESHOLDS_W_M2,
)
from stomatal_optimiaztion.domains.tomato.tomics.observers.parquet_streaming import (
    iter_projected_parquet_batches,
    parquet_metadata_summary,
    projected_columns,
)
from stomatal_optimiaztion.domains.tomato.tomics.observers.radiation_windows import (
    add_radiation_phase_columns,
)


@dataclass
class ChunkCarryState:
    previous_by_group: dict[tuple[Any, ...], tuple[pd.Timestamp, float]] = field(default_factory=dict)
    sortedness_violations: list[str] = field(default_factory=list)


def _present(columns: Iterable[str], frame: pd.DataFrame) -> list[str]:
    return [column for column in columns if column in frame.columns]


def _combine_mean(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    return numerator / denominator.replace(0, np.nan)


def _finalize_radiation_base(partials: list[pd.DataFrame]) -> pd.DataFrame:
    if not partials:
        return pd.DataFrame()
    combined = pd.concat(partials, ignore_index=True)
    group_cols = [column for column in ("interval_start", "loadcell_id", "treatment") if column in combined.columns]
    aggregations: dict[str, tuple[str, str]] = {
        "radiation_sum": ("radiation_sum", "sum"),
        "radiation_count": ("radiation_count", "sum"),
        "radiation_wm2_max": ("radiation_wm2_max", "max"),
        "radiation_wm2_min": ("radiation_wm2_min", "min"),
        "sample_count": ("sample_count", "sum"),
        "source_row_count": ("source_row_count", "sum"),
    }
    for env_col in ("env_vpd_kpa", "env_air_temperature_c", "env_co2_ppm"):
        sum_col = f"{env_col}_sum"
        count_col = f"{env_col}_count"
        if sum_col in combined.columns:
            aggregations[sum_col] = (sum_col, "sum")
            aggregations[count_col] = (count_col, "sum")
    out = combined.groupby(group_cols, dropna=False).agg(**aggregations).reset_index()
    out["radiation_wm2_mean"] = _combine_mean(out["radiation_sum"], out["radiation_count"])
    for env_col in ("env_vpd_kpa", "env_air_temperature_c", "env_co2_ppm"):
        sum_col = f"{env_col}_sum"
        count_col = f"{env_col}_count"
        if sum_col in out.columns:
            out[f"{env_col}_mean"] = _combine_mean(out[sum_col], out[count_col])
    out["interval_start"] = pd.to_datetime(out["interval_start"], errors="coerce")
    out["interval_end"] = out["interval_start"] + pd.to_timedelta(10, unit="min")
    out["date"] = out["interval_start"].dt.strftime("%Y-%m-%d")
    out["interval_seconds"] = 600.0
    out["radiation_source_used"] = RADIATION_PRIMARY_SOURCE
    out["radiation_column_used"] = RADIATION_COLUMN_USED
    keep = [
        column
        for column in (
            "interval_start",
            "interval_end",
            "date",
            "loadcell_id",
            "treatment",
            "radiation_wm2_mean",
            "radiation_wm2_max",
            "radiation_wm2_min",
            "sample_count",
            "source_row_count",
            "env_vpd_kpa_mean",
            "env_air_temperature_c_mean",
            "env_co2_ppm_mean",
            "interval_seconds",
            "radiation_source_used",
            "radiation_column_used",
        )
        if column in out.columns
    ]
    return out[keep].sort_values([column for column in ("loadcell_id", "interval_start") if column in keep]).reset_index(
        drop=True
    )


def expand_radiation_thresholds(
    radiation_base: pd.DataFrame,
    *,
    thresholds_w_m2: Iterable[int | float] = RADIATION_THRESHOLDS_W_M2,
) -> pd.DataFrame:
    rows: list[pd.DataFrame] = []
    for threshold in thresholds_w_m2:
        threshold_frame = radiation_base.copy()
        threshold_frame["threshold_w_m2"] = float(threshold)
        threshold_frame["radiation_phase"] = np.where(
            threshold_frame["radiation_wm2_max"].fillna(0.0) > float(threshold),
            "day",
            "night",
        )
        rows.append(threshold_frame)
    return pd.concat(rows, ignore_index=True) if rows else radiation_base.iloc[0:0].copy()


def _radiation_partial(chunk: pd.DataFrame) -> pd.DataFrame:
    data = chunk.copy()
    data["timestamp"] = pd.to_datetime(data["timestamp"], errors="coerce")
    data = data.dropna(subset=["timestamp"])
    data[RADIATION_COLUMN_USED] = pd.to_numeric(data[RADIATION_COLUMN_USED], errors="coerce")
    data["interval_start"] = data["timestamp"].dt.floor("10min")
    group_cols = [column for column in ("interval_start", "loadcell_id", "treatment") if column in data.columns]
    data["_source_row"] = 1
    aggregations: dict[str, tuple[str, str]] = {
        "radiation_sum": (RADIATION_COLUMN_USED, "sum"),
        "radiation_count": (RADIATION_COLUMN_USED, "count"),
        "radiation_wm2_max": (RADIATION_COLUMN_USED, "max"),
        "radiation_wm2_min": (RADIATION_COLUMN_USED, "min"),
        "sample_count": (RADIATION_COLUMN_USED, "count"),
        "source_row_count": ("_source_row", "sum"),
    }
    for env_col in ("env_vpd_kpa", "env_air_temperature_c", "env_co2_ppm"):
        if env_col in data.columns:
            data[env_col] = pd.to_numeric(data[env_col], errors="coerce")
            data[f"{env_col}_present"] = data[env_col].notna().astype("int64")
            aggregations[f"{env_col}_sum"] = (env_col, "sum")
            aggregations[f"{env_col}_count"] = (f"{env_col}_present", "sum")
    return data.groupby(group_cols, dropna=False).agg(**aggregations).reset_index()


def _sorted_group_key(value: tuple[Any, ...] | Any) -> tuple[Any, ...]:
    if isinstance(value, tuple):
        return value
    return (value,)


def _water_partial(
    chunk: pd.DataFrame,
    *,
    carry_state: ChunkCarryState,
    event_threshold_g: float,
) -> pd.DataFrame:
    group_cols = _present(("loadcell_id", "treatment", "sample_id"), chunk)
    output_group_cols = _present(("loadcell_id", "treatment"), chunk)
    required = ["timestamp", "loadcell_weight_kg", *group_cols]
    data = chunk[required].copy()
    data["timestamp"] = pd.to_datetime(data["timestamp"], errors="coerce")
    data["loadcell_weight_kg"] = pd.to_numeric(data["loadcell_weight_kg"], errors="coerce")
    data = data.dropna(subset=["timestamp", "loadcell_weight_kg"]).sort_values([*group_cols, "timestamp"])
    if data.empty:
        return pd.DataFrame(columns=[*output_group_cols, "interval_start", "loss_g_10min_unscaled", "event_flag"])

    carry_rows: list[dict[str, Any]] = []
    for key, group in data.groupby(group_cols, dropna=False):
        key_tuple = _sorted_group_key(key)
        if key_tuple not in carry_state.previous_by_group:
            continue
        previous_timestamp, previous_weight = carry_state.previous_by_group[key_tuple]
        first_timestamp = pd.Timestamp(group["timestamp"].iloc[0])
        if first_timestamp < previous_timestamp:
            carry_state.sortedness_violations.append(
                f"group={key_tuple} first={first_timestamp.isoformat()} previous={previous_timestamp.isoformat()}"
            )
            continue
        carry_row = {column: value for column, value in zip(group_cols, key_tuple, strict=True)}
        carry_row.update(
            {
                "timestamp": previous_timestamp,
                "loadcell_weight_kg": previous_weight,
                "_carry_row": True,
            }
        )
        carry_rows.append(carry_row)

    data["_carry_row"] = False
    if carry_rows:
        data = pd.concat([pd.DataFrame(carry_rows), data], ignore_index=True, sort=False)
        data["_carry_sort"] = np.where(data["_carry_row"].astype(bool), 0, 1)
        data = data.sort_values([*group_cols, "timestamp", "_carry_sort"])
    else:
        data["_carry_sort"] = 1

    data["weight_delta_g"] = data.groupby(group_cols, dropna=False)["loadcell_weight_kg"].diff() * 1000.0
    work = data[~data["_carry_row"].astype(bool)].copy()
    work["positive_loss_g"] = (-work["weight_delta_g"]).clip(lower=0.0)
    work["event_flag"] = work["weight_delta_g"].abs().gt(event_threshold_g)
    work["interval_start"] = work["timestamp"].dt.floor("10min")

    for key, group in work.groupby(group_cols, dropna=False):
        key_tuple = _sorted_group_key(key)
        last = group.dropna(subset=["timestamp", "loadcell_weight_kg"]).iloc[-1]
        carry_state.previous_by_group[key_tuple] = (
            pd.Timestamp(last["timestamp"]),
            float(last["loadcell_weight_kg"]),
        )

    group_keys = [*output_group_cols, "interval_start"]
    return (
        work.groupby(group_keys, dropna=False)
        .agg(
            loss_g_10min_unscaled=("positive_loss_g", "sum"),
            event_flag=("event_flag", "max"),
            source_row_count=("positive_loss_g", "count"),
        )
        .reset_index()
    )


def _finalize_water_intervals(water_partials: list[pd.DataFrame], radiation_intervals: pd.DataFrame) -> pd.DataFrame:
    if not water_partials:
        out = pd.DataFrame(columns=["interval_start", "loss_g_10min_unscaled", "event_flag"])
    else:
        combined = pd.concat(water_partials, ignore_index=True)
        group_cols = [column for column in ("loadcell_id", "treatment", "interval_start") if column in combined.columns]
        out = (
            combined.groupby(group_cols, dropna=False)
            .agg(
                loss_g_10min_unscaled=("loss_g_10min_unscaled", "sum"),
                event_flag=("event_flag", "max"),
                source_row_count=("source_row_count", "sum"),
            )
            .reset_index()
        )
    out["interval_start"] = pd.to_datetime(out["interval_start"], errors="coerce")
    out["interval_end"] = out["interval_start"] + pd.to_timedelta(10, unit="min")
    out["date"] = out["interval_start"].dt.strftime("%Y-%m-%d")
    out["event_type"] = np.where(out["event_flag"].fillna(False).astype(bool), "irrigation_or_drainage", "quiet")
    out["warnings"] = ""
    out["daily_bridge_scale_factor"] = np.nan
    out["loss_g_10min_event_bridged_calibrated"] = np.nan
    out["bridge_status"] = "uncalibrated_no_daily_total"
    out["water_flux_source_used"] = "loadcell_weight_kg_derivative_chunked"

    phase_wide = add_radiation_phase_columns(radiation_intervals)
    merge_cols = [
        column
        for column in ("interval_start", "loadcell_id", "treatment")
        if column in out.columns and column in phase_wide.columns
    ]
    if merge_cols:
        out = out.merge(phase_wide, on=merge_cols, how="left", suffixes=("", "_radiation"))
        for column in ("date_radiation", "interval_end_radiation"):
            if column in out.columns:
                out = out.drop(columns=[column])
    return out.sort_values([column for column in ("date", "loadcell_id", "interval_start") if column in out.columns]).reset_index(
        drop=True
    )


def aggregate_dataset1_streaming(
    *,
    path: str | Path,
    columns: tuple[str, ...],
    batch_size: int,
    max_rows: int | None,
    event_threshold_g: float = 50.0,
    thresholds_w_m2: Iterable[int | float] = RADIATION_THRESHOLDS_W_M2,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any], pd.DataFrame]:
    metadata = parquet_metadata_summary(path)
    available = projected_columns(path, columns)
    radiation_partials: list[pd.DataFrame] = []
    water_partials: list[pd.DataFrame] = []
    manifest_rows: list[dict[str, Any]] = []
    carry_state = ChunkCarryState()
    rows_processed = 0
    batches_processed = 0
    for batch_idx, chunk in enumerate(
        iter_projected_parquet_batches(path, columns, batch_size=batch_size, max_rows=max_rows),
        start=1,
    ):
        batches_processed += 1
        rows_processed += int(chunk.shape[0])
        radiation_partials.append(_radiation_partial(chunk))
        water_partials.append(
            _water_partial(
                chunk,
                carry_state=carry_state,
                event_threshold_g=event_threshold_g,
            )
        )
        manifest_rows.append(
            {
                "dataset_role": "dataset1",
                "batch_index": batch_idx,
                "rows_processed": int(chunk.shape[0]),
                "cumulative_rows_processed": rows_processed,
                "aggregation_status": "ok",
            }
        )

    if carry_state.sortedness_violations:
        sample = "; ".join(carry_state.sortedness_violations[:5])
        raise RuntimeError(f"Dataset1 timestamp sortedness precondition failed for water flux carryover: {sample}")

    radiation_base = _finalize_radiation_base(radiation_partials)
    radiation_intervals = expand_radiation_thresholds(radiation_base, thresholds_w_m2=thresholds_w_m2)
    water_intervals = _finalize_water_intervals(water_partials, radiation_intervals)
    total_rows = int(metadata["total_rows"])
    load_meta = {
        "path": str(path),
        "projected_columns": available,
        "total_rows": total_rows,
        "rows_loaded": rows_processed,
        "rows_processed": rows_processed,
        "rows_processed_fraction": rows_processed / total_rows if total_rows else 1.0,
        "row_limit_applied": max_rows is not None and rows_processed < total_rows,
        "max_rows": max_rows,
        "batches_processed": batches_processed,
        "chunk_aggregation_complete": rows_processed == total_rows,
        "chunk_aggregation_used": True,
        "full_in_memory_large_dataset_used": False,
        "water_flux_chunk_carryover_used": True,
        "water_flux_chunk_carryover_group_keys": ["loadcell_id", "treatment", "sample_id"],
    }
    return radiation_intervals, water_intervals, load_meta, pd.DataFrame(manifest_rows)


def aggregate_dataset2_daily_streaming(
    *,
    path: str | Path,
    columns: tuple[str, ...],
    batch_size: int,
    max_rows: int | None,
) -> tuple[pd.DataFrame, dict[str, Any], pd.DataFrame]:
    metadata = parquet_metadata_summary(path)
    available = projected_columns(path, columns)
    partials: list[pd.DataFrame] = []
    manifest_rows: list[dict[str, Any]] = []
    rows_processed = 0
    batches_processed = 0
    for batch_idx, chunk in enumerate(
        iter_projected_parquet_batches(path, columns, batch_size=batch_size, max_rows=max_rows),
        start=1,
    ):
        batches_processed += 1
        rows_processed += int(chunk.shape[0])
        data = chunk.copy()
        if "date" not in data.columns and "timestamp" in data.columns:
            data["date"] = pd.to_datetime(data["timestamp"], errors="coerce").dt.strftime("%Y-%m-%d")
        data["date"] = data["date"].astype(str)
        group_cols = [column for column in ("date", "loadcell_id", "treatment") if column in data.columns]
        data["_source_row"] = 1
        aggregations: dict[str, tuple[str, str]] = {"source_row_count": ("_source_row", "sum")}
        for column in ("moisture_percent", "ec_ds", "tensiometer_hp"):
            if column in data.columns:
                data[column] = pd.to_numeric(data[column], errors="coerce")
                data[f"{column}_present"] = data[column].notna().astype("int64")
                aggregations[f"{column}_sum"] = (column, "sum")
                aggregations[f"{column}_count"] = (f"{column}_present", "sum")
        partials.append(data.groupby(group_cols, dropna=False).agg(**aggregations).reset_index())
        manifest_rows.append(
            {
                "dataset_role": "dataset2",
                "batch_index": batch_idx,
                "rows_processed": int(chunk.shape[0]),
                "cumulative_rows_processed": rows_processed,
                "aggregation_status": "ok",
            }
        )

    combined = pd.concat(partials, ignore_index=True) if partials else pd.DataFrame()
    if combined.empty:
        daily = combined
    else:
        group_cols = [column for column in ("date", "loadcell_id", "treatment") if column in combined.columns]
        aggregations = {"source_row_count": ("source_row_count", "sum")}
        for column in ("moisture_percent", "ec_ds", "tensiometer_hp"):
            sum_col = f"{column}_sum"
            count_col = f"{column}_count"
            if sum_col in combined.columns:
                aggregations[sum_col] = (sum_col, "sum")
                aggregations[count_col] = (count_col, "sum")
        daily = combined.groupby(group_cols, dropna=False).agg(**aggregations).reset_index()
        if "moisture_percent_sum" in daily.columns:
            daily["moisture_percent_mean"] = _combine_mean(daily["moisture_percent_sum"], daily["moisture_percent_count"])
        if "ec_ds_sum" in daily.columns:
            daily["ec_ds_mean"] = _combine_mean(daily["ec_ds_sum"], daily["ec_ds_count"])
        if "tensiometer_hp_sum" in daily.columns:
            daily["tensiometer_hp_mean"] = _combine_mean(daily["tensiometer_hp_sum"], daily["tensiometer_hp_count"])
            daily["tensiometer_available"] = daily["tensiometer_hp_count"].gt(0)
            daily["tensiometer_coverage_fraction"] = daily["tensiometer_hp_count"] / daily["source_row_count"].replace(0, np.nan)
    total_rows = int(metadata["total_rows"])
    load_meta = {
        "path": str(path),
        "projected_columns": available,
        "total_rows": total_rows,
        "rows_loaded": rows_processed,
        "rows_processed": rows_processed,
        "rows_processed_fraction": rows_processed / total_rows if total_rows else 1.0,
        "row_limit_applied": max_rows is not None and rows_processed < total_rows,
        "max_rows": max_rows,
        "batches_processed": batches_processed,
        "chunk_aggregation_complete": rows_processed == total_rows,
        "chunk_aggregation_used": True,
        "full_in_memory_large_dataset_used": False,
    }
    return daily, load_meta, pd.DataFrame(manifest_rows)
