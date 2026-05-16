from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.alloc.core import ensure_dir, load_config, write_json
from stomatal_optimiaztion.domains.tomato.tomics.observers.contracts import (
    DATASET1_COLUMN_CANDIDATES,
    DATASET2_COLUMN_CANDIDATES,
    DATASET3_COLUMN_CANDIDATES,
    MAIN_RADIATION_THRESHOLD_W_M2,
    OUTPUT_FILENAMES,
    RADIATION_THRESHOLDS_W_M2,
    RAW_INPUT_FILENAMES,
    base_metadata,
    resolve_repo_path,
)
from stomatal_optimiaztion.domains.tomato.tomics.observers.dataset3_bridge import (
    build_dataset3_growth_phenology_bridge,
)
from stomatal_optimiaztion.domains.tomato.tomics.observers.event_bridge_calibration import (
    CALIBRATION_TOTAL_COL,
    calibration_match_metadata,
    load_legacy_event_bridge_daily_totals,
)
from stomatal_optimiaztion.domains.tomato.tomics.observers.feature_frame import build_observer_feature_frame
from stomatal_optimiaztion.domains.tomato.tomics.observers.fruit_diameter_windows import (
    build_fixed_clock_compat_windows,
    build_fruit_leaf_loadcell_bridge,
    build_fruit_leaf_radiation_windows,
)
from stomatal_optimiaztion.domains.tomato.tomics.observers.legacy_v1_3_bridge import (
    audit_legacy_v1_3_bridge,
    legacy_v1_3_config,
)
from stomatal_optimiaztion.domains.tomato.tomics.observers.metadata_contract import (
    metadata_contract_audit,
    normalize_metadata,
    write_normalized_metadata,
    write_stage_metadata_snapshot,
)
from stomatal_optimiaztion.domains.tomato.tomics.observers.parquet_streaming import (
    assert_no_large_full_load_without_limit,
    iter_projected_parquet_batches,
    parquet_metadata_summary,
    projected_columns,
    validate_production_row_cap_policy,
)
from stomatal_optimiaztion.domains.tomato.tomics.observers.production_export import (
    aggregate_dataset1_rootzone_reference_streaming,
    aggregate_dataset1_streaming,
    aggregate_dataset2_daily_streaming,
)
from stomatal_optimiaztion.domains.tomato.tomics.observers.qc import apply_fruit_leaf_qc
from stomatal_optimiaztion.domains.tomato.tomics.observers.radiation_source import (
    build_radiation_source_verification,
)
from stomatal_optimiaztion.domains.tomato.tomics.observers.radiation_windows import (
    build_photoperiod_table,
    build_radiation_daily_summary,
    build_radiation_intervals,
)
from stomatal_optimiaztion.domains.tomato.tomics.observers.rootzone_indices import build_rootzone_indices
from stomatal_optimiaztion.domains.tomato.tomics.observers.sensor_mapping import (
    fruit_diameter_policy_metadata,
    load_sensor_mapping,
)
from stomatal_optimiaztion.domains.tomato.tomics.observers.toa5_parser import read_toa5_dat
from stomatal_optimiaztion.domains.tomato.tomics.observers.water_flux_event_bridge import (
    build_10min_event_bridged_water_loss,
    build_daily_wide_et_summary,
    calibrate_to_daily_event_bridged_total,
    summarize_radiation_daynight_et,
)
from stomatal_optimiaztion.domains.tomato.tomics.observers.yield_bridge import load_legacy_yield_bridge


def _repo_root_from_config(config_path: Path, config: dict[str, Any]) -> Path:
    repo_root_value = config.get("paths", {}).get("repo_root", "../..")
    repo_root = Path(repo_root_value)
    if repo_root.is_absolute():
        return repo_root.resolve()
    return (config_path.parent / repo_root).resolve()


def _tomics_haf_config(config: dict[str, Any]) -> dict[str, Any]:
    return dict(config.get("tomics_haf", {}))


def _write_csv(output_root: Path, key: str, frame: pd.DataFrame) -> Path:
    ensure_dir(output_root)
    path = output_root / OUTPUT_FILENAMES[key]
    frame.to_csv(path, index=False, encoding="utf-8")
    return path


def _write_text(output_root: Path, key: str, text: str) -> Path:
    ensure_dir(output_root)
    path = output_root / OUTPUT_FILENAMES[key]
    path.write_text(text, encoding="utf-8")
    return path


def _load_goal1_metadata(output_root: Path) -> dict[str, Any]:
    metadata_path = output_root / OUTPUT_FILENAMES["metadata"]
    if not metadata_path.exists():
        return {}
    with metadata_path.open("r", encoding="utf-8") as handle:
        loaded = json.load(handle)
    return loaded if isinstance(loaded, dict) else {}


def _load_audit_rows(output_root: Path) -> dict[str, dict[str, Any]]:
    path = output_root / "input_schema_audit.csv"
    if not path.exists():
        return {}
    rows = pd.read_csv(path).to_dict(orient="records")
    return {str(row.get("file_role")): row for row in rows}


