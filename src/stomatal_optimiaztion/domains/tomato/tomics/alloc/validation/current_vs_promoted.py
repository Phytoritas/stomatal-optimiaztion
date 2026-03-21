from __future__ import annotations

import copy
import json
import math
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.partitioning import (
    PromotedAllocatorConfig,
    ResearchArchitectureConfig,
    equation_traceability_rows,
    promoted_traceability_rows,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.core import (
    ensure_dir,
    load_config,
    write_json,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.pipelines import (
    resolve_repo_root,
    run_tomato_legacy_pipeline,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.knu_data import (
    KnuValidationData,
    load_knu_validation_data,
    resample_forcing,
    write_knu_manifest,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.data_contract import (
    KnuDataContractPaths,
    resolve_knu_data_contract,
    write_data_contract_manifest,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.artifact_sync import (
    CanonicalWinnerIds,
    write_canonical_winner_manifest,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.metrics import (
    REPORTING_BASIS_FLOOR_AREA,
    canopy_collapse_days,
    compute_validation_bundle,
    model_floor_area_cumulative_total_fruit,
    observed_floor_area_yield,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.theta_proxy import (
    DEFAULT_SCENARIOS,
    apply_theta_substrate_proxy,
    theta_proxy_summary,
)
from stomatal_optimiaztion.domains.tomato.tomics.plotting import (
    render_architecture_summary_bundle,
    render_main_effects_bundle,
    render_partition_compare_bundle,
)


CURRENT_RESEARCH_POLICIES = {"tomics_alloc_research", "tomics_architecture_research"}
PROMOTED_RESEARCH_POLICIES = {"tomics_promoted_research", "tomics_alloc_promoted_research"}
CURRENT_FACTOR_COLUMNS = [
    "fruit_structure_mode",
    "fruit_partition_mode",
    "vegetative_demand_mode",
    "reserve_buffer_mode",
    "fruit_feedback_mode",
    "sla_mode",
    "maintenance_mode",
    "canopy_governor_mode",
    "root_representation_mode",
    "thorp_root_correction_mode",
    "temporal_coupling_mode",
    "allocation_scheme",
]
PROMOTED_FACTOR_COLUMNS = [
    "optimizer_mode",
    "vegetative_prior_mode",
    "leaf_marginal_mode",
    "stem_marginal_mode",
    "root_marginal_mode",
    "fruit_feedback_mode",
    "reserve_buffer_mode",
    "canopy_governor_mode",
    "temporal_mode",
    "thorp_root_correction_mode",
    "allocation_scheme",
]


@dataclass(frozen=True, slots=True)
class PreparedThetaScenario:
    scenario_id: str
    minute_df: pd.DataFrame
    hourly_df: pd.DataFrame
    forcing_csv_path: Path
    summary: dict[str, object]


@dataclass(frozen=True, slots=True)
class PreparedKnuBundle:
    data: KnuValidationData
    data_contract: KnuDataContractPaths
    observed_df: pd.DataFrame
    validation_start: pd.Timestamp
    validation_end: pd.Timestamp
    calibration_end: pd.Timestamp
    holdout_start: pd.Timestamp
    prepared_root: Path
    scenarios: dict[str, PreparedThetaScenario]
    workbook_validation_df: pd.DataFrame
    workbook_metrics: dict[str, object]
    manifest_summary: dict[str, object]


def _as_dict(raw: object) -> dict[str, Any]:
    if isinstance(raw, dict):
        return {str(key): value for key, value in raw.items()}
    return {}


def _as_list(raw: object) -> list[Any]:
    if isinstance(raw, list):
        return list(raw)
    return []


def _finite(raw: object, *, default: float) -> float:
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return float(default)
    if not math.isfinite(value):
        return float(default)
    return float(value)


def _nanmean(frame: pd.DataFrame, column: str, *, default: float = math.nan) -> float:
    if column not in frame.columns:
        return float(default)
    series = pd.to_numeric(frame[column], errors="coerce")
    if series.dropna().empty:
        return float(default)
    return float(series.mean())


def _nanlast(frame: pd.DataFrame, column: str, *, default: float = math.nan) -> float:
    if column not in frame.columns or frame.empty:
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


def _base_tomics_params(config: dict[str, Any]) -> dict[str, object]:
    pipeline_cfg = _as_dict(config.get("pipeline"))
    params = _as_dict(pipeline_cfg.get("partition_policy_params"))
    tomics = _as_dict(pipeline_cfg.get("tomics"))
    if tomics:
        params = {**params, **tomics}
    return params


def _plot_spec_path(config: dict[str, Any], *, repo_root: Path, key: str, default_path: Path) -> Path:
    plots_cfg = _as_dict(config.get("plots"))
    raw = Path(str(plots_cfg.get(key, default_path)))
    if raw.is_absolute():
        return raw
    return (repo_root / raw).resolve()


def _score_row(row: pd.Series) -> float:
    if int(row.get("nonfinite_flag", 0)) or int(row.get("negative_fraction_flag", 0)):
        return -1_000_000.0
    if str(row.get("fruit_load_regime", "observed_baseline")) != "observed_baseline":
        return math.nan
    return float(
        -1.2 * _finite(row.get("yield_rmse_offset_adjusted"), default=1_000.0)
        -0.7 * _finite(row.get("yield_mae_offset_adjusted"), default=1_000.0)
        -0.5 * abs(_finite(row.get("yield_bias_offset_adjusted"), default=1_000.0))
        -0.6 * _finite(row.get("peak_daily_increment_error"), default=1_000.0)
        -0.8 * abs(_finite(row.get("final_window_error"), default=1_000.0))
        -35.0 * _finite(row.get("fruit_anchor_error_vs_legacy"), default=1.0)
        -18.0 * _finite(row.get("canopy_collapse_days"), default=10.0)
        -80.0 * _finite(row.get("wet_condition_root_excess_penalty"), default=1.0)
        -20.0 * _finite(row.get("sum_to_one_error"), default=1.0)
        +0.03 * _finite(row.get("final_fruit_dry_weight_floor_area"), default=0.0)
    )


def _window_metrics(
    observed_df: pd.DataFrame,
    *,
    candidate_series: pd.Series,
    candidate_label: str,
    unit_label: str,
    start: pd.Timestamp,
    end: pd.Timestamp,
) -> dict[str, float | bool | str]:
    mask = (observed_df["date"] >= start) & (observed_df["date"] <= end)
    bundle = compute_validation_bundle(
        observed_df.loc[mask].copy(),
        candidate_series=candidate_series.loc[mask],
        candidate_label=candidate_label,
        unit_declared_in_observation_file=unit_label,
    )
    return bundle.metrics


def prepare_knu_bundle(
    config: dict[str, Any],
    *,
    repo_root: Path,
    config_path: Path,
) -> PreparedKnuBundle:
    validation_cfg = _as_dict(config.get("validation"))
    data_contract = resolve_knu_data_contract(
        validation_cfg=validation_cfg,
        repo_root=repo_root,
        config_path=config_path,
    )
    prepared_root = _resolve_config_path(
        validation_cfg.get("prepared_output_root", "out/knu_longrun"),
        repo_root=repo_root,
        config_path=config_path,
    )
    prepared_root.mkdir(parents=True, exist_ok=True)
    resample_rule = str(validation_cfg.get("resample_rule", "1h"))
    theta_mode = str(validation_cfg.get("theta_proxy_mode", "bucket_irrigated"))
    scenario_ids = [str(value) for value in _as_list(validation_cfg.get("theta_proxy_scenarios"))] or list(DEFAULT_SCENARIOS)

    data = load_knu_validation_data(
        forcing_path=data_contract.forcing_path,
        yield_path=data_contract.yield_path,
    )
    manifest_summary = write_knu_manifest(
        output_root=prepared_root,
        forcing_df=data.forcing_df,
        yield_df=data.yield_df,
        measured_column=data.measured_column,
        estimated_column=data.estimated_column,
        observation_unit_label=data.observation_unit_label,
        forcing_source_path=data_contract.forcing_path,
        yield_source_path=data_contract.yield_path,
        resample_rule=resample_rule,
    )
    data_contract_manifest = write_data_contract_manifest(
        output_root=prepared_root,
        contract=data_contract,
        data=data,
    )
    observed_df = observed_floor_area_yield(
        data.yield_df,
        measured_column=data.measured_column,
        estimated_column=data.estimated_column,
    )
    validation_start = pd.Timestamp(observed_df["date"].min()).normalize()
    validation_end = pd.Timestamp(observed_df["date"].max()).normalize()
    if validation_cfg.get("calibration_end"):
        calibration_end = pd.Timestamp(validation_cfg["calibration_end"]).normalize()
    else:
        midpoint = len(observed_df) // 2
        calibration_end = pd.Timestamp(observed_df["date"].iloc[max(midpoint - 1, 0)]).normalize()
    holdout_start = calibration_end + pd.Timedelta(days=1)

    workbook_bundle = compute_validation_bundle(
        observed_df.copy(),
        candidate_series=observed_df["estimated_cumulative_total_fruit_dry_weight_floor_area"],
        candidate_label="estimated",
        unit_declared_in_observation_file=data.observation_unit_label,
    )
    observed_df = workbook_bundle.merged_df.copy()

    prepared_dir = ensure_dir(prepared_root / "prepared_forcing")
    scenarios: dict[str, PreparedThetaScenario] = {}
    for scenario_id in scenario_ids:
        minute_df = apply_theta_substrate_proxy(data.forcing_df, mode=theta_mode, scenario=scenario_id)
        hourly_df = resample_forcing(minute_df, freq=resample_rule)
        hourly_path = prepared_dir / f"knu_longrun_{theta_mode}_{scenario_id}_{resample_rule.replace('/', '_')}.csv"
        hourly_df.to_csv(hourly_path, index=False)
        scenarios[scenario_id] = PreparedThetaScenario(
            scenario_id=scenario_id,
            minute_df=minute_df,
            hourly_df=hourly_df,
            forcing_csv_path=hourly_path,
            summary=theta_proxy_summary(minute_df),
        )

    return PreparedKnuBundle(
        data=data,
        data_contract=data_contract,
        observed_df=observed_df,
        validation_start=validation_start,
        validation_end=validation_end,
        calibration_end=calibration_end,
        holdout_start=holdout_start,
        prepared_root=prepared_root,
        scenarios=scenarios,
        workbook_validation_df=workbook_bundle.merged_df,
        workbook_metrics=workbook_bundle.metrics,
        manifest_summary={**manifest_summary, "data_contract_manifest_json": str(data_contract_manifest)},
    )


def _normalize_current_axes(row: dict[str, object]) -> dict[str, object]:
    temporal_map = {
        "daily_alloc": "daily_marginal_daily_alloc",
        "hourly_source_daily_alloc": "subdaily_signal_daily_integral_alloc",
        "buffered_daily": "subdaily_signal_daily_integral_alloc_lowpass",
    }
    return {
        "optimizer_mode": "bounded_static_current",
        "vegetative_prior_mode": "current_tomics_prior",
        "leaf_marginal_mode": "canopy_only",
        "stem_marginal_mode": "support_only",
        "root_marginal_mode": "water_only_gate",
        "temporal_mode": temporal_map.get(str(row.get("temporal_coupling_mode", "daily_alloc")), "daily_marginal_daily_alloc"),
    }


def _normalize_promoted_axes(row: dict[str, object]) -> dict[str, object]:
    config = PromotedAllocatorConfig.from_params(row, scheme=str(row.get("allocation_scheme", "4pool")))
    public = config.to_public_dict()
    public.update(
        {
            "fruit_structure_mode": config.fruit_structure_mode,
            "fruit_partition_mode": config.fruit_partition_mode,
            "vegetative_demand_mode": config.vegetative_demand_mode,
            "sla_mode": config.sla_mode,
            "maintenance_mode": config.maintenance_mode,
            "temporal_coupling_mode": config.temporal_coupling_mode,
        }
    )
    return public


def _current_params_from_row(row: dict[str, object]) -> dict[str, object]:
    params = ResearchArchitectureConfig.from_params(row, scheme=str(row.get("allocation_scheme", "4pool"))).to_public_dict()
    params["fruit_load_multiplier"] = float(row.get("fruit_load_multiplier", params.get("fruit_load_multiplier", 1.0)))
    return params


def _promoted_params_from_row(row: dict[str, object]) -> dict[str, object]:
    params = PromotedAllocatorConfig.from_params(row, scheme=str(row.get("allocation_scheme", "4pool"))).to_public_dict()
    params["fruit_load_multiplier"] = float(row.get("fruit_load_multiplier", params.get("fruit_load_multiplier", 1.0)))
    return params


def configure_candidate_run(
    base_config: dict[str, Any],
    *,
    forcing_csv_path: Path,
    theta_center: float,
    row: dict[str, object],
    initial_state_overrides: dict[str, object] | None = None,
) -> dict[str, Any]:
    config = copy.deepcopy(base_config)
    pipeline_cfg = config.setdefault("pipeline", {})
    forcing_cfg = config.setdefault("forcing", {})
    if not isinstance(pipeline_cfg, dict) or not isinstance(forcing_cfg, dict):
        raise TypeError("pipeline/forcing config sections must be mappings.")

    forcing_cfg["csv_path"] = str(forcing_csv_path)
    forcing_cfg["default_dt_s"] = 3600
    forcing_cfg.pop("repeat_cycles", None)
    forcing_cfg.pop("max_steps", None)
    pipeline_cfg["model"] = "tomato_legacy"
    pipeline_cfg["theta_substrate"] = float(theta_center)
    pipeline_cfg["partition_policy"] = str(row["partition_policy"])
    pipeline_cfg["allocation_scheme"] = str(row.get("allocation_scheme", "4pool"))
    pipeline_cfg["fixed_lai"] = row.get("fixed_lai")
    if initial_state_overrides:
        pipeline_cfg["initial_state_overrides"] = copy.deepcopy(initial_state_overrides)

    base_params = _base_tomics_params(config)
    if str(row["partition_policy"]) in PROMOTED_RESEARCH_POLICIES:
        params = _promoted_params_from_row(row)
    elif str(row["partition_policy"]) in CURRENT_RESEARCH_POLICIES:
        params = _current_params_from_row(row)
    else:
        params = {
            "wet_root_cap": float(row.get("wet_root_cap", base_params.get("wet_root_cap", 0.10))),
            "dry_root_cap": float(row.get("dry_root_cap", base_params.get("dry_root_cap", 0.18))),
            "lai_target_center": float(row.get("lai_target_center", base_params.get("lai_target_center", 2.75))),
            "leaf_fraction_of_shoot_base": float(
                row.get("leaf_fraction_of_shoot_base", base_params.get("leaf_fraction_of_shoot_base", 0.70))
            ),
            "fruit_load_multiplier": float(row.get("fruit_load_multiplier", 1.0)),
            "thorp_root_blend": float(row.get("thorp_root_blend", base_params.get("thorp_root_blend", 1.0))),
        }
    pipeline_cfg["partition_policy_params"] = {**base_params, **params}
    return config


def _legacy_cache_key(row: dict[str, object]) -> tuple[str, str, float]:
    return (
        str(row["theta_proxy_scenario"]),
        str(row.get("fruit_load_regime", "observed_baseline")),
        float(row.get("fruit_load_multiplier", 1.0)),
    )


def _current_metrics_defaults(row: dict[str, object]) -> dict[str, object]:
    defaults = {name: row.get(name, "") for name in CURRENT_FACTOR_COLUMNS}
    defaults.update(_normalize_current_axes(row))
    return defaults


def _promoted_metrics_defaults(row: dict[str, object]) -> dict[str, object]:
    promoted = _normalize_promoted_axes(row)
    current_like = {
        "fruit_structure_mode": promoted["fruit_structure_mode"],
        "fruit_partition_mode": promoted["fruit_partition_mode"],
        "vegetative_demand_mode": promoted["vegetative_demand_mode"],
        "reserve_buffer_mode": promoted["reserve_buffer_mode"],
        "fruit_feedback_mode": promoted["fruit_feedback_mode"],
        "sla_mode": promoted["sla_mode"],
        "maintenance_mode": promoted["maintenance_mode"],
        "canopy_governor_mode": promoted["canopy_governor_mode"],
        "root_representation_mode": "bounded_explicit_root",
        "thorp_root_correction_mode": promoted["thorp_root_correction_mode"],
        "temporal_coupling_mode": promoted["temporal_coupling_mode"],
        "allocation_scheme": promoted["allocation_scheme"],
    }
    return {**current_like, **promoted}


def _validation_series_rows(
    merged_df: pd.DataFrame,
    *,
    row: dict[str, object],
    candidate_label: str,
) -> pd.DataFrame:
    frame = merged_df.copy()
    frame["architecture_id"] = str(row["architecture_id"])
    frame["policy_family"] = str(row["policy_family"])
    frame["stage"] = str(row["stage"])
    frame["theta_proxy_mode"] = str(row["theta_proxy_mode"])
    frame["theta_proxy_scenario"] = str(row["theta_proxy_scenario"])
    frame["fruit_load_regime"] = str(row.get("fruit_load_regime", "observed_baseline"))
    frame["candidate_label"] = candidate_label
    return frame


def _compute_run_metrics(
    row: dict[str, object],
    *,
    run_df: pd.DataFrame | None,
    legacy_df: pd.DataFrame | None,
    prepared_bundle: PreparedKnuBundle,
    runtime_seconds: float,
    study_cfg: dict[str, Any],
    candidate_label: str,
) -> tuple[dict[str, object], pd.DataFrame]:
    reporting_fields = {
        "architecture_id": str(row["architecture_id"]),
        "policy_family": str(row["policy_family"]),
        "stage": str(row["stage"]),
        "reporting_basis": REPORTING_BASIS_FLOOR_AREA,
        "unit_declared_in_observation_file": prepared_bundle.data.observation_unit_label,
        "theta_proxy_mode": str(row["theta_proxy_mode"]),
        "theta_proxy_scenario": str(row["theta_proxy_scenario"]),
        "fruit_load_regime": str(row.get("fruit_load_regime", "observed_baseline")),
        "partition_policy": str(row.get("partition_policy", "")),
    }
    factor_fields = (
        _promoted_metrics_defaults(row)
        if str(row.get("policy_family")) == "promoted"
        else _current_metrics_defaults(row)
    )

    if run_df is None:
        merged = prepared_bundle.workbook_validation_df.copy()
        metrics = {
            **reporting_fields,
            **factor_fields,
            "mean_alloc_frac_fruit": math.nan,
            "mean_alloc_frac_leaf": math.nan,
            "mean_alloc_frac_stem": math.nan,
            "mean_alloc_frac_root": math.nan,
            "final_lai": math.nan,
            "final_total_dry_weight_floor_area": math.nan,
            "final_fruit_dry_weight_floor_area": float(
                merged["estimated_cumulative_total_fruit_dry_weight_floor_area"].iloc[-1]
            ),
            "fruit_anchor_error_vs_legacy": math.nan,
            "canopy_collapse_days": math.nan,
            "mean_theta_substrate": math.nan,
            "mean_water_supply_stress": math.nan,
            "wet_condition_root_excess_penalty": math.nan,
            "mean_leaf_canopy_return_proxy": math.nan,
            "mean_root_gate_activation": math.nan,
            "mean_stem_support_signal": math.nan,
            "nonfinite_flag": 0,
            "negative_fraction_flag": 0,
            "sum_to_one_error": math.nan,
            "runtime_seconds": 0.0,
            **prepared_bundle.workbook_metrics,
        }
        metrics["score"] = _score_row(pd.Series(metrics))
        return metrics, _validation_series_rows(merged, row=row, candidate_label=candidate_label)

    alloc = pd.to_numeric(
        run_df[["alloc_frac_fruit", "alloc_frac_leaf", "alloc_frac_stem", "alloc_frac_root"]].stack(),
        errors="coerce",
    )
    validation_df = model_floor_area_cumulative_total_fruit(run_df)
    validation_df = validation_df[
        (validation_df["date"] >= prepared_bundle.validation_start)
        & (validation_df["date"] <= prepared_bundle.validation_end)
    ].reset_index(drop=True)
    bundle = compute_validation_bundle(
        prepared_bundle.observed_df.copy(),
        candidate_series=validation_df["model_cumulative_total_fruit_dry_weight_floor_area"],
        candidate_label=candidate_label,
        unit_declared_in_observation_file=prepared_bundle.data.observation_unit_label,
    )
    calibration_metrics = _window_metrics(
        prepared_bundle.observed_df,
        candidate_series=validation_df["model_cumulative_total_fruit_dry_weight_floor_area"],
        candidate_label=candidate_label,
        unit_label=prepared_bundle.data.observation_unit_label,
        start=prepared_bundle.validation_start,
        end=prepared_bundle.calibration_end,
    )
    holdout_metrics = _window_metrics(
        prepared_bundle.observed_df,
        candidate_series=validation_df["model_cumulative_total_fruit_dry_weight_floor_area"],
        candidate_label=candidate_label,
        unit_label=prepared_bundle.data.observation_unit_label,
        start=prepared_bundle.holdout_start,
        end=prepared_bundle.validation_end,
    )

    wet_theta_threshold = float(study_cfg.get("wet_theta_threshold", 0.75))
    wet_root_cap = float(row.get("wet_root_cap", 0.10))
    mean_root = _nanmean(run_df, "alloc_frac_root", default=0.0)
    mean_theta = _nanmean(run_df, "theta_substrate", default=math.nan)
    wet_penalty = max(mean_root - wet_root_cap, 0.0) if mean_theta >= wet_theta_threshold else 0.0
    fruit_anchor_error = math.nan
    if legacy_df is not None:
        fruit_anchor_error = abs(
            _nanmean(run_df, "alloc_frac_fruit", default=math.nan)
            - _nanmean(legacy_df, "alloc_frac_fruit", default=math.nan)
        )

    metrics = {
        **reporting_fields,
        **factor_fields,
        "mean_alloc_frac_fruit": _nanmean(run_df, "alloc_frac_fruit"),
        "mean_alloc_frac_leaf": _nanmean(run_df, "alloc_frac_leaf"),
        "mean_alloc_frac_stem": _nanmean(run_df, "alloc_frac_stem"),
        "mean_alloc_frac_root": mean_root,
        "final_lai": _nanlast(run_df, "LAI"),
        "final_total_dry_weight_floor_area": _nanlast(run_df, "total_dry_weight_g_m2"),
        "final_fruit_dry_weight_floor_area": _nanlast(
            validation_df,
            "model_cumulative_total_fruit_dry_weight_floor_area",
        ),
        "fruit_anchor_error_vs_legacy": fruit_anchor_error,
        "canopy_collapse_days": canopy_collapse_days(
            run_df,
            lai_floor=float(study_cfg.get("canopy_lai_floor", 2.0)),
            leaf_floor=float(study_cfg.get("leaf_fraction_floor", 0.18)),
        ),
        "mean_theta_substrate": mean_theta,
        "mean_water_supply_stress": _nanmean(run_df, "water_supply_stress"),
        "wet_condition_root_excess_penalty": wet_penalty,
        "mean_leaf_canopy_return_proxy": _nanmean(run_df, "promoted_leaf_canopy_return_proxy", default=0.0),
        "mean_root_gate_activation": _nanmean(run_df, "promoted_root_gate_activation", default=0.0),
        "mean_stem_support_signal": _nanmean(run_df, "promoted_stem_support_signal", default=0.0),
        "nonfinite_flag": int(not alloc.dropna().map(math.isfinite).all()),
        "negative_fraction_flag": int((alloc.dropna() < -1e-9).any()),
        "sum_to_one_error": abs(
            (
                _nanmean(run_df, "alloc_frac_fruit", default=0.0)
                + _nanmean(run_df, "alloc_frac_leaf", default=0.0)
                + _nanmean(run_df, "alloc_frac_stem", default=0.0)
                + _nanmean(run_df, "alloc_frac_root", default=0.0)
            )
            - 1.0
        ),
        "runtime_seconds": runtime_seconds,
        **bundle.metrics,
        "yield_rmse_offset_adjusted_calibration": calibration_metrics["yield_rmse_offset_adjusted"],
        "yield_rmse_offset_adjusted_holdout": holdout_metrics["yield_rmse_offset_adjusted"],
        "yield_r2_offset_adjusted_calibration": calibration_metrics["yield_r2_offset_adjusted"],
        "yield_r2_offset_adjusted_holdout": holdout_metrics["yield_r2_offset_adjusted"],
    }
    metrics["final_fruit_dry_weight"] = metrics["final_fruit_dry_weight_floor_area"]
    metrics["score"] = _score_row(pd.Series(metrics))
    return metrics, _validation_series_rows(bundle.merged_df, row=row, candidate_label=candidate_label)


def _interaction_summary(metrics_df: pd.DataFrame, *, factor_columns: list[str]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for factor in factor_columns:
        if factor not in metrics_df.columns:
            continue
        for level, group in metrics_df.groupby(factor, dropna=False):
            rows.append(
                {
                    "factor": factor,
                    "level": level,
                    "count": int(group.shape[0]),
                    "mean_score": float(pd.to_numeric(group["score"], errors="coerce").mean()),
                }
            )
    return pd.DataFrame(rows)


def _load_current_base_config(path: Path) -> dict[str, Any]:
    return load_config(path)


def _current_stage1_rows(current_cfg: dict[str, Any], scenario_ids: list[str]) -> list[dict[str, object]]:
    stage1_cfg = _as_dict(current_cfg.get("stage1"))
    candidates = _as_list(stage1_cfg.get("candidates"))
    rows: list[dict[str, object]] = []
    for candidate in candidates:
        base = ResearchArchitectureConfig.from_params(candidate, scheme=str(_as_dict(candidate).get("allocation_scheme", "4pool"))).to_public_dict()
        base_row = {**_as_dict(candidate), **base}
        for scenario_id in scenario_ids:
            rows.append(
                {
                    **base_row,
                    "stage": "stage1",
                    "policy_family": "current",
                    "theta_proxy_mode": "bucket_irrigated",
                    "theta_proxy_scenario": scenario_id,
                    "fruit_load_regime": "observed_baseline",
                    "fruit_load_multiplier": float(base_row.get("fruit_load_multiplier", 1.0)),
                }
            )
    return rows


def _current_candidate_map(current_cfg: dict[str, Any]) -> dict[str, dict[str, object]]:
    mapping: dict[str, dict[str, object]] = {}
    for row in _current_stage1_rows(current_cfg, ["moderate"]):
        mapping[str(row["architecture_id"])] = row
    return mapping


def _select_shortlist(
    metrics_df: pd.DataFrame,
    *,
    count: int,
    policy_family: str,
) -> list[str]:
    subset = metrics_df[
        (metrics_df["policy_family"] == policy_family)
        & metrics_df["fruit_load_regime"].eq("observed_baseline")
        & metrics_df["score"].notna()
    ].copy()
    if subset.empty:
        return []
    ranked = (
        subset.groupby("architecture_id", as_index=False)["score"]
        .mean()
        .sort_values("score", ascending=False)
        .head(count)
    )
    return [str(value) for value in ranked["architecture_id"].tolist()]


def _current_stage2_rows(current_cfg: dict[str, Any], shortlist_ids: list[str]) -> list[dict[str, object]]:
    if not shortlist_ids:
        return []
    candidate_map = _current_candidate_map(current_cfg)
    axes = _as_dict(_as_dict(current_cfg.get("stage2")).get("parameter_axes"))
    rows: list[dict[str, object]] = []
    for architecture_id in shortlist_ids:
        base = dict(candidate_map[architecture_id])
        base["stage"] = "stage2"
        rows.append(dict(base))
        for axis, values in axes.items():
            if not isinstance(values, list):
                continue
            if axis.startswith("storage_") and str(base.get("reserve_buffer_mode")) == "off":
                continue
            if axis.startswith("fruit_feedback_") and str(base.get("fruit_feedback_mode")) == "off":
                continue
            if axis == "thorp_root_blend" and str(base.get("thorp_root_correction_mode")) == "off":
                continue
            base_value = base.get(axis)
            for value in values:
                if base_value is not None and math.isclose(float(value), float(base_value), abs_tol=1e-9):
                    continue
                row = dict(base)
                row[axis] = float(value)
                row["architecture_id"] = f"{architecture_id}__{axis}_{str(value).replace('.', 'p')}"
                rows.append(row)
    return rows


def _default_current_selected(current_cfg: dict[str, Any]) -> dict[str, object]:
    return _current_candidate_map(current_cfg).get("kuijpers_hybrid_candidate", _current_stage1_rows(current_cfg, ["moderate"])[0])


def _load_previous_selected_current(
    config: dict[str, Any],
    *,
    repo_root: Path,
    config_path: Path,
    current_cfg: dict[str, Any],
) -> dict[str, object]:
    current_section = _as_dict(config.get("current"))
    raw = current_section.get("prior_selected_architecture_json", "out/tomics_allocation_factorial/selected_architecture.json")
    path = _resolve_config_path(raw, repo_root=repo_root, config_path=config_path)
    if path.exists():
        payload = json.loads(path.read_text(encoding="utf-8"))
        selected = _as_dict(payload.get("selected_architecture"))
        if selected:
            selected["policy_family"] = "current"
            selected["theta_proxy_mode"] = "bucket_irrigated"
            selected["theta_proxy_scenario"] = "moderate"
            selected["fruit_load_regime"] = "observed_baseline"
            return selected
    fallback = dict(_default_current_selected(current_cfg))
    fallback["thorp_root_blend"] = 1.0
    return fallback


def _current_stage3_rows(
    current_cfg: dict[str, Any],
    *,
    selected_row: dict[str, object],
    scenario_ids: list[str],
    fruit_load_regimes: dict[str, float],
) -> list[dict[str, object]]:
    defaults = ResearchArchitectureConfig.from_params({}, scheme="4pool").to_public_dict()
    baselines = [
        {
            "architecture_id": "legacy_control",
            "partition_policy": "legacy",
            "policy_family": "control",
            **defaults,
        },
        {
            "architecture_id": "raw_thorp_like_control",
            "partition_policy": "thorp_fruit_veg",
            "policy_family": "control",
            **defaults,
        },
        {
            "architecture_id": "shipped_tomics_control",
            "partition_policy": "tomics",
            "policy_family": "control",
            **defaults,
        },
        dict(selected_row),
    ]
    rows: list[dict[str, object]] = []
    for base in baselines:
        for scenario_id in scenario_ids:
            for fruit_load_regime, multiplier in fruit_load_regimes.items():
                rows.append(
                    {
                        **base,
                        "stage": "stage3",
                        "theta_proxy_mode": "bucket_irrigated",
                        "theta_proxy_scenario": scenario_id,
                        "fruit_load_regime": fruit_load_regime,
                        "fruit_load_multiplier": float(multiplier),
                    }
                )
    return rows


def _promoted_candidate_templates(current_selected: dict[str, object]) -> list[dict[str, object]]:
    shared = {
        "partition_policy": "tomics_promoted_research",
        "policy_family": "promoted",
        "allocation_scheme": "4pool",
        "wet_root_cap": 0.10,
        "dry_root_cap": 0.18,
        "lai_target_center": 2.75,
        "leaf_fraction_of_shoot_base": 0.70,
        "beta": 3.0,
        "tau_alloc_days": 3.0,
        "thorp_root_blend": 0.5,
        "canopy_governor_mode": "lai_band",
        "optimizer_mode": "prior_weighted_softmax",
        "vegetative_prior_mode": "current_tomics_prior",
        "leaf_marginal_mode": "canopy_only",
        "stem_marginal_mode": "support_only",
        "root_marginal_mode": "water_only_gate",
        "fruit_feedback_mode": "off",
        "reserve_buffer_mode": "off",
        "temporal_mode": "daily_marginal_daily_alloc",
        "thorp_root_correction_mode": "bounded",
    }
    return [
        {"architecture_id": "shipped_tomics_control", "partition_policy": "tomics", "policy_family": "control", **shared},
        {"architecture_id": "current_kuijpers_candidate_control", "policy_family": "control", **current_selected},
        {"architecture_id": "constrained_prior_base", **shared},
        {
            "architecture_id": "constrained_prior_lowpass",
            **shared,
            "optimizer_mode": "prior_weighted_softmax_plus_lowpass",
            "temporal_mode": "subdaily_signal_daily_integral_alloc_lowpass",
        },
        {
            "architecture_id": "constrained_leaf_canopy",
            **shared,
            "leaf_marginal_mode": "canopy_plus_weak_sink_penalty",
        },
        {
            "architecture_id": "constrained_stem_support_transport",
            **shared,
            "stem_marginal_mode": "support_plus_transport",
        },
        {
            "architecture_id": "constrained_root_multistress",
            **shared,
            "root_marginal_mode": "greenhouse_multistress_gate",
        },
        {
            "architecture_id": "constrained_full_lsr",
            **shared,
            "leaf_marginal_mode": "canopy_plus_turnover",
            "stem_marginal_mode": "support_transport_positioning",
            "root_marginal_mode": "greenhouse_multistress_gate_plus_saturation",
            "canopy_governor_mode": "lai_band_plus_leaf_floor",
        },
        {
            "architecture_id": "constrained_full_plus_storage",
            **shared,
            "leaf_marginal_mode": "canopy_plus_turnover",
            "stem_marginal_mode": "support_transport_positioning",
            "root_marginal_mode": "greenhouse_multistress_gate_plus_saturation",
            "reserve_buffer_mode": "tomsim_storage_pool",
            "canopy_governor_mode": "lai_band_plus_leaf_floor",
        },
        {
            "architecture_id": "constrained_full_plus_feedback",
            **shared,
            "leaf_marginal_mode": "canopy_plus_weak_sink_penalty",
            "stem_marginal_mode": "support_transport_positioning",
            "root_marginal_mode": "greenhouse_multistress_gate_plus_saturation",
            "reserve_buffer_mode": "vanthoor_carbohydrate_buffer",
            "fruit_feedback_mode": "dekoning_source_demand_proxy",
            "temporal_mode": "subdaily_signal_daily_integral_alloc",
            "canopy_governor_mode": "lai_band_plus_leaf_floor",
        },
    ]


def _promoted_p1_rows(current_selected: dict[str, object], scenario_ids: list[str]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for template in _promoted_candidate_templates(current_selected):
        for scenario_id in scenario_ids:
            rows.append(
                {
                    **template,
                    "stage": "p1",
                    "theta_proxy_mode": "bucket_irrigated",
                    "theta_proxy_scenario": scenario_id,
                    "fruit_load_regime": "observed_baseline",
                    "fruit_load_multiplier": float(template.get("fruit_load_multiplier", 1.0)),
                }
            )
    return rows


def _promoted_p2_rows(shortlist_ids: list[str], *, p1_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    base_map = {str(row["architecture_id"]): row for row in p1_rows if str(row.get("policy_family")) == "promoted" and str(row.get("theta_proxy_scenario")) == "moderate"}
    value_map = {
        "wet_root_cap": [0.08, 0.12],
        "dry_root_cap": [0.15, 0.21],
        "lai_target_center": [2.5, 3.0],
        "leaf_fraction_of_shoot_base": [0.65, 0.75],
        "beta": [1.0, 5.0],
        "tau_alloc_days": [1.0, 5.0],
        "thorp_root_blend": [0.0, 1.0],
        "reserve_capacity_g_m2": [10.0, 20.0],
        "reserve_carryover_fraction": [0.60, 0.90],
        "buffer_capacity_g_m2": [12.0, 24.0],
        "fruit_abort_threshold": [0.75, 0.90],
        "fruit_abort_slope": [1.5, 3.5],
        "low_sink_threshold": [0.60, 0.80],
        "low_sink_slope": [0.10, 0.30],
        "rootzone_multistress_weight": [0.15, 0.45],
        "rootzone_saturation_weight": [0.10, 0.35],
    }
    rows: list[dict[str, object]] = []
    for architecture_id in shortlist_ids:
        base = dict(base_map[architecture_id])
        base["stage"] = "p2"
        base["theta_proxy_scenario"] = "moderate"
        rows.append(dict(base))
        axis_priority = [
            "wet_root_cap",
            "dry_root_cap",
            "lai_target_center",
        ]
        if str(base.get("reserve_buffer_mode")) == "tomsim_storage_pool":
            axis_priority.extend(["reserve_capacity_g_m2", "reserve_carryover_fraction"])
        elif str(base.get("reserve_buffer_mode")) == "vanthoor_carbohydrate_buffer":
            axis_priority.extend(["buffer_capacity_g_m2", "reserve_carryover_fraction"])
        if str(base.get("fruit_feedback_mode")) != "off":
            axis_priority.extend(["fruit_abort_threshold", "fruit_abort_slope"])
        if str(base.get("root_marginal_mode")) != "water_only_gate":
            axis_priority.extend(["rootzone_multistress_weight", "rootzone_saturation_weight"])
        if str(base.get("leaf_marginal_mode")) != "canopy_only":
            axis_priority.extend(["low_sink_threshold", "low_sink_slope"])
        if str(base.get("thorp_root_correction_mode")) != "off":
            axis_priority.append("thorp_root_blend")
        axis_priority.extend(["leaf_fraction_of_shoot_base", "beta", "tau_alloc_days"])
        chosen_axes: list[str] = []
        for axis in axis_priority:
            if axis in value_map and axis not in chosen_axes:
                chosen_axes.append(axis)
            if len(chosen_axes) == 6:
                break
        for axis in chosen_axes:
            values = value_map[axis]
            for value in values:
                row = dict(base)
                row[axis] = float(value)
                row["architecture_id"] = f"{architecture_id}__{axis}_{str(value).replace('.', 'p')}"
                rows.append(row)
    return rows


def _promoted_p3_rows(
    *,
    current_selected: dict[str, object],
    promoted_selected: dict[str, object],
    scenario_ids: list[str],
    fruit_load_regimes: dict[str, float],
) -> list[dict[str, object]]:
    baselines = [
        {"architecture_id": "legacy_control", "partition_policy": "legacy", "policy_family": "control"},
        {"architecture_id": "shipped_tomics_control", "partition_policy": "tomics", "policy_family": "control"},
        dict(current_selected),
        dict(promoted_selected),
    ]
    defaults = ResearchArchitectureConfig.from_params({}, scheme="4pool").to_public_dict()
    rows: list[dict[str, object]] = []
    for base in baselines:
        merged = {**defaults, **base}
        for scenario_id in scenario_ids:
            for fruit_load_regime, multiplier in fruit_load_regimes.items():
                rows.append(
                    {
                        **merged,
                        "stage": "p3",
                        "theta_proxy_mode": "bucket_irrigated",
                        "theta_proxy_scenario": scenario_id,
                        "fruit_load_regime": fruit_load_regime,
                        "fruit_load_multiplier": float(multiplier),
                    }
                )
    return rows


def _execute_rows(
    rows: list[dict[str, object]],
    *,
    prepared_bundle: PreparedKnuBundle,
    base_config: dict[str, Any],
    study_cfg: dict[str, Any],
    legacy_cache: dict[tuple[str, str, float], pd.DataFrame],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    metrics_rows: list[dict[str, object]] = []
    validation_frames: list[pd.DataFrame] = []
    for row in rows:
        scenario = prepared_bundle.scenarios[str(row["theta_proxy_scenario"])]
        theta_center = float(scenario.summary.get("theta_mean", _finite(row.get("wet_root_cap"), default=0.65)))
        if str(row.get("partition_policy")) == "workbook_estimated_baseline":
            metrics, validation_df = _compute_run_metrics(
                row,
                run_df=None,
                legacy_df=None,
                prepared_bundle=prepared_bundle,
                runtime_seconds=0.0,
                study_cfg=study_cfg,
                candidate_label="estimated",
            )
        else:
            run_config = configure_candidate_run(
                base_config,
                forcing_csv_path=scenario.forcing_csv_path,
                theta_center=theta_center,
                row=row,
            )
            start = time.perf_counter()
            run_df = run_tomato_legacy_pipeline(run_config)
            runtime = time.perf_counter() - start
            cache_key = _legacy_cache_key(row)
            if str(row.get("partition_policy")) == "legacy":
                legacy_cache[cache_key] = run_df.copy()
            legacy_df = legacy_cache.get(cache_key)
            if legacy_df is None:
                legacy_config = configure_candidate_run(
                    base_config,
                    forcing_csv_path=scenario.forcing_csv_path,
                    theta_center=theta_center,
                    row={**row, "partition_policy": "legacy"},
                )
                legacy_df = run_tomato_legacy_pipeline(legacy_config)
                legacy_cache[cache_key] = legacy_df.copy()
            metrics, validation_df = _compute_run_metrics(
                row,
                run_df=run_df,
                legacy_df=legacy_df,
                prepared_bundle=prepared_bundle,
                runtime_seconds=runtime,
                study_cfg=study_cfg,
                candidate_label="model",
            )
        metrics_rows.append(metrics)
        validation_frames.append(validation_df)
    return pd.DataFrame(metrics_rows), pd.concat(validation_frames, ignore_index=True)


def _ranking(
    metrics_df: pd.DataFrame,
    *,
    policy_family: str,
    stages: list[str],
) -> pd.DataFrame:
    subset = metrics_df[
        (metrics_df["policy_family"] == policy_family)
        & metrics_df["stage"].isin(stages)
        & metrics_df["fruit_load_regime"].eq("observed_baseline")
    ].copy()
    if subset.empty:
        return pd.DataFrame(columns=["architecture_id", "mean_score"])
    return (
        subset.groupby("architecture_id", as_index=False)
        .agg(
            mean_score=("score", "mean"),
            mean_yield_rmse_offset_adjusted=("yield_rmse_offset_adjusted", "mean"),
            mean_final_fruit_dry_weight_floor_area=("final_fruit_dry_weight_floor_area", "mean"),
            mean_canopy_collapse_days=("canopy_collapse_days", "mean"),
            mean_fruit_anchor_error_vs_legacy=("fruit_anchor_error_vs_legacy", "mean"),
        )
        .sort_values("mean_score", ascending=False)
    )


def _study_bundle_payload(
    *,
    selected_architecture_id: str,
    selected_row: dict[str, object],
    ranking_df: pd.DataFrame,
    shortlist_ids: list[str],
    design_counts: dict[str, int],
    recommendation: str,
    rationale_lines: list[str],
) -> dict[str, object]:
    top_score = math.nan if ranking_df.empty else float(ranking_df.iloc[0]["mean_score"])
    return {
        "selected_architecture_id": selected_architecture_id,
        "selected_architecture": selected_row,
        "shortlisted_architecture_ids": shortlist_ids,
        "design_counts": design_counts,
        "selection_basis": "Highest mean score on observed-baseline KNU validation with biological penalty guardrails.",
        "recommendation": recommendation,
        "top_mean_score": top_score,
        "rationale_lines": rationale_lines,
    }


def _decision_bundle_markdown(
    *,
    title: str,
    selected_architecture_id: str,
    ranking_df: pd.DataFrame,
    design_counts: dict[str, int],
    recommendation: str,
    rationale_lines: list[str],
) -> str:
    score = math.nan if ranking_df.empty else float(ranking_df.iloc[0]["mean_score"])
    rmse = math.nan if ranking_df.empty else float(ranking_df.iloc[0]["mean_yield_rmse_offset_adjusted"])
    lines = [
        f"# {title}",
        "",
        f"Selected architecture: `{selected_architecture_id}`",
        f"- Mean score: {score:.4f}" if math.isfinite(score) else "- Mean score: n/a",
        f"- Mean offset-adjusted RMSE: {rmse:.4f}" if math.isfinite(rmse) else "- Mean offset-adjusted RMSE: n/a",
        f"- Recommendation: {recommendation}",
        "",
        "Design counts:",
    ]
    for key, value in design_counts.items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "Rationale:"])
    lines.extend([f"- {line}" for line in rationale_lines])
    return "\n".join(lines) + "\n"


def _render_study_plots(
    *,
    output_root: Path,
    metrics_df: pd.DataFrame,
    interaction_df: pd.DataFrame,
    summary_spec_path: Path,
    main_effects_spec_path: Path,
) -> dict[str, dict[str, str]]:
    summary_artifacts = render_architecture_summary_bundle(
        metrics_df=metrics_df,
        out_path=output_root / "summary_plot.png",
        spec_path=summary_spec_path,
    )
    main_effects_artifacts = render_main_effects_bundle(
        interactions_df=interaction_df,
        out_path=output_root / "main_effects.png",
        spec_path=main_effects_spec_path,
    )
    return {
        "summary_plot": summary_artifacts.to_summary(),
        "main_effects_plot": main_effects_artifacts.to_summary(),
    }


def run_current_factorial_knu(
    config: dict[str, Any],
    *,
    repo_root: Path,
    config_path: Path,
    prepared_bundle: PreparedKnuBundle,
) -> dict[str, object]:
    current_section = _as_dict(config.get("current"))
    current_cfg_path = _resolve_config_path(
        current_section.get("base_config", "configs/exp/tomics_allocation_factorial.yaml"),
        repo_root=repo_root,
        config_path=config_path,
    )
    current_cfg = _load_current_base_config(current_cfg_path)
    base_config = copy.deepcopy(current_cfg)
    base_config.setdefault("pipeline", {})
    base_config["pipeline"]["fixed_lai"] = current_section.get("fixed_lai")

    output_root = ensure_dir(
        _resolve_config_path(
            _as_dict(config.get("paths")).get("current_output_root", "out/tomics_current_factorial_knu"),
            repo_root=repo_root,
            config_path=config_path,
        )
    )
    scenario_ids = [str(value) for value in _as_list(current_section.get("theta_proxy_scenarios"))] or list(prepared_bundle.scenarios)
    fruit_load_regimes = {
        str(key): float(value)
        for key, value in _as_dict(current_section.get("fruit_load_regimes", {"observed_baseline": 1.0, "high_fruit_load": 1.25})).items()
    }
    summary_spec_path = _plot_spec_path(
        config,
        repo_root=repo_root,
        key="current_summary_plot_spec",
        default_path=repo_root / "configs" / "plotkit" / "tomics" / "allocation_factorial_summary.yaml",
    )
    main_effects_spec_path = _plot_spec_path(
        config,
        repo_root=repo_root,
        key="current_main_effects_plot_spec",
        default_path=repo_root / "configs" / "plotkit" / "tomics" / "allocation_factorial_main_effects.yaml",
    )
    yield_spec_path = _plot_spec_path(
        config,
        repo_root=repo_root,
        key="yield_fit_overlay_spec",
        default_path=repo_root / "configs" / "plotkit" / "tomics" / "knu_yield_fit_overlay.yaml",
    )

    stage1_rows = _current_stage1_rows(current_cfg, scenario_ids)
    legacy_cache: dict[tuple[str, str, float], pd.DataFrame] = {}
    study_cfg = {
        "wet_theta_threshold": float(current_section.get("wet_theta_threshold", 0.75)),
        "canopy_lai_floor": float(current_section.get("canopy_lai_floor", 2.0)),
        "leaf_fraction_floor": float(current_section.get("leaf_fraction_floor", 0.18)),
    }
    stage1_metrics, validation_df = _execute_rows(
        stage1_rows,
        prepared_bundle=prepared_bundle,
        base_config=base_config,
        study_cfg=study_cfg,
        legacy_cache=legacy_cache,
    )
    shortlist_ids = _select_shortlist(
        stage1_metrics,
        count=int(current_section.get("shortlist_count", 2)),
        policy_family="current",
    )
    stage2_rows = _current_stage2_rows(current_cfg, shortlist_ids)
    stage2_metrics = pd.DataFrame()
    if stage2_rows:
        stage2_metrics, validation_stage2 = _execute_rows(
            stage2_rows,
            prepared_bundle=prepared_bundle,
            base_config=base_config,
            study_cfg=study_cfg,
            legacy_cache=legacy_cache,
        )
        validation_df = pd.concat([validation_df, validation_stage2], ignore_index=True)

    screening_metrics = pd.concat([stage1_metrics, stage2_metrics], ignore_index=True)
    ranking_df = _ranking(screening_metrics, policy_family="current", stages=["stage1", "stage2"])
    previous_selected = _load_previous_selected_current(
        config,
        repo_root=repo_root,
        config_path=config_path,
        current_cfg=current_cfg,
    )
    selected_architecture_id = (
        str(ranking_df.iloc[0]["architecture_id"])
        if not ranking_df.empty
        else str(previous_selected["architecture_id"])
    )
    selected_row = next(
        (
            row
            for row in stage2_rows + stage1_rows + [previous_selected]
            if str(row["architecture_id"]).startswith(selected_architecture_id)
        ),
        previous_selected,
    )
    stage3_rows = _current_stage3_rows(
        current_cfg,
        selected_row=selected_row,
        scenario_ids=scenario_ids,
        fruit_load_regimes=fruit_load_regimes,
    )
    stage3_metrics, validation_stage3 = _execute_rows(
        stage3_rows,
        prepared_bundle=prepared_bundle,
        base_config=base_config,
        study_cfg=study_cfg,
        legacy_cache=legacy_cache,
    )
    validation_df = pd.concat([validation_df, validation_stage3], ignore_index=True)

    metrics_df = pd.concat([screening_metrics, stage3_metrics], ignore_index=True)
    interaction_df = _interaction_summary(
        screening_metrics[screening_metrics["score"].notna()].copy(),
        factor_columns=CURRENT_FACTOR_COLUMNS,
    )
    plots = _render_study_plots(
        output_root=output_root,
        metrics_df=screening_metrics[screening_metrics["score"].notna()].copy(),
        interaction_df=interaction_df,
        summary_spec_path=summary_spec_path,
        main_effects_spec_path=main_effects_spec_path,
    )
    metrics_df.to_csv(output_root / "run_metrics.csv", index=False)
    validation_df.to_csv(output_root / "validation_vs_measured.csv", index=False)
    interaction_df.to_csv(output_root / "interaction_summary.csv", index=False)
    ranking_df.to_csv(output_root / "candidate_ranking.csv", index=False)
    pd.DataFrame(stage1_rows + stage2_rows + stage3_rows).to_csv(output_root / "design_table.csv", index=False)
    pd.DataFrame(equation_traceability_rows()).to_csv(output_root / "equation_traceability.csv", index=False)
    rationale_lines = [
        "Stage 1 replayed the merged current architecture study on actual KNU forcing with dry/moderate/wet substrate proxies.",
        "Stage 2 used the existing reduced one-at-a-time perturbation ladder around shortlisted current research candidates.",
        "Stage 3 confirmed legacy, raw THORP-like, shipped TOMICS, and the selected current research candidate across substrate proxy and fruit-load regimes.",
        "Selection remained research-only because the short observed window still limits promotion confidence.",
    ]
    payload = _study_bundle_payload(
        selected_architecture_id=selected_architecture_id,
        selected_row=selected_row,
        ranking_df=ranking_df,
        shortlist_ids=shortlist_ids,
        design_counts={"stage1": len(stage1_rows), "stage2": len(stage2_rows), "stage3": len(stage3_rows)},
        recommendation="research-only current actual-data benchmark",
        rationale_lines=rationale_lines,
    )
    write_json(output_root / "selected_architecture.json", payload)
    (output_root / "decision_bundle.md").write_text(
        _decision_bundle_markdown(
            title="Current TOMICS KNU Actual-Data Decision Bundle",
            selected_architecture_id=selected_architecture_id,
            ranking_df=ranking_df,
            design_counts=payload["design_counts"],
            recommendation=str(payload["recommendation"]),
            rationale_lines=rationale_lines,
        ),
        encoding="utf-8",
    )
    _write_study_validation_plots(
        study_root=output_root,
        validation_df=validation_df,
        selected_architecture_id=selected_architecture_id,
        shipped_architecture_id="shipped_tomics_control",
        spec_path=yield_spec_path,
    )
    return {
        "output_root": output_root,
        "metrics_df": metrics_df,
        "screening_metrics_df": screening_metrics,
        "validation_df": validation_df,
        "ranking_df": ranking_df,
        "selected_payload": payload,
        "plots": plots,
    }


def run_promoted_factorial_knu(
    config: dict[str, Any],
    *,
    repo_root: Path,
    config_path: Path,
    prepared_bundle: PreparedKnuBundle,
    current_selected: dict[str, object],
) -> dict[str, object]:
    promoted_section = _as_dict(config.get("promoted"))
    current_cfg_path = _resolve_config_path(
        promoted_section.get("base_config", "configs/exp/tomics_allocation_factorial.yaml"),
        repo_root=repo_root,
        config_path=config_path,
    )
    base_config = _load_current_base_config(current_cfg_path)
    base_config.setdefault("pipeline", {})
    base_config["pipeline"]["fixed_lai"] = promoted_section.get("fixed_lai")
    output_root = ensure_dir(
        _resolve_config_path(
            _as_dict(config.get("paths")).get("promoted_output_root", "out/tomics_promoted_factorial_knu"),
            repo_root=repo_root,
            config_path=config_path,
        )
    )
    scenario_ids = [str(value) for value in _as_list(promoted_section.get("theta_proxy_scenarios"))] or list(prepared_bundle.scenarios)
    fruit_load_regimes = {
        str(key): float(value)
        for key, value in _as_dict(promoted_section.get("fruit_load_regimes", {"observed_baseline": 1.0, "high_fruit_load": 1.25})).items()
    }
    summary_spec_path = _plot_spec_path(
        config,
        repo_root=repo_root,
        key="promoted_summary_plot_spec",
        default_path=repo_root / "configs" / "plotkit" / "tomics" / "allocation_factorial_summary.yaml",
    )
    main_effects_spec_path = _plot_spec_path(
        config,
        repo_root=repo_root,
        key="promoted_main_effects_plot_spec",
        default_path=repo_root / "configs" / "plotkit" / "tomics" / "allocation_factorial_main_effects.yaml",
    )
    yield_spec_path = _plot_spec_path(
        config,
        repo_root=repo_root,
        key="yield_fit_overlay_spec",
        default_path=repo_root / "configs" / "plotkit" / "tomics" / "knu_yield_fit_overlay.yaml",
    )
    study_cfg = {
        "wet_theta_threshold": float(promoted_section.get("wet_theta_threshold", 0.75)),
        "canopy_lai_floor": float(promoted_section.get("canopy_lai_floor", 2.0)),
        "leaf_fraction_floor": float(promoted_section.get("leaf_fraction_floor", 0.18)),
    }
    legacy_cache: dict[tuple[str, str, float], pd.DataFrame] = {}
    p0_rows = [
        {
            "architecture_id": "workbook_estimated_baseline",
            "partition_policy": "workbook_estimated_baseline",
            "policy_family": "workbook",
            "stage": "p0",
            "theta_proxy_mode": "bucket_irrigated",
            "theta_proxy_scenario": "moderate",
            "fruit_load_regime": "observed_baseline",
            "allocation_scheme": "4pool",
        },
        {
            "architecture_id": "legacy_control",
            "partition_policy": "legacy",
            "policy_family": "control",
            "stage": "p0",
            "theta_proxy_mode": "bucket_irrigated",
            "theta_proxy_scenario": "moderate",
            "fruit_load_regime": "observed_baseline",
            "allocation_scheme": "4pool",
        },
        {
            "architecture_id": "raw_thorp_like_control",
            "partition_policy": "thorp_fruit_veg",
            "policy_family": "control",
            "stage": "p0",
            "theta_proxy_mode": "bucket_irrigated",
            "theta_proxy_scenario": "moderate",
            "fruit_load_regime": "observed_baseline",
            "allocation_scheme": "4pool",
        },
        {
            "architecture_id": "shipped_tomics_control",
            "partition_policy": "tomics",
            "policy_family": "control",
            "stage": "p0",
            "theta_proxy_mode": "bucket_irrigated",
            "theta_proxy_scenario": "moderate",
            "fruit_load_regime": "observed_baseline",
            "allocation_scheme": "4pool",
        },
        {
            **dict(current_selected),
            "architecture_id": "current_kuijpers_candidate_control",
            "policy_family": "control",
            "stage": "p0",
            "theta_proxy_mode": "bucket_irrigated",
            "theta_proxy_scenario": "moderate",
            "fruit_load_regime": "observed_baseline",
        },
    ]
    p0_metrics, validation_df = _execute_rows(
        p0_rows,
        prepared_bundle=prepared_bundle,
        base_config=base_config,
        study_cfg=study_cfg,
        legacy_cache=legacy_cache,
    )
    p1_rows = _promoted_p1_rows(current_selected, scenario_ids)
    p1_metrics, validation_p1 = _execute_rows(
        p1_rows,
        prepared_bundle=prepared_bundle,
        base_config=base_config,
        study_cfg=study_cfg,
        legacy_cache=legacy_cache,
    )
    validation_df = pd.concat([validation_df, validation_p1], ignore_index=True)
    shortlist_ids = _select_shortlist(
        p1_metrics,
        count=int(promoted_section.get("shortlist_count", 3)),
        policy_family="promoted",
    )
    p2_rows = _promoted_p2_rows(shortlist_ids, p1_rows=p1_rows)
    p2_metrics, validation_p2 = _execute_rows(
        p2_rows,
        prepared_bundle=prepared_bundle,
        base_config=base_config,
        study_cfg=study_cfg,
        legacy_cache=legacy_cache,
    )
    validation_df = pd.concat([validation_df, validation_p2], ignore_index=True)
    screening_metrics = pd.concat([p0_metrics, p1_metrics, p2_metrics], ignore_index=True)
    ranking_df = _ranking(screening_metrics, policy_family="promoted", stages=["p1", "p2"])
    promoted_selected = next(
        row
        for row in p2_rows + p1_rows
        if str(row["architecture_id"]).startswith(str(ranking_df.iloc[0]["architecture_id"]) if not ranking_df.empty else "constrained_prior_base")
    )
    p3_rows = _promoted_p3_rows(
        current_selected=current_selected,
        promoted_selected=promoted_selected,
        scenario_ids=scenario_ids,
        fruit_load_regimes=fruit_load_regimes,
    )
    p3_metrics, validation_p3 = _execute_rows(
        p3_rows,
        prepared_bundle=prepared_bundle,
        base_config=base_config,
        study_cfg=study_cfg,
        legacy_cache=legacy_cache,
    )
    validation_df = pd.concat([validation_df, validation_p3], ignore_index=True)
    metrics_df = pd.concat([screening_metrics, p3_metrics], ignore_index=True)
    interaction_df = _interaction_summary(
        metrics_df[
            (metrics_df["policy_family"] == "promoted")
            & metrics_df["stage"].isin(["p1", "p2"])
            & metrics_df["score"].notna()
        ].copy(),
        factor_columns=PROMOTED_FACTOR_COLUMNS,
    )
    plots = _render_study_plots(
        output_root=output_root,
        metrics_df=metrics_df[
            (metrics_df["policy_family"] == "promoted")
            & metrics_df["stage"].isin(["p1", "p2"])
            & metrics_df["score"].notna()
        ].copy(),
        interaction_df=interaction_df,
        summary_spec_path=summary_spec_path,
        main_effects_spec_path=main_effects_spec_path,
    )
    metrics_df.to_csv(output_root / "run_metrics.csv", index=False)
    validation_df.to_csv(output_root / "validation_vs_measured.csv", index=False)
    interaction_df.to_csv(output_root / "interaction_summary.csv", index=False)
    ranking_df.to_csv(output_root / "candidate_ranking.csv", index=False)
    pd.DataFrame(p0_rows + p1_rows + p2_rows + p3_rows).to_csv(output_root / "design_table.csv", index=False)
    pd.DataFrame(
        equation_traceability_rows() + promoted_traceability_rows()
    ).drop_duplicates().to_csv(output_root / "equation_traceability.csv", index=False)
    rationale_lines = [
        "P0 ran workbook, legacy, raw THORP-like, shipped TOMICS, and the current selected control on actual KNU forcing.",
        "P1 screened ten curated structural families across dry, moderate, and wet substrate proxy scenarios.",
        "P2 used thirteen-run reduced perturbation ladders around each shortlisted promoted architecture.",
        "P3 confirmed legacy, shipped TOMICS, the current selected candidate, and the promoted selected candidate across substrate and fruit-load regimes.",
    ]
    payload = _study_bundle_payload(
        selected_architecture_id=str(promoted_selected["architecture_id"]),
        selected_row=promoted_selected,
        ranking_df=ranking_df,
        shortlist_ids=shortlist_ids,
        design_counts={"p0": len(p0_rows), "p1": len(p1_rows), "p2": len(p2_rows), "p3": len(p3_rows)},
        recommendation="research-only promoted allocator candidate",
        rationale_lines=rationale_lines,
    )
    write_json(output_root / "selected_architecture.json", payload)
    (output_root / "decision_bundle.md").write_text(
        _decision_bundle_markdown(
            title="Promoted TOMICS KNU Actual-Data Decision Bundle",
            selected_architecture_id=str(promoted_selected["architecture_id"]),
            ranking_df=ranking_df,
            design_counts=payload["design_counts"],
            recommendation=str(payload["recommendation"]),
            rationale_lines=rationale_lines,
        ),
        encoding="utf-8",
    )
    _write_study_validation_plots(
        study_root=output_root,
        validation_df=validation_df,
        selected_architecture_id=str(promoted_selected["architecture_id"]),
        shipped_architecture_id="shipped_tomics_control",
        spec_path=yield_spec_path,
    )
    return {
        "output_root": output_root,
        "metrics_df": metrics_df,
        "screening_metrics_df": metrics_df[
            metrics_df["stage"].isin(["p0", "p1", "p2"])
        ].copy(),
        "validation_df": validation_df,
        "ranking_df": ranking_df,
        "selected_payload": payload,
        "plots": plots,
    }


def _daily_source_frame(
    validation_df: pd.DataFrame,
    *,
    value_column: str,
    offset_column: str,
    increment_column: str,
) -> pd.DataFrame:
    out = pd.DataFrame({"datetime": pd.to_datetime(validation_df["date"])})
    out["cumulative_total_fruit_floor_area"] = pd.to_numeric(validation_df[value_column], errors="coerce")
    out["offset_adjusted_cumulative_total_fruit_floor_area"] = pd.to_numeric(validation_df[offset_column], errors="coerce")
    out["daily_increment_floor_area"] = pd.to_numeric(validation_df[increment_column], errors="coerce")
    return out.sort_values("datetime").drop_duplicates(subset=["datetime"], keep="last")


def _selected_validation_frame(
    validation_df: pd.DataFrame,
    architecture_id: str,
    *,
    candidate_label: str,
    theta_proxy_scenario: str = "moderate",
    fruit_load_regime: str = "observed_baseline",
) -> pd.DataFrame:
    subset = validation_df[
        validation_df["architecture_id"].eq(architecture_id)
        & validation_df["theta_proxy_scenario"].eq(theta_proxy_scenario)
        & validation_df["fruit_load_regime"].eq(fruit_load_regime)
    ].copy()
    subset = subset.sort_values("date")
    return _daily_source_frame(
        subset,
        value_column=f"{candidate_label}_cumulative_total_fruit_dry_weight_floor_area",
        offset_column=f"{candidate_label}_offset_adjusted",
        increment_column=f"{candidate_label}_daily_increment_floor_area",
    )


def _write_study_validation_plots(
    *,
    study_root: Path,
    validation_df: pd.DataFrame,
    selected_architecture_id: str,
    shipped_architecture_id: str,
    spec_path: Path,
) -> None:
    plots_dir = ensure_dir(study_root / "validation_plots")
    observed = validation_df[validation_df["architecture_id"].eq(selected_architecture_id)].copy()
    observed = observed.sort_values("date")
    runs = {
        "measured": _daily_source_frame(
            observed,
            value_column="measured_cumulative_total_fruit_dry_weight_floor_area",
            offset_column="measured_offset_adjusted",
            increment_column="measured_daily_increment_floor_area",
        ),
        "selected": _selected_validation_frame(validation_df, selected_architecture_id, candidate_label="model"),
        "shipped": _selected_validation_frame(validation_df, shipped_architecture_id, candidate_label="model"),
    }
    render_partition_compare_bundle(
        runs=runs,
        out_path=plots_dir / "yield_fit_overlay.png",
        spec_path=spec_path,
    )


def _comparison_scorecard(
    *,
    current_metrics_df: pd.DataFrame,
    promoted_metrics_df: pd.DataFrame,
    current_selected_id: str,
    promoted_selected_id: str,
) -> pd.DataFrame:
    score_rows: list[dict[str, object]] = []
    frames = [
        current_metrics_df[current_metrics_df["stage"].eq("stage3")].copy(),
        promoted_metrics_df[promoted_metrics_df["stage"].eq("p3")].copy(),
    ]
    combined = pd.concat(frames, ignore_index=True)
    combined = combined[combined["fruit_load_regime"].eq("observed_baseline")].copy()
    candidates = {
        "workbook_estimated": promoted_metrics_df[promoted_metrics_df["architecture_id"].eq("workbook_estimated_baseline")],
        "legacy": combined[combined["architecture_id"].eq("legacy_control")],
        "raw_thorp_like": combined[combined["architecture_id"].eq("raw_thorp_like_control")],
        "shipped_tomics": combined[combined["architecture_id"].eq("shipped_tomics_control")],
        "current_selected": combined[combined["architecture_id"].eq(current_selected_id)],
        "promoted_selected": combined[combined["architecture_id"].eq(promoted_selected_id)],
    }
    for label, frame in candidates.items():
        if frame.empty:
            continue
        score_rows.append(
            {
                "candidate_label": label,
                "architecture_id": str(frame["architecture_id"].iloc[0]),
                "mean_yield_rmse_offset_adjusted": float(pd.to_numeric(frame["yield_rmse_offset_adjusted"], errors="coerce").mean()),
                "mean_yield_r2_offset_adjusted": float(pd.to_numeric(frame["yield_r2_offset_adjusted"], errors="coerce").mean()),
                "max_canopy_collapse_days": float(pd.to_numeric(frame["canopy_collapse_days"], errors="coerce").max()),
                "max_wet_condition_root_excess_penalty": float(pd.to_numeric(frame["wet_condition_root_excess_penalty"], errors="coerce").max()),
                "mean_fruit_anchor_error_vs_legacy": float(pd.to_numeric(frame["fruit_anchor_error_vs_legacy"], errors="coerce").mean()),
                "mean_final_window_error": float(pd.to_numeric(frame["final_window_error"], errors="coerce").mean()),
            }
        )
    return pd.DataFrame(score_rows)


def write_side_by_side_bundle(
    config: dict[str, Any],
    *,
    repo_root: Path,
    config_path: Path,
    prepared_bundle: PreparedKnuBundle,
    current_result: dict[str, object],
    promoted_result: dict[str, object],
) -> dict[str, object]:
    output_root = ensure_dir(
        _resolve_config_path(
            _as_dict(config.get("paths")).get("comparison_output_root", "out/tomics_current_vs_promoted_knu"),
            repo_root=repo_root,
            config_path=config_path,
        )
    )
    comparison_summary_spec = _plot_spec_path(
        config,
        repo_root=repo_root,
        key="comparison_summary_plot_spec",
        default_path=repo_root / "configs" / "plotkit" / "tomics" / "knu_current_vs_promoted_summary.yaml",
    )
    yield_spec = _plot_spec_path(
        config,
        repo_root=repo_root,
        key="yield_fit_overlay_spec",
        default_path=repo_root / "configs" / "plotkit" / "tomics" / "knu_yield_fit_overlay.yaml",
    )
    allocation_spec = _plot_spec_path(
        config,
        repo_root=repo_root,
        key="allocation_behavior_overlay_spec",
        default_path=repo_root / "configs" / "plotkit" / "tomics" / "knu_allocation_behavior_overlay.yaml",
    )
    theta_spec = _plot_spec_path(
        config,
        repo_root=repo_root,
        key="theta_proxy_diagnostics_spec",
        default_path=repo_root / "configs" / "plotkit" / "tomics" / "knu_theta_proxy_diagnostics.yaml",
    )
    current_selected_id = str(_as_dict(current_result["selected_payload"])["selected_architecture_id"])
    promoted_selected_id = str(_as_dict(promoted_result["selected_payload"])["selected_architecture_id"])
    canonical_manifest = write_canonical_winner_manifest(
        output_root=output_root,
        winners=CanonicalWinnerIds(
            current_selected_architecture_id=current_selected_id,
            promoted_selected_architecture_id=promoted_selected_id,
        ),
    )
    canonical_winner_path = write_canonical_winner_manifest(
        output_root=output_root,
        winners=CanonicalWinnerIds(
            current_selected_architecture_id=current_selected_id,
            promoted_selected_architecture_id=promoted_selected_id,
        ),
    )

    scorecard_df = _comparison_scorecard(
        current_metrics_df=current_result["metrics_df"],
        promoted_metrics_df=promoted_result["metrics_df"],
        current_selected_id=current_selected_id,
        promoted_selected_id=promoted_selected_id,
    )
    scorecard_df["score"] = -pd.to_numeric(scorecard_df["mean_yield_rmse_offset_adjusted"], errors="coerce")
    scorecard_df["final_fruit_dry_weight"] = scorecard_df["mean_final_window_error"].abs().mul(-1.0)
    scorecard_df["canopy_collapse_days"] = scorecard_df["max_canopy_collapse_days"]
    scorecard_df.to_csv(output_root / "architecture_promotion_scorecard.csv", index=False)
    scorecard_df.to_csv(output_root / "comparison_summary.csv", index=False)

    summary_plot = render_architecture_summary_bundle(
        metrics_df=scorecard_df,
        out_path=output_root / "current_vs_promoted_plot.png",
        spec_path=comparison_summary_spec,
    ).to_summary()

    promoted_validation = promoted_result["validation_df"]
    current_validation = current_result["validation_df"]
    reference_validation = promoted_validation[
        promoted_validation["architecture_id"].eq("shipped_tomics_control")
        & promoted_validation["theta_proxy_scenario"].eq("moderate")
        & promoted_validation["fruit_load_regime"].eq("observed_baseline")
    ].copy()
    reference_validation = reference_validation.sort_values("date")
    runs = {
        "measured": _daily_source_frame(
            reference_validation,
            value_column="measured_cumulative_total_fruit_dry_weight_floor_area",
            offset_column="measured_offset_adjusted",
            increment_column="measured_daily_increment_floor_area",
        ),
        "workbook_estimated": _daily_source_frame(
            prepared_bundle.workbook_validation_df,
            value_column="estimated_cumulative_total_fruit_dry_weight_floor_area",
            offset_column="estimated_offset_adjusted",
            increment_column="estimated_daily_increment_floor_area",
        ),
        "shipped_tomics": _selected_validation_frame(promoted_validation, "shipped_tomics_control", candidate_label="model"),
        "current_selected": _selected_validation_frame(current_validation, current_selected_id, candidate_label="model"),
        "promoted_selected": _selected_validation_frame(promoted_validation, promoted_selected_id, candidate_label="model"),
    }
    yield_plot = render_partition_compare_bundle(
        runs=runs,
        out_path=output_root / "yield_fit_overlay.png",
        spec_path=yield_spec,
    ).to_summary()

    promoted_metrics_df = promoted_result["metrics_df"]
    moderate_rows = promoted_metrics_df[
        promoted_metrics_df["stage"].eq("p3")
        & promoted_metrics_df["theta_proxy_scenario"].eq("moderate")
        & promoted_metrics_df["fruit_load_regime"].eq("observed_baseline")
    ]
    allocation_runs: dict[str, pd.DataFrame] = {}
    for label, arch_id in {
        "shipped_tomics": "shipped_tomics_control",
        "current_selected": current_selected_id,
        "promoted_selected": promoted_selected_id,
    }.items():
        scenario_row = moderate_rows[moderate_rows["architecture_id"].eq(arch_id)]
        if scenario_row.empty and label == "current_selected":
            scenario_row = current_result["metrics_df"][
                current_result["metrics_df"]["stage"].eq("stage3")
                & current_result["metrics_df"]["theta_proxy_scenario"].eq("moderate")
                & current_result["metrics_df"]["fruit_load_regime"].eq("observed_baseline")
                & current_result["metrics_df"]["architecture_id"].eq(arch_id)
            ]
        if scenario_row.empty:
            continue
        scenario_id = str(scenario_row.iloc[0]["theta_proxy_scenario"])
        forcing_path = prepared_bundle.scenarios[scenario_id].forcing_csv_path
        base_cfg = load_config(_resolve_config_path("configs/exp/tomics_allocation_factorial.yaml", repo_root=repo_root, config_path=config_path))
        run_cfg = configure_candidate_run(
            base_cfg,
            forcing_csv_path=forcing_path,
            theta_center=float(prepared_bundle.scenarios[scenario_id].summary.get("theta_mean", 0.65)),
            row=scenario_row.iloc[0].to_dict(),
        )
        allocation_runs[label] = run_tomato_legacy_pipeline(run_cfg)
    allocation_plot = render_partition_compare_bundle(
        runs=allocation_runs,
        out_path=output_root / "allocation_behavior_overlay.png",
        spec_path=allocation_spec,
    ).to_summary()

    theta_runs = {
        scenario_id: pd.DataFrame(
            {
                "datetime": scenario.hourly_df["datetime"],
                "theta_substrate": scenario.hourly_df["theta_substrate"],
                "rootzone_multistress": scenario.hourly_df.get("rootzone_multistress", 0.0),
                "rootzone_saturation": scenario.hourly_df.get("rootzone_saturation", 0.0),
                "demand_index": scenario.hourly_df.get("demand_index", 0.0),
            }
        )
        for scenario_id, scenario in prepared_bundle.scenarios.items()
    }
    theta_plot = render_partition_compare_bundle(
        runs=theta_runs,
        out_path=output_root / "theta_proxy_diagnostics.png",
        spec_path=theta_spec,
    ).to_summary()

    shipped_rmse = float(scorecard_df.loc[scorecard_df["candidate_label"].eq("shipped_tomics"), "mean_yield_rmse_offset_adjusted"].iloc[0])
    current_rmse = float(scorecard_df.loc[scorecard_df["candidate_label"].eq("current_selected"), "mean_yield_rmse_offset_adjusted"].iloc[0])
    promoted_row = scorecard_df.loc[scorecard_df["candidate_label"].eq("promoted_selected")].iloc[0]
    promoted_rmse = float(promoted_row["mean_yield_rmse_offset_adjusted"])
    promoted_anchor = float(promoted_row["mean_fruit_anchor_error_vs_legacy"])
    promoted_collapse = float(promoted_row["max_canopy_collapse_days"])
    promoted_root = float(promoted_row["max_wet_condition_root_excess_penalty"])
    ready = (
        promoted_rmse < shipped_rmse
        and promoted_rmse < current_rmse
        and promoted_anchor <= 0.03
        and promoted_collapse <= 0.0
        and promoted_root <= 0.02
    )
    recommendation = "next shipped-default candidate" if ready else "research-only"
    recommendation_md = "\n".join(
        [
            "# TOMICS Promotion Recommendation",
            "",
            f"Recommendation: `{recommendation}`",
            f"- Current selected architecture ID: `{current_selected_id}`",
            f"- Promoted selected architecture ID: `{promoted_selected_id}`",
            "",
            "Decision basis:",
            f"- shipped TOMICS mean offset-adjusted RMSE: {shipped_rmse:.4f}",
            f"- current selected candidate mean offset-adjusted harvested-yield RMSE: {current_rmse:.4f}",
            f"- promoted selected candidate mean offset-adjusted harvested-yield RMSE: {promoted_rmse:.4f}",
            f"- promoted selected candidate mean fruit anchor error vs legacy: {promoted_anchor:.4f}",
            f"- promoted selected candidate max canopy collapse days: {promoted_collapse:.4f}",
            f"- promoted selected candidate max wet-condition root excess penalty: {promoted_root:.4f}",
            "",
            "The promoted allocator stays research-only unless it beats both shipped TOMICS and the current selected candidate on harvested-yield fit without violating tomato-first guardrails.",
        ]
    )
    (output_root / "promotion_recommendation.md").write_text(recommendation_md, encoding="utf-8")
    return {
        "output_root": output_root,
        "scorecard_df": scorecard_df,
        "recommendation": recommendation,
        "canonical_winner_path": str(canonical_winner_path),
        "summary_plot": summary_plot,
        "yield_fit_overlay": yield_plot,
        "allocation_behavior_overlay": allocation_plot,
        "theta_proxy_diagnostics": theta_plot,
        "canonical_winner_manifest": str(canonical_manifest),
    }


def run_current_vs_promoted_factorial(
    *,
    config_path: str | Path,
    mode: str = "both",
) -> dict[str, object]:
    resolved_config_path = Path(config_path).resolve()
    config = load_config(resolved_config_path)
    repo_root = resolve_repo_root(config, config_path=resolved_config_path)
    prepared_bundle = prepare_knu_bundle(config, repo_root=repo_root, config_path=resolved_config_path)
    mode_key = str(mode).strip().lower()
    if mode_key not in {"current", "promoted", "both"}:
        raise ValueError("mode must be one of: current, promoted, both")

    result: dict[str, object] = {
        "prepared_bundle": {
            "prepared_root": str(prepared_bundle.prepared_root),
            "manifest_summary": prepared_bundle.manifest_summary,
            "data_contract": {
                "forcing_path": str(prepared_bundle.data_contract.forcing_path),
                "yield_path": str(prepared_bundle.data_contract.yield_path),
                "forcing_source_kind": prepared_bundle.data_contract.forcing_source_kind,
                "yield_source_kind": prepared_bundle.data_contract.yield_source_kind,
            },
            "validation_start": str(prepared_bundle.validation_start.date()),
            "validation_end": str(prepared_bundle.validation_end.date()),
            "calibration_end": str(prepared_bundle.calibration_end.date()),
            "holdout_start": str(prepared_bundle.holdout_start.date()),
        }
    }
    current_result: dict[str, object] | None = None
    promoted_result: dict[str, object] | None = None
    if mode_key in {"current", "both"}:
        current_result = run_current_factorial_knu(
            config,
            repo_root=repo_root,
            config_path=resolved_config_path,
            prepared_bundle=prepared_bundle,
        )
        result["current"] = {
            "output_root": str(current_result["output_root"]),
            "selected_architecture_id": _as_dict(current_result["selected_payload"])["selected_architecture_id"],
        }
    if mode_key in {"promoted", "both"}:
        current_selected = (
            _as_dict(current_result["selected_payload"])["selected_architecture"]
            if current_result is not None
            else _load_previous_selected_current(
                config,
                repo_root=repo_root,
                config_path=resolved_config_path,
                current_cfg=_load_current_base_config(
                    _resolve_config_path("configs/exp/tomics_allocation_factorial.yaml", repo_root=repo_root, config_path=resolved_config_path)
                ),
            )
        )
        promoted_result = run_promoted_factorial_knu(
            config,
            repo_root=repo_root,
            config_path=resolved_config_path,
            prepared_bundle=prepared_bundle,
            current_selected=current_selected,
        )
        result["promoted"] = {
            "output_root": str(promoted_result["output_root"]),
            "selected_architecture_id": _as_dict(promoted_result["selected_payload"])["selected_architecture_id"],
        }
    if mode_key == "both" and current_result is not None and promoted_result is not None:
        comparison = write_side_by_side_bundle(
            config,
            repo_root=repo_root,
            config_path=resolved_config_path,
            prepared_bundle=prepared_bundle,
            current_result=current_result,
            promoted_result=promoted_result,
        )
        result["comparison"] = {
            "output_root": str(comparison["output_root"]),
            "recommendation": comparison["recommendation"],
        }
    return result


__all__ = [
    "PreparedKnuBundle",
    "PreparedThetaScenario",
    "configure_candidate_run",
    "prepare_knu_bundle",
    "run_current_factorial_knu",
    "run_current_vs_promoted_factorial",
    "run_promoted_factorial_knu",
    "write_side_by_side_bundle",
]
