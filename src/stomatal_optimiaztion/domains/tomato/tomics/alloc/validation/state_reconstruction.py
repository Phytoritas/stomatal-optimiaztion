from __future__ import annotations

import copy
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.alloc.core import ensure_dir, load_config
from stomatal_optimiaztion.domains.tomato.tomics.alloc.pipelines import run_tomato_legacy_pipeline
from stomatal_optimiaztion.domains.tomato.tomics.alloc.pipelines import resolve_repo_root
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.harvest_operator import (
    model_floor_area_cumulative_total_fruit,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.init_search import (
    build_reconstruction_candidates,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.observation_model import (
    compute_validation_bundle,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.current_vs_promoted import (
    configure_candidate_run,
    prepare_knu_bundle,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.parameter_budget import (
    load_fairness_candidates,
)
from stomatal_optimiaztion.domains.tomato.tomics.plotting import render_partition_compare_bundle


@dataclass(frozen=True, slots=True)
class ReconstructionResult:
    architecture_id: str
    mode: str
    candidate_label: str
    initial_state_overrides: dict[str, object]
    metrics: dict[str, float | str | bool]
    validation_df: pd.DataFrame
    run_df: pd.DataFrame


def _aligned_candidate_series(observed_df: pd.DataFrame, model_daily_df: pd.DataFrame) -> pd.Series:
    indexed = model_daily_df.set_index("date")
    return observed_df["date"].map(indexed["model_cumulative_total_fruit_dry_weight_floor_area"])


def _initial_fruit_mass(initial_state_overrides: dict[str, object]) -> float:
    if initial_state_overrides.get("W_fr") is not None:
        return float(initial_state_overrides["W_fr"])
    cohorts = initial_state_overrides.get("truss_cohorts")
    if isinstance(cohorts, list):
        total = 0.0
        for cohort in cohorts:
            if isinstance(cohort, dict):
                total += float(cohort.get("w_fr_cohort", 0.0))
        return total
    return 0.0


def _initial_snapshot(
    initial_state_overrides: dict[str, object],
) -> dict[str, float]:
    return {
        "lai": float(initial_state_overrides.get("LAI", math.nan))
        if initial_state_overrides.get("LAI") is not None
        else math.nan,
        "fruit_mass": _initial_fruit_mass(initial_state_overrides),
        "harvested_mass": float(initial_state_overrides.get("W_fr_harvested", 0.0)),
        "buffer_mass": float(initial_state_overrides.get("reserve_ch2o_g", 0.0))
        + float(initial_state_overrides.get("buffer_pool_g", 0.0)),
    }


def _reconstruction_metrics(
    *,
    observed_df: pd.DataFrame,
    model_daily_df: pd.DataFrame,
    run_df: pd.DataFrame,
    candidate_label: str,
    unit_label: str,
    initial_state_overrides: dict[str, object],
) -> tuple[pd.DataFrame, dict[str, float | str | bool]]:
    bundle = compute_validation_bundle(
        observed_df.copy(),
        candidate_series=_aligned_candidate_series(observed_df, model_daily_df),
        candidate_label=candidate_label,
        unit_declared_in_observation_file=unit_label,
    )
    snapshot = _initial_snapshot(initial_state_overrides)
    first_lai = float(pd.to_numeric(run_df.get("LAI"), errors="coerce").dropna().iloc[0]) if "LAI" in run_df else math.nan
    first_model_daily = model_daily_df.iloc[0] if not model_daily_df.empty else {}
    first_buffer = 0.0
    if {"reserve_pool_g_m2", "buffer_pool_g_m2"}.issubset(run_df.columns):
        first_buffer = float(
            pd.to_numeric(run_df["reserve_pool_g_m2"], errors="coerce").fillna(0.0).iloc[0]
            + pd.to_numeric(run_df["buffer_pool_g_m2"], errors="coerce").fillna(0.0).iloc[0]
        )
    harvest_alignment = abs(
        snapshot["harvested_mass"]
        - float(pd.to_numeric(observed_df["measured_cumulative_total_fruit_dry_weight_floor_area"], errors="coerce").iloc[0])
    )
    lai_launch_discontinuity = abs(first_lai - snapshot["lai"]) if math.isfinite(snapshot["lai"]) else math.nan
    fruit_launch_discontinuity = abs(
        float(first_model_daily.get("model_onplant_fruit_dry_weight_floor_area", 0.0)) - snapshot["fruit_mass"]
    )
    buffer_launch_discontinuity = abs(first_buffer - snapshot["buffer_mass"])
    metrics = {
        **bundle.metrics,
        "init_fit_score": float(
            -1.0 * float(bundle.metrics["yield_rmse_offset_adjusted"])
            -0.6 * float(bundle.metrics["rmse_daily_increment"])
            -0.4 * harvest_alignment
            -0.2 * (0.0 if math.isnan(lai_launch_discontinuity) else lai_launch_discontinuity)
            -0.2 * fruit_launch_discontinuity
        ),
        "lai_init_error_proxy": lai_launch_discontinuity,
        "fruit_mass_init_error_proxy": fruit_launch_discontinuity,
        "buffer_state_init_proxy": buffer_launch_discontinuity,
        "harvest_offset_alignment_error": harvest_alignment,
    }
    return bundle.merged_df, metrics


def reconstruct_hidden_state(
    *,
    architecture_row: dict[str, object],
    base_config: dict[str, Any],
    forcing_csv_path: Path,
    theta_center: float,
    observed_df: pd.DataFrame,
    calibration_end: pd.Timestamp,
    repo_root: Path,
    unit_label: str,
    modes: tuple[str, ...] = ("minimal_scalar_init", "cohort_aware_init", "buffer_aware_init"),
) -> ReconstructionResult:
    calib_obs = observed_df[observed_df["date"] <= calibration_end].reset_index(drop=True)
    candidates = build_reconstruction_candidates(calib_obs, modes=modes)
    if not candidates:
        raise ValueError("No reconstruction candidates were generated.")

    best_result: ReconstructionResult | None = None
    best_score = -math.inf
    for candidate in candidates:
        run_cfg = configure_candidate_run(
            base_config=copy.deepcopy(base_config),
            forcing_csv_path=forcing_csv_path,
            theta_center=theta_center,
            row=architecture_row,
            initial_state_overrides=candidate.initial_state_overrides,
        )
        run_df = run_tomato_legacy_pipeline(run_cfg, repo_root=repo_root)
        model_daily_df = model_floor_area_cumulative_total_fruit(run_df)
        model_daily_df = model_daily_df[model_daily_df["date"] <= calibration_end].reset_index(drop=True)
        run_dates = pd.to_datetime(run_df.get("datetime"), errors="coerce").dt.normalize()
        merged_df, metrics = _reconstruction_metrics(
            observed_df=calib_obs,
            model_daily_df=model_daily_df,
            run_df=run_df.loc[run_dates <= calibration_end].copy(),
            candidate_label="model",
            unit_label=unit_label,
            initial_state_overrides=candidate.initial_state_overrides,
        )
        score = float(metrics["init_fit_score"])
        result = ReconstructionResult(
            architecture_id=str(architecture_row["architecture_id"]),
            mode=candidate.mode,
            candidate_label=candidate.label,
            initial_state_overrides=candidate.initial_state_overrides,
            metrics=metrics,
            validation_df=merged_df,
            run_df=run_df,
        )
        if score > best_score:
            best_score = score
            best_result = result
    if best_result is None:
        raise RuntimeError("State reconstruction did not produce any valid result.")
    return best_result


def _as_dict(raw: object) -> dict[str, Any]:
    if isinstance(raw, dict):
        return {str(key): value for key, value in raw.items()}
    return {}


def _resolve_config_path(raw: str | Path, *, repo_root: Path, config_path: Path) -> Path:
    candidate = Path(raw)
    if candidate.is_absolute():
        return candidate
    probes = [
        (config_path.parent / candidate).resolve(),
        (repo_root / candidate).resolve(),
    ]
    for probe in probes:
        if probe.exists():
            return probe
    return probes[0]


def _overlay_frame(validation_df: pd.DataFrame, *, candidate_label: str) -> pd.DataFrame:
    out = pd.DataFrame({"datetime": pd.to_datetime(validation_df["date"], errors="coerce")})
    out["cumulative_total_fruit_floor_area"] = pd.to_numeric(
        validation_df[f"{candidate_label}_cumulative_total_fruit_dry_weight_floor_area"],
        errors="coerce",
    )
    out["offset_adjusted_cumulative_total_fruit_floor_area"] = pd.to_numeric(
        validation_df[f"{candidate_label}_offset_adjusted"],
        errors="coerce",
    )
    out["daily_increment_floor_area"] = pd.to_numeric(
        validation_df[f"{candidate_label}_daily_increment_floor_area"],
        errors="coerce",
    )
    return out


def _measured_overlay_frame(observed_df: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame({"datetime": pd.to_datetime(observed_df["date"], errors="coerce")})
    out["cumulative_total_fruit_floor_area"] = pd.to_numeric(
        observed_df["measured_cumulative_total_fruit_dry_weight_floor_area"],
        errors="coerce",
    )
    out["offset_adjusted_cumulative_total_fruit_floor_area"] = pd.to_numeric(
        observed_df["measured_offset_adjusted"],
        errors="coerce",
    )
    out["daily_increment_floor_area"] = pd.to_numeric(
        observed_df["measured_daily_increment_floor_area"],
        errors="coerce",
    )
    return out


def run_knu_state_reconstruction(*, config_path: str | Path) -> dict[str, object]:
    resolved_config_path = Path(config_path).resolve()
    config = load_config(resolved_config_path)
    repo_root = resolve_repo_root(config, config_path=resolved_config_path)
    prepared_bundle = prepare_knu_bundle(config, repo_root=repo_root, config_path=resolved_config_path)
    _, candidates, reference_meta = load_fairness_candidates(
        fairness_config=config,
        repo_root=repo_root,
        config_path=resolved_config_path,
    )
    base_config = copy.deepcopy(_as_dict(reference_meta.get("base_config")))
    reconstruction_cfg = _as_dict(config.get("state_reconstruction"))
    output_root = ensure_dir(
        _resolve_config_path(
            reconstruction_cfg.get("output_root", "out/tomics_knu_state_reconstruction"),
            repo_root=repo_root,
            config_path=resolved_config_path,
        )
    )
    plot_spec = _resolve_config_path(
        _as_dict(config.get("plots")).get(
            "yield_fit_overlay_spec",
            "configs/plotkit/tomics/knu_yield_fit_overlay.yaml",
        ),
        repo_root=repo_root,
        config_path=resolved_config_path,
    )
    scenario = prepared_bundle.scenarios[str(reconstruction_cfg.get("theta_proxy_scenario", "moderate"))]
    rows: list[dict[str, object]] = []
    selected_payload: dict[str, Any] = {}
    runs = {"measured": _measured_overlay_frame(prepared_bundle.observed_df)}
    for candidate in candidates:
        if not candidate.calibratable:
            continue
        result = reconstruct_hidden_state(
            architecture_row=candidate.row,
            base_config=base_config,
            forcing_csv_path=scenario.forcing_csv_path,
            theta_center=float(scenario.summary.get("theta_mean", 0.65)),
            observed_df=prepared_bundle.observed_df,
            calibration_end=prepared_bundle.calibration_end,
            repo_root=repo_root,
            unit_label=prepared_bundle.data.observation_unit_label,
        )
        rows.append(
            {
                "candidate_label": candidate.candidate_label,
                "architecture_id": candidate.architecture_id,
                "mode": result.mode,
                "candidate_label_detail": result.candidate_label,
                **result.metrics,
            }
        )
        selected_payload[candidate.candidate_label] = {
            "architecture_id": candidate.architecture_id,
            "mode": result.mode,
            "candidate_label": result.candidate_label,
            "initial_state_overrides": result.initial_state_overrides,
        }
        runs[candidate.candidate_label] = _overlay_frame(result.validation_df, candidate_label="model")
    summary_df = pd.DataFrame(rows)
    summary_df.to_csv(output_root / "reconstruction_summary.csv", index=False)
    (output_root / "reconstructed_initial_state.json").write_text(
        json.dumps(selected_payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    render_partition_compare_bundle(
        runs=runs,
        out_path=output_root / "reconstruction_overlay.png",
        spec_path=plot_spec,
    )
    return {
        "output_root": str(output_root),
        "reconstruction_summary_csv": str(output_root / "reconstruction_summary.csv"),
        "reconstructed_initial_state_json": str(output_root / "reconstructed_initial_state.json"),
    }


__all__ = [
    "ReconstructionResult",
    "reconstruct_hidden_state",
    "run_knu_state_reconstruction",
]