def _read_projected_parquet(
    path: Path,
    columns: tuple[str, ...],
    *,
    max_rows: int | None,
    batch_size: int,
    max_full_rows_without_limit: int,
    mode: str = "smoke",
    fail_on_full_in_memory_large_dataset: bool = True,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    parquet_meta = parquet_metadata_summary(path)
    available = projected_columns(path, columns)
    total_rows = int(parquet_meta["total_rows"])
    assert_no_large_full_load_without_limit(
        total_rows=total_rows,
        max_rows=max_rows,
        mode=mode,
        max_full_rows_without_limit=max_full_rows_without_limit,
        fail_on_full_in_memory_large_dataset=fail_on_full_in_memory_large_dataset,
    )

    frames: list[pd.DataFrame] = []
    rows_loaded = 0
    batches_processed = 0
    for chunk in iter_projected_parquet_batches(path, columns, batch_size=batch_size, max_rows=max_rows):
        batches_processed += 1
        frames.append(chunk)
        rows_loaded += int(chunk.shape[0])
    frame = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=available)
    metadata = {
        "path": str(path),
        "projected_columns": available,
        "total_rows": total_rows,
        "rows_loaded": rows_loaded,
        "rows_processed": rows_loaded,
        "rows_processed_fraction": rows_loaded / total_rows if total_rows else 1.0,
        "row_limit_applied": max_rows is not None and rows_loaded < total_rows,
        "max_rows": max_rows,
        "batches_processed": batches_processed,
        "chunk_aggregation_complete": rows_loaded == total_rows,
        "chunk_aggregation_used": False,
        "full_in_memory_large_dataset_used": bool(total_rows > max_full_rows_without_limit),
    }
    return frame, metadata


def _read_projected_sample(path: Path, columns: tuple[str, ...], *, batch_size: int = 10_000) -> pd.DataFrame:
    for chunk in iter_projected_parquet_batches(path, columns, batch_size=batch_size, max_rows=batch_size):
        return chunk
    return pd.DataFrame(columns=projected_columns(path, columns))


def _radiation_column_for_pipeline(radiation_decision: dict[str, Any]) -> str:
    source = str(radiation_decision.get("radiation_daynight_primary_source") or "")
    column = str(radiation_decision.get("radiation_column_used") or "")
    if not bool(radiation_decision.get("selected_for_daynight_10min")):
        raise RuntimeError(
            "No radiation source is selected for 10-minute day/night intervals; "
            f"decision={radiation_decision}"
        )
    if source != "dataset1":
        raise RuntimeError(
            "The HAF 2025-2C observer pipeline currently requires Dataset1 radiation for canonical "
            f"10-minute day/night intervals; selected source={source!r} column={column!r}."
        )
    if not column:
        raise RuntimeError("Radiation decision selected Dataset1 but did not provide radiation_column_used.")
    return column


