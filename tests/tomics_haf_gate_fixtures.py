from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


SELECTED_CANDIDATE_ID = (
    "HF3|tomics_haf_latent_allocation_research|tomato_constrained_thorp_prior|"
    "tomgro_ageclass_mature_pool|leaf_harvest_tomsim_legacy|constant_0p056|0.0|1.0||last_two"
)
SHIPPED_CANDIDATE_ID = (
    "HF0|shipped_tomics|none|tomsim_truss_incumbent|leaf_harvest_tomsim_legacy|"
    "constant_0p056|0.0|1.0||"
)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _base_metadata() -> dict[str, Any]:
    return {
        "season_id": "2025_2C",
        "canonical_fruit_DMC_fraction": 0.056,
        "fruit_DMC_fraction": 0.056,
        "default_fruit_dry_matter_content": 0.056,
        "DMC_fixed_for_2025_2C": True,
        "DMC_sensitivity_enabled": False,
        "DMC_sensitivity_values": [],
        "dry_yield_is_dmc_estimated": True,
        "direct_dry_yield_measured": False,
        "radiation_daynight_primary_source": "dataset1",
        "radiation_column_used": "env_inside_radiation_wm2",
        "fixed_clock_daynight_primary": False,
        "fruit_diameter_p_values_allowed": False,
        "fruit_diameter_allocation_calibration_target": False,
        "fruit_diameter_model_promotion_target": False,
        "latent_allocation_directly_validated": False,
        "raw_THORP_allocator_used": False,
        "THORP_used_as_bounded_prior": True,
        "shipped_TOMICS_incumbent_changed": False,
    }


