#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import json
import math
import time
from pathlib import Path
import sys
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.partitioning import (  # noqa: E402
    ResearchArchitectureConfig,
    equation_traceability_rows,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.core import (  # noqa: E402
    ensure_dir,
    load_config,
    write_json,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.pipelines import (  # noqa: E402
    resolve_repo_root,
    resolve_forcing_path,
    run_tomato_legacy_pipeline,
)
from stomatal_optimiaztion.domains.tomato.tomics.plotting import (  # noqa: E402
    render_architecture_summary_bundle,
    render_main_effects_bundle,
)


FACTOR_COLUMNS = [
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
DEFAULT_ALLOCATION_SUMMARY_SPEC_PATH = PROJECT_ROOT / "configs" / "plotkit" / "tomics" / "allocation_factorial_summary.yaml"
DEFAULT_ALLOCATION_MAIN_EFFECTS_SPEC_PATH = PROJECT_ROOT / "configs" / "plotkit" / "tomics" / "allocation_factorial_main_effects.yaml"


def _as_dict(raw: object) -> dict[str, Any]:
    if isinstance(raw, dict):
        return {str(key): value for key, value in raw.items()}
    return {}


def _as_list(raw: object) -> list[Any]:
    if isinstance(raw, list):
        return list(raw)
    return []


def _resolve_output_root(config: dict[str, Any], repo_root: Path, override: str | None = None) -> Path:
    raw = Path(override) if override else Path(str(_as_dict(config.get("paths")).get("output_root", "out/tomics_allocation_factorial")))
    return raw if raw.is_absolute() else (repo_root / raw).resolve()


def _resolve_plot_spec_path(config: dict[str, Any], repo_root: Path, key: str, default_path: Path) -> Path:
    plots_cfg = _as_dict(config.get("plots"))
    raw = Path(str(plots_cfg.get(key, default_path)))
    return raw if raw.is_absolute() else (repo_root / raw).resolve()


def _base_pipeline_params(config: dict[str, Any]) -> dict[str, Any]:
    pipeline_cfg = _as_dict(config.get("pipeline"))
    params = _as_dict(pipeline_cfg.get("partition_policy_params"))
    return {str(key): value for key, value in params.items()}


def _candidate_factor_defaults() -> dict[str, object]:
    return {
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
        "allocation_scheme": "4pool",
    }


def _candidate_rows(config: dict[str, Any]) -> list[dict[str, object]]:
    candidates = _as_dict(config.get("stage1")).get("candidates", [])
    if not isinstance(candidates, list):
        raise TypeError("stage1.candidates must be a list.")
    defaults = _candidate_factor_defaults()
    rows: list[dict[str, object]] = []
    for raw in candidates:
        row = {**defaults, **_as_dict(raw)}
        row["architecture_id"] = str(row["architecture_id"])
        row["partition_policy"] = str(row.get("partition_policy", "tomics"))
        normalized = ResearchArchitectureConfig.from_params(row, scheme=str(row.get("allocation_scheme", "4pool")))
        rows.append(
            {
                **row,
                **normalized.to_public_dict(),
                "architecture_id": str(row["architecture_id"]),
                "partition_policy": str(row["partition_policy"]),
            }
        )
    return rows


def _design_stage1(config: dict[str, Any]) -> list[dict[str, object]]:
    theta_levels = list(_as_dict(config.get("stage1")).get("theta_substrate", [0.20, 0.33, 0.50]))
    design: list[dict[str, object]] = []
    for candidate in _candidate_rows(config):
        for theta in theta_levels:
            row = dict(candidate)
            row["stage"] = "stage1"
            row["theta_substrate"] = float(theta)
            row["fruit_load_multiplier"] = float(row.get("fruit_load_multiplier", 1.0))
            design.append(row)
    return design


def _score_metrics(row: pd.Series) -> float:
    if int(row["nonfinite_flag"]) or int(row["negative_fraction_flag"]):
        return -1_000.0
    return float(
        15.0 * row["final_fruit_dry_weight"]
        + 5.0 * row["final_total_dry_weight"]
        - 40.0 * row["fruit_anchor_error_vs_legacy"]
        - 12.0 * row["canopy_collapse_days"]
        - 50.0 * row["wet_condition_root_excess_penalty"]
        - 10.0 * row["sum_to_one_error"]
    )


def _select_shortlist(metrics_df: pd.DataFrame, count: int) -> pd.DataFrame:
    research = metrics_df[
        metrics_df["partition_policy"].isin(["tomics_architecture_research", "tomics_alloc_research"])
    ].copy()
    ranked = (
        research.groupby("architecture_id", as_index=False)["score"]
        .mean()
        .sort_values("score", ascending=False)
        .head(count)
    )
    return ranked


def _design_stage2(config: dict[str, Any], shortlist_ids: list[str]) -> list[dict[str, object]]:
    stage1_candidates = {row["architecture_id"]: row for row in _candidate_rows(config)}
    axes = _as_dict(_as_dict(config.get("stage2")).get("parameter_axes"))
    theta = float(_as_dict(config.get("stage2")).get("theta_substrate", 0.33))
    design: list[dict[str, object]] = []
    for architecture_id in shortlist_ids:
        base = dict(stage1_candidates[architecture_id])
        base["stage"] = "stage2"
        base["theta_substrate"] = theta
        base["fruit_load_multiplier"] = float(base.get("fruit_load_multiplier", 1.0))
        design.append(dict(base))
        for axis, values in axes.items():
            if not isinstance(values, list):
                continue
            if axis.startswith("reserve_") and base["reserve_buffer_mode"] == "off":
                continue
            if axis.startswith("fruit_abort_") and base["fruit_feedback_mode"] == "off":
                continue
            if axis == "thorp_root_blend" and base["thorp_root_correction_mode"] == "off":
                continue
            base_value = base.get(axis)
            for value in values:
                if base_value is not None and float(value) == float(base_value):
                    continue
                row = dict(base)
                row[axis] = float(value)
                row["architecture_id"] = f"{architecture_id}__{axis}_{str(value).replace('.', 'p')}"
                design.append(row)
    return design


def _design_stage3(config: dict[str, Any], selected_row: dict[str, object]) -> list[dict[str, object]]:
    theta_map = _as_dict(_as_dict(config.get("stage3")).get("theta_substrate"))
    fruit_load_map = _as_dict(_as_dict(config.get("stage3")).get("fruit_load_regimes"))
    baselines = [
        {
            "architecture_id": "legacy_baseline",
            "partition_policy": "legacy",
            **_candidate_factor_defaults(),
        },
        {
            "architecture_id": "raw_thorp_like",
            "partition_policy": "thorp_fruit_veg",
            **_candidate_factor_defaults(),
            "root_representation_mode": "bounded_explicit_root",
            "thorp_root_correction_mode": "bounded",
        },
        {
            "architecture_id": "shipped_default_tomics",
            "partition_policy": "tomics",
            **_candidate_factor_defaults(),
        },
        dict(selected_row),
    ]
    design: list[dict[str, object]] = []
    for arch in baselines:
        for scenario_id, theta in theta_map.items():
            for fruit_regime, multiplier in fruit_load_map.items():
                row = dict(arch)
                row["stage"] = "stage3"
                row["scenario_id"] = str(scenario_id)
                row["theta_substrate"] = float(theta)
                row["fruit_load_regime"] = str(fruit_regime)
                row["fruit_load_multiplier"] = float(multiplier)
                design.append(row)
    return design


def _row_to_params(row: dict[str, object]) -> dict[str, object]:
    params = {
        key: row[key]
        for key in (
            "architecture_id",
            *FACTOR_COLUMNS,
            "wet_root_cap",
            "dry_root_cap",
            "lai_target_center",
            "lai_target_half_band",
            "leaf_fraction_of_shoot_base",
            "min_leaf_fraction_of_shoot",
            "max_leaf_fraction_of_shoot",
            "leaf_fraction_floor",
            "smoothing_tau_days",
            "thorp_root_blend",
            "fruit_feedback_threshold",
            "fruit_feedback_slope",
            "storage_capacity_g_ch2o_m2",
            "storage_carryover_fraction",
            "buffer_capacity_g_ch2o_m2",
            "buffer_min_fraction",
            "fruit_load_multiplier",
        )
        if key in row
    }
    return {str(key): value for key, value in params.items()}


def _config_for_row(base_config: dict[str, Any], row: dict[str, object]) -> dict[str, Any]:
    config = copy.deepcopy(base_config)
    pipeline_cfg = config.setdefault("pipeline", {})
    pipeline_cfg["partition_policy"] = row["partition_policy"]
    pipeline_cfg["allocation_scheme"] = row["allocation_scheme"]
    pipeline_cfg["theta_substrate"] = row["theta_substrate"]
    pipeline_cfg["partition_policy_params"] = {
        **_base_pipeline_params(base_config),
        **_row_to_params(row),
    }
    return config


def _prepare_repeated_forcing(
    config: dict[str, Any],
    *,
    repo_root: Path,
    config_path: Path,
    output_root: Path,
) -> dict[str, Any]:
    forcing_cfg = _as_dict(config.get("forcing"))
    repeat_cycles = int(forcing_cfg.get("repeat_cycles", 1) or 1)
    if repeat_cycles <= 1:
        return config

    forcing_path = resolve_forcing_path(config, repo_root=repo_root, config_path=config_path)
    source_df = pd.read_csv(forcing_path)
    if source_df.empty:
        return config

    dt_s = float(forcing_cfg.get("default_dt_s", 6.0 * 3600.0))
    start_timestamp = pd.to_datetime(source_df["datetime"].iloc[0]) if "datetime" in source_df.columns else pd.Timestamp("2026-01-01T00:00:00")
    rows: list[dict[str, object]] = []
    total_rows = source_df.shape[0] * repeat_cycles
    for idx in range(total_rows):
        row = source_df.iloc[idx % source_df.shape[0]].to_dict()
        row["datetime"] = (start_timestamp + pd.to_timedelta(idx * dt_s, unit="s")).isoformat()
        rows.append(row)

    repeated_df = pd.DataFrame(rows)
    repeated_path = output_root / "_forcing_repeated.csv"
    repeated_df.to_csv(repeated_path, index=False)

    updated = copy.deepcopy(config)
    updated.setdefault("forcing", {})
    updated["forcing"]["csv_path"] = str(repeated_path)
    configured_max_steps = int(updated["forcing"].get("max_steps", total_rows) or total_rows)
    updated["forcing"]["max_steps"] = min(configured_max_steps, total_rows)
    return updated


def _baseline_key(row: dict[str, object]) -> tuple[float, str, float]:
    return (float(row["theta_substrate"]), str(row["allocation_scheme"]), float(row.get("fruit_load_multiplier", 1.0)))


def _canopy_collapse_days(df: pd.DataFrame, *, lai_floor: float, leaf_fraction_floor: float) -> int:
    if df.empty:
        return 0
    work = df.copy()
    work["date"] = pd.to_datetime(work["datetime"]).dt.date
    active = (pd.to_numeric(work.get("active_trusses", 0.0), errors="coerce").fillna(0.0) > 0.0) | (
        pd.to_numeric(work.get("fruit_dry_weight_g_m2", 0.0), errors="coerce").fillna(0.0) > 0.0
    )
    collapse = active & (
        (pd.to_numeric(work.get("LAI", 0.0), errors="coerce").fillna(0.0) < lai_floor)
        | (pd.to_numeric(work.get("alloc_frac_leaf", 0.0), errors="coerce").fillna(0.0) < leaf_fraction_floor)
    )
    return int(collapse.groupby(work["date"]).any().sum())


def _run_metrics(row: dict[str, object], df: pd.DataFrame, legacy_df: pd.DataFrame, runtime_seconds: float, study_cfg: dict[str, Any]) -> dict[str, object]:
    alloc = pd.to_numeric(df[["alloc_frac_fruit", "alloc_frac_leaf", "alloc_frac_stem", "alloc_frac_root"]].stack(), errors="coerce") if {"alloc_frac_fruit", "alloc_frac_leaf", "alloc_frac_stem", "alloc_frac_root"}.issubset(df.columns) else pd.Series(dtype=float)
    wet_theta_threshold = float(study_cfg.get("wet_theta_threshold", 0.40))
    wet_root_cap = float(row.get("wet_root_cap", 0.10))
    mean_root = float(pd.to_numeric(df.get("alloc_frac_root"), errors="coerce").mean()) if "alloc_frac_root" in df else 0.0
    wet_penalty = max(mean_root - wet_root_cap, 0.0) if float(row["theta_substrate"]) >= wet_theta_threshold else 0.0
    metrics = {
        "architecture_id": row["architecture_id"],
        "stage": row["stage"],
        "scenario_id": row.get("scenario_id", ""),
        "fruit_load_regime": row.get("fruit_load_regime", ""),
        "partition_policy": row["partition_policy"],
        **{name: row.get(name) for name in FACTOR_COLUMNS},
        "mean_alloc_frac_fruit": float(pd.to_numeric(df.get("alloc_frac_fruit"), errors="coerce").mean()),
        "mean_alloc_frac_leaf": float(pd.to_numeric(df.get("alloc_frac_leaf"), errors="coerce").mean()),
        "mean_alloc_frac_stem": float(pd.to_numeric(df.get("alloc_frac_stem"), errors="coerce").mean()),
        "mean_alloc_frac_root": mean_root,
        "final_lai": float(pd.to_numeric(df.get("LAI"), errors="coerce").iloc[-1]),
        "final_total_dry_weight": float(pd.to_numeric(df.get("total_dry_weight_g_m2"), errors="coerce").iloc[-1]),
        "final_fruit_dry_weight": float(pd.to_numeric(df.get("fruit_dry_weight_g_m2"), errors="coerce").iloc[-1]),
        "fruit_anchor_error_vs_legacy": abs(
            float(pd.to_numeric(df.get("alloc_frac_fruit"), errors="coerce").mean())
            - float(pd.to_numeric(legacy_df.get("alloc_frac_fruit"), errors="coerce").mean())
        ),
        "canopy_collapse_days": _canopy_collapse_days(
            df,
            lai_floor=float(study_cfg.get("canopy_lai_floor", 2.0)),
            leaf_fraction_floor=float(study_cfg.get("leaf_fraction_floor", 0.18)),
        ),
        "mean_water_supply_stress": float(pd.to_numeric(df.get("water_supply_stress"), errors="coerce").mean()),
        "mean_theta_substrate": float(pd.to_numeric(df.get("theta_substrate"), errors="coerce").mean()),
        "wet_condition_root_excess_penalty": wet_penalty,
        "nonfinite_flag": int(not alloc.empty and not alloc.dropna().map(math.isfinite).all()),
        "negative_fraction_flag": int(not alloc.empty and (alloc.dropna() < -1e-9).any()),
        "sum_to_one_error": abs(
            float(
                (
                    pd.to_numeric(df.get("alloc_frac_fruit"), errors="coerce")
                    + pd.to_numeric(df.get("alloc_frac_leaf"), errors="coerce")
                    + pd.to_numeric(df.get("alloc_frac_stem"), errors="coerce")
                    + pd.to_numeric(df.get("alloc_frac_root"), errors="coerce")
                ).mean()
            )
            - 1.0
        ),
        "runtime_seconds": runtime_seconds,
        "reserve_pool_mean": float(pd.to_numeric(df.get("reserve_pool_g_m2"), errors="coerce").mean()),
        "reserve_pool_peak": float(pd.to_numeric(df.get("reserve_pool_g_m2"), errors="coerce").max()),
        "buffer_pool_mean": float(pd.to_numeric(df.get("buffer_pool_g_m2"), errors="coerce").mean()),
        "buffer_pool_peak": float(pd.to_numeric(df.get("buffer_pool_g_m2"), errors="coerce").max()),
        "fruit_abort_fraction": float(pd.to_numeric(df.get("fruit_abort_fraction"), errors="coerce").mean()),
        "fruit_set_feedback_events": float(pd.to_numeric(df.get("fruit_set_feedback_events"), errors="coerce").sum()),
        "mean_stage_residence_time": float(pd.to_numeric(df.get("mean_stage_residence_time_d"), errors="coerce").mean()),
        "maintenance_respiration_share": float(pd.to_numeric(df.get("maintenance_respiration_share"), errors="coerce").mean()),
    }
    metrics["score"] = _score_metrics(pd.Series(metrics))
    return metrics


def _interaction_summary(metrics_df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for factor in FACTOR_COLUMNS:
        for level, group in metrics_df.groupby(factor, dropna=False):
            rows.append({"factor": factor, "level": level, "count": int(group.shape[0]), "mean_score": float(group["score"].mean())})
    return pd.DataFrame(rows)


def _candidate_ranking(metrics_df: pd.DataFrame) -> pd.DataFrame:
    return (
        metrics_df[
            metrics_df["partition_policy"].isin(["tomics_architecture_research", "tomics_alloc_research"])
            & metrics_df["stage"].isin(["stage1", "stage2"])
        ]
        .groupby("architecture_id", as_index=False)
        .agg(mean_score=("score", "mean"), mean_final_fruit_dry_weight=("final_fruit_dry_weight", "mean"), mean_canopy_collapse_days=("canopy_collapse_days", "mean"))
        .sort_values("mean_score", ascending=False)
    )


def _plot_metric(metrics_df: pd.DataFrame, out_path: Path, spec_path: Path) -> dict[str, str]:
    artifacts = render_architecture_summary_bundle(
        metrics_df=metrics_df,
        out_path=out_path,
        spec_path=spec_path,
    )
    return artifacts.to_summary()


def _plot_main_effects(interactions_df: pd.DataFrame, out_path: Path, spec_path: Path) -> dict[str, str]:
    artifacts = render_main_effects_bundle(
        interactions_df=interactions_df,
        out_path=out_path,
        spec_path=spec_path,
    )
    return artifacts.to_summary()


def main() -> int:
    parser = argparse.ArgumentParser(description="Run staged TOMICS allocation architecture screening.")
    parser.add_argument("--config", default="configs/exp/tomics_allocation_factorial.yaml")
    parser.add_argument("--output-root", default=None)
    args = parser.parse_args()

    config_path = Path(args.config).resolve()
    config = load_config(config_path)
    repo_root = resolve_repo_root(config, config_path=config_path)
    output_root = ensure_dir(_resolve_output_root(config, repo_root, args.output_root))
    summary_spec_path = _resolve_plot_spec_path(
        config,
        repo_root,
        key="summary_plot_spec",
        default_path=DEFAULT_ALLOCATION_SUMMARY_SPEC_PATH,
    )
    main_effects_spec_path = _resolve_plot_spec_path(
        config,
        repo_root,
        key="main_effects_plot_spec",
        default_path=DEFAULT_ALLOCATION_MAIN_EFFECTS_SPEC_PATH,
    )
    config = _prepare_repeated_forcing(
        config,
        repo_root=repo_root,
        config_path=config_path,
        output_root=output_root,
    )
    study_cfg = _as_dict(config.get("study"))

    equation_trace_df = pd.DataFrame(equation_traceability_rows())
    equation_trace_df.to_csv(output_root / "equation_traceability.csv", index=False)

    baseline_cache: dict[tuple[float, str, float], pd.DataFrame] = {}
    design_rows = _design_stage1(config)
    metrics_rows: list[dict[str, object]] = []

    def run_and_record(row: dict[str, object]) -> None:
        run_cfg = _config_for_row(config, row)
        start = time.perf_counter()
        df = run_tomato_legacy_pipeline(run_cfg, repo_root=repo_root, config_path=config_path)
        runtime = time.perf_counter() - start
        key = _baseline_key(row)
        if key not in baseline_cache:
            baseline_cfg = _config_for_row(config, {**row, "partition_policy": "legacy"})
            baseline_cache[key] = run_tomato_legacy_pipeline(baseline_cfg, repo_root=repo_root, config_path=config_path)
        metrics_rows.append(_run_metrics(row, df, baseline_cache[key], runtime, study_cfg))

    for row in design_rows:
        run_and_record(row)

    stage1_df = pd.DataFrame(metrics_rows)
    shortlist = _select_shortlist(stage1_df, int(study_cfg.get("shortlist_count", 2)))
    stage2_design = _design_stage2(config, shortlist["architecture_id"].tolist())
    for row in stage2_design:
        design_rows.append(row)
        run_and_record(row)

    ranking = _candidate_ranking(pd.DataFrame(metrics_rows))
    if ranking.empty:
        selected_architecture_id = str(_candidate_rows(config)[0]["architecture_id"])
    else:
        selected_architecture_id = str(ranking.iloc[0]["architecture_id"])
    selected_row = next(row for row in stage2_design + _candidate_rows(config) if row["architecture_id"] == selected_architecture_id or row["architecture_id"].startswith(f"{selected_architecture_id}__"))
    stage3_design = _design_stage3(config, selected_row)
    for row in stage3_design:
        design_rows.append(row)
        run_and_record(row)

    design_df = pd.DataFrame(design_rows)
    metrics_df = pd.DataFrame(metrics_rows)
    screening_metrics_df = metrics_df[metrics_df["stage"].isin(["stage1", "stage2"])].copy()
    interaction_df = _interaction_summary(screening_metrics_df)
    ranking_df = _candidate_ranking(screening_metrics_df)

    design_df.index = range(1, len(design_df) + 1)
    design_df.index.name = "design_id"
    design_df.to_csv(output_root / "design_table.csv")
    metrics_df.to_csv(output_root / "run_metrics.csv", index=False)
    interaction_df.to_csv(output_root / "interaction_summary.csv", index=False)
    ranking_df.to_csv(output_root / "candidate_ranking.csv", index=False)
    summary_plot = _plot_metric(metrics_df, output_root / "summary_plot.png", summary_spec_path)
    main_effects_plot = _plot_main_effects(interaction_df, output_root / "main_effects.png", main_effects_spec_path)

    selected_payload = {
        "selected_architecture_id": selected_architecture_id,
        "selected_architecture": selected_row,
        "shortlisted_architecture_ids": shortlist["architecture_id"].tolist(),
        "selection_basis": "Highest mean stage1/stage2 score before stage3 confirmation matrix.",
        "reduced_design_rationale": {
            "stage1": "Source-derived architecture candidates across dry, moderate, and wet substrate scenarios.",
            "stage2": "One-at-a-time parameter perturbations around shortlisted research candidates.",
            "stage3": "Confirmation matrix against legacy, raw THORP-like, shipped TOMICS, and the selected research candidate.",
        },
        "recommended_status": "research-only next architecture candidate",
        "equation_traceability_csv": str(output_root / "equation_traceability.csv"),
    }
    write_json(output_root / "selected_architecture.json", selected_payload)
    decision_bundle = "\n".join(
        [
            "# TOMICS Allocation Decision Bundle",
            "",
            "Reduced design rationale:",
            "- Stage 1 screens source-derived candidate architectures across wet/moderate/dry substrate states.",
            "- Stage 2 uses one-at-a-time perturbations around shortlisted candidates instead of a full cartesian sweep.",
            "- Stage 3 confirms legacy, raw THORP, shipped TOMICS, and the selected research candidate across root-zone and fruit-load scenarios.",
            "",
            f"Selected architecture: `{selected_architecture_id}`",
            f"- Mean score: {0.0 if ranking_df.empty else float(ranking_df.iloc[0]['mean_score']):.4f}",
            f"- Mean final fruit dry weight: {0.0 if ranking_df.empty else float(ranking_df.iloc[0]['mean_final_fruit_dry_weight']):.4f}",
            f"- Mean canopy collapse days: {0.0 if ranking_df.empty else float(ranking_df.iloc[0]['mean_canopy_collapse_days']):.4f}",
            "",
            "Canopy collapse definition:",
            f"- A day counts as collapse if active fruiting is present and either LAI < {float(study_cfg.get('canopy_lai_floor', 2.0)):.2f} or leaf allocation fraction < {float(study_cfg.get('leaf_fraction_floor', 0.18)):.2f}.",
        ]
    )
    (output_root / "decision_bundle.md").write_text(decision_bundle, encoding="utf-8")

    print(
        json.dumps(
            {
                "output_root": str(output_root),
                "design_table_csv": str(output_root / "design_table.csv"),
                "run_metrics_csv": str(output_root / "run_metrics.csv"),
                "interaction_summary_csv": str(output_root / "interaction_summary.csv"),
                "candidate_ranking_csv": str(output_root / "candidate_ranking.csv"),
                "selected_architecture_json": str(output_root / "selected_architecture.json"),
                "decision_bundle_md": str(output_root / "decision_bundle.md"),
                "equation_traceability_csv": str(output_root / "equation_traceability.csv"),
                "summary_plot": str(output_root / "summary_plot.png"),
                "summary_plot_metadata": summary_plot.get("metadata"),
                "main_effects_plot": str(output_root / "main_effects.png"),
                "main_effects_plot_metadata": main_effects_plot.get("metadata"),
                "selected_architecture": selected_architecture_id,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