def _normalize_join_keys(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    if "date" in out.columns:
        out["date"] = pd.to_datetime(out["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    if "loadcell_id" in out.columns:
        out["loadcell_id"] = pd.to_numeric(out["loadcell_id"], errors="coerce").astype("Int64")
    if "treatment" in out.columns:
        out["treatment"] = out["treatment"].astype(str)
    return out


def _merge_legacy_yield_bridge(feature_frame: pd.DataFrame, yield_bridge: pd.DataFrame) -> pd.DataFrame:
    if yield_bridge.empty or feature_frame.empty:
        return feature_frame
    left = _normalize_join_keys(feature_frame)
    right = _normalize_join_keys(yield_bridge)
    keys = [column for column in ("date", "loadcell_id", "treatment") if column in left.columns and column in right.columns]
    if not keys:
        return feature_frame
    bridge_columns = keys + [column for column in right.columns if column not in keys]
    merged = left.merge(right[bridge_columns], on=keys, how="left", suffixes=("", "_legacy_yield"))
    for column in (
        "fresh_yield_source",
        "dry_yield_source",
        "observed_fruit_FW_g_loadcell",
        "observed_fruit_DW_g_loadcell_dmc_0p056",
        "observed_fruit_DW_g_m2_floor_dmc_0p056",
        "canonical_fruit_DMC_fraction",
        "fruit_DMC_fraction",
        "default_fruit_dry_matter_content",
        "DMC_fixed_for_2025_2C",
        "DMC_sensitivity_enabled",
        "dry_yield_is_dmc_estimated",
        "direct_dry_yield_measured",
        "legacy_yield_bridge_provenance",
        "legacy_sensitivity_columns_present",
    ):
        legacy_column = f"{column}_legacy_yield"
        if legacy_column in merged.columns:
            if column in merged.columns:
                merged[column] = merged[legacy_column].combine_first(merged[column])
            else:
                merged[column] = merged[legacy_column]
    fresh_cols = [
        column
        for column in (
            "measured_or_legacy_fresh_yield_g",
            "loadcell_daily_yield_g",
            "loadcell_cumulative_yield_g",
            "individual_cumulative_yield_g",
            "final_fresh_yield_g",
        )
        if column in merged.columns
    ]
    dry_cols = [
        column
        for column in (
            "observed_fruit_DW_g_loadcell_dmc_0p056",
            "observed_fruit_DW_g_m2_floor_dmc_0p056",
        )
        if column in merged.columns
    ]
    fresh_available = merged[fresh_cols].notna().any(axis=1) if fresh_cols else pd.Series(False, index=merged.index)
    dry_available = merged[dry_cols].notna().any(axis=1) if dry_cols else pd.Series(False, index=merged.index)
    direct_dry = (
        merged["direct_dry_yield_measured"].fillna(False).astype(bool)
        if "direct_dry_yield_measured" in merged.columns
        else pd.Series(False, index=merged.index)
    )
    merged["harvest_yield_available"] = fresh_available | dry_available
    merged["fresh_yield_available"] = fresh_available
    merged["dry_yield_available"] = dry_available
    merged["direct_dry_yield_measured"] = direct_dry & dry_available
    merged["dry_yield_is_dmc_estimated"] = dry_available & ~merged["direct_dry_yield_measured"]
    merged["DMC_conversion_performed"] = dry_available
    return merged


def _rootzone_reference_audit(rootzone: pd.DataFrame) -> pd.DataFrame:
    if rootzone.empty:
        return pd.DataFrame(
            [
                {
                    "check_name": "RZI_main_available",
                    "status": "fail",
                    "value": False,
                    "notes": "No rootzone rows were produced.",
                }
            ]
        )
    available = bool(rootzone.get("RZI_main_available", pd.Series(dtype=bool)).fillna(False).any())
    source_values = (
        ";".join(sorted(rootzone.get("RZI_main_source", pd.Series(dtype=str)).dropna().astype(str).unique()))
        if "RZI_main_source" in rootzone.columns
        else ""
    )
    control_source = (
        ";".join(sorted(rootzone.get("RZI_control_reference_source", pd.Series(dtype=str)).dropna().astype(str).unique()))
        if "RZI_control_reference_source" in rootzone.columns
        else ""
    )
    return pd.DataFrame(
        [
            {
                "check_name": "RZI_main_available",
                "status": "pass" if available else "fail",
                "value": available,
                "notes": source_values,
            },
            {
                "check_name": "RZI_control_reference_source",
                "status": "pass" if control_source else "fail",
                "value": control_source,
                "notes": "Dataset1 moisture should be preferred when available.",
            },
        ]
    )


def _dataset3_size_guard(
    dataset3_load_meta: dict[str, Any],
    *,
    max_full_rows_without_limit: int,
    mode: str,
) -> dict[str, Any]:
    total_rows = int(dataset3_load_meta.get("total_rows") or 0)
    rows_processed = int(dataset3_load_meta.get("rows_processed") or 0)
    guard_passed = bool(total_rows <= max_full_rows_without_limit or dataset3_load_meta.get("row_limit_applied"))
    allowed_reason = (
        "small_dataset3_within_max_full_rows_without_limit"
        if total_rows <= max_full_rows_without_limit
        else "dataset3_row_cap_applied"
        if dataset3_load_meta.get("row_limit_applied")
        else "dataset3_exceeds_max_full_rows_without_limit"
    )
    if mode == "production" and not guard_passed:
        raise RuntimeError(f"Dataset3 size guard failed: total_rows={total_rows}, limit={max_full_rows_without_limit}.")
    return {
        "dataset3_total_rows": total_rows,
        "dataset3_rows_processed": rows_processed,
        "dataset3_full_in_memory_allowed_reason": allowed_reason,
        "dataset3_size_guard_passed": guard_passed,
    }


def _assert_dataset3_size_guard_before_read(
    *,
    path: Path,
    max_rows: int | None,
    max_full_rows_without_limit: int,
    mode: str,
) -> dict[str, Any]:
    parquet_meta = parquet_metadata_summary(path)
    total_rows = int(parquet_meta["total_rows"])
    if mode == "production" and max_rows is None and total_rows > max_full_rows_without_limit:
        raise RuntimeError(
            "Dataset3 size guard failed before full read: "
            f"total_rows={total_rows}, limit={max_full_rows_without_limit}."
        )
    return {"dataset3_total_rows_preflight": total_rows}


def _production_requirement_failures(
    *,
    mode: str,
    pipeline_config: dict[str, Any],
    row_cap_applied: bool,
    chunk_aggregation_used: bool,
    full_in_memory_large_dataset_used: bool,
    dataset1_load_meta: dict[str, Any],
    dataset2_load_meta: dict[str, Any],
) -> list[str]:
    if mode != "production":
        return []
    failures: list[str] = []
    if bool(pipeline_config.get("require_chunk_aggregation")) and not chunk_aggregation_used:
        failures.append("require_chunk_aggregation=true but chunk_aggregation_used=false")
    if bool(pipeline_config.get("require_dataset1_full_processed")) and dataset1_load_meta.get("rows_processed_fraction") != 1.0:
        failures.append("require_dataset1_full_processed=true but dataset1_rows_processed_fraction != 1.0")
    if bool(pipeline_config.get("require_dataset2_full_processed")) and dataset2_load_meta.get("rows_processed_fraction") != 1.0:
        failures.append("require_dataset2_full_processed=true but dataset2_rows_processed_fraction != 1.0")
    if full_in_memory_large_dataset_used:
        failures.append("full_in_memory_large_dataset_used=true")
    if row_cap_applied:
        failures.append("row_cap_applied=true")
    return failures


def _path_for_input(raw_root: Path, role: str, config: dict[str, Any]) -> Path:
    configured = config.get("input_files", {}).get(role, RAW_INPUT_FILENAMES[role])
    return raw_root / configured


def run_tomics_haf_observer_pipeline(config_path: str | Path) -> dict[str, Any]:
    config_path = Path(config_path).resolve()
    config = load_config(config_path)
    repo_root = _repo_root_from_config(config_path, config)
    tomics_haf = _tomics_haf_config(config)
    output_root = resolve_repo_path(repo_root, tomics_haf.get("output_root", "out/tomics/analysis/haf_2025_2c"))
    raw_root = resolve_repo_path(
        repo_root,
        tomics_haf.get("raw_data_root", "artifacts/tomato_integrated_radiation_architecture_v1_3/input_raw"),
    )
    ensure_dir(output_root)
    legacy_config = legacy_v1_3_config(config, repo_root=repo_root)
    legacy_audit = audit_legacy_v1_3_bridge(legacy_config)
    legacy_audit_path = _write_csv(output_root, "legacy_bridge_audit", legacy_audit)
    legacy_audit_json_path = write_json(
        output_root / OUTPUT_FILENAMES["legacy_bridge_audit_json"],
        {"sources": legacy_audit.to_dict(orient="records")},
    )
    legacy_event_totals, event_calibration_audit, event_calibration_metadata = (
        load_legacy_event_bridge_daily_totals(legacy_config)
    )
    event_calibration_audit_path = _write_csv(output_root, "event_bridge_calibration_audit", event_calibration_audit)
    legacy_yield, yield_audit, yield_metadata = load_legacy_yield_bridge(legacy_config)
    yield_audit_path = _write_csv(output_root, "fresh_dry_yield_bridge_audit", yield_audit)

    pipeline_config = dict(config.get("observer_pipeline", {}))
    mode = str(pipeline_config.get("mode", "smoke"))
    if mode not in {"smoke", "production"}:
        raise ValueError(f"observer_pipeline.mode must be 'smoke' or 'production', got {mode!r}.")
    batch_size = int(pipeline_config.get("parquet_batch_size", 250_000))
    max_full_rows_without_limit = int(pipeline_config.get("max_full_rows_without_limit", 2_000_000))
    fail_on_full_in_memory_large_dataset = bool(pipeline_config.get("fail_on_full_in_memory_large_dataset", True))
    require_row_cap_absent_for_production = bool(
        pipeline_config.get("require_row_cap_absent_for_production", True)
    )
    write_intermediate_chunk_manifests = bool(pipeline_config.get("write_intermediate_chunk_manifests", False))
    max_rows = pipeline_config.get("max_rows", {})
    max_rows = max_rows if isinstance(max_rows, dict) else {}
    validate_production_row_cap_policy(
        mode=mode,
        max_rows_by_dataset=max_rows,
        require_row_cap_absent_for_production=require_row_cap_absent_for_production,
    )
    dataset1_max_rows = max_rows.get("dataset1") if isinstance(max_rows, dict) else None
    dataset2_max_rows = max_rows.get("dataset2") if isinstance(max_rows, dict) else None
    dataset3_max_rows = max_rows.get("dataset3") if isinstance(max_rows, dict) else None

    mapping_path = resolve_repo_path(
        repo_root,
        tomics_haf.get("sensor_mapping_path", "configs/sensor_mapping/2025_2c_fruit_leaf_loadcell.yaml"),
    )
    mapping = load_sensor_mapping(mapping_path)

    raw_dat_path = _path_for_input(raw_root, "fruit_leaf_temperature_solar_raw_dat", tomics_haf)
    dataset1_path = _path_for_input(raw_root, "dataset1", tomics_haf)
    dataset2_path = _path_for_input(raw_root, "dataset2", tomics_haf)
    dataset3_path = _path_for_input(raw_root, "dataset3", tomics_haf)

    raw_dat = read_toa5_dat(raw_dat_path, timestamp_col=mapping.get("timestamp_col", "TIMESTAMP"))
    fruit_leaf_qc, sensor_qc_report = apply_fruit_leaf_qc(
        raw_dat,
        timestamp_col=mapping.get("timestamp_col", "TIMESTAMP"),
        fruit_columns=mapping.get("fruit_sensor_map", {}).keys(),
        leaf_columns=mapping.get("leaf_sensor_map", {}).keys(),
    )
    fruit_leaf_qc_path = _write_csv(output_root, "fruit_leaf_timeseries_qc", fruit_leaf_qc)
    sensor_qc_path = _write_csv(output_root, "sensor_qc_report", sensor_qc_report)

    audit_rows = _load_audit_rows(output_root)
    dataset1_sample = _read_projected_sample(dataset1_path, DATASET1_COLUMN_CANDIDATES)
    radiation_rows, radiation_decision = build_radiation_source_verification(
        {"dataset1": dataset1_sample, "fruit_leaf_temperature_solar_raw_dat": raw_dat},
        audit_rows,
    )
    radiation_col = _radiation_column_for_pipeline(radiation_decision)

    chunk_manifest_frames: list[pd.DataFrame] = []
    if mode == "production":
        radiation_intervals, event_intervals, dataset1_load_meta, dataset1_manifest = aggregate_dataset1_streaming(
            path=dataset1_path,
            columns=DATASET1_COLUMN_CANDIDATES,
            batch_size=batch_size,
            max_rows=None,
            thresholds_w_m2=RADIATION_THRESHOLDS_W_M2,
            radiation_col=radiation_col,
        )
        dataset1_rootzone_reference, dataset1_rootzone_meta, dataset1_rootzone_manifest = (
            aggregate_dataset1_rootzone_reference_streaming(
                path=dataset1_path,
                columns=DATASET1_COLUMN_CANDIDATES,
                batch_size=batch_size,
                max_rows=None,
            )
        )
        chunk_manifest_frames.append(dataset1_manifest)
        chunk_manifest_frames.append(dataset1_rootzone_manifest)
    else:
        dataset1, dataset1_load_meta = _read_projected_parquet(
            dataset1_path,
            DATASET1_COLUMN_CANDIDATES,
            max_rows=int(dataset1_max_rows) if dataset1_max_rows is not None else None,
            batch_size=batch_size,
            max_full_rows_without_limit=max_full_rows_without_limit,
            mode=mode,
            fail_on_full_in_memory_large_dataset=fail_on_full_in_memory_large_dataset,
        )
        dataset1["timestamp"] = pd.to_datetime(dataset1["timestamp"], errors="coerce")
        radiation_intervals = build_radiation_intervals(
            dataset1,
            thresholds_w_m2=RADIATION_THRESHOLDS_W_M2,
            timestamp_col="timestamp",
            radiation_col=radiation_col,
        )
        event_intervals = build_10min_event_bridged_water_loss(dataset1, radiation_intervals)
        dataset1_rootzone_reference = dataset1
        dataset1_rootzone_meta = dict(dataset1_load_meta)
    photoperiod = build_photoperiod_table(radiation_intervals)
    radiation_daily = build_radiation_daily_summary(radiation_intervals)
    photoperiod_path = _write_csv(output_root, "radiation_photoperiod", photoperiod)

    event_intervals = calibrate_to_daily_event_bridged_total(
        event_intervals,
        legacy_event_totals,
        total_col=CALIBRATION_TOTAL_COL,
    )
    event_calibration_metadata = calibration_match_metadata(
        event_intervals,
        legacy_event_totals,
        event_calibration_metadata,
    )
    event_intervals_path = _write_csv(output_root, "event_intervals", event_intervals)
    event_daily_all = summarize_radiation_daynight_et(event_intervals)
    event_daily_all_path = _write_csv(output_root, "event_daily_all_thresholds", event_daily_all)
    event_daily_main = event_daily_all[event_daily_all["threshold_w_m2"].eq(float(MAIN_RADIATION_THRESHOLD_W_M2))].copy()
    event_daily_main_path = _write_csv(output_root, "event_daily_main_0w", event_daily_main)
    radiation_main = radiation_daily[radiation_daily["threshold_w_m2"].eq(float(MAIN_RADIATION_THRESHOLD_W_M2))].copy()
    daily_wide = build_daily_wide_et_summary(event_daily_all, threshold_w_m2=MAIN_RADIATION_THRESHOLD_W_M2)
    daily_wide = daily_wide.merge(
        radiation_main[
            [
                column
                for column in (
                    "date",
                    "loadcell_id",
                    "treatment",
                    "threshold_w_m2",
                    "day_vpd_kpa_mean",
                    "day_air_temp_c_mean",
                    "day_co2_ppm_mean",
                )
                if column in radiation_main.columns
            ]
        ],
        on=[column for column in ("date", "loadcell_id", "treatment", "threshold_w_m2") if column in daily_wide.columns],
        how="left",
    )
    daily_wide_path = _write_csv(output_root, "event_daily_wide_main_0w", daily_wide)

    fruit_windows, leaf_windows = build_fruit_leaf_radiation_windows(
        fruit_leaf_qc,
        photoperiod,
        mapping,
        timestamp_col=mapping.get("timestamp_col", "TIMESTAMP"),
        thresholds_w_m2=RADIATION_THRESHOLDS_W_M2,
    )
    fruit_leaf_windows = fruit_windows.merge(leaf_windows, on=["date", "threshold_w_m2"], how="left")
    fruit_leaf_windows_path = _write_csv(output_root, "fruit_leaf_radiation_windows", fruit_leaf_windows)
    clock_windows = build_fixed_clock_compat_windows(
        fruit_leaf_qc,
        mapping,
        timestamp_col=mapping.get("timestamp_col", "TIMESTAMP"),
    )
    clock_windows_path = _write_csv(output_root, "fruit_leaf_clock_windows", clock_windows)
    sensor_bridge = build_fruit_leaf_loadcell_bridge(mapping)
    sensor_bridge_path = _write_csv(output_root, "fruit_leaf_loadcell_bridge", sensor_bridge)

    if mode == "production":
        dataset2, dataset2_load_meta, dataset2_manifest = aggregate_dataset2_daily_streaming(
            path=dataset2_path,
            columns=DATASET2_COLUMN_CANDIDATES,
            batch_size=batch_size,
            max_rows=None,
        )
        chunk_manifest_frames.append(dataset2_manifest)
    else:
        dataset2, dataset2_load_meta = _read_projected_parquet(
            dataset2_path,
            DATASET2_COLUMN_CANDIDATES,
            max_rows=int(dataset2_max_rows) if dataset2_max_rows is not None else None,
            batch_size=batch_size,
            max_full_rows_without_limit=max_full_rows_without_limit,
            mode=mode,
            fail_on_full_in_memory_large_dataset=fail_on_full_in_memory_large_dataset,
        )
    rootzone = build_rootzone_indices(dataset2, daily_wide, dataset1_reference_frame=dataset1_rootzone_reference)
    rootzone_path = _write_csv(output_root, "rootzone_indices", rootzone)
    rootzone_reference_audit = _rootzone_reference_audit(rootzone)
    rootzone_reference_audit_passed = bool(rootzone_reference_audit["status"].eq("pass").all())
    rootzone_reference_audit_path = _write_csv(output_root, "rootzone_rzi_reference_audit", rootzone_reference_audit)

    dataset3_preflight_metadata = _assert_dataset3_size_guard_before_read(
        path=dataset3_path,
        max_rows=int(dataset3_max_rows) if dataset3_max_rows is not None else None,
        max_full_rows_without_limit=max_full_rows_without_limit,
        mode=mode,
    )
    dataset3, dataset3_load_meta = _read_projected_parquet(
        dataset3_path,
        DATASET3_COLUMN_CANDIDATES,
        max_rows=int(dataset3_max_rows) if dataset3_max_rows is not None else None,
        batch_size=batch_size,
        max_full_rows_without_limit=max_full_rows_without_limit,
        mode=mode,
        fail_on_full_in_memory_large_dataset=fail_on_full_in_memory_large_dataset,
    )
    dataset3_guard_metadata = _dataset3_size_guard(
        dataset3_load_meta,
        max_full_rows_without_limit=max_full_rows_without_limit,
        mode=mode,
    )
    dataset3_guard_metadata.update(dataset3_preflight_metadata)
    dataset3_bridge, dataset3_metadata = build_dataset3_growth_phenology_bridge(dataset3)
    dataset3_path_out = _write_csv(output_root, "dataset3_bridge", dataset3_bridge)

    feature_frame = build_observer_feature_frame(
        daily_et_wide=daily_wide,
        radiation_daily=radiation_daily,
        rootzone_indices=rootzone,
        fruit_windows=fruit_windows,
        leaf_windows=leaf_windows,
        dataset3_bridge=dataset3_bridge,
        radiation_source_used=str(radiation_decision.get("radiation_daynight_primary_source") or "dataset1"),
        radiation_column_used=radiation_col,
    )
    feature_frame = _merge_legacy_yield_bridge(feature_frame, legacy_yield)
    feature_frame_path = _write_csv(output_root, "observer_feature_frame", feature_frame)

    chunk_manifest = (
        pd.concat(chunk_manifest_frames, ignore_index=True)
        if chunk_manifest_frames
        else pd.DataFrame(columns=["dataset_role", "batch_index", "rows_processed", "aggregation_status"])
    )
    chunk_manifest_path: Path | None = None
    if mode == "production" or write_intermediate_chunk_manifests:
        chunk_manifest_path = _write_csv(output_root, "chunk_manifest", chunk_manifest)

    row_cap_applied = bool(
        dataset1_load_meta.get("row_limit_applied")
        or dataset2_load_meta.get("row_limit_applied")
        or dataset3_load_meta.get("row_limit_applied")
    )
    chunk_aggregation_used = bool(
        dataset1_load_meta.get("chunk_aggregation_used") and dataset2_load_meta.get("chunk_aggregation_used")
    )
    full_in_memory_large_dataset_used = bool(
        dataset1_load_meta.get("full_in_memory_large_dataset_used")
        or dataset2_load_meta.get("full_in_memory_large_dataset_used")
        or dataset3_load_meta.get("full_in_memory_large_dataset_used")
    )
    production_failures = _production_requirement_failures(
        mode=mode,
        pipeline_config=pipeline_config,
        row_cap_applied=row_cap_applied,
        chunk_aggregation_used=chunk_aggregation_used,
        full_in_memory_large_dataset_used=full_in_memory_large_dataset_used,
        dataset1_load_meta=dataset1_load_meta,
        dataset2_load_meta=dataset2_load_meta,
    )
    production_export_completed = bool(
        mode == "production"
        and not row_cap_applied
        and dataset1_load_meta.get("rows_processed_fraction") == 1.0
        and dataset2_load_meta.get("rows_processed_fraction") == 1.0
        and not production_failures
    )
    production_ready_for_latent_allocation = bool(
        production_export_completed
        and chunk_aggregation_used
        and not row_cap_applied
        and feature_frame_path.exists()
        and rootzone_path.exists()
        and rootzone_reference_audit_passed
        and event_intervals_path.exists()
    )
    production_summary_path: Path | None = None
    if mode == "production" or write_intermediate_chunk_manifests:
        production_summary_path = _write_text(
            output_root,
            "production_export_summary",
            "\n".join(
                [
                    "# TOMICS-HAF 2025-2C Observer Production Export Summary",
                    "",
                    f"- observer_pipeline_mode: {mode}",
                    f"- production_export_completed: {production_export_completed}",
                    f"- production_ready_for_latent_allocation: {production_ready_for_latent_allocation}",
                    f"- dataset1_rows_processed: {dataset1_load_meta.get('rows_processed')}",
                    f"- dataset1_total_rows: {dataset1_load_meta.get('total_rows')}",
                    f"- dataset2_rows_processed: {dataset2_load_meta.get('rows_processed')}",
                    f"- dataset2_total_rows: {dataset2_load_meta.get('total_rows')}",
                    f"- row_cap_applied: {row_cap_applied}",
                    f"- chunk_aggregation_used: {chunk_aggregation_used}",
                    f"- full_in_memory_large_dataset_used: {full_in_memory_large_dataset_used}",
                    f"- production_requirement_failures: {'; '.join(production_failures)}",
                    "",
                ]
            ),
        )

    metadata = base_metadata()
    metadata.update(_load_goal1_metadata(output_root))
    metadata.update(base_metadata())
    metadata.update(fruit_diameter_policy_metadata(mapping))
    metadata.update(
        {
            "radiation_source_decision": radiation_decision,
            "radiation_source_candidate_count": len(radiation_rows),
            "radiation_daynight_primary_source": radiation_decision.get("radiation_daynight_primary_source"),
            "radiation_column_used": radiation_decision.get("radiation_column_used"),
            "dataset1_radiation_directly_usable": radiation_decision.get("dataset1_radiation_directly_usable"),
            "dataset1_radiation_grain": radiation_decision.get("dataset1_radiation_grain"),
            "fallback_required": radiation_decision.get("fallback_required"),
            "fallback_source_if_required": radiation_decision.get("fallback_source_if_required") or None,
            "event_bridged_ET_outputs_produced": True,
            "fruit_leaf_qc_outputs_produced": True,
            "fruit_diameter_observer_inference_level": "sensor_level_apparent_expansion_diagnostics",
            "apparent_canopy_conductance_available": bool(
                rootzone.get("apparent_canopy_conductance_available", pd.Series(dtype=bool)).any()
            ),
            "Dataset3_mapping_confidence": dataset3_metadata.get("Dataset3_mapping_confidence"),
            "Dataset3_mapping_confidence_counts": dataset3_metadata.get("Dataset3_mapping_confidence_counts", {}),
            "Dataset3_datetime_or_date_available": bool(dataset3_metadata.get("datetime_or_date_available", False)),
            "Dataset3_truss_position_available": bool(dataset3_metadata.get("truss_position_available", False)),
            "observer_pipeline_mode": mode,
            "production_export_requested": mode == "production",
            "production_export_completed": production_export_completed,
            "chunk_aggregation_used": chunk_aggregation_used,
            "full_in_memory_large_dataset_used": full_in_memory_large_dataset_used,
            "row_cap_applied": row_cap_applied,
            "row_cap_allowed": mode == "smoke",
            "production_requirement_failures": production_failures,
            "dataset1_total_rows": dataset1_load_meta.get("total_rows"),
            "dataset1_rows_processed": dataset1_load_meta.get("rows_processed"),
            "dataset1_rows_processed_fraction": dataset1_load_meta.get("rows_processed_fraction"),
            "dataset1_batches_processed": dataset1_load_meta.get("batches_processed"),
            "dataset1_projected_columns": dataset1_load_meta.get("projected_columns"),
            "dataset1_chunk_aggregation_complete": bool(dataset1_load_meta.get("chunk_aggregation_complete")),
            "dataset2_total_rows": dataset2_load_meta.get("total_rows"),
            "dataset2_rows_processed": dataset2_load_meta.get("rows_processed"),
            "dataset2_rows_processed_fraction": dataset2_load_meta.get("rows_processed_fraction"),
            "dataset2_batches_processed": dataset2_load_meta.get("batches_processed"),
            "dataset2_projected_columns": dataset2_load_meta.get("projected_columns"),
            "dataset2_chunk_aggregation_complete": bool(dataset2_load_meta.get("chunk_aggregation_complete")),
            **dataset3_guard_metadata,
            "row_cap_warning": (
                "row caps applied; observer feature frame is not production-ready for latent allocation"
                if row_cap_applied
                else ""
            ),
            "water_flux_chunk_carryover_used": bool(dataset1_load_meta.get("water_flux_chunk_carryover_used", False)),
            "water_flux_chunk_carryover_group_keys": dataset1_load_meta.get("water_flux_chunk_carryover_group_keys", []),
            "dataset1_rootzone_reference_rows_processed": dataset1_rootzone_meta.get("rows_processed"),
            "dataset1_rootzone_reference_rows_processed_fraction": dataset1_rootzone_meta.get("rows_processed_fraction"),
            "RZI_main_available": bool(rootzone.get("RZI_main_available", pd.Series(dtype=bool)).fillna(False).any()),
            "RZI_main_source": ";".join(
                sorted(rootzone.get("RZI_main_source", pd.Series(dtype=str)).dropna().astype(str).unique())
            ),
            "RZI_control_reference_source": ";".join(
                sorted(rootzone.get("RZI_control_reference_source", pd.Series(dtype=str)).dropna().astype(str).unique())
            ),
            "rootzone_rzi_reference_audit_passed": rootzone_reference_audit_passed,
            "Dataset2_tensiometer_drought_only": bool(
                rootzone.get("Dataset2_tensiometer_drought_only", pd.Series(dtype=bool)).fillna(False).any()
            ),
            "tensiometer_extrapolated_to_all_loadcells": False,
            **event_calibration_metadata,
            **yield_metadata,
            "radiation_interval_aggregation_grain": "10min",
            "radiation_phase_rule": "day_if_any_interval_sample_gt_threshold",
            "production_ready_for_latent_allocation": production_ready_for_latent_allocation,
            "row_loading": {
                "dataset1": dataset1_load_meta,
                "dataset2": dataset2_load_meta,
                "dataset3": dataset3_load_meta,
            },
            "outputs": {},
            "fixed_clock_daynight_primary": False,
            "clock_06_18_used_only_for_compatibility": True,
            "raw_dat_solar_rad_fallback_verified": True,
            "shipped_TOMICS_incumbent_changed": False,
            "latent_allocation_inference_run": False,
            "harvest_family_factorial_run": False,
            "promotion_gate_run": False,
        }
    )

    output_paths = {
        "fruit_leaf_timeseries_qc": fruit_leaf_qc_path,
        "sensor_qc_report": sensor_qc_path,
        "radiation_photoperiod": photoperiod_path,
        "event_intervals": event_intervals_path,
        "event_daily_all_thresholds": event_daily_all_path,
        "event_daily_main_0w": event_daily_main_path,
        "event_daily_wide_main_0w": daily_wide_path,
        "fruit_leaf_radiation_windows": fruit_leaf_windows_path,
        "fruit_leaf_clock_windows": clock_windows_path,
        "fruit_leaf_loadcell_bridge": sensor_bridge_path,
        "rootzone_indices": rootzone_path,
        "rootzone_rzi_reference_audit": rootzone_reference_audit_path,
        "dataset3_bridge": dataset3_path_out,
        "observer_feature_frame": feature_frame_path,
        "legacy_v1_3_bridge_audit": legacy_audit_path,
        "legacy_v1_3_bridge_audit_json": legacy_audit_json_path,
        "event_bridge_calibration_audit": event_calibration_audit_path,
        "fresh_dry_yield_bridge_audit": yield_audit_path,
        "metadata_contract_audit": output_root / OUTPUT_FILENAMES["metadata_contract_audit"],
        "metadata_goal2_observer": output_root / OUTPUT_FILENAMES["metadata_goal2_observer"],
        "metadata_goal2_5_production_observer": output_root / OUTPUT_FILENAMES["metadata_goal2_5_production_observer"],
        "metadata": output_root / OUTPUT_FILENAMES["metadata"],
    }
    if chunk_manifest_path is not None:
        output_paths["chunk_manifest"] = chunk_manifest_path
    if production_summary_path is not None:
        output_paths["production_export_summary"] = production_summary_path
    metadata["outputs"] = {key: str(path) for key, path in output_paths.items()}
    metadata = normalize_metadata(metadata)
    metadata_contract_path = _write_csv(output_root, "metadata_contract_audit", metadata_contract_audit(metadata))
    output_paths["metadata_contract_audit"] = metadata_contract_path
    write_stage_metadata_snapshot(output_root / OUTPUT_FILENAMES["metadata_goal2_observer"], metadata)
    if mode == "production":
        write_stage_metadata_snapshot(output_root / OUTPUT_FILENAMES["metadata_goal2_5_production_observer"], metadata)
    metadata["outputs"] = {key: str(path) for key, path in output_paths.items()}
    metadata_path = write_normalized_metadata(output_root / OUTPUT_FILENAMES["metadata"], metadata)
    output_paths["metadata"] = metadata_path

    if production_failures:
        raise RuntimeError("Production observer export failed hard requirements: " + "; ".join(production_failures))

    return {
        "output_root": str(output_root),
        "outputs": {key: str(path) for key, path in output_paths.items()},
        "metadata": metadata,
    }
