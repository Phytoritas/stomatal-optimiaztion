from __future__ import annotations

import copy
import json
import math
import time
from pathlib import Path
from typing import Any

import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.alloc.core import ensure_dir, write_json
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.current_vs_promoted import (
    PreparedKnuBundle,
    configure_candidate_run,
    prepare_knu_bundle,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.harvest_calibration_bridge import (
    HarvestDesignRow,
    load_harvest_base_config,
    load_harvest_candidates,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.harvest_family_eval import (
    HarvestFamilyRunResult,
    build_harvest_mass_balance_overlay_frame,
    build_harvest_overlay_frame,
    run_harvest_family_simulation,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.harvest_family_summary import (
    rank_harvest_candidates,
    score_harvest_row,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.metrics import REPORTING_BASIS_FLOOR_AREA
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.observation_model import (
    validation_overlay_frame,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.state_reconstruction import (
    reconstruct_hidden_state,
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


def _stage_hf1_rows(candidates_by_label: dict[str, object]) -> list[HarvestDesignRow]:
    shipped = candidates_by_label["shipped_tomics"]
    return [
        HarvestDesignRow(
            stage="HF1",
            allocator_family="shipped_tomics",
            candidate_label=shipped.candidate_label,
            architecture_id=shipped.architecture_id,
            fruit_harvest_family="tomsim_truss",
            leaf_harvest_family="linked_truss_stage",
            fdmc_mode="constant_observed_mean",
            harvest_delay_days=0.0,
            harvest_readiness_threshold=1.0,
            fruit_params={"tdvs_harvest_threshold": 1.0},
            leaf_params={"linked_leaf_stage": 0.9},
            candidate_row=shipped.row,
        ),
        HarvestDesignRow(
            stage="HF1",
            allocator_family="shipped_tomics",
            candidate_label=shipped.candidate_label,
            architecture_id=shipped.architecture_id,
            fruit_harvest_family="tomgro_ageclass",
            leaf_harvest_family="vegetative_unit_pruning",
            fdmc_mode="constant_observed_mean",
            harvest_delay_days=0.0,
            harvest_readiness_threshold=20.0,
            fruit_params={"mature_class_index": 20},
            leaf_params={"colour_threshold": 0.9},
            candidate_row=shipped.row,
        ),
        HarvestDesignRow(
            stage="HF1",
            allocator_family="shipped_tomics",
            candidate_label=shipped.candidate_label,
            architecture_id=shipped.architecture_id,
            fruit_harvest_family="dekoning_fds",
            leaf_harvest_family="vegetative_unit_pruning",
            fdmc_mode="dekoning_fds",
            harvest_delay_days=0.0,
            harvest_readiness_threshold=1.0,
            fruit_params={"fds_harvest_threshold": 1.0, "fdmc_mode": "dekoning_fds"},
            leaf_params={"colour_threshold": 0.9},
            candidate_row=shipped.row,
        ),
        HarvestDesignRow(
            stage="HF1",
            allocator_family="shipped_tomics",
            candidate_label=shipped.candidate_label,
            architecture_id=shipped.architecture_id,
            fruit_harvest_family="vanthoor_boxcar",
            leaf_harvest_family="max_lai_pruning_flow",
            fdmc_mode="constant_observed_mean",
            harvest_delay_days=0.0,
            harvest_readiness_threshold=5.0,
            fruit_params={"n_dev": 5, "outflow_fraction_per_day": 1.0},
            leaf_params={"max_lai": 3.0},
            candidate_row=shipped.row,
        ),
    ]


def _shortlist_research_families(hf1_ranking_df: pd.DataFrame, *, count: int = 2) -> list[tuple[str, str, str]]:
    shortlisted: list[tuple[str, str, str]] = []
    for _, row in hf1_ranking_df.iterrows():
        family = str(row["fruit_harvest_family"])
        if family == "tomsim_truss":
            continue
        shortlisted.append((family, str(row["leaf_harvest_family"]), str(row["fdmc_mode"])))
        if len(shortlisted) >= count:
            break
    return shortlisted


def _family_only_ranking(metrics_df: pd.DataFrame, *, stages: list[str] | None = None) -> pd.DataFrame:
    return rank_harvest_candidates(
        metrics_df,
        candidate_columns=["fruit_harvest_family", "leaf_harvest_family", "fdmc_mode"],
        stages=stages,
    )


def _match_row_family(
    row: HarvestDesignRow,
    *,
    fruit_harvest_family: str,
    leaf_harvest_family: str,
    fdmc_mode: str,
) -> bool:
    return (
        row.fruit_harvest_family == fruit_harvest_family
        and row.leaf_harvest_family == leaf_harvest_family
        and row.fdmc_mode == fdmc_mode
    )


def _stage_hf2_rows(
    candidates_by_label: dict[str, object],
    *,
    shortlisted: list[tuple[str, str, str]],
) -> list[HarvestDesignRow]:
    rows: list[HarvestDesignRow] = []
    all_families = [("tomsim_truss", "linked_truss_stage", "constant_observed_mean"), *shortlisted]
    for candidate_key in ("shipped_tomics", "current_selected", "promoted_selected"):
        candidate = candidates_by_label[candidate_key]
        for fruit_family, leaf_family, fdmc_mode in all_families:
            threshold = 1.0 if fruit_family in {"tomsim_truss", "dekoning_fds"} else (20.0 if fruit_family == "tomgro_ageclass" else 5.0)
            fruit_params: dict[str, object]
            leaf_params: dict[str, object]
            if fruit_family == "tomsim_truss":
                fruit_params = {"tdvs_harvest_threshold": 1.0}
                leaf_params = {"linked_leaf_stage": 0.9}
            elif fruit_family == "tomgro_ageclass":
                fruit_params = {"mature_class_index": 20}
                leaf_params = {"colour_threshold": 0.9}
            elif fruit_family == "dekoning_fds":
                fruit_params = {"fds_harvest_threshold": 1.0, "fdmc_mode": fdmc_mode}
                leaf_params = {"colour_threshold": 0.9}
            else:
                fruit_params = {"n_dev": 5, "outflow_fraction_per_day": 1.0}
                leaf_params = {"max_lai": 3.0}
            rows.append(
                HarvestDesignRow(
                    stage="HF2",
                    allocator_family=candidate_key,
                    candidate_label=candidate.candidate_label,
                    architecture_id=candidate.architecture_id,
                    fruit_harvest_family=fruit_family,
                    leaf_harvest_family=leaf_family,
                    fdmc_mode=fdmc_mode,
                    harvest_delay_days=0.0,
                    harvest_readiness_threshold=threshold,
                    fruit_params=fruit_params,
                    leaf_params=leaf_params,
                    candidate_row=candidate.row,
                )
            )
    return rows


def _stage_hf3_rows(best_row: HarvestDesignRow) -> list[HarvestDesignRow]:
    threshold_axis = {
        "tomsim_truss": [0.95, 1.0, 1.05],
        "dekoning_fds": [0.95, 1.0, 1.05],
        "tomgro_ageclass": [18.0, 20.0, 22.0],
        "vanthoor_boxcar": [4.0, 5.0, 6.0],
    }[best_row.fruit_harvest_family]
    delay_axis = [0.0, 1.0, 3.0]
    rows: list[HarvestDesignRow] = []
    for threshold in threshold_axis:
        for delay in delay_axis:
            fruit_params = dict(best_row.fruit_params)
            if best_row.fruit_harvest_family == "tomsim_truss":
                fruit_params["tdvs_harvest_threshold"] = threshold
                fruit_params["harvest_delay_days"] = delay
            elif best_row.fruit_harvest_family == "dekoning_fds":
                fruit_params["fds_harvest_threshold"] = threshold
                fruit_params["harvest_delay_days"] = delay
            elif best_row.fruit_harvest_family == "tomgro_ageclass":
                fruit_params["mature_class_index"] = int(threshold)
            else:
                fruit_params["n_dev"] = int(threshold)
                fruit_params["outflow_fraction_per_day"] = 1.0 / max(delay + 1.0, 1.0)
            rows.append(
                HarvestDesignRow(
                    stage="HF3",
                    allocator_family=best_row.allocator_family,
                    candidate_label=best_row.candidate_label,
                    architecture_id=best_row.architecture_id,
                    fruit_harvest_family=best_row.fruit_harvest_family,
                    leaf_harvest_family=best_row.leaf_harvest_family,
                    fdmc_mode=best_row.fdmc_mode,
                    harvest_delay_days=delay,
                    harvest_readiness_threshold=float(threshold),
                    fruit_params=fruit_params,
                    leaf_params=dict(best_row.leaf_params),
                    candidate_row=dict(best_row.candidate_row),
                )
            )
    return rows


def _design_frame(rows: list[HarvestDesignRow]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "stage": row.stage,
                "allocator_family": row.allocator_family,
                "candidate_label": row.candidate_label,
                "architecture_id": row.architecture_id,
                "fruit_harvest_family": row.fruit_harvest_family,
                "leaf_harvest_family": row.leaf_harvest_family,
                "fdmc_mode": row.fdmc_mode,
                "harvest_delay_days": row.harvest_delay_days,
                "harvest_readiness_threshold": row.harvest_readiness_threshold,
                "candidate_key": row.candidate_key,
                "fruit_params_json": json.dumps(row.fruit_params, sort_keys=True),
                "leaf_params_json": json.dumps(row.leaf_params, sort_keys=True),
            }
            for row in rows
        ]
    )


def _run_design_rows(
    rows: list[HarvestDesignRow],
    *,
    prepared_bundle: PreparedKnuBundle,
    base_config: dict[str, Any],
    repo_root: Path,
    theta_center: float,
    forcing_csv_path: Path,
) -> tuple[pd.DataFrame, dict[str, HarvestFamilyRunResult]]:
    recon_cache: dict[str, dict[str, object]] = {}
    results: dict[str, HarvestFamilyRunResult] = {}
    metrics_rows: list[dict[str, object]] = []
    for row in rows:
        cache_key = row.candidate_label
        if cache_key not in recon_cache:
            reconstruction = reconstruct_hidden_state(
                architecture_row=row.candidate_row,
                base_config=copy.deepcopy(base_config),
                forcing_csv_path=forcing_csv_path,
                theta_center=theta_center,
                observed_df=prepared_bundle.observed_df,
                calibration_end=prepared_bundle.calibration_end,
                repo_root=repo_root,
                unit_label=prepared_bundle.data.observation_unit_label,
            )
            recon_cache[cache_key] = dict(reconstruction.initial_state_overrides)
        run_cfg = configure_candidate_run(
            base_config=copy.deepcopy(base_config),
            forcing_csv_path=forcing_csv_path,
            theta_center=theta_center,
            row=row.candidate_row,
            initial_state_overrides=dict(recon_cache[cache_key]),
        )
        started = time.perf_counter()
        result = run_harvest_family_simulation(
            run_config=run_cfg,
            observed_df=prepared_bundle.observed_df,
            unit_label=prepared_bundle.data.observation_unit_label,
            repo_root=repo_root,
            fruit_harvest_family=row.fruit_harvest_family,
            leaf_harvest_family=row.leaf_harvest_family,
            fdmc_mode=row.fdmc_mode,
            fruit_params=row.fruit_params,
            leaf_params=row.leaf_params,
        )
        runtime_seconds = time.perf_counter() - started
        results[row.candidate_key] = result
        alloc = pd.to_numeric(
            result.run_df[["alloc_frac_fruit", "alloc_frac_leaf", "alloc_frac_stem", "alloc_frac_root"]].stack(),
            errors="coerce",
        )
        metrics_row = {
            "stage": row.stage,
            "allocator_family": row.allocator_family,
            "candidate_label": row.candidate_label,
            "candidate_key": row.candidate_key,
            "architecture_id": row.architecture_id,
            "fruit_harvest_family": row.fruit_harvest_family,
            "leaf_harvest_family": row.leaf_harvest_family,
            "fdmc_mode": row.fdmc_mode,
            "harvest_delay_days": row.harvest_delay_days,
            "harvest_readiness_threshold": row.harvest_readiness_threshold,
            "reporting_basis": REPORTING_BASIS_FLOOR_AREA,
            "rmse_cumulative_raw": result.metrics["rmse_cumulative_raw"],
            "rmse_cumulative_offset": result.metrics["rmse_cumulative_offset"],
            "mae_cumulative_offset": result.metrics["mae_cumulative_offset"],
            "r2_cumulative_offset": result.metrics["r2_cumulative_offset"],
            "rmse_daily_increment": result.metrics["rmse_daily_increment"],
            "mae_daily_increment": result.metrics["mae_daily_increment"],
            "harvest_timing_mae_days": result.metrics["harvest_timing_mae_days"],
            "final_cumulative_bias": result.metrics["final_cumulative_bias"],
            "final_cumulative_bias_pct": result.metrics["final_cumulative_bias_pct"],
            "harvest_mass_balance_error": result.metrics["harvest_mass_balance_error"],
            "latent_fruit_residual_end": result.metrics["latent_fruit_residual_end"],
            "leaf_harvest_mass_balance_error": result.metrics["leaf_harvest_mass_balance_error"],
            "canopy_collapse_days": result.metrics["canopy_collapse_days"],
            "fruit_anchor_error_vs_legacy": math.nan,
            "wet_condition_root_excess_penalty": 0.0,
            "winner_stability_score": math.nan,
            "mean_alloc_frac_fruit": float(pd.to_numeric(result.run_df["alloc_frac_fruit"], errors="coerce").mean()),
            "mean_alloc_frac_leaf": float(pd.to_numeric(result.run_df["alloc_frac_leaf"], errors="coerce").mean()),
            "mean_alloc_frac_stem": float(pd.to_numeric(result.run_df["alloc_frac_stem"], errors="coerce").mean()),
            "mean_alloc_frac_root": float(pd.to_numeric(result.run_df["alloc_frac_root"], errors="coerce").mean()),
            "nonfinite_flag": int(not alloc.dropna().map(math.isfinite).all()),
            "invalid_run_flag": int(float(result.metrics["harvest_mass_balance_error"]) > 1e-4),
            "runtime_seconds": runtime_seconds,
        }
        metrics_row["score"] = score_harvest_row(pd.Series(metrics_row))
        metrics_rows.append(metrics_row)
    return pd.DataFrame(metrics_rows), results


def _select_overlay_runs(
    metrics_df: pd.DataFrame,
    results: dict[str, HarvestFamilyRunResult],
    *,
    prepared_bundle: PreparedKnuBundle,
) -> tuple[dict[str, pd.DataFrame], dict[str, pd.DataFrame], dict[str, pd.DataFrame]]:
    cumulative_runs = {
        "measured": validation_overlay_frame(prepared_bundle.observed_df.rename(
            columns={
                "measured_cumulative_total_fruit_dry_weight_floor_area": "measured_cumulative_total_fruit_dry_weight_floor_area",
                "measured_offset_adjusted": "measured_offset_adjusted",
                "measured_daily_increment_floor_area": "measured_daily_increment_floor_area",
            }
        ), source_label="measured"),
        "workbook_estimated": validation_overlay_frame(prepared_bundle.workbook_validation_df, source_label="workbook_estimated"),
    }
    mass_runs: dict[str, pd.DataFrame] = {}
    top_rows = metrics_df.sort_values(["score", "rmse_cumulative_offset"], ascending=[False, True]).head(4).copy()
    label_map = ["baseline", "research_1", "research_2", "research_3"]
    for (_, ranking_row), source_label in zip(top_rows.iterrows(), label_map, strict=False):
        result = results.get(str(ranking_row["candidate_key"]))
        if result is None:
            continue
        cumulative_runs[source_label] = build_harvest_overlay_frame(result.validation_df, source_label="model")
        mass_runs[source_label] = build_harvest_mass_balance_overlay_frame(result.harvest_mass_balance_df)
    return cumulative_runs, cumulative_runs, mass_runs


def run_harvest_family_factorial(
    config: dict[str, Any],
    *,
    repo_root: Path,
    config_path: Path,
) -> dict[str, object]:
    prepared_bundle = prepare_knu_bundle(config, repo_root=repo_root, config_path=config_path)
    candidates, reference_meta = load_harvest_candidates(config=config, repo_root=repo_root, config_path=config_path)
    candidates_by_label = {candidate.candidate_label: candidate for candidate in candidates}
    base_config = load_harvest_base_config(reference_meta)
    scenario_id = str(_as_dict(config.get("harvest_factorial")).get("theta_proxy_scenario", "moderate"))
    scenario = prepared_bundle.scenarios[scenario_id]
    output_root = ensure_dir(
        _resolve_config_path(
            _as_dict(config.get("harvest_factorial")).get("output_root", "out/tomics_knu_harvest_family_factorial"),
            repo_root=repo_root,
            config_path=config_path,
        )
    )

    hf1_rows = _stage_hf1_rows(candidates_by_label)
    hf1_metrics_df, hf1_results = _run_design_rows(
        hf1_rows,
        prepared_bundle=prepared_bundle,
        base_config=base_config,
        repo_root=repo_root,
        theta_center=float(scenario.summary.get("theta_mean", 0.65)),
        forcing_csv_path=scenario.forcing_csv_path,
    )
    hf1_ranking = rank_harvest_candidates(hf1_metrics_df, stages=["HF1"])
    shortlisted = _shortlist_research_families(hf1_ranking, count=2)

    hf2_rows = _stage_hf2_rows(candidates_by_label, shortlisted=shortlisted)
    hf2_metrics_df, hf2_results = _run_design_rows(
        hf2_rows,
        prepared_bundle=prepared_bundle,
        base_config=base_config,
        repo_root=repo_root,
        theta_center=float(scenario.summary.get("theta_mean", 0.65)),
        forcing_csv_path=scenario.forcing_csv_path,
    )
    hf2_family_ranking = _family_only_ranking(
        hf2_metrics_df.loc[hf2_metrics_df["fruit_harvest_family"].ne("tomsim_truss")].copy(),
        stages=["HF2"],
    )
    best_hf2_family = hf2_family_ranking.iloc[0]
    best_hf2_metric_row = (
        hf2_metrics_df.loc[
            hf2_metrics_df["fruit_harvest_family"].eq(str(best_hf2_family["fruit_harvest_family"]))
            & hf2_metrics_df["leaf_harvest_family"].eq(str(best_hf2_family["leaf_harvest_family"]))
            & hf2_metrics_df["fdmc_mode"].eq(str(best_hf2_family["fdmc_mode"]))
        ]
        .sort_values(["score", "rmse_cumulative_offset"], ascending=[False, True])
        .iloc[0]
    )
    best_hf2_row = next(
        row
        for row in hf2_rows
        if row.candidate_key == str(best_hf2_metric_row["candidate_key"])
    )
    hf3_rows = _stage_hf3_rows(best_hf2_row)
    hf3_metrics_df, hf3_results = _run_design_rows(
        hf3_rows,
        prepared_bundle=prepared_bundle,
        base_config=base_config,
        repo_root=repo_root,
        theta_center=float(scenario.summary.get("theta_mean", 0.65)),
        forcing_csv_path=scenario.forcing_csv_path,
    )

    design_df = _design_frame([*hf1_rows, *hf2_rows, *hf3_rows])
    metrics_df = pd.concat([hf1_metrics_df, hf2_metrics_df, hf3_metrics_df], ignore_index=True)
    ranking_df = _family_only_ranking(metrics_df, stages=["HF1", "HF2", "HF3"])
    all_results = {**hf1_results, **hf2_results, **hf3_results}
    research_metrics_df = metrics_df.loc[metrics_df["fruit_harvest_family"].ne("tomsim_truss")].copy()
    research_ranking_df = _family_only_ranking(research_metrics_df, stages=["HF1", "HF2", "HF3"])
    selected = research_ranking_df.iloc[0].to_dict() if not research_ranking_df.empty else {}
    selected_metric_row = (
        research_metrics_df.loc[
            research_metrics_df["fruit_harvest_family"].eq(str(selected.get("fruit_harvest_family", "")))
            & research_metrics_df["leaf_harvest_family"].eq(str(selected.get("leaf_harvest_family", "")))
            & research_metrics_df["fdmc_mode"].eq(str(selected.get("fdmc_mode", "")))
        ]
        .sort_values(["score", "rmse_cumulative_offset"], ascending=[False, True])
        .iloc[0]
        .to_dict()
        if selected
        else {}
    )
    selected_payload = {
        "selection_scope": "research_harvest_family_aggregated_across_allocators",
        "selected_harvest_family_id": "|".join(
            [
                str(selected.get("fruit_harvest_family", "tomsim_truss")),
                str(selected.get("leaf_harvest_family", "linked_truss_stage")),
                str(selected.get("fdmc_mode", "constant_observed_mean")),
            ]
        ),
        "selected_fruit_harvest_family": selected.get("fruit_harvest_family", "tomsim_truss"),
        "selected_leaf_harvest_family": selected.get("leaf_harvest_family", "linked_truss_stage"),
        "selected_fdmc_mode": selected.get("fdmc_mode", "constant_observed_mean"),
        "best_metric_allocator_family": selected_metric_row.get("allocator_family", "shipped_tomics"),
        "best_metric_candidate_label": selected_metric_row.get("candidate_label", "shipped_tomics"),
        "best_metric_architecture_id": selected_metric_row.get("architecture_id", "shipped_tomics_control"),
        "harvest_delay_days": selected_metric_row.get("harvest_delay_days", 0.0),
        "harvest_readiness_threshold": selected_metric_row.get("harvest_readiness_threshold", 1.0),
        "fruit_params": next(
            (
                row.fruit_params
                for row in [*hf1_rows, *hf2_rows, *hf3_rows]
                if row.candidate_key == selected_metric_row.get("candidate_key")
            ),
            {},
        ),
        "leaf_params": next(
            (
                row.leaf_params
                for row in [*hf1_rows, *hf2_rows, *hf3_rows]
                if row.candidate_key == selected_metric_row.get("candidate_key")
            ),
            {},
        ),
        "ranking_row": selected,
        "selected_metric_row": selected_metric_row,
    }
    canonical_winners = {
        "incumbent_baseline": {
            "allocator_family": "shipped_tomics",
            "fruit_harvest_family": "tomsim_truss",
            "leaf_harvest_family": "linked_truss_stage",
            "fdmc_mode": "constant_observed_mean",
        },
        "research_shortlist": [
            {
                "fruit_harvest_family": family,
                "leaf_harvest_family": leaf,
                "fdmc_mode": fdmc,
            }
            for family, leaf, fdmc in shortlisted
        ],
        "selected_research_family": selected_payload,
    }

    design_df.to_csv(output_root / "design_table.csv", index=False)
    metrics_df.to_csv(output_root / "run_metrics.csv", index=False)
    ranking_df.to_csv(output_root / "candidate_ranking.csv", index=False)
    write_json(output_root / "selected_harvest_family.json", selected_payload)
    write_json(output_root / "canonical_harvest_winners.json", canonical_winners)
    write_json(
        output_root / "harvest_family_manifest.json",
        {
            "theta_proxy_scenario": scenario_id,
            "plants_per_m2": prepared_bundle.data_contract.plants_per_m2,
            "observation_unit_label": prepared_bundle.data.observation_unit_label,
            "hf1_count": len(hf1_rows),
            "hf2_count": len(hf2_rows),
            "hf3_count": len(hf3_rows),
            "shortlisted_research_families": canonical_winners["research_shortlist"],
        },
    )
    equation_traceability = pd.DataFrame(
        [
            {
                "family": "tomsim_truss",
                "code_path": "src/stomatal_optimiaztion/domains/tomato/tomics/alloc/components/harvest/fruit_harvest_tomsim.py",
                "status": "coded",
            },
            {
                "family": "tomgro_ageclass",
                "code_path": "src/stomatal_optimiaztion/domains/tomato/tomics/alloc/components/harvest/fruit_harvest_tomgro.py",
                "status": "research_proxy",
            },
            {
                "family": "dekoning_fds",
                "code_path": "src/stomatal_optimiaztion/domains/tomato/tomics/alloc/components/harvest/fruit_harvest_dekoning.py",
                "status": "coded",
            },
            {
                "family": "vanthoor_boxcar",
                "code_path": "src/stomatal_optimiaztion/domains/tomato/tomics/alloc/components/harvest/fruit_harvest_vanthoor.py",
                "status": "coded_research",
            },
        ]
    )
    equation_traceability.to_csv(output_root / "equation_traceability.csv", index=False)

    cumulative_spec = _resolve_config_path(
        _as_dict(config.get("harvest_factorial")).get(
            "cumulative_overlay_spec",
            "configs/plotkit/tomics/knu_harvest_yield_fit_overlay.yaml",
        ),
        repo_root=repo_root,
        config_path=config_path,
    )
    daily_spec = _resolve_config_path(
        _as_dict(config.get("harvest_factorial")).get(
            "daily_overlay_spec",
            "configs/plotkit/tomics/knu_harvest_daily_increment_overlay.yaml",
        ),
        repo_root=repo_root,
        config_path=config_path,
    )
    mass_spec = _resolve_config_path(
        _as_dict(config.get("harvest_factorial")).get(
            "mass_balance_overlay_spec",
            "configs/plotkit/tomics/knu_harvest_mass_balance_overlay.yaml",
        ),
        repo_root=repo_root,
        config_path=config_path,
    )
    cumulative_runs, daily_runs, mass_runs = _select_overlay_runs(metrics_df, all_results, prepared_bundle=prepared_bundle)
    render_partition_compare_bundle(
        runs=cumulative_runs,
        out_path=output_root / "cumulative_harvest_overlay.png",
        spec_path=cumulative_spec,
    )
    render_partition_compare_bundle(
        runs=daily_runs,
        out_path=output_root / "daily_increment_overlay.png",
        spec_path=daily_spec,
    )
    render_partition_compare_bundle(
        runs=mass_runs,
        out_path=output_root / "harvest_mass_balance_overlay.png",
        spec_path=mass_spec,
    )
    return {
        "output_root": str(output_root),
        "selected_payload": selected_payload,
        "ranking_df": ranking_df,
    }


__all__ = ["run_harvest_family_factorial"]
