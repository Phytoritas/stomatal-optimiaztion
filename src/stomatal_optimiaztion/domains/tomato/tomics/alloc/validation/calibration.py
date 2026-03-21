from __future__ import annotations

import copy
import itertools
import json
import math
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.alloc.core import ensure_dir, load_config, write_json
from stomatal_optimiaztion.domains.tomato.tomics.alloc.pipelines import run_tomato_legacy_pipeline
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.current_vs_promoted import (
    PreparedKnuBundle,
    configure_candidate_run,
    prepare_knu_bundle,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.harvest_operator import (
    MODEL_HARVESTED_CUMULATIVE_COLUMN,
    model_floor_area_cumulative_total_fruit,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.metrics import (
    REPORTING_BASIS_FLOOR_AREA,
    canopy_collapse_days,
    compute_validation_bundle,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.observation_model import (
    validation_overlay_frame,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.parameter_budget import (
    CalibrationBudget,
    build_calibration_budget,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.state_reconstruction import (
    reconstruct_hidden_state,
)


@dataclass(frozen=True, slots=True)
class CalibrationSplit:
    split_label: str
    split_kind: str
    calibration_start: pd.Timestamp
    calibration_end: pd.Timestamp
    holdout_start: pd.Timestamp
    holdout_end: pd.Timestamp


@dataclass(frozen=True, slots=True)
class CandidateSpec:
    candidate_label: str
    architecture_id: str
    candidate_row: dict[str, Any] | None
    base_config_path: Path | None
    is_observation_only: bool = False


@dataclass(frozen=True, slots=True)
class CalibrationArtifacts:
    output_root: Path
    calibration_manifest: dict[str, Any]
    calibration_results_df: pd.DataFrame
    holdout_results_df: pd.DataFrame
    winner_stability_df: pd.DataFrame
    parameter_stability_df: pd.DataFrame


def _as_dict(raw: object) -> dict[str, Any]:
    if isinstance(raw, dict):
        return {str(key): value for key, value in raw.items()}
    return {}


def _as_list(raw: object) -> list[Any]:
    if isinstance(raw, list):
        return list(raw)
    return []


def _nanmean(frame: pd.DataFrame, column: str, *, default: float = math.nan) -> float:
    if column not in frame.columns:
        return float(default)
    series = pd.to_numeric(frame[column], errors="coerce").dropna()
    if series.empty:
        return float(default)
    return float(series.mean())


def _nanlast(frame: pd.DataFrame, column: str, *, default: float = math.nan) -> float:
    if column not in frame.columns:
        return float(default)
    series = pd.to_numeric(frame[column], errors="coerce").dropna()
    if series.empty:
        return float(default)
    return float(series.iloc[-1])


def _resolve_config_path(raw: str | Path, *, repo_root: Path, config_path: Path) -> Path:
    candidate = Path(raw)
    if candidate.is_absolute():
        return candidate
    return (repo_root / candidate).resolve()


def _base_pipeline_params(config: dict[str, Any]) -> dict[str, Any]:
    pipeline_cfg = _as_dict(config.get("pipeline"))
    params = _as_dict(pipeline_cfg.get("partition_policy_params"))
    tomics = _as_dict(pipeline_cfg.get("tomics"))
    if tomics:
        params = {**params, **tomics}
    return params


def _shipped_candidate_row(base_config: dict[str, Any]) -> dict[str, Any]:
    params = _base_pipeline_params(base_config)
    return {
        "architecture_id": "shipped_tomics_control",
        "partition_policy": "tomics",
        "policy_family": "shipped",
        "allocation_scheme": str(_as_dict(base_config.get("pipeline")).get("allocation_scheme", "4pool")),
        "fruit_structure_mode": "tomsim_truss_cohort",
        "fruit_partition_mode": "legacy_sink_exact",
        "vegetative_demand_mode": "tomsim_constant_wholecrop",
        "reserve_buffer_mode": "off",
        "fruit_feedback_mode": "off",
        "sla_mode": "derived_not_driver",
        "maintenance_mode": "rgr_adjusted",
        "canopy_governor_mode": "lai_band",
        "root_representation_mode": "bounded_explicit_root",
        "thorp_root_correction_mode": "bounded",
        "temporal_coupling_mode": "daily_alloc",
        "leaf_marginal_mode": "canopy_only",
        "stem_marginal_mode": "support_only",
        "root_marginal_mode": "water_only_gate",
        "vegetative_prior_mode": "current_tomics_prior",
        "optimizer_mode": "bounded_static_current",
        "temporal_mode": "daily_marginal_daily_alloc",
        "wet_root_cap": float(params.get("wet_root_cap", 0.10)),
        "dry_root_cap": float(params.get("dry_root_cap", 0.18)),
        "lai_target_center": float(params.get("lai_target_center", 2.75)),
        "leaf_fraction_of_shoot_base": float(params.get("leaf_fraction_of_shoot_base", 0.70)),
        "fruit_load_multiplier": 1.0,
        "thorp_root_blend": float(params.get("thorp_root_blend", 1.0)),
    }


def _legacy_candidate_row(base_config: dict[str, Any]) -> dict[str, Any]:
    row = _shipped_candidate_row(base_config)
    row["architecture_id"] = "legacy_reference"
    row["partition_policy"] = "legacy"
    row["policy_family"] = "legacy"
    return row


def _load_selected_payload(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    selected = _as_dict(payload.get("selected_architecture"))
    selected.setdefault("architecture_id", str(payload["selected_architecture_id"]))
    return selected


def load_candidate_specs(
    *,
    config: dict[str, Any],
    repo_root: Path,
    config_path: Path,
) -> tuple[dict[str, CandidateSpec], dict[str, Path], dict[str, Any]]:
    calibration_cfg = _as_dict(config.get("calibration"))
    selection_cfg = _as_dict(config.get("selection"))
    base_config_path = _resolve_config_path(
        calibration_cfg.get("base_config", "configs/exp/tomics_allocation_factorial.yaml"),
        repo_root=repo_root,
        config_path=config_path,
    )
    base_config = load_config(base_config_path)
    current_output_root = _resolve_config_path(
        selection_cfg.get("current_output_root", "out/tomics/validation/knu/architecture/current-factorial"),
        repo_root=repo_root,
        config_path=config_path,
    )
    promoted_output_root = _resolve_config_path(
        selection_cfg.get("promoted_output_root", "out/tomics/validation/knu/architecture/promoted-factorial"),
        repo_root=repo_root,
        config_path=config_path,
    )
    current_selected = _load_selected_payload(current_output_root / "selected_architecture.json")
    promoted_selected = _load_selected_payload(promoted_output_root / "selected_architecture.json")
    current_selected["policy_family"] = "current"
    promoted_selected["policy_family"] = "promoted"
    specs = {
        "workbook_estimated": CandidateSpec(
            candidate_label="workbook_estimated",
            architecture_id="workbook_estimated_baseline",
            candidate_row=None,
            base_config_path=None,
            is_observation_only=True,
        ),
        "shipped_tomics": CandidateSpec(
            candidate_label="shipped_tomics",
            architecture_id="shipped_tomics_control",
            candidate_row=_shipped_candidate_row(base_config),
            base_config_path=base_config_path,
        ),
        "current_selected": CandidateSpec(
            candidate_label="current_selected",
            architecture_id=str(current_selected["architecture_id"]),
            candidate_row=current_selected,
            base_config_path=base_config_path,
        ),
        "promoted_selected": CandidateSpec(
            candidate_label="promoted_selected",
            architecture_id=str(promoted_selected["architecture_id"]),
            candidate_row=promoted_selected,
            base_config_path=base_config_path,
        ),
    }
    metadata = {
        "base_config_path": str(base_config_path),
        "current_output_root": str(current_output_root),
        "promoted_output_root": str(promoted_output_root),
        "current_selected_architecture_id": str(current_selected["architecture_id"]),
        "promoted_selected_architecture_id": str(promoted_selected["architecture_id"]),
    }
    return specs, {"current": current_output_root, "promoted": promoted_output_root}, metadata


def build_calibration_splits(
    observed_df: pd.DataFrame,
    *,
    calibration_end: pd.Timestamp,
    rolling_window_days: int = 4,
) -> list[CalibrationSplit]:
    dates = pd.Series(pd.to_datetime(observed_df["date"]).dt.normalize().sort_values().unique())
    start = pd.Timestamp(dates.iloc[0]).normalize()
    end = pd.Timestamp(dates.iloc[-1]).normalize()
    alt_calibration_end = pd.Timestamp(dates.iloc[min(7, len(dates) - 2)]).normalize()
    rolling_pos = min(10, len(dates) - 2)
    rolling_calibration_end = pd.Timestamp(dates.iloc[rolling_pos]).normalize()
    rolling_holdout_start = (rolling_calibration_end + pd.Timedelta(days=1)).normalize()
    rolling_holdout_end = min(
        pd.Timestamp(dates.iloc[min(rolling_pos + rolling_window_days, len(dates) - 1)]).normalize(),
        end,
    )
    splits = [
        CalibrationSplit(
            split_label="blocked_holdout",
            split_kind="blocked",
            calibration_start=start,
            calibration_end=calibration_end.normalize(),
            holdout_start=(calibration_end + pd.Timedelta(days=1)).normalize(),
            holdout_end=end,
        ),
        CalibrationSplit(
            split_label="alternate_holdout",
            split_kind="blocked",
            calibration_start=start,
            calibration_end=alt_calibration_end,
            holdout_start=(alt_calibration_end + pd.Timedelta(days=1)).normalize(),
            holdout_end=end,
        ),
        CalibrationSplit(
            split_label="rolling_origin_1",
            split_kind="rolling_origin",
            calibration_start=start,
            calibration_end=rolling_calibration_end,
            holdout_start=rolling_holdout_start,
            holdout_end=rolling_holdout_end,
        ),
    ]
    return splits


def _parameter_grid(config: dict[str, Any]) -> list[dict[str, float]]:
    calibration_cfg = _as_dict(config.get("calibration"))
    grid_cfg = _as_dict(calibration_cfg.get("shared_parameter_grid"))
    fruit_load_values = [float(value) for value in _as_list(grid_cfg.get("fruit_load_multiplier", [0.9, 1.0, 1.1]))]
    lai_values = [float(value) for value in _as_list(grid_cfg.get("lai_target_center", [2.5, 2.75, 3.0]))]
    rows: list[dict[str, float]] = []
    for fruit_load_multiplier, lai_target_center in itertools.product(fruit_load_values, lai_values):
        rows.append(
            {
                "fruit_load_multiplier": float(fruit_load_multiplier),
                "lai_target_center": float(lai_target_center),
            }
        )
    return rows


def _candidate_series(observed_df: pd.DataFrame, run_df: pd.DataFrame) -> pd.Series:
    model_daily_df = model_floor_area_cumulative_total_fruit(run_df)
    indexed = model_daily_df.set_index("date")
    return observed_df["date"].map(indexed[MODEL_HARVESTED_CUMULATIVE_COLUMN])


def _window_bundle(
    observed_df: pd.DataFrame,
    *,
    candidate_series: pd.Series,
    candidate_label: str,
    unit_label: str,
    start: pd.Timestamp,
    end: pd.Timestamp,
) -> tuple[pd.DataFrame, dict[str, float | bool | str]]:
    mask = (observed_df["date"] >= start) & (observed_df["date"] <= end)
    candidate_daily_increment_series = pd.to_numeric(candidate_series, errors="coerce").diff()
    bundle = compute_validation_bundle(
        observed_df.loc[mask].copy(),
        candidate_series=candidate_series.loc[mask],
        candidate_daily_increment_series=candidate_daily_increment_series.loc[mask],
        candidate_label=candidate_label,
        unit_declared_in_observation_file=unit_label,
    )
    return bundle.merged_df, bundle.metrics


def _objective_score(metrics: dict[str, float | bool | str]) -> float:
    return float(
        -1.2 * float(metrics.get("yield_rmse_offset_adjusted", 1_000.0))
        -0.7 * float(metrics.get("rmse_daily_increment", 1_000.0))
        -0.5 * abs(float(metrics.get("final_cumulative_bias", 1_000.0)))
        -0.4 * abs(float(metrics.get("harvest_timing_mae_days", 10.0)))
    )


def _evaluate_model_candidate(
    *,
    repo_root: Path,
    prepared_bundle: PreparedKnuBundle,
    candidate_label: str,
    candidate_row: dict[str, Any],
    base_config_path: Path,
    split: CalibrationSplit,
    parameter_values: dict[str, float],
    initial_state_overrides: dict[str, Any],
    legacy_reference_df: pd.DataFrame,
    wet_theta_threshold: float,
    canopy_lai_floor: float,
    leaf_fraction_floor: float,
    validation_dir: Path,
) -> dict[str, Any]:
    tuned_row = {**candidate_row, **parameter_values}
    moderate_scenario = prepared_bundle.scenarios["moderate"]
    wet_scenario = prepared_bundle.scenarios["wet"]

    started = time.perf_counter()
    moderate_cfg = configure_candidate_run(
        copy.deepcopy(load_config(base_config_path)),
        forcing_csv_path=moderate_scenario.forcing_csv_path,
        theta_center=float(moderate_scenario.summary.get("theta_mean", 0.65)),
        row=tuned_row,
        initial_state_overrides=initial_state_overrides,
    )
    moderate_run_df = run_tomato_legacy_pipeline(moderate_cfg, repo_root=repo_root)
    runtime_seconds = time.perf_counter() - started

    candidate_series = _candidate_series(prepared_bundle.observed_df, moderate_run_df)
    _, calibration_metrics = _window_bundle(
        prepared_bundle.observed_df,
        candidate_series=candidate_series,
        candidate_label="model",
        unit_label=prepared_bundle.data.observation_unit_label,
        start=split.calibration_start,
        end=split.calibration_end,
    )
    holdout_df, holdout_metrics = _window_bundle(
        prepared_bundle.observed_df,
        candidate_series=candidate_series,
        candidate_label="model",
        unit_label=prepared_bundle.data.observation_unit_label,
        start=split.holdout_start,
        end=split.holdout_end,
    )

    wet_cfg = configure_candidate_run(
        copy.deepcopy(load_config(base_config_path)),
        forcing_csv_path=wet_scenario.forcing_csv_path,
        theta_center=float(wet_scenario.summary.get("theta_mean", 0.80)),
        row=tuned_row,
        initial_state_overrides=initial_state_overrides,
    )
    wet_run_df = run_tomato_legacy_pipeline(wet_cfg, repo_root=repo_root)

    alloc = pd.to_numeric(
        moderate_run_df[["alloc_frac_fruit", "alloc_frac_leaf", "alloc_frac_stem", "alloc_frac_root"]].stack(),
        errors="coerce",
    )
    mean_theta_wet = _nanmean(wet_run_df, "theta_substrate", default=math.nan)
    mean_root_wet = _nanmean(wet_run_df, "alloc_frac_root", default=0.0)
    wet_root_cap = float(tuned_row.get("wet_root_cap", 0.10))
    wet_penalty = max(mean_root_wet - wet_root_cap, 0.0) if mean_theta_wet >= wet_theta_threshold else 0.0
    fruit_anchor_error = abs(
        _nanmean(moderate_run_df, "alloc_frac_fruit", default=math.nan)
        - _nanmean(legacy_reference_df, "alloc_frac_fruit", default=math.nan)
    )
    sum_to_one_error = abs(
        (
            _nanmean(moderate_run_df, "alloc_frac_fruit", default=0.0)
            + _nanmean(moderate_run_df, "alloc_frac_leaf", default=0.0)
            + _nanmean(moderate_run_df, "alloc_frac_stem", default=0.0)
            + _nanmean(moderate_run_df, "alloc_frac_root", default=0.0)
        )
        - 1.0
    )
    invalid_run_flag = int(
        (not alloc.dropna().map(math.isfinite).all())
        or bool((alloc.dropna() < -1e-9).any())
        or sum_to_one_error > 1e-6
    )
    validation_path = validation_dir / f"{candidate_label}__{split.split_label}.csv"
    holdout_df.to_csv(validation_path, index=False)
    return {
        "candidate_label": candidate_label,
        "architecture_id": str(tuned_row["architecture_id"]),
        "policy_family": str(tuned_row.get("policy_family", candidate_label)),
        "split_label": split.split_label,
        "split_kind": split.split_kind,
        "reconstruction_mode": str(initial_state_overrides.get("reconstruction_mode", "")),
        "selected_params_json": json.dumps(parameter_values, sort_keys=True),
        "initial_state_overrides_json": json.dumps(initial_state_overrides, sort_keys=True),
        "reporting_basis": REPORTING_BASIS_FLOOR_AREA,
        "holdout_rmse_cumulative_offset": holdout_metrics["yield_rmse_offset_adjusted"],
        "holdout_mae_cumulative_offset": holdout_metrics["yield_mae_offset_adjusted"],
        "holdout_r2_cumulative_offset": holdout_metrics["yield_r2_offset_adjusted"],
        "holdout_rmse_daily_increment": holdout_metrics["rmse_daily_increment"],
        "holdout_mae_daily_increment": holdout_metrics["mae_daily_increment"],
        "holdout_final_bias": holdout_metrics["final_cumulative_bias"],
        "fruit_anchor_error_vs_legacy": fruit_anchor_error,
        "canopy_collapse_days": canopy_collapse_days(
            moderate_run_df,
            lai_floor=canopy_lai_floor,
            leaf_floor=leaf_fraction_floor,
        ),
        "wet_condition_root_excess_penalty": wet_penalty,
        "mean_alloc_frac_fruit": _nanmean(moderate_run_df, "alloc_frac_fruit"),
        "mean_alloc_frac_leaf": _nanmean(moderate_run_df, "alloc_frac_leaf"),
        "mean_alloc_frac_stem": _nanmean(moderate_run_df, "alloc_frac_stem"),
        "mean_alloc_frac_root": _nanmean(moderate_run_df, "alloc_frac_root"),
        "final_lai": _nanlast(moderate_run_df, "LAI"),
        "final_total_dry_weight_floor_area": _nanlast(moderate_run_df, "total_dry_weight_g_m2"),
        "final_fruit_dry_weight_floor_area": float(pd.to_numeric(candidate_series, errors="coerce").dropna().iloc[-1]),
        "nonfinite_flag": int(not alloc.dropna().map(math.isfinite).all()),
        "invalid_run_flag": invalid_run_flag,
        "runtime_seconds": runtime_seconds,
        "calibration_score": _objective_score(calibration_metrics),
        "validation_series_csv": str(validation_path),
        "parameter_instability_score": math.nan,
        "calibration_rmse_cumulative_offset": calibration_metrics["yield_rmse_offset_adjusted"],
        "calibration_rmse_daily_increment": calibration_metrics["rmse_daily_increment"],
        "calibration_final_bias": calibration_metrics["final_cumulative_bias"],
    }


def _evaluate_observation_only_candidate(
    *,
    prepared_bundle: PreparedKnuBundle,
    candidate_label: str,
    split: CalibrationSplit,
    validation_dir: Path,
) -> dict[str, Any]:
    _, calibration_metrics = _window_bundle(
        prepared_bundle.workbook_validation_df,
        candidate_series=prepared_bundle.workbook_validation_df["estimated_cumulative_total_fruit_dry_weight_floor_area"],
        candidate_label="estimated",
        unit_label=prepared_bundle.data.observation_unit_label,
        start=split.calibration_start,
        end=split.calibration_end,
    )
    holdout_df, holdout_metrics = _window_bundle(
        prepared_bundle.workbook_validation_df,
        candidate_series=prepared_bundle.workbook_validation_df["estimated_cumulative_total_fruit_dry_weight_floor_area"],
        candidate_label="estimated",
        unit_label=prepared_bundle.data.observation_unit_label,
        start=split.holdout_start,
        end=split.holdout_end,
    )
    validation_path = validation_dir / f"{candidate_label}__{split.split_label}.csv"
    holdout_df.to_csv(validation_path, index=False)
    final_series = pd.to_numeric(holdout_df["estimated_cumulative_total_fruit_dry_weight_floor_area"], errors="coerce").dropna()
    return {
        "candidate_label": candidate_label,
        "architecture_id": "workbook_estimated_baseline",
        "policy_family": "observation_only",
        "split_label": split.split_label,
        "split_kind": split.split_kind,
        "reconstruction_mode": "",
        "selected_params_json": "{}",
        "initial_state_overrides_json": "{}",
        "reporting_basis": REPORTING_BASIS_FLOOR_AREA,
        "holdout_rmse_cumulative_offset": holdout_metrics["yield_rmse_offset_adjusted"],
        "holdout_mae_cumulative_offset": holdout_metrics["yield_mae_offset_adjusted"],
        "holdout_r2_cumulative_offset": holdout_metrics["yield_r2_offset_adjusted"],
        "holdout_rmse_daily_increment": holdout_metrics["rmse_daily_increment"],
        "holdout_mae_daily_increment": holdout_metrics["mae_daily_increment"],
        "holdout_final_bias": holdout_metrics["final_cumulative_bias"],
        "fruit_anchor_error_vs_legacy": math.nan,
        "canopy_collapse_days": math.nan,
        "wet_condition_root_excess_penalty": math.nan,
        "mean_alloc_frac_fruit": math.nan,
        "mean_alloc_frac_leaf": math.nan,
        "mean_alloc_frac_stem": math.nan,
        "mean_alloc_frac_root": math.nan,
        "final_lai": math.nan,
        "final_total_dry_weight_floor_area": math.nan,
        "final_fruit_dry_weight_floor_area": float(final_series.iloc[-1]) if not final_series.empty else math.nan,
        "nonfinite_flag": 0,
        "invalid_run_flag": 0,
        "runtime_seconds": 0.0,
        "calibration_score": _objective_score(calibration_metrics),
        "validation_series_csv": str(validation_path),
        "parameter_instability_score": 0.0,
        "calibration_rmse_cumulative_offset": calibration_metrics["yield_rmse_offset_adjusted"],
        "calibration_rmse_daily_increment": calibration_metrics["rmse_daily_increment"],
        "calibration_final_bias": calibration_metrics["final_cumulative_bias"],
    }


def _parameter_stability(calibration_results_df: pd.DataFrame) -> pd.DataFrame:
    records: list[dict[str, Any]] = []
    for candidate_label, group in calibration_results_df.groupby("candidate_label"):
        params = [json.loads(text) for text in group["selected_params_json"].astype(str)]
        if not params or not params[0]:
            records.append(
                {
                    "candidate_label": candidate_label,
                    "parameter_name": "",
                    "mean_value": math.nan,
                    "std_value": math.nan,
                    "range_value": math.nan,
                    "parameter_instability_score": 0.0,
                    "overall_parameter_instability_score": 0.0,
                }
            )
            continue
        instability_values: list[float] = []
        start_idx = len(records)
        for parameter_name in params[0]:
            values = pd.Series([float(param[parameter_name]) for param in params], dtype=float)
            mean_value = float(values.mean())
            std_value = float(values.std(ddof=0))
            range_value = float(values.max() - values.min())
            instability = std_value / max(abs(mean_value), 1e-6)
            instability_values.append(instability)
            records.append(
                {
                    "candidate_label": candidate_label,
                    "parameter_name": parameter_name,
                    "mean_value": mean_value,
                    "std_value": std_value,
                    "range_value": range_value,
                    "parameter_instability_score": instability,
                    "overall_parameter_instability_score": math.nan,
                }
            )
        overall = max(instability_values) if instability_values else 0.0
        for idx in range(start_idx, len(records)):
            records[idx]["overall_parameter_instability_score"] = overall
    return pd.DataFrame(records)


def _winner_stability(holdout_results_df: pd.DataFrame) -> pd.DataFrame:
    scored = holdout_results_df.copy()
    scored["holdout_score"] = (
        -1.2 * pd.to_numeric(scored["holdout_rmse_cumulative_offset"], errors="coerce")
        -0.7 * pd.to_numeric(scored["holdout_rmse_daily_increment"], errors="coerce")
        -0.6 * pd.to_numeric(scored["fruit_anchor_error_vs_legacy"], errors="coerce").fillna(0.0) * 20.0
        -1.0 * pd.to_numeric(scored["canopy_collapse_days"], errors="coerce").fillna(0.0) * 5.0
        -1.0 * pd.to_numeric(scored["wet_condition_root_excess_penalty"], errors="coerce").fillna(0.0) * 20.0
    )
    winners = (
        scored.sort_values(["split_label", "holdout_score"], ascending=[True, False])
        .groupby("split_label", as_index=False)
        .first()[["split_label", "candidate_label", "architecture_id", "holdout_score"]]
    )
    counts = (
        winners.groupby(["candidate_label", "architecture_id"], as_index=False)
        .agg(win_count=("split_label", "count"), mean_holdout_score=("holdout_score", "mean"))
    )
    counts["win_fraction"] = counts["win_count"] / max(len(winners), 1)
    return counts.sort_values(["win_count", "mean_holdout_score"], ascending=[False, False]).reset_index(drop=True)


def _write_holdout_overlay(
    *,
    output_root: Path,
    holdout_results_df: pd.DataFrame,
    plot_spec_path: Path,
    daily_plot_spec_path: Path,
) -> None:
    from stomatal_optimiaztion.domains.tomato.tomics.plotting import render_partition_compare_bundle

    blocked = holdout_results_df[holdout_results_df["split_label"].eq("blocked_holdout")].copy()
    runs: dict[str, pd.DataFrame] = {}
    for _, row in blocked.iterrows():
        frame = pd.read_csv(row["validation_series_csv"])
        runs[str(row["candidate_label"])] = validation_overlay_frame(
            frame,
            source_label=str(row["candidate_label"]),
        )
    if not runs:
        return
    render_partition_compare_bundle(
        runs=runs,
        out_path=output_root / "holdout_overlay.png",
        spec_path=plot_spec_path,
    )
    render_partition_compare_bundle(
        runs=runs,
        out_path=output_root / "daily_increment_holdout_overlay.png",
        spec_path=daily_plot_spec_path,
    )


def run_calibration_suite(
    config: dict[str, Any],
    *,
    repo_root: Path,
    config_path: Path,
) -> CalibrationArtifacts:
    prepared_bundle = prepare_knu_bundle(config, repo_root=repo_root, config_path=config_path)
    specs, _, metadata = load_candidate_specs(config=config, repo_root=repo_root, config_path=config_path)
    calibration_cfg = _as_dict(config.get("calibration"))
    output_root = ensure_dir(
        _resolve_config_path(
            calibration_cfg.get("output_root", "out/tomics/validation/knu/fairness/calibration"),
            repo_root=repo_root,
            config_path=config_path,
        )
    )
    validation_dir = ensure_dir(output_root / "validation_runs")
    canopy_lai_floor = float(calibration_cfg.get("canopy_lai_floor", 2.0))
    leaf_fraction_floor = float(calibration_cfg.get("leaf_fraction_floor", 0.18))
    wet_theta_threshold = float(calibration_cfg.get("wet_theta_threshold", 0.75))
    splits = build_calibration_splits(
        prepared_bundle.observed_df,
        calibration_end=prepared_bundle.calibration_end,
        rolling_window_days=int(calibration_cfg.get("rolling_window_days", 4)),
    )
    parameter_grid = _parameter_grid(config)

    legacy_base_config = load_config(specs["shipped_tomics"].base_config_path)
    legacy_row = _legacy_candidate_row(legacy_base_config)
    budgets = [
        build_calibration_budget(
            candidate_label=spec.candidate_label,
            candidate_row=spec.candidate_row or {"architecture_id": spec.architecture_id},
        )
        for spec in specs.values()
    ]

    calibration_rows: list[dict[str, Any]] = []
    holdout_rows: list[dict[str, Any]] = []
    for split in splits:
        legacy_reconstruction = reconstruct_hidden_state(
            architecture_row=legacy_row,
            base_config=legacy_base_config,
            forcing_csv_path=prepared_bundle.scenarios["moderate"].forcing_csv_path,
            theta_center=float(prepared_bundle.scenarios["moderate"].summary.get("theta_mean", 0.65)),
            observed_df=prepared_bundle.observed_df,
            calibration_end=split.calibration_end,
            repo_root=repo_root,
            unit_label=prepared_bundle.data.observation_unit_label,
        )
        legacy_reference_cfg = configure_candidate_run(
            copy.deepcopy(legacy_base_config),
            forcing_csv_path=prepared_bundle.scenarios["moderate"].forcing_csv_path,
            theta_center=float(prepared_bundle.scenarios["moderate"].summary.get("theta_mean", 0.65)),
            row=legacy_row,
            initial_state_overrides=legacy_reconstruction.initial_state_overrides,
        )
        legacy_reference_df = run_tomato_legacy_pipeline(legacy_reference_cfg, repo_root=repo_root)

        for spec in specs.values():
            if spec.is_observation_only:
                row = _evaluate_observation_only_candidate(
                    prepared_bundle=prepared_bundle,
                    candidate_label=spec.candidate_label,
                    split=split,
                    validation_dir=validation_dir,
                )
                calibration_rows.append(dict(row))
                holdout_rows.append(dict(row))
                continue

            assert spec.candidate_row is not None
            assert spec.base_config_path is not None
            reconstruction = reconstruct_hidden_state(
                architecture_row=spec.candidate_row,
                base_config=load_config(spec.base_config_path),
                forcing_csv_path=prepared_bundle.scenarios["moderate"].forcing_csv_path,
                theta_center=float(prepared_bundle.scenarios["moderate"].summary.get("theta_mean", 0.65)),
                observed_df=prepared_bundle.observed_df,
                calibration_end=split.calibration_end,
                repo_root=repo_root,
                unit_label=prepared_bundle.data.observation_unit_label,
            )
            initial_state_overrides = dict(reconstruction.initial_state_overrides)
            initial_state_overrides["reconstruction_mode"] = reconstruction.mode
            candidates_for_split: list[dict[str, Any]] = []
            for parameter_values in parameter_grid:
                row = _evaluate_model_candidate(
                    repo_root=repo_root,
                    prepared_bundle=prepared_bundle,
                    candidate_label=spec.candidate_label,
                    candidate_row=spec.candidate_row,
                    base_config_path=spec.base_config_path,
                    split=split,
                    parameter_values=parameter_values,
                    initial_state_overrides=initial_state_overrides,
                    legacy_reference_df=legacy_reference_df,
                    wet_theta_threshold=wet_theta_threshold,
                    canopy_lai_floor=canopy_lai_floor,
                    leaf_fraction_floor=leaf_fraction_floor,
                    validation_dir=validation_dir,
                )
                candidates_for_split.append(row)
            best_row = max(candidates_for_split, key=lambda item: float(item["calibration_score"]))
            calibration_rows.append(dict(best_row))
            holdout_rows.append(dict(best_row))

    calibration_results_df = pd.DataFrame(calibration_rows).sort_values(["split_label", "candidate_label"]).reset_index(drop=True)
    holdout_results_df = pd.DataFrame(holdout_rows).sort_values(["split_label", "candidate_label"]).reset_index(drop=True)
    parameter_stability_df = _parameter_stability(calibration_results_df)
    stability_map = (
        parameter_stability_df.groupby("candidate_label", as_index=False)["overall_parameter_instability_score"].max()
        if not parameter_stability_df.empty and "overall_parameter_instability_score" in parameter_stability_df.columns
        else pd.DataFrame(columns=["candidate_label", "overall_parameter_instability_score"])
    )
    if not stability_map.empty:
        holdout_results_df = holdout_results_df.merge(stability_map, on="candidate_label", how="left")
        holdout_results_df["parameter_instability_score"] = holdout_results_df["overall_parameter_instability_score"]
        holdout_results_df = holdout_results_df.drop(columns=["overall_parameter_instability_score"])
    winner_stability_df = _winner_stability(
        holdout_results_df[holdout_results_df["candidate_label"].isin(["shipped_tomics", "current_selected", "promoted_selected"])]
    )

    manifest = {
        "reporting_basis": REPORTING_BASIS_FLOOR_AREA,
        "plants_per_m2": prepared_bundle.data_contract.plants_per_m2,
        "observation_unit_label": prepared_bundle.data.observation_unit_label,
        "base_config_path": metadata["base_config_path"],
        "candidate_architecture_ids": {key: spec.architecture_id for key, spec in specs.items()},
        "budget": [budget.to_dict() for budget in budgets],
        "splits": [
            {
                "split_label": split.split_label,
                "split_kind": split.split_kind,
                "calibration_start": str(split.calibration_start.date()),
                "calibration_end": str(split.calibration_end.date()),
                "holdout_start": str(split.holdout_start.date()),
                "holdout_end": str(split.holdout_end.date()),
            }
            for split in splits
        ],
        "shared_parameter_grid": parameter_grid,
        "reconstruction_modes": ["minimal_scalar_init", "cohort_aware_init", "buffer_aware_init"],
        "theta_proxy_mode": "bucket_irrigated",
        "theta_proxy_scenarios": ["moderate", "wet"],
    }
    write_json(output_root / "calibration_manifest.json", manifest)
    calibration_results_df.to_csv(output_root / "calibration_results.csv", index=False)
    holdout_results_df.to_csv(output_root / "holdout_results.csv", index=False)
    winner_stability_df.to_csv(output_root / "winner_stability.csv", index=False)
    parameter_stability_df.to_csv(output_root / "parameter_stability.csv", index=False)

    plot_spec_path = _resolve_config_path(
        calibration_cfg.get("holdout_overlay_spec", "configs/plotkit/tomics/knu_yield_fit_overlay.yaml"),
        repo_root=repo_root,
        config_path=config_path,
    )
    daily_plot_spec_path = _resolve_config_path(
        calibration_cfg.get("daily_increment_overlay_spec", "configs/plotkit/tomics/knu_daily_increment_overlay.yaml"),
        repo_root=repo_root,
        config_path=config_path,
    )
    _write_holdout_overlay(
        output_root=output_root,
        holdout_results_df=holdout_results_df,
        plot_spec_path=plot_spec_path,
        daily_plot_spec_path=daily_plot_spec_path,
    )

    return CalibrationArtifacts(
        output_root=output_root,
        calibration_manifest=manifest,
        calibration_results_df=calibration_results_df,
        holdout_results_df=holdout_results_df,
        winner_stability_df=winner_stability_df,
        parameter_stability_df=parameter_stability_df,
    )


__all__ = [
    "CalibrationArtifacts",
    "CalibrationBudget",
    "CalibrationSplit",
    "CandidateSpec",
    "build_calibration_splits",
    "load_candidate_specs",
    "run_calibration_suite",
]
