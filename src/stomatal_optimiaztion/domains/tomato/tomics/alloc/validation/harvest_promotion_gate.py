from __future__ import annotations

import copy
import json
import math
from pathlib import Path
from typing import Any

import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.alloc.core import ensure_dir, write_json
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.current_vs_promoted import (
    configure_candidate_run,
    prepare_knu_bundle,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.harvest_calibration_bridge import (
    HarvestDesignRow,
    build_harvest_budget_manifest,
    build_split_windows,
    load_harvest_base_config,
    load_harvest_candidates,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.harvest_factorial import (
    _as_dict,
    _resolve_config_path,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.harvest_family_eval import (
    build_harvest_overlay_frame,
    run_harvest_family_simulation,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.harvest_mass_balance_eval import (
    winner_stability_score,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.observation_model import (
    compute_validation_bundle,
    validation_overlay_frame,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.state_reconstruction import (
    reconstruct_hidden_state,
)
from stomatal_optimiaztion.domains.tomato.tomics.plotting import render_partition_compare_bundle


def _window_metrics(validation_df: pd.DataFrame, *, start: pd.Timestamp, end: pd.Timestamp) -> dict[str, float | str | bool]:
    mask = (pd.to_datetime(validation_df["date"]).dt.normalize() >= start) & (
        pd.to_datetime(validation_df["date"]).dt.normalize() <= end
    )
    window = validation_df.loc[mask].copy()
    if window.empty:
        return {
            "rmse_cumulative_offset": math.nan,
            "mae_cumulative_offset": math.nan,
            "r2_cumulative_offset": math.nan,
            "rmse_daily_increment": math.nan,
            "mae_daily_increment": math.nan,
            "final_cumulative_bias": math.nan,
            "harvest_timing_mae_days": math.nan,
        }
    bundle = compute_validation_bundle(
        window[
            [
                "date",
                "measured_cumulative_total_fruit_dry_weight_floor_area",
                "measured_daily_increment_floor_area",
            ]
        ].copy(),
        candidate_series=window["model_cumulative_total_fruit_dry_weight_floor_area"],
        candidate_daily_increment_series=window["model_daily_increment_floor_area"],
        candidate_label="model",
        unit_declared_in_observation_file="g/m^2",
    )
    return bundle.metrics


def _build_candidate_rows(
    *,
    candidates_by_label: dict[str, object],
    selected_family: dict[str, object],
) -> list[HarvestDesignRow]:
    baseline = HarvestDesignRow(
        stage="HF5",
        allocator_family="shipped_tomics",
        candidate_label="shipped_tomics",
        architecture_id=candidates_by_label["shipped_tomics"].architecture_id,
        fruit_harvest_family="tomsim_truss",
        leaf_harvest_family="linked_truss_stage",
        fdmc_mode="constant_observed_mean",
        harvest_delay_days=0.0,
        harvest_readiness_threshold=1.0,
        fruit_params={"tdvs_harvest_threshold": 1.0},
        leaf_params={"linked_leaf_stage": 0.9},
        candidate_row=candidates_by_label["shipped_tomics"].row,
    )
    research_rows = []
    for label in ("current_selected", "promoted_selected"):
        research_rows.append(
            HarvestDesignRow(
                stage="HF5",
                allocator_family=label,
                candidate_label=label,
                architecture_id=candidates_by_label[label].architecture_id,
                fruit_harvest_family=str(selected_family["selected_fruit_harvest_family"]),
                leaf_harvest_family=str(selected_family["selected_leaf_harvest_family"]),
                fdmc_mode=str(selected_family["selected_fdmc_mode"]),
                harvest_delay_days=float(selected_family.get("harvest_delay_days", 0.0)),
                harvest_readiness_threshold=float(selected_family.get("harvest_readiness_threshold", 1.0)),
                fruit_params=_as_dict(selected_family.get("fruit_params")),
                leaf_params=_as_dict(selected_family.get("leaf_params")),
                candidate_row=candidates_by_label[label].row,
            )
        )
    return [baseline, *research_rows]


def _parameter_grid(base_row: HarvestDesignRow) -> list[dict[str, float]]:
    threshold_values = [base_row.harvest_readiness_threshold]
    if base_row.fruit_harvest_family in {"tomsim_truss", "dekoning_fds"}:
        threshold_values = [base_row.harvest_readiness_threshold - 0.05, base_row.harvest_readiness_threshold, base_row.harvest_readiness_threshold + 0.05]
    delay_values = [0.0, 1.0]
    fruit_load_values = [0.95, 1.0]
    lai_values = [2.5, 2.75]
    rows: list[dict[str, float]] = []
    for fruit_load in fruit_load_values:
        for lai_target in lai_values:
            for delay in delay_values:
                for threshold in threshold_values:
                    rows.append(
                        {
                            "fruit_load_multiplier": float(fruit_load),
                            "lai_target_center": float(lai_target),
                            "harvest_delay_days": float(delay),
                            "harvest_readiness_threshold": float(threshold),
                        }
                    )
    return rows


def _params_cache_key(params: dict[str, float]) -> tuple[float, float]:
    return (
        float(params["fruit_load_multiplier"]),
        float(params["lai_target_center"]),
    )


def run_harvest_promotion_gate(
    config: dict[str, Any],
    *,
    repo_root: Path,
    config_path: Path,
) -> dict[str, object]:
    prepared_bundle = prepare_knu_bundle(config, repo_root=repo_root, config_path=config_path)
    candidates, reference_meta = load_harvest_candidates(config=config, repo_root=repo_root, config_path=config_path)
    candidates_by_label = {candidate.candidate_label: candidate for candidate in candidates}
    base_config = load_harvest_base_config(reference_meta)
    gate_cfg = _as_dict(config.get("harvest_promotion_gate"))
    output_root = ensure_dir(
        _resolve_config_path(
            gate_cfg.get("output_root", "out/tomics_knu_harvest_promotion_gate"),
            repo_root=repo_root,
            config_path=config_path,
        )
    )
    factorial_root = _resolve_config_path(
        gate_cfg.get("harvest_factorial_root", "out/tomics_knu_harvest_family_factorial"),
        repo_root=repo_root,
        config_path=config_path,
    )
    selected_family = json.loads((factorial_root / "selected_harvest_family.json").read_text(encoding="utf-8"))
    candidate_rows = _build_candidate_rows(candidates_by_label=candidates_by_label, selected_family=selected_family)
    splits = build_split_windows(prepared_bundle.observed_df)
    write_json(output_root / "harvest_calibration_budget_manifest.json", build_harvest_budget_manifest(candidates=candidate_rows, splits=splits))

    scenario = prepared_bundle.scenarios[str(gate_cfg.get("theta_proxy_scenario", "moderate"))]
    wet_scenario = prepared_bundle.scenarios[str(gate_cfg.get("wet_theta_proxy_scenario", "wet"))]
    results_rows: list[dict[str, object]] = []
    overlay_runs = {
        "measured": validation_overlay_frame(prepared_bundle.observed_df, source_label="measured"),
        "workbook_estimated": validation_overlay_frame(prepared_bundle.workbook_validation_df, source_label="workbook_estimated"),
    }
    shipped_candidate = candidates_by_label["shipped_tomics"]
    reference_cache: dict[tuple[str, tuple[float, float]], dict[str, float]] = {}

    def _reference_metrics(split, params: dict[str, float]) -> dict[str, float]:
        cache_key = (split.split_id, _params_cache_key(params))
        cached = reference_cache.get(cache_key)
        if cached is not None:
            return cached
        reconstruction = reconstruct_hidden_state(
            architecture_row=shipped_candidate.row,
            base_config=copy.deepcopy(base_config),
            forcing_csv_path=scenario.forcing_csv_path,
            theta_center=float(scenario.summary.get("theta_mean", 0.65)),
            observed_df=prepared_bundle.observed_df,
            calibration_end=split.calibration_end,
            repo_root=repo_root,
            unit_label=prepared_bundle.data.observation_unit_label,
        )
        candidate_row = {
            **shipped_candidate.row,
            "fruit_load_multiplier": params["fruit_load_multiplier"],
            "lai_target_center": params["lai_target_center"],
        }
        run_cfg = configure_candidate_run(
            base_config=copy.deepcopy(base_config),
            forcing_csv_path=scenario.forcing_csv_path,
            theta_center=float(scenario.summary.get("theta_mean", 0.65)),
            row=candidate_row,
            initial_state_overrides=dict(reconstruction.initial_state_overrides),
        )
        result = run_harvest_family_simulation(
            run_config=run_cfg,
            observed_df=prepared_bundle.observed_df,
            unit_label=prepared_bundle.data.observation_unit_label,
            repo_root=repo_root,
            fruit_harvest_family="tomsim_truss",
            leaf_harvest_family="linked_truss_stage",
            fdmc_mode="constant_observed_mean",
            fruit_params={"tdvs_harvest_threshold": 1.0},
            leaf_params={"linked_leaf_stage": 0.9},
        )
        cached = {
            "mean_alloc_frac_fruit": float(pd.to_numeric(result.run_df["alloc_frac_fruit"], errors="coerce").mean()),
        }
        reference_cache[cache_key] = cached
        return cached

    for candidate in candidate_rows:
        param_grid = _parameter_grid(candidate)
        for split in splits:
            reconstruction = reconstruct_hidden_state(
                architecture_row=candidate.candidate_row,
                base_config=copy.deepcopy(base_config),
                forcing_csv_path=scenario.forcing_csv_path,
                theta_center=float(scenario.summary.get("theta_mean", 0.65)),
                observed_df=prepared_bundle.observed_df,
                calibration_end=split.calibration_end,
                repo_root=repo_root,
                unit_label=prepared_bundle.data.observation_unit_label,
            )
            best_row: dict[str, object] | None = None
            best_score = -math.inf
            best_validation_df = pd.DataFrame()
            for params in param_grid:
                candidate_row = {**candidate.candidate_row, "fruit_load_multiplier": params["fruit_load_multiplier"], "lai_target_center": params["lai_target_center"]}
                run_cfg = configure_candidate_run(
                    base_config=copy.deepcopy(base_config),
                    forcing_csv_path=scenario.forcing_csv_path,
                    theta_center=float(scenario.summary.get("theta_mean", 0.65)),
                    row=candidate_row,
                    initial_state_overrides=dict(reconstruction.initial_state_overrides),
                )
                fruit_params = dict(candidate.fruit_params)
                leaf_params = dict(candidate.leaf_params)
                if candidate.fruit_harvest_family == "tomsim_truss":
                    fruit_params["tdvs_harvest_threshold"] = params["harvest_readiness_threshold"]
                    fruit_params["harvest_delay_days"] = params["harvest_delay_days"]
                elif candidate.fruit_harvest_family == "dekoning_fds":
                    fruit_params["fds_harvest_threshold"] = params["harvest_readiness_threshold"]
                    fruit_params["harvest_delay_days"] = params["harvest_delay_days"]
                result = run_harvest_family_simulation(
                    run_config=run_cfg,
                    observed_df=prepared_bundle.observed_df,
                    unit_label=prepared_bundle.data.observation_unit_label,
                    repo_root=repo_root,
                    fruit_harvest_family=candidate.fruit_harvest_family,
                    leaf_harvest_family=candidate.leaf_harvest_family,
                    fdmc_mode=candidate.fdmc_mode,
                    fruit_params=fruit_params,
                    leaf_params=leaf_params,
                )
                calibration_metrics = _window_metrics(
                    result.validation_df,
                    start=split.calibration_start,
                    end=split.calibration_end,
                )
                holdout_metrics = _window_metrics(
                    result.validation_df,
                    start=split.holdout_start,
                    end=split.holdout_end,
                )
                score = float(
                    -1.2 * float(calibration_metrics["rmse_cumulative_offset"])
                    -0.8 * float(calibration_metrics["rmse_daily_increment"])
                    -0.5 * abs(float(calibration_metrics["final_cumulative_bias"]))
                )
                if score > best_score:
                    reference_metrics = _reference_metrics(split, params)
                    wet_cfg = configure_candidate_run(
                        base_config=copy.deepcopy(base_config),
                        forcing_csv_path=wet_scenario.forcing_csv_path,
                        theta_center=float(wet_scenario.summary.get("theta_mean", 0.80)),
                        row=candidate_row,
                        initial_state_overrides=dict(reconstruction.initial_state_overrides),
                    )
                    wet_result = run_harvest_family_simulation(
                        run_config=wet_cfg,
                        observed_df=prepared_bundle.observed_df,
                        unit_label=prepared_bundle.data.observation_unit_label,
                        repo_root=repo_root,
                        fruit_harvest_family=candidate.fruit_harvest_family,
                        leaf_harvest_family=candidate.leaf_harvest_family,
                        fdmc_mode=candidate.fdmc_mode,
                        fruit_params=fruit_params,
                        leaf_params=leaf_params,
                    )
                    if "theta_substrate" in wet_result.run_df.columns:
                        mean_theta_wet = float(pd.to_numeric(wet_result.run_df["theta_substrate"], errors="coerce").mean())
                    else:
                        mean_theta_wet = float(wet_scenario.summary.get("theta_mean", 0.80))
                    mean_root_wet = float(pd.to_numeric(wet_result.run_df["alloc_frac_root"], errors="coerce").mean())
                    wet_root_cap = float(candidate.candidate_row.get("wet_root_cap", 0.10))
                    wet_penalty = max(mean_root_wet - wet_root_cap, 0.0) if mean_theta_wet >= 0.75 else 0.0
                    mean_alloc_frac_fruit = float(pd.to_numeric(result.run_df["alloc_frac_fruit"], errors="coerce").mean())
                    best_score = score
                    best_validation_df = result.validation_df.copy()
                    best_row = {
                        "candidate_label": candidate.candidate_label,
                        "architecture_id": candidate.architecture_id,
                        "fruit_harvest_family": candidate.fruit_harvest_family,
                        "leaf_harvest_family": candidate.leaf_harvest_family,
                        "fdmc_mode": candidate.fdmc_mode,
                        "split_label": split.split_id,
                        "split_kind": split.split_kind,
                        "holdout_rmse_cumulative_offset": holdout_metrics["rmse_cumulative_offset"],
                        "holdout_mae_cumulative_offset": holdout_metrics["mae_cumulative_offset"],
                        "holdout_r2_cumulative_offset": holdout_metrics["r2_cumulative_offset"],
                        "holdout_rmse_daily_increment": holdout_metrics["rmse_daily_increment"],
                        "holdout_mae_daily_increment": holdout_metrics["mae_daily_increment"],
                        "holdout_final_bias": holdout_metrics["final_cumulative_bias"],
                        "fruit_anchor_error_vs_legacy": 0.0
                        if candidate.candidate_label == "shipped_tomics"
                        else abs(mean_alloc_frac_fruit - float(reference_metrics["mean_alloc_frac_fruit"])),
                        "canopy_collapse_days": result.metrics["canopy_collapse_days"],
                        "harvest_mass_balance_error": result.metrics["harvest_mass_balance_error"],
                        "latent_fruit_residual_end": result.metrics["latent_fruit_residual_end"],
                        "leaf_harvest_mass_balance_error": result.metrics["leaf_harvest_mass_balance_error"],
                        "wet_condition_root_excess_penalty": wet_penalty,
                        "score": score,
                        "selected_params_json": json.dumps(params, sort_keys=True),
                    }
            if best_row is None:
                continue
            results_rows.append(best_row)
            if split.split_id == "blocked_primary":
                overlay_runs[candidate.candidate_label] = build_harvest_overlay_frame(best_validation_df, source_label="model")

    results_df = pd.DataFrame(results_rows)
    scorecard_df = (
        results_df.groupby(["candidate_label", "architecture_id", "fruit_harvest_family", "leaf_harvest_family", "fdmc_mode"], as_index=False)
        .agg(
            mean_holdout_rmse_cumulative_offset=("holdout_rmse_cumulative_offset", "mean"),
            mean_holdout_rmse_daily_increment=("holdout_rmse_daily_increment", "mean"),
            mean_holdout_final_bias=("holdout_final_bias", "mean"),
            max_fruit_anchor_error_vs_legacy=("fruit_anchor_error_vs_legacy", "max"),
            max_canopy_collapse_days=("canopy_collapse_days", "max"),
            max_harvest_mass_balance_error=("harvest_mass_balance_error", "max"),
            max_leaf_harvest_mass_balance_error=("leaf_harvest_mass_balance_error", "max"),
            max_wet_condition_root_excess_penalty=("wet_condition_root_excess_penalty", "max"),
        )
        .reset_index(drop=True)
    )
    stability_df = winner_stability_score(results_df, candidate_column="candidate_label")
    scorecard_df = scorecard_df.merge(stability_df, on="candidate_label", how="left")
    scorecard_df["winner_stability_score"] = scorecard_df["winner_stability_score"].fillna(0.0)
    scorecard_df.to_csv(output_root / "harvest_promotion_scorecard.csv", index=False)
    stability_df.to_csv(output_root / "winner_stability.csv", index=False)

    shipped = scorecard_df[scorecard_df["candidate_label"].eq("shipped_tomics")].iloc[0]
    current = scorecard_df[scorecard_df["candidate_label"].eq("current_selected")].iloc[0]
    promoted = scorecard_df[scorecard_df["candidate_label"].eq("promoted_selected")].iloc[0]
    guardrails = {
        "fruit_anchor_error_vs_legacy_max": 0.03,
        "canopy_collapse_days_max": 0.0,
        "harvest_mass_balance_error_max": float(gate_cfg.get("harvest_mass_balance_error_max", 1e-4)),
        "wet_condition_root_excess_penalty_max": float(gate_cfg.get("wet_root_penalty_max", 0.02)),
        "winner_stability_score_min": float(gate_cfg.get("winner_stability_score_min", 0.5)),
        "material_cumulative_rmse_margin": float(gate_cfg.get("material_cumulative_rmse_margin", 0.5)),
        "material_daily_rmse_margin": float(gate_cfg.get("material_daily_rmse_margin", 0.25)),
    }

    def _passes(candidate: pd.Series) -> bool:
        return (
            float(shipped["mean_holdout_rmse_cumulative_offset"]) - float(candidate["mean_holdout_rmse_cumulative_offset"]) >= guardrails["material_cumulative_rmse_margin"]
            and float(shipped["mean_holdout_rmse_daily_increment"]) - float(candidate["mean_holdout_rmse_daily_increment"]) >= guardrails["material_daily_rmse_margin"]
            and float(candidate["max_fruit_anchor_error_vs_legacy"]) <= guardrails["fruit_anchor_error_vs_legacy_max"]
            and float(candidate["max_canopy_collapse_days"]) <= guardrails["canopy_collapse_days_max"]
            and float(candidate["max_harvest_mass_balance_error"]) <= guardrails["harvest_mass_balance_error_max"]
            and float(candidate["max_wet_condition_root_excess_penalty"]) <= guardrails["wet_condition_root_excess_penalty_max"]
            and float(candidate["winner_stability_score"]) >= guardrails["winner_stability_score_min"]
        )

    current_passes = _passes(current)
    promoted_passes = _passes(promoted)
    recommendation = "No candidate clears promotion gate; keep research-only."
    if current_passes or promoted_passes:
        if promoted_passes and float(promoted["mean_holdout_rmse_cumulative_offset"]) <= float(current["mean_holdout_rmse_cumulative_offset"]):
            recommendation = "Promote a harvest-aware research candidate into a new incumbent."
        elif current_passes:
            recommendation = "Promote a harvest-aware research candidate into a new incumbent."
    else:
        recommendation = "Keep shipped TOMICS + incumbent TOMSIM harvest as the incumbent baseline."

    decision_lines = [
        "# Harvest-aware TOMICS Promotion Gate",
        "",
        f"Recommendation: `{recommendation}`",
        "",
        "Summary:",
        f"- shipped mean holdout RMSE offset: {float(shipped['mean_holdout_rmse_cumulative_offset']):.4f}",
        f"- current mean holdout RMSE offset: {float(current['mean_holdout_rmse_cumulative_offset']):.4f}",
        f"- promoted mean holdout RMSE offset: {float(promoted['mean_holdout_rmse_cumulative_offset']):.4f}",
        f"- current stability score: {float(current['winner_stability_score']):.2f}",
        f"- promoted stability score: {float(promoted['winner_stability_score']):.2f}",
    ]
    (output_root / "harvest_promotion_decision.md").write_text("\n".join(decision_lines) + "\n", encoding="utf-8")
    write_json(
        output_root / "promotion_guardrails.json",
        {
            "guardrails": guardrails,
            "current_selected": {"passes": current_passes, "metrics": current.to_dict()},
            "promoted_selected": {"passes": promoted_passes, "metrics": promoted.to_dict()},
            "recommendation": recommendation,
        },
    )
    render_partition_compare_bundle(
        runs=overlay_runs,
        out_path=output_root / "promotion_holdout_overlay.png",
        spec_path=_resolve_config_path(
            gate_cfg.get("promotion_overlay_spec", "configs/plotkit/tomics/knu_yield_fit_overlay.yaml"),
            repo_root=repo_root,
            config_path=config_path,
        ),
    )
    return {
        "output_root": str(output_root),
        "recommendation": recommendation,
        "scorecard_df": scorecard_df,
    }


__all__ = ["run_harvest_promotion_gate"]
