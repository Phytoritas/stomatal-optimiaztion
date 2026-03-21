from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.alloc.core import ensure_dir, load_config, write_json
from stomatal_optimiaztion.domains.tomato.tomics.alloc.pipelines import resolve_repo_root, run_tomato_legacy_pipeline
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.current_vs_promoted import (
    configure_candidate_run,
    prepare_knu_bundle,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.harvest_operator import (
    model_floor_area_cumulative_total_fruit,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.observation_model import (
    compute_validation_bundle,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.parameter_budget import (
    load_fairness_candidates,
)
from stomatal_optimiaztion.domains.tomato.tomics.plotting import render_partition_compare_bundle


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


def _workbook_overlay_frame(observed_df: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame({"datetime": pd.to_datetime(observed_df["date"], errors="coerce")})
    out["cumulative_total_fruit_floor_area"] = pd.to_numeric(
        observed_df["estimated_cumulative_total_fruit_dry_weight_floor_area"],
        errors="coerce",
    )
    out["offset_adjusted_cumulative_total_fruit_floor_area"] = pd.to_numeric(
        observed_df["estimated_offset_adjusted"],
        errors="coerce",
    )
    out["daily_increment_floor_area"] = pd.to_numeric(
        observed_df["estimated_daily_increment_floor_area"],
        errors="coerce",
    )
    return out


def run_knu_observation_eval(*, config_path: str | Path) -> dict[str, object]:
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
    evaluation_cfg = _as_dict(config.get("observation_eval"))
    output_root = ensure_dir(
        _resolve_config_path(
            evaluation_cfg.get("output_root", "out/tomics/validation/knu/fairness/observation-eval"),
            repo_root=repo_root,
            config_path=resolved_config_path,
        )
    )
    cumulative_spec = _resolve_config_path(
        evaluation_cfg.get("cumulative_overlay_spec", "configs/plotkit/tomics/knu_cumulative_overlay.yaml"),
        repo_root=repo_root,
        config_path=resolved_config_path,
    )
    daily_spec = _resolve_config_path(
        evaluation_cfg.get("daily_overlay_spec", "configs/plotkit/tomics/knu_daily_increment_overlay.yaml"),
        repo_root=repo_root,
        config_path=resolved_config_path,
    )
    scenario = prepared_bundle.scenarios[str(evaluation_cfg.get("theta_proxy_scenario", "moderate"))]

    rows: list[dict[str, object]] = []
    runs: dict[str, pd.DataFrame] = {
        "measured": _measured_overlay_frame(prepared_bundle.observed_df),
        "workbook_estimated": _workbook_overlay_frame(prepared_bundle.workbook_validation_df),
    }
    rows.append(
        {
            "candidate_label": "workbook_estimated",
            "architecture_id": "workbook_estimated_baseline",
            **prepared_bundle.workbook_metrics,
        }
    )

    for candidate in candidates:
        if candidate.candidate_label == "workbook_estimated":
            continue
        run_cfg = configure_candidate_run(
            base_config=copy.deepcopy(base_config),
            forcing_csv_path=scenario.forcing_csv_path,
            theta_center=float(scenario.summary.get("theta_mean", 0.65)),
            row=candidate.row,
        )
        run_df = run_tomato_legacy_pipeline(run_cfg, repo_root=repo_root)
        model_daily_df = model_floor_area_cumulative_total_fruit(run_df)
        candidate_series = prepared_bundle.observed_df["date"].map(
            model_daily_df.set_index("date")["model_cumulative_total_fruit_dry_weight_floor_area"]
        )
        bundle = compute_validation_bundle(
            prepared_bundle.observed_df.copy(),
            candidate_series=candidate_series,
            candidate_label="model",
            unit_declared_in_observation_file=prepared_bundle.data.observation_unit_label,
        )
        rows.append(
            {
                "candidate_label": candidate.candidate_label,
                "architecture_id": candidate.architecture_id,
                **bundle.metrics,
            }
        )
        runs[candidate.candidate_label] = _overlay_frame(bundle.merged_df, candidate_label="model")

    summary_df = pd.DataFrame(rows)
    summary_df.to_csv(output_root / "observation_fit_summary.csv", index=False)
    render_partition_compare_bundle(
        runs=runs,
        out_path=output_root / "cumulative_overlay.png",
        spec_path=cumulative_spec,
    )
    render_partition_compare_bundle(
        runs=runs,
        out_path=output_root / "daily_increment_overlay.png",
        spec_path=daily_spec,
    )
    manifest = {
        "observation_operator": {
            "measured_target": "cumulative_harvested_fruit_dry_weight_floor_area",
            "model_mapping": "harvested_fruit_g_m2 -> cumulative harvested fruit dry weight on floor area basis",
            "daily_increment_policy": "daily increment is the first difference of cumulative harvested fruit dry weight; the first observed day stays undefined because prior-day harvest is outside the window",
            "offset_adjustment_policy": "subtract model and observed cumulative values at validation-window start",
        },
        "theta_proxy_scenario": str(evaluation_cfg.get("theta_proxy_scenario", "moderate")),
        "reporting_basis": "floor_area_g_m2",
        "plants_per_m2": prepared_bundle.data_contract.plants_per_m2,
    }
    write_json(output_root / "observation_operator_manifest.json", manifest)
    return {
        "output_root": str(output_root),
        "observation_fit_summary_csv": str(output_root / "observation_fit_summary.csv"),
        "manifest_json": str(output_root / "observation_operator_manifest.json"),
        "summary_df": summary_df,
    }


__all__ = [
    "run_knu_observation_eval",
]