def write_haf_gate_fixture(
    tmp_path: Path,
    *,
    observer_overrides: dict[str, Any] | None = None,
    latent_overrides: dict[str, Any] | None = None,
    harvest_overrides: dict[str, Any] | None = None,
    guardrail_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    repo_root = tmp_path
    harvest_root = repo_root / "out" / "tomics" / "validation" / "harvest-family" / "haf_2025_2c"
    latent_root = repo_root / "out" / "tomics" / "validation" / "latent-allocation" / "haf_2025_2c"
    analysis_root = repo_root / "out" / "tomics" / "analysis" / "haf_2025_2c"
    figure_root = repo_root / "out" / "tomics" / "figures" / "haf_2025_2c"
    promotion_root = repo_root / "out" / "tomics" / "validation" / "promotion-gate" / "haf_2025_2c"
    multi_root = repo_root / "out" / "tomics" / "validation" / "multi-dataset" / "haf_2025_2c"

    observer = _base_metadata()
    observer.update(observer_overrides or {})
    latent = {**_base_metadata(), "latent_allocation_ready": True}
    latent.update(latent_overrides or {})
    harvest = {
        **_base_metadata(),
        "production_observer_ready": True,
        "latent_allocation_ready": True,
        "harvest_family_factorial_run": True,
        "candidate_count": 2,
        "promotion_gate_run": False,
        "cross_dataset_gate_run": False,
        "single_dataset_promotion_allowed": False,
        "budget_parity_basis": "knob_count_and_hidden_calibration_budget",
        "wall_clock_compute_budget_parity_evaluated": False,
        "wall_clock_compute_budget_parity_required_for_goal_3b": False,
        "budget_parity_limitations": (
            "Budget parity is knob-count and hidden-calibration-budget parity, not wall-clock compute-budget parity."
        ),
    }
    harvest.update(harvest_overrides or {})
    _write_json(analysis_root / "2025_2c_tomics_haf_metadata.json", observer)
    _write_json(latent_root / "latent_allocation_metadata.json", latent)
    _write_json(harvest_root / "harvest_family_metadata.json", harvest)
    _write_json(
        harvest_root / "goal3c_readiness_audit.json",
        {"goal3c_ready": True, "blockers": []},
    )
    _write_json(
        harvest_root / "harvest_family_selected_research_candidate.json",
        {"selected_candidate_id": SELECTED_CANDIDATE_ID},
    )
    _write_json(
        harvest_root / "harvest_family_reproducibility_manifest.json",
        {"repo_head_sha": "synthetic"},
    )
    ranking_rows = [
        {
            "candidate_id": SHIPPED_CANDIDATE_ID,
            "stage": "HF0",
            "allocator_family": "shipped_tomics",
            "latent_allocation_prior_family": "none",
            "fruit_harvest_family": "tomsim_truss_incumbent",
            "leaf_harvest_family": "leaf_harvest_tomsim_legacy",
            "observation_operator": "fresh_to_dry_dmc_0p056",
            "fdmc_mode": "constant_0p056",
            "rmse_cumulative_DW_g_m2_floor": 10.0,
            "rmse_daily_increment_DW_g_m2_floor": 1.0,
            "final_cumulative_bias_pct": -21.0,
            "harvest_mass_balance_error": 0.0,
            "canopy_collapse_days": 0,
            "leaf_harvest_mass_balance_error": 0.0,
            "budget_units_used": 0,
            "budget_parity_violation": False,
            "invalid_run_flag": 0,
            "nonfinite_flag": 0,
            "ranking_score": -20.0,
            "promotable_in_goal3b": False,
        },
        {
            "candidate_id": SELECTED_CANDIDATE_ID,
            "stage": "HF3",
            "allocator_family": "tomics_haf_latent_allocation_research",
            "latent_allocation_prior_family": "tomato_constrained_thorp_prior",
            "fruit_harvest_family": "tomgro_ageclass_mature_pool",
            "leaf_harvest_family": "leaf_harvest_tomsim_legacy",
            "observation_operator": "fresh_to_dry_dmc_0p056",
            "fdmc_mode": "constant_0p056",
            "rmse_cumulative_DW_g_m2_floor": 7.0,
            "rmse_daily_increment_DW_g_m2_floor": 0.7,
            "final_cumulative_bias_pct": -10.0,
            "harvest_mass_balance_error": 0.0,
            "canopy_collapse_days": 0,
            "leaf_harvest_mass_balance_error": 0.0,
            "budget_units_used": 9,
            "budget_parity_violation": False,
            "invalid_run_flag": 0,
            "nonfinite_flag": 0,
            "ranking_score": -10.0,
            "promotable_in_goal3b": False,
        },
    ]
    pd.DataFrame(ranking_rows).to_csv(harvest_root / "harvest_family_rankings.csv", index=False)
    pd.DataFrame(ranking_rows).to_csv(harvest_root / "harvest_family_metrics_pooled.csv", index=False)
    by_loadcell = []
    for loadcell_id, treatment in [(1, "Control"), (2, "Control"), (4, "Drought"), (5, "Drought")]:
        for row in ranking_rows:
            by_loadcell.append(
                {
                    **row,
                    "loadcell_id": loadcell_id,
                    "treatment": treatment,
                    "final_cumulative_bias_pct": -9.0 if row["candidate_id"] == SELECTED_CANDIDATE_ID else -21.0,
                }
            )
    pd.DataFrame(by_loadcell).to_csv(harvest_root / "harvest_family_metrics_by_loadcell.csv", index=False)
    mean_sd = []
    for treatment in ["Control", "Drought"]:
        for row in ranking_rows:
            mean_sd.append(
                {
                    **row,
                    "treatment": treatment,
                    "mean_rmse_cumulative_DW_g_m2_floor": row["rmse_cumulative_DW_g_m2_floor"],
                    "sd_rmse_cumulative_DW_g_m2_floor": 0.1,
                    "mean_rmse_daily_increment_DW_g_m2_floor": row["rmse_daily_increment_DW_g_m2_floor"],
                    "sd_rmse_daily_increment_DW_g_m2_floor": 0.1,
                    "mean_final_cumulative_bias_pct": -9.0
                    if row["candidate_id"] == SELECTED_CANDIDATE_ID
                    else -21.0,
                    "sd_final_cumulative_bias_pct": 0.1,
                    "n_loadcells": 2,
                    "n_dates": 3,
                }
            )
    pd.DataFrame(mean_sd).to_csv(harvest_root / "harvest_family_metrics_mean_sd.csv", index=False)
    pd.DataFrame(ranking_rows).to_csv(harvest_root / "harvest_family_budget_parity.csv", index=False)
    mass_rows = []
    for date in ["2025-11-01", "2025-11-02"]:
        for row in ranking_rows:
            mass_rows.append(
                {
                    "date": date,
                    "loadcell_id": 1,
                    "treatment": "Control",
                    "candidate_id": row["candidate_id"],
                    "stage": row["stage"],
                    "allocator_family": row["allocator_family"],
                    "fruit_harvest_family": row["fruit_harvest_family"],
                    "leaf_harvest_family": row["leaf_harvest_family"],
                    "mass_balance_error": 0.0,
                    "leaf_harvest_mass_balance_error": 0.0,
                    "invalid_run_flag": False,
                }
            )
    pd.DataFrame(mass_rows).to_csv(harvest_root / "harvest_family_mass_balance.csv", index=False)
    guardrail_rows = [
        {"guardrail_name": name, "status": "pass", "pass_fail": True, "violation_count": 0}
        for name in [
            "no_leaf_collapse",
            "no_wet_root_excess",
            "stress_gated_root_increase",
            "sum_to_one",
            "no_raw_THORP",
            "no_fruit_diameter_calibration",
            "no_direct_validation_claim",
        ]
    ]
    for row in guardrail_rows:
        row.update(guardrail_overrides or {})
    pd.DataFrame(guardrail_rows).to_csv(latent_root / "latent_allocation_guardrails.csv", index=False)
    figure_root.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [
            {
                "bundle": "harvest_family_performance_matrix",
                "render_status": "spec_validated_only",
                "blocker": "spec_scaffold_missing_renderer_layout_panels_styling",
            }
        ]
    ).to_csv(figure_root / "plotkit_render_manifest.csv", index=False)
    promotion_config = {
        "exp": {"name": "synthetic_haf_promotion_gate"},
        "tomics_haf": {
            "season_id": "2025_2C",
            "current_dataset_id": "haf_2025_2c",
            "observer_metadata": str(analysis_root / "2025_2c_tomics_haf_metadata.json"),
            "latent_allocation_metadata": str(latent_root / "latent_allocation_metadata.json"),
            "latent_allocation_guardrails": str(latent_root / "latent_allocation_guardrails.csv"),
            "harvest_family_output_root": str(harvest_root),
            "harvest_family_metadata": str(harvest_root / "harvest_family_metadata.json"),
            "harvest_family_rankings": str(harvest_root / "harvest_family_rankings.csv"),
            "harvest_family_metrics_by_loadcell": str(harvest_root / "harvest_family_metrics_by_loadcell.csv"),
            "harvest_family_metrics_mean_sd": str(harvest_root / "harvest_family_metrics_mean_sd.csv"),
            "harvest_family_budget_parity": str(harvest_root / "harvest_family_budget_parity.csv"),
            "harvest_family_mass_balance": str(harvest_root / "harvest_family_mass_balance.csv"),
            "goal3c_readiness_audit": str(harvest_root / "goal3c_readiness_audit.json"),
            "output_root": str(promotion_root),
        },
        "gate": {
            "allow_single_dataset_promotion": False,
            "require_measured_dataset_count_min": 2,
            "current_dataset_id": "haf_2025_2c",
            "promotion_effect_size_requirements": {
                "min_relative_improvement_vs_incumbent": 0.05,
                "max_final_bias_pct_abs": 20.0,
                "require_by_loadcell_consistency": True,
                "require_no_treatment_group_failure": True,
            },
        },
    }
    cross_config = {
        "exp": {"name": "synthetic_haf_cross_dataset_gate"},
        "cross_dataset_gate": {
            "current_dataset_id": "haf_2025_2c",
            "require_measured_dataset_count_min": 2,
            "available_dataset_outputs": [
                {
                    "dataset_id": "haf_2025_2c",
                    "dataset_type": "haf_measured_actual",
                    "measured_or_proxy": "measured",
                    "harvest_family_metadata": str(harvest_root / "harvest_family_metadata.json"),
                    "harvest_family_rankings": str(harvest_root / "harvest_family_rankings.csv"),
                    "contributes_to_promotion_gate": True,
                }
            ],
            "allow_legacy_or_public_proxy_for_promotion": False,
            "proxy_dataset_use": "diagnostic_only",
            "single_dataset_promotion_allowed": False,
            "output_root": str(multi_root),
        },
    }
    return {
        "repo_root": repo_root,
        "promotion_config": promotion_config,
        "cross_config": cross_config,
        "config_path": repo_root / "synthetic.yaml",
        "promotion_root": promotion_root,
        "multi_root": multi_root,
        "harvest_root": harvest_root,
    }
