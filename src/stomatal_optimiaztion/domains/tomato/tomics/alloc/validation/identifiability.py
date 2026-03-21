from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.alloc.core import load_config
from stomatal_optimiaztion.domains.tomato.tomics.alloc.pipelines import run_tomato_legacy_pipeline
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.calibration import (
    _as_dict,
    _candidate_series,
    _resolve_config_path,
    _window_bundle,
    load_candidate_specs,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.current_vs_promoted import (
    configure_candidate_run,
    prepare_knu_bundle,
)


def run_identifiability_analysis(
    config: dict[str, Any],
    *,
    repo_root: Path,
    config_path: Path,
) -> dict[str, Path]:
    prepared_bundle = prepare_knu_bundle(config, repo_root=repo_root, config_path=config_path)
    specs, _, _ = load_candidate_specs(config=config, repo_root=repo_root, config_path=config_path)
    ident_cfg = _as_dict(config.get("identifiability"))
    calibration_cfg = _as_dict(config.get("calibration"))
    calibration_root = _resolve_config_path(
        calibration_cfg.get("output_root", "out/tomics/validation/knu/fairness/calibration"),
        repo_root=repo_root,
        config_path=config_path,
    )
    holdout_results = pd.read_csv(calibration_root / "holdout_results.csv")
    parameter_stability = pd.read_csv(calibration_root / "parameter_stability.csv")
    deltas = {
        "fruit_load_multiplier": float(ident_cfg.get("fruit_load_multiplier_delta", 0.05)),
        "lai_target_center": float(ident_cfg.get("lai_target_center_delta", 0.25)),
    }
    local_rows: list[dict[str, object]] = []

    blocked = holdout_results[
        holdout_results["split_label"].eq("blocked_holdout")
        & holdout_results["candidate_label"].isin(["shipped_tomics", "current_selected", "promoted_selected"])
    ].copy()
    for _, row in blocked.iterrows():
        candidate_label = str(row["candidate_label"])
        spec = specs[candidate_label]
        assert spec.candidate_row is not None
        assert spec.base_config_path is not None
        selected_params = json.loads(str(row["selected_params_json"]))
        initial_state_overrides = json.loads(str(row["initial_state_overrides_json"]))
        baseline_rmse = float(row["holdout_rmse_cumulative_offset"])
        for parameter_name, delta in deltas.items():
            if parameter_name not in selected_params:
                continue
            for direction, signed_delta in (("minus", -delta), ("plus", delta)):
                perturbed = dict(selected_params)
                perturbed[parameter_name] = float(selected_params[parameter_name]) + signed_delta
                tuned_row = {**spec.candidate_row, **perturbed}
                cfg = configure_candidate_run(
                    copy.deepcopy(load_config(spec.base_config_path)),
                    forcing_csv_path=prepared_bundle.scenarios["moderate"].forcing_csv_path,
                    theta_center=float(prepared_bundle.scenarios["moderate"].summary.get("theta_mean", 0.65)),
                    row=tuned_row,
                    initial_state_overrides=initial_state_overrides,
                )
                run_df = run_tomato_legacy_pipeline(cfg, repo_root=repo_root)
                candidate_series = _candidate_series(prepared_bundle.observed_df, run_df)
                _, holdout_metrics = _window_bundle(
                    prepared_bundle.observed_df,
                    candidate_series=candidate_series,
                    candidate_label="model",
                    unit_label=prepared_bundle.data.observation_unit_label,
                    start=prepared_bundle.holdout_start,
                    end=prepared_bundle.validation_end,
                )
                local_rows.append(
                    {
                        "candidate_label": candidate_label,
                        "architecture_id": str(row["architecture_id"]),
                        "parameter_name": parameter_name,
                        "direction": direction,
                        "delta": signed_delta,
                        "holdout_rmse_cumulative_offset": holdout_metrics["yield_rmse_offset_adjusted"],
                        "rmse_delta": float(holdout_metrics["yield_rmse_offset_adjusted"]) - baseline_rmse,
                    }
                )

    local_sensitivity_df = pd.DataFrame(local_rows)
    local_sensitivity_df.to_csv(calibration_root / "local_sensitivity.csv", index=False)

    if not local_sensitivity_df.empty:
        summary = (
            local_sensitivity_df.groupby(["candidate_label", "parameter_name"], as_index=False)
            .agg(
                local_sensitivity_mean_abs_delta=("rmse_delta", lambda series: float(pd.Series(series).abs().mean())),
                local_sensitivity_max_abs_delta=("rmse_delta", lambda series: float(pd.Series(series).abs().max())),
            )
        )
        parameter_stability = parameter_stability.merge(
            summary,
            on=["candidate_label", "parameter_name"],
            how="left",
        )
    parameter_stability.to_csv(calibration_root / "parameter_stability.csv", index=False)
    return {
        "parameter_stability_csv": calibration_root / "parameter_stability.csv",
        "local_sensitivity_csv": calibration_root / "local_sensitivity.csv",
    }


__all__ = ["run_identifiability_analysis"]
