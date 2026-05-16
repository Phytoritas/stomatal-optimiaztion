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
    RADIATION_COLUMN_USED,
    RADIATION_THRESHOLDS_W_M2,
    RAW_INPUT_FILENAMES,
    base_metadata,
    resolve_repo_path,
)
from stomatal_optimiaztion.domains.tomato.tomics.observers.dataset3_bridge import (
    build_dataset3_growth_phenology_bridge,
)
from stomatal_optimiaztion.domains.tomato.tomics.observers.feature_frame import build_observer_feature_frame
from stomatal_optimiaztion.domains.tomato.tomics.observers.fruit_diameter_windows import (
    build_fixed_clock_compat_windows,
    build_fruit_leaf_loadcell_bridge,
    build_fruit_leaf_radiation_windows,
)
from stomatal_optimiaztion.domains.tomato.tomics.observers.parquet_streaming import (
    assert_no_large_full_load_without_limit,
    iter_projected_parquet_batches,
    parquet_metadata_summary,
    projected_columns,
    validate_production_row_cap_policy,
)
from stomatal_optimiaztion.domains.tomato.tomics.observers.production_export import (
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

    chunk_manifest_frames: list[pd.DataFrame] = []
    if mode == "production":
        radiation_intervals, event_intervals, dataset1_load_meta, dataset1_manifest = aggregate_dataset1_streaming(
            path=dataset1_path,
            columns=DATASET1_COLUMN_CANDIDATES,
            batch_size=batch_size,
            max_rows=None,
            thresholds_w_m2=RADIATION_THRESHOLDS_W_M2,
        )
        chunk_manifest_frames.append(dataset1_manifest)
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
            radiation_col=RADIATION_COLUMN_USED,
        )
        event_intervals = build_10min_event_bridged_water_loss(dataset1, radiation_intervals)
    photoperiod = build_photoperiod_table(radiation_intervals)
    radiation_daily = build_radiation_daily_summary(radiation_intervals)
    photoperiod_path = _write_csv(output_root, "radiation_photoperiod", photoperiod)

    event_intervals = calibrate_to_daily_event_bridged_total(event_intervals)
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
    rootzone = build_rootzone_indices(dataset2, daily_wide)
    rootzone_path = _write_csv(output_root, "rootzone_indices", rootzone)

    dataset3, dataset3_load_meta = _read_projected_parquet(
        dataset3_path,
        DATASET3_COLUMN_CANDIDATES,
        max_rows=int(dataset3_max_rows) if dataset3_max_rows is not None else None,
        batch_size=batch_size,
        max_full_rows_without_limit=max_full_rows_without_limit,
        mode=mode,
        fail_on_full_in_memory_large_dataset=fail_on_full_in_memory_large_dataset,
    )
    dataset3_bridge, dataset3_metadata = build_dataset3_growth_phenology_bridge(dataset3)
    dataset3_path_out = _write_csv(output_root, "dataset3_bridge", dataset3_bridge)

    feature_frame = build_observer_feature_frame(
        daily_et_wide=daily_wide,
        radiation_daily=radiation_daily,
        rootzone_indices=rootzone,
        fruit_windows=fruit_windows,
        leaf_windows=leaf_windows,
        dataset3_bridge=dataset3_bridge,
    )
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
    production_export_completed = bool(
        mode == "production"
        and not row_cap_applied
        and dataset1_load_meta.get("rows_processed_fraction") == 1.0
        and dataset2_load_meta.get("rows_processed_fraction") == 1.0
    )
    production_ready_for_latent_allocation = bool(
        production_export_completed
        and chunk_aggregation_used
        and not row_cap_applied
        and feature_frame_path.exists()
        and rootzone_path.exists()
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
                    f"- full_in_memory_large_dataset_used: {bool(dataset1_load_meta.get('full_in_memory_large_dataset_used') or dataset2_load_meta.get('full_in_memory_large_dataset_used'))}",
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
            "full_in_memory_large_dataset_used": bool(
                dataset1_load_meta.get("full_in_memory_large_dataset_used")
                or dataset2_load_meta.get("full_in_memory_large_dataset_used")
            ),
            "row_cap_applied": row_cap_applied,
            "row_cap_allowed": mode == "smoke",
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
            "dataset3_total_rows": dataset3_load_meta.get("total_rows"),
            "dataset3_rows_processed": dataset3_load_meta.get("rows_processed"),
            "row_cap_warning": (
                "row caps applied; observer feature frame is not production-ready for latent allocation"
                if row_cap_applied
                else ""
            ),
            "water_flux_chunk_carryover_used": bool(dataset1_load_meta.get("water_flux_chunk_carryover_used", False)),
            "water_flux_chunk_carryover_group_keys": dataset1_load_meta.get("water_flux_chunk_carryover_group_keys", []),
            "event_bridged_ET_calibration_status": "uncalibrated_no_daily_total",
            "existing_daily_event_bridged_total_available": False,
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
            "fallback_required": False,
            "fallback_source_if_required": None,
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
        "dataset3_bridge": dataset3_path_out,
        "observer_feature_frame": feature_frame_path,
        "metadata": output_root / OUTPUT_FILENAMES["metadata"],
    }
    if chunk_manifest_path is not None:
        output_paths["chunk_manifest"] = chunk_manifest_path
    if production_summary_path is not None:
        output_paths["production_export_summary"] = production_summary_path
    metadata["outputs"] = {key: str(path) for key, path in output_paths.items()}
    metadata_path = write_json(output_root / OUTPUT_FILENAMES["metadata"], metadata)
    output_paths["metadata"] = metadata_path

    return {
        "output_root": str(output_root),
        "outputs": {key: str(path) for key, path in output_paths.items()},
        "metadata": metadata,
    }
