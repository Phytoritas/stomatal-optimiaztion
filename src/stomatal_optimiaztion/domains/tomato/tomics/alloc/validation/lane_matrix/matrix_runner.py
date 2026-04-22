from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.alloc.core import ensure_dir, write_json
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.current_vs_promoted import (
    configure_candidate_run,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.datasets.registry import (
    load_dataset_registry,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.datasets.runtime import (
    prepare_dataset_runtime_bundle,
    prepare_measured_harvest_bundle,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.harvest_calibration_bridge import (
    load_harvest_base_config,
    load_harvest_candidates,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.harvest_family_eval import (
    run_harvest_family_simulation,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.lane_matrix.allocation_lane_registry import (
    resolve_allocation_lanes,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.lane_matrix.artifact_schema import (
    LaneMatrixArtifactPaths,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.lane_matrix.dataset_role_registry import (
    resolve_dataset_roles,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.lane_matrix.harvest_profile_registry import (
    resolve_harvest_profiles,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.lane_matrix.lane_scorecard import (
    build_context_only_lane_scorecard_row,
    build_diagnostic_runtime_lane_scorecard_row,
    build_lane_scorecard_row,
    build_split_score_rows,
    finalize_lane_scorecard,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.lane_matrix.scenario import (
    ComparisonScenario,
    compose_scenarios,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.state_reconstruction import (
    reconstruct_hidden_state,
)


def _as_dict(raw: object) -> dict[str, Any]:
    if isinstance(raw, dict):
        return {str(key): value for key, value in raw.items()}
    return {}


def _as_list(raw: object) -> list[Any]:
    if isinstance(raw, list):
        return list(raw)
    return []


def _resolve_artifact_path(raw: str | Path, *, repo_root: Path) -> Path:
    candidate = Path(raw)
    if candidate.is_absolute():
        return candidate
    return (repo_root / candidate).resolve()


def _lane_matrix_config(config: dict[str, Any]) -> dict[str, Any]:
    validation_cfg = _as_dict(config.get("validation"))
    return _as_dict(validation_cfg.get("lane_matrix"))


def _requested_ids(cfg: dict[str, Any], key: str) -> list[str] | None:
    values = [str(value) for value in _as_list(cfg.get(key)) if str(value).strip()]
    return values or None


def _scenario_index_row(scenario: ComparisonScenario) -> dict[str, object]:
    dataset_assignment = scenario.dataset_role_assignment
    return {
        "scenario_id": scenario.scenario_id,
        "allocation_lane_id": scenario.allocation_lane.lane_id,
        "harvest_profile_id": scenario.harvest_profile.harvest_profile_id,
        "dataset_id": dataset_assignment.dataset_id,
        "dataset_role": dataset_assignment.dataset_role,
        "promotion_surface_eligible": bool(scenario.promotion_surface_eligible),
        "scorecard_included": bool(dataset_assignment.scorecard_included),
    }


def _write_scenario_sidecars(
    scenario: ComparisonScenario,
    *,
    scenario_root: Path,
    validation_df: pd.DataFrame,
    harvest_mass_balance_df: pd.DataFrame,
    metrics: dict[str, object],
) -> None:
    validation_df.to_csv(scenario_root / "validation_overlay.csv", index=False)
    harvest_mass_balance_df.to_csv(scenario_root / "harvest_mass_balance.csv", index=False)
    write_json(
        scenario_root / "audit.json",
        {
            "scenario_id": scenario.scenario_id,
            "allocation_lane_id": scenario.allocation_lane.lane_id,
            "harvest_profile_id": scenario.harvest_profile.harvest_profile_id,
            "dataset_id": scenario.dataset_role_assignment.dataset_id,
            "metrics": dict(metrics),
        },
    )


def _write_scenario_error_sidecar(
    scenario: ComparisonScenario,
    *,
    scenario_root: Path,
    error: Exception,
) -> None:
    write_json(
        scenario_root / "audit.json",
        {
            "scenario_id": scenario.scenario_id,
            "allocation_lane_id": scenario.allocation_lane.lane_id,
            "harvest_profile_id": scenario.harvest_profile.harvest_profile_id,
            "dataset_id": scenario.dataset_role_assignment.dataset_id,
            "error": {
                "type": type(error).__name__,
                "message": str(error),
            },
        },
    )


def _build_diagnostic_observed_df(*, validation_start: pd.Timestamp, validation_end: pd.Timestamp) -> pd.DataFrame:
    dates = pd.date_range(validation_start.normalize(), validation_end.normalize(), freq="D")
    return pd.DataFrame(
        {
            "date": dates,
            "measured_cumulative_harvested_fruit_dry_weight_floor_area": pd.Series(
                [pd.NA] * len(dates),
                dtype="Float64",
            ),
            "estimated_cumulative_harvested_fruit_dry_weight_floor_area": pd.Series(
                [pd.NA] * len(dates),
                dtype="Float64",
            ),
            "measured_cumulative_total_fruit_dry_weight_floor_area": pd.Series(
                [pd.NA] * len(dates),
                dtype="Float64",
            ),
            "estimated_cumulative_total_fruit_dry_weight_floor_area": pd.Series(
                [pd.NA] * len(dates),
                dtype="Float64",
            ),
            "measured_daily_increment_floor_area": pd.Series([pd.NA] * len(dates), dtype="Float64"),
            "estimated_daily_increment_floor_area": pd.Series([pd.NA] * len(dates), dtype="Float64"),
        }
    )


def run_lane_matrix(
    config: dict[str, Any],
    *,
    repo_root: Path,
    config_path: Path,
) -> dict[str, object]:
    validation_cfg = _as_dict(config.get("validation"))
    lane_cfg = _lane_matrix_config(config)
    output_root = ensure_dir(
        _resolve_artifact_path(
            lane_cfg.get("output_root", "out/tomics/validation/lane-matrix"),
            repo_root=repo_root,
        )
    )
    paths = LaneMatrixArtifactPaths(output_root)
    ensure_dir(paths.scenarios_root)

    registry = load_dataset_registry(config, repo_root=repo_root, config_path=config_path)
    dataset_roles = resolve_dataset_roles(
        registry,
        dataset_ids=_requested_ids(lane_cfg, "dataset_ids"),
    )
    candidates, reference_meta = load_harvest_candidates(config=config, repo_root=repo_root, config_path=config_path)
    allocation_lanes = resolve_allocation_lanes(
        candidates,
        lane_ids=_requested_ids(lane_cfg, "allocation_lane_ids"),
    )
    harvest_profiles = resolve_harvest_profiles(
        repo_root=repo_root,
        requested_ids=_requested_ids(lane_cfg, "harvest_profile_ids"),
        selected_payload_path=lane_cfg.get("selected_harvest_family_path"),
    )
    scenarios = compose_scenarios(allocation_lanes, harvest_profiles, dataset_roles)
    write_json(
        paths.matrix_spec_path,
        {
            "allocation_lane_ids": [lane.lane_id for lane in allocation_lanes],
            "harvest_profile_ids": [profile.harvest_profile_id for profile in harvest_profiles],
            "dataset_ids": [dataset.dataset_id for dataset in dataset_roles],
        },
    )
    write_json(
        paths.resolved_matrix_spec_path,
        {
            "allocation_lanes": [
                {
                    "lane_id": lane.lane_id,
                    "partition_policy": lane.partition_policy,
                    "candidate_label": lane.candidate_label,
                    "architecture_id": lane.architecture_id,
                    "promotion_eligible": lane.promotion_eligible,
                    "reference_only": lane.reference_only,
                }
                for lane in allocation_lanes
            ],
            "harvest_profiles": [
                {
                    "harvest_profile_id": profile.harvest_profile_id,
                    "fruit_harvest_family": profile.fruit_harvest_family,
                    "leaf_harvest_family": profile.leaf_harvest_family,
                    "fdmc_mode": profile.fdmc_mode,
                    "promotion_eligible": profile.promotion_eligible,
                }
                for profile in harvest_profiles
            ],
            "datasets": [
                {
                    "dataset_id": dataset.dataset_id,
                    "dataset_role": dataset.dataset_role,
                    "reporting_basis": dataset.reporting_basis,
                    "promotion_denominator_eligible": dataset.promotion_denominator_eligible,
                }
                for dataset in dataset_roles
            ],
        },
    )

    dataset_summary_df = pd.DataFrame(
        [
            {
                "dataset_id": dataset.dataset_id,
                "dataset_kind": dataset.dataset_kind,
                "display_name": dataset.display_name,
                "dataset_role": dataset.dataset_role,
                "promotion_denominator_eligible": dataset.promotion_denominator_eligible,
                "scorecard_included": dataset.scorecard_included,
                "has_measured_harvest_contract": dataset.has_measured_harvest_contract,
                "reporting_basis": dataset.reporting_basis,
                "plants_per_m2": dataset.plants_per_m2,
            }
            for dataset in dataset_roles
        ]
    )
    dataset_summary_df.to_csv(paths.dataset_role_summary_path, index=False)

    base_config = load_harvest_base_config(reference_meta)
    theta_scenario_id = str(lane_cfg.get("theta_proxy_scenario", "moderate"))
    measured_bundle_cache: dict[str, Any] = {}
    runtime_bundle_cache: dict[str, Any] = {}
    reconstruction_cache: dict[tuple[str, str], dict[str, object]] = {}
    scorecard_rows: list[dict[str, object]] = []
    split_rows: list[dict[str, object]] = []
    scenario_index_rows: list[dict[str, object]] = []

    for scenario in scenarios:
        scenario_index_rows.append(_scenario_index_row(scenario))
        scenario_root = ensure_dir(paths.scenario_root(scenario.scenario_id))
        dataset_assignment = scenario.dataset_role_assignment
        if not dataset_assignment.scorecard_included:
            scorecard_rows.append(
                build_context_only_lane_scorecard_row(
                    scenario,
                    execution_status="metadata_only",
                )
            )
            continue
        if dataset_assignment.dataset_role != "measured_harvest":
            try:
                runtime_bundle = runtime_bundle_cache.get(dataset_assignment.dataset_id)
                if runtime_bundle is None:
                    prepared_root = ensure_dir(output_root / "_prepared" / dataset_assignment.dataset_id)
                    runtime_bundle = prepare_dataset_runtime_bundle(
                        dataset_assignment.dataset,
                        validation_cfg=validation_cfg,
                        prepared_root=prepared_root,
                    )
                    runtime_bundle_cache[dataset_assignment.dataset_id] = runtime_bundle
                forcing_scenario = runtime_bundle.scenarios[theta_scenario_id]
                diagnostic_observed_df = _build_diagnostic_observed_df(
                    validation_start=runtime_bundle.validation_start,
                    validation_end=runtime_bundle.validation_end,
                )
                run_cfg = configure_candidate_run(
                    base_config=copy.deepcopy(base_config),
                    forcing_csv_path=forcing_scenario.forcing_csv_path,
                    theta_center=float(forcing_scenario.summary.get("theta_mean", 0.65)),
                    row=scenario.allocation_lane.candidate_row,
                    initial_state_overrides={},
                )
                result = run_harvest_family_simulation(
                    run_config=run_cfg,
                    observed_df=diagnostic_observed_df,
                    unit_label=runtime_bundle.source_unit_label,
                    repo_root=repo_root,
                    fruit_harvest_family=scenario.harvest_profile.fruit_harvest_family,
                    leaf_harvest_family=scenario.harvest_profile.leaf_harvest_family,
                    fdmc_mode=scenario.harvest_profile.fdmc_mode,
                    fruit_params=scenario.harvest_profile.fruit_params,
                    leaf_params=scenario.harvest_profile.leaf_params,
                )
                diagnostic_metrics = dict(result.metrics)
                diagnostic_metrics["diagnostic_hidden_state_mode"] = "no_observed_harvest_default_init"
                diagnostic_metrics["diagnostic_dataset_role"] = dataset_assignment.dataset_role
                scorecard_rows.append(
                    build_diagnostic_runtime_lane_scorecard_row(
                        scenario,
                        validation_df=result.validation_df,
                        run_df=result.run_df,
                        metrics=diagnostic_metrics,
                        basis_normalization_resolved=runtime_bundle.basis_normalization_resolved,
                    )
                )
                _write_scenario_sidecars(
                    scenario,
                    scenario_root=scenario_root,
                    validation_df=result.validation_df,
                    harvest_mass_balance_df=result.harvest_mass_balance_df,
                    metrics=diagnostic_metrics,
                )
            except (FileNotFoundError, KeyError, ValueError) as error:
                scorecard_rows.append(
                    build_context_only_lane_scorecard_row(
                        scenario,
                        execution_status="diagnostic_runtime_unavailable",
                    )
                )
                _write_scenario_error_sidecar(
                    scenario,
                    scenario_root=scenario_root,
                    error=error,
                )
            continue
        bundle = measured_bundle_cache.get(dataset_assignment.dataset_id)
        if bundle is None:
            prepared_root = ensure_dir(output_root / "_prepared" / dataset_assignment.dataset_id)
            bundle = prepare_measured_harvest_bundle(
                dataset_assignment.dataset,
                validation_cfg=validation_cfg,
                prepared_root=prepared_root,
            )
            measured_bundle_cache[dataset_assignment.dataset_id] = bundle
        forcing_scenario = bundle.scenarios[theta_scenario_id]
        cache_key = (dataset_assignment.dataset_id, scenario.allocation_lane.lane_id)
        initial_state_overrides = reconstruction_cache.get(cache_key)
        if initial_state_overrides is None:
            reconstruction = reconstruct_hidden_state(
                architecture_row=scenario.allocation_lane.candidate_row,
                base_config=copy.deepcopy(base_config),
                forcing_csv_path=forcing_scenario.forcing_csv_path,
                theta_center=float(forcing_scenario.summary.get("theta_mean", 0.65)),
                observed_df=bundle.observed_df,
                calibration_end=bundle.calibration_end,
                repo_root=repo_root,
                unit_label=bundle.source_unit_label,
            )
            initial_state_overrides = dict(reconstruction.initial_state_overrides)
            reconstruction_cache[cache_key] = initial_state_overrides
        run_cfg = configure_candidate_run(
            base_config=copy.deepcopy(base_config),
            forcing_csv_path=forcing_scenario.forcing_csv_path,
            theta_center=float(forcing_scenario.summary.get("theta_mean", 0.65)),
            row=scenario.allocation_lane.candidate_row,
            initial_state_overrides=dict(initial_state_overrides),
        )
        result = run_harvest_family_simulation(
            run_config=run_cfg,
            observed_df=bundle.observed_df,
            unit_label=bundle.source_unit_label,
            repo_root=repo_root,
            fruit_harvest_family=scenario.harvest_profile.fruit_harvest_family,
            leaf_harvest_family=scenario.harvest_profile.leaf_harvest_family,
            fdmc_mode=scenario.harvest_profile.fdmc_mode,
            fruit_params=scenario.harvest_profile.fruit_params,
            leaf_params=scenario.harvest_profile.leaf_params,
        )
        scorecard_rows.append(
            build_lane_scorecard_row(
                scenario,
                validation_df=result.validation_df,
                run_df=result.run_df,
                metrics=result.metrics,
                basis_normalization_resolved=bundle.basis_normalization_resolved,
            )
        )
        split_rows.extend(
            build_split_score_rows(
                scenario,
                observed_df=bundle.observed_df,
                validation_df=result.validation_df,
            )
        )
        _write_scenario_sidecars(
            scenario,
            scenario_root=scenario_root,
            validation_df=result.validation_df,
            harvest_mass_balance_df=result.harvest_mass_balance_df,
            metrics=result.metrics,
        )

    scenario_index_df = pd.DataFrame(scenario_index_rows)
    scenario_index_df.to_csv(paths.scenario_index_path, index=False)
    scorecard_df = finalize_lane_scorecard(
        pd.DataFrame(scorecard_rows),
        split_score_df=pd.DataFrame(split_rows),
    )
    scorecard_df.to_csv(paths.lane_scorecard_path, index=False)
    return {
        "output_root": str(output_root),
        "scenario_count": len(scenarios),
        "scorecard_rows": int(scorecard_df.shape[0]),
    }


__all__ = ["run_lane_matrix"]
