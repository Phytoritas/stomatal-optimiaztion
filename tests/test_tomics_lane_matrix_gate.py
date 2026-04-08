from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.lane_matrix.lane_gate import (
    run_lane_matrix_gate,
)


def test_lane_matrix_gate_filters_reference_and_audit_failures(tmp_path: Path) -> None:
    matrix_root = tmp_path / "out" / "tomics" / "validation" / "lane-matrix"
    matrix_root.mkdir(parents=True, exist_ok=True)
    scorecard_df = pd.DataFrame(
        [
            {
                "scenario_id": "incumbent_current__incumbent_harvest_profile__ds1",
                "allocation_lane_id": "incumbent_current",
                "harvest_profile_id": "incumbent_harvest_profile",
                "dataset_id": "ds1",
                "dataset_role": "measured_harvest",
                "promotion_eligible": True,
                "reference_only": False,
                "reporting_basis_in": "floor_area_g_m2",
                "reporting_basis_canonical": "floor_area_g_m2",
                "basis_normalization_resolved": True,
                "rmse_cumulative_offset": 1.0,
                "rmse_daily_increment": 0.5,
                "fruit_anchor_error": 0.0,
                "canopy_collapse_days": 0.0,
                "winner_stability_score": 1.0,
                "native_state_coverage": 0.9,
                "shared_tdvs_proxy_fraction": 0.1,
                "family_separability_score": 0.8,
                "any_all_zero_harvest_series": False,
                "dropped_nonharvested_mass_g_m2": 0.0,
                "offplant_with_positive_mass_flag": False,
                "runtime_complete_semantics": "explicit_harvested_cumulative_writeback_audited",
                "selected_family_label": "incumbent",
                "selected_family_is_native": True,
                "selected_family_is_proxy": False,
                "execution_status": "scored",
                "candidate_label": "shipped_tomics",
                "architecture_id": "shipped_tomics_control",
                "partition_policy": "tomics",
                "mean_alloc_frac_fruit": 0.45,
                "mean_proxy_family_state_fraction": 0.1,
            },
            {
                "scenario_id": "incumbent_current__incumbent_harvest_profile__ds2",
                "allocation_lane_id": "incumbent_current",
                "harvest_profile_id": "incumbent_harvest_profile",
                "dataset_id": "ds2",
                "dataset_role": "measured_harvest",
                "promotion_eligible": True,
                "reference_only": False,
                "reporting_basis_in": "floor_area_g_m2",
                "reporting_basis_canonical": "floor_area_g_m2",
                "basis_normalization_resolved": True,
                "rmse_cumulative_offset": 1.1,
                "rmse_daily_increment": 0.6,
                "fruit_anchor_error": 0.0,
                "canopy_collapse_days": 0.0,
                "winner_stability_score": 1.0,
                "native_state_coverage": 0.9,
                "shared_tdvs_proxy_fraction": 0.1,
                "family_separability_score": 0.8,
                "any_all_zero_harvest_series": False,
                "dropped_nonharvested_mass_g_m2": 0.0,
                "offplant_with_positive_mass_flag": False,
                "runtime_complete_semantics": "explicit_harvested_cumulative_writeback_audited",
                "selected_family_label": "incumbent",
                "selected_family_is_native": True,
                "selected_family_is_proxy": False,
                "execution_status": "scored",
                "candidate_label": "shipped_tomics",
                "architecture_id": "shipped_tomics_control",
                "partition_policy": "tomics",
                "mean_alloc_frac_fruit": 0.45,
                "mean_proxy_family_state_fraction": 0.1,
            },
            {
                "scenario_id": "research_current__incumbent_harvest_profile__ds1",
                "allocation_lane_id": "research_current",
                "harvest_profile_id": "incumbent_harvest_profile",
                "dataset_id": "ds1",
                "dataset_role": "measured_harvest",
                "promotion_eligible": True,
                "reference_only": False,
                "reporting_basis_in": "floor_area_g_m2",
                "reporting_basis_canonical": "floor_area_g_m2",
                "basis_normalization_resolved": True,
                "rmse_cumulative_offset": 0.9,
                "rmse_daily_increment": 0.4,
                "fruit_anchor_error": 0.2,
                "canopy_collapse_days": 0.0,
                "winner_stability_score": 1.0,
                "native_state_coverage": 0.9,
                "shared_tdvs_proxy_fraction": 0.1,
                "family_separability_score": 0.8,
                "any_all_zero_harvest_series": True,
                "dropped_nonharvested_mass_g_m2": 0.0,
                "offplant_with_positive_mass_flag": False,
                "runtime_complete_semantics": "explicit_harvested_cumulative_writeback_audited",
                "selected_family_label": "research",
                "selected_family_is_native": True,
                "selected_family_is_proxy": False,
                "execution_status": "scored",
                "candidate_label": "current_selected",
                "architecture_id": "kuijpers_hybrid_candidate",
                "partition_policy": "tomics_alloc_research",
                "mean_alloc_frac_fruit": 0.44,
                "mean_proxy_family_state_fraction": 0.1,
            },
            {
                "scenario_id": "research_current__incumbent_harvest_profile__ds2",
                "allocation_lane_id": "research_current",
                "harvest_profile_id": "incumbent_harvest_profile",
                "dataset_id": "ds2",
                "dataset_role": "measured_harvest",
                "promotion_eligible": True,
                "reference_only": False,
                "reporting_basis_in": "floor_area_g_m2",
                "reporting_basis_canonical": "floor_area_g_m2",
                "basis_normalization_resolved": True,
                "rmse_cumulative_offset": 0.85,
                "rmse_daily_increment": 0.35,
                "fruit_anchor_error": 0.2,
                "canopy_collapse_days": 0.0,
                "winner_stability_score": 1.0,
                "native_state_coverage": 0.9,
                "shared_tdvs_proxy_fraction": 0.1,
                "family_separability_score": 0.8,
                "any_all_zero_harvest_series": False,
                "dropped_nonharvested_mass_g_m2": 0.0,
                "offplant_with_positive_mass_flag": False,
                "runtime_complete_semantics": "explicit_harvested_cumulative_writeback_audited",
                "selected_family_label": "research",
                "selected_family_is_native": True,
                "selected_family_is_proxy": False,
                "execution_status": "scored",
                "candidate_label": "current_selected",
                "architecture_id": "kuijpers_hybrid_candidate",
                "partition_policy": "tomics_alloc_research",
                "mean_alloc_frac_fruit": 0.44,
                "mean_proxy_family_state_fraction": 0.1,
            },
            {
                "scenario_id": "research_promoted__incumbent_harvest_profile__ds1",
                "allocation_lane_id": "research_promoted",
                "harvest_profile_id": "incumbent_harvest_profile",
                "dataset_id": "ds1",
                "dataset_role": "measured_harvest",
                "promotion_eligible": True,
                "reference_only": False,
                "reporting_basis_in": "per_unknown",
                "reporting_basis_canonical": "floor_area_g_m2",
                "basis_normalization_resolved": False,
                "rmse_cumulative_offset": 0.8,
                "rmse_daily_increment": 0.4,
                "fruit_anchor_error": 0.3,
                "canopy_collapse_days": 0.0,
                "winner_stability_score": 1.0,
                "native_state_coverage": 0.9,
                "shared_tdvs_proxy_fraction": 0.1,
                "family_separability_score": 0.8,
                "any_all_zero_harvest_series": False,
                "dropped_nonharvested_mass_g_m2": 0.0,
                "offplant_with_positive_mass_flag": False,
                "runtime_complete_semantics": "explicit_harvested_cumulative_writeback_audited",
                "selected_family_label": "research",
                "selected_family_is_native": True,
                "selected_family_is_proxy": False,
                "execution_status": "scored",
                "candidate_label": "promoted_selected",
                "architecture_id": "constrained_full_plus_feedback__buffer_capacity_g_m2_12p0",
                "partition_policy": "tomics_promoted_research",
                "mean_alloc_frac_fruit": 0.43,
                "mean_proxy_family_state_fraction": 0.1,
            },
            {
                "scenario_id": "raw_reference_thorp__incumbent_harvest_profile__ds1",
                "allocation_lane_id": "raw_reference_thorp",
                "harvest_profile_id": "incumbent_harvest_profile",
                "dataset_id": "ds1",
                "dataset_role": "measured_harvest",
                "promotion_eligible": False,
                "reference_only": True,
                "reporting_basis_in": "floor_area_g_m2",
                "reporting_basis_canonical": "floor_area_g_m2",
                "basis_normalization_resolved": True,
                "rmse_cumulative_offset": 0.7,
                "rmse_daily_increment": 0.4,
                "fruit_anchor_error": 0.5,
                "canopy_collapse_days": 0.0,
                "winner_stability_score": 1.0,
                "native_state_coverage": 0.6,
                "shared_tdvs_proxy_fraction": 0.4,
                "family_separability_score": 0.2,
                "any_all_zero_harvest_series": False,
                "dropped_nonharvested_mass_g_m2": 0.0,
                "offplant_with_positive_mass_flag": False,
                "runtime_complete_semantics": "explicit_harvested_cumulative_writeback_audited",
                "selected_family_label": "reference",
                "selected_family_is_native": False,
                "selected_family_is_proxy": True,
                "execution_status": "scored",
                "candidate_label": "shipped_tomics",
                "architecture_id": "raw_thorp_like_control",
                "partition_policy": "thorp_fruit_veg",
                "mean_alloc_frac_fruit": 0.35,
                "mean_proxy_family_state_fraction": 0.4,
            },
        ]
    )
    scorecard_df.to_csv(matrix_root / "lane_scorecard.csv", index=False)
    config = {
        "validation": {
            "lane_matrix_gate": {
                "matrix_root": str(matrix_root),
                "output_root": str(matrix_root),
                "min_dataset_count": 2,
            }
        }
    }
    result = run_lane_matrix_gate(config, repo_root=tmp_path, config_path=tmp_path / "gate.yaml")
    assert result["promotion_rows"] == 2
    assert (matrix_root / "promotion_surface.csv").exists()
    assert (matrix_root / "diagnostic_surface.csv").exists()
    assert (matrix_root / "lane_gate_decision.json").exists()
    promotion_df = pd.read_csv(matrix_root / "promotion_surface.csv")
    diagnostic_df = pd.read_csv(matrix_root / "diagnostic_surface.csv")
    decision = json.loads((matrix_root / "lane_gate_decision.json").read_text(encoding="utf-8"))
    assert set(promotion_df["allocation_lane_id"]) == {"incumbent_current", "research_current"}
    research_row = promotion_df.loc[promotion_df["allocation_lane_id"].eq("research_current")]
    assert not research_row.empty
    assert bool(research_row.iloc[0]["lane_any_audit_failure"]) is True
    assert bool(research_row.iloc[0]["passes"]) is False
    assert "raw_reference_thorp" not in set(promotion_df["allocation_lane_id"])
    assert "raw_reference_thorp" in set(diagnostic_df["allocation_lane_id"])
    assert decision["promotion_blocked"] is False


def test_lane_matrix_gate_counts_only_audit_passing_measured_datasets_in_denominator(tmp_path: Path) -> None:
    matrix_root = tmp_path / "out" / "tomics" / "validation" / "lane-matrix"
    matrix_root.mkdir(parents=True, exist_ok=True)
    scorecard_df = pd.DataFrame(
        [
            {
                "scenario_id": "incumbent_current__incumbent_harvest_profile__ds1",
                "allocation_lane_id": "incumbent_current",
                "harvest_profile_id": "incumbent_harvest_profile",
                "dataset_id": "ds1",
                "dataset_role": "measured_harvest",
                "promotion_eligible": True,
                "reference_only": False,
                "reporting_basis_in": "floor_area_g_m2",
                "reporting_basis_canonical": "floor_area_g_m2",
                "basis_normalization_resolved": True,
                "rmse_cumulative_offset": 0.8,
                "rmse_daily_increment": 0.4,
                "fruit_anchor_error": 0.0,
                "canopy_collapse_days": 0.0,
                "winner_stability_score": 1.0,
                "native_state_coverage": 0.9,
                "shared_tdvs_proxy_fraction": 0.1,
                "family_separability_score": 0.8,
                "any_all_zero_harvest_series": False,
                "dropped_nonharvested_mass_g_m2": 0.0,
                "offplant_with_positive_mass_flag": False,
                "runtime_complete_semantics": "explicit_harvested_cumulative_writeback_audited",
                "selected_family_label": "incumbent",
                "selected_family_is_native": True,
                "selected_family_is_proxy": False,
                "execution_status": "scored",
                "candidate_label": "shipped_tomics",
                "architecture_id": "shipped_tomics_control",
                "partition_policy": "tomics",
                "mean_alloc_frac_fruit": 0.45,
                "mean_proxy_family_state_fraction": 0.1,
            },
            {
                "scenario_id": "incumbent_current__incumbent_harvest_profile__ds2",
                "allocation_lane_id": "incumbent_current",
                "harvest_profile_id": "incumbent_harvest_profile",
                "dataset_id": "ds2",
                "dataset_role": "measured_harvest",
                "promotion_eligible": True,
                "reference_only": False,
                "reporting_basis_in": "floor_area_g_m2",
                "reporting_basis_canonical": "floor_area_g_m2",
                "basis_normalization_resolved": True,
                "rmse_cumulative_offset": 0.7,
                "rmse_daily_increment": 0.3,
                "fruit_anchor_error": 0.0,
                "canopy_collapse_days": 0.0,
                "winner_stability_score": 1.0,
                "native_state_coverage": 0.9,
                "shared_tdvs_proxy_fraction": 0.1,
                "family_separability_score": 0.8,
                "any_all_zero_harvest_series": True,
                "dropped_nonharvested_mass_g_m2": 0.0,
                "offplant_with_positive_mass_flag": False,
                "runtime_complete_semantics": "explicit_harvested_cumulative_writeback_audited",
                "selected_family_label": "incumbent",
                "selected_family_is_native": True,
                "selected_family_is_proxy": False,
                "execution_status": "scored",
                "candidate_label": "shipped_tomics",
                "architecture_id": "shipped_tomics_control",
                "partition_policy": "tomics",
                "mean_alloc_frac_fruit": 0.45,
                "mean_proxy_family_state_fraction": 0.1,
            },
        ]
    )
    scorecard_df.to_csv(matrix_root / "lane_scorecard.csv", index=False)
    config = {
        "validation": {
            "lane_matrix_gate": {
                "matrix_root": str(matrix_root),
                "output_root": str(matrix_root),
                "min_dataset_count": 2,
            }
        }
    }

    run_lane_matrix_gate(config, repo_root=tmp_path, config_path=tmp_path / "gate.yaml")

    promotion_df = pd.read_csv(matrix_root / "promotion_surface.csv")
    decision = json.loads((matrix_root / "lane_gate_decision.json").read_text(encoding="utf-8"))
    assert int(decision["measured_dataset_count"]) == 1
    assert int(promotion_df.loc[0, "dataset_count"]) == 1
    assert bool(promotion_df.loc[0, "single_dataset_only_flag"]) is True
    assert bool(promotion_df.loc[0, "passes"]) is False


def test_lane_matrix_gate_measured_dataset_count_uses_only_promotion_passing_rows(tmp_path: Path) -> None:
    matrix_root = tmp_path / "out" / "tomics" / "validation" / "lane-matrix"
    matrix_root.mkdir(parents=True, exist_ok=True)
    scorecard_df = pd.DataFrame(
        [
            {
                "scenario_id": "incumbent_current__incumbent_harvest_profile__ds_pass",
                "allocation_lane_id": "incumbent_current",
                "harvest_profile_id": "incumbent_harvest_profile",
                "dataset_id": "ds_pass",
                "dataset_role": "measured_harvest",
                "promotion_eligible": True,
                "reference_only": False,
                "reporting_basis_in": "floor_area_g_m2",
                "reporting_basis_canonical": "floor_area_g_m2",
                "basis_normalization_resolved": True,
                "rmse_cumulative_offset": 1.0,
                "rmse_daily_increment": 0.5,
                "fruit_anchor_error": 0.0,
                "canopy_collapse_days": 0.0,
                "winner_stability_score": 1.0,
                "native_state_coverage": 0.9,
                "shared_tdvs_proxy_fraction": 0.1,
                "family_separability_score": 0.8,
                "any_all_zero_harvest_series": False,
                "dropped_nonharvested_mass_g_m2": 0.0,
                "offplant_with_positive_mass_flag": False,
                "runtime_complete_semantics": "explicit_harvested_cumulative_writeback_audited",
                "selected_family_label": "incumbent",
                "selected_family_is_native": True,
                "selected_family_is_proxy": False,
                "execution_status": "scored",
                "candidate_label": "shipped_tomics",
                "architecture_id": "shipped_tomics_control",
                "partition_policy": "tomics",
                "mean_alloc_frac_fruit": 0.45,
                "mean_proxy_family_state_fraction": 0.1,
            },
            {
                "scenario_id": "research_promoted__incumbent_harvest_profile__ds_failed",
                "allocation_lane_id": "research_promoted",
                "harvest_profile_id": "incumbent_harvest_profile",
                "dataset_id": "ds_failed",
                "dataset_role": "measured_harvest",
                "promotion_eligible": True,
                "reference_only": False,
                "reporting_basis_in": "floor_area_g_m2",
                "reporting_basis_canonical": "floor_area_g_m2",
                "basis_normalization_resolved": True,
                "rmse_cumulative_offset": 0.8,
                "rmse_daily_increment": 0.4,
                "fruit_anchor_error": 0.1,
                "canopy_collapse_days": 0.0,
                "winner_stability_score": 1.0,
                "native_state_coverage": 0.9,
                "shared_tdvs_proxy_fraction": 0.1,
                "family_separability_score": 0.8,
                "any_all_zero_harvest_series": True,
                "dropped_nonharvested_mass_g_m2": 0.0,
                "offplant_with_positive_mass_flag": False,
                "runtime_complete_semantics": "explicit_harvested_cumulative_writeback_audited",
                "selected_family_label": "research",
                "selected_family_is_native": True,
                "selected_family_is_proxy": False,
                "execution_status": "scored",
                "candidate_label": "promoted_selected",
                "architecture_id": "constrained_full_plus_feedback__buffer_capacity_g_m2_12p0",
                "partition_policy": "tomics_promoted_research",
                "mean_alloc_frac_fruit": 0.44,
                "mean_proxy_family_state_fraction": 0.1,
            },
        ]
    )
    scorecard_df.to_csv(matrix_root / "lane_scorecard.csv", index=False)
    config = {
        "validation": {
            "lane_matrix_gate": {
                "matrix_root": str(matrix_root),
                "output_root": str(matrix_root),
                "cross_dataset_stability_score_min": 1.0,
                "min_dataset_count": 1,
            }
        }
    }

    run_lane_matrix_gate(config, repo_root=tmp_path, config_path=tmp_path / "gate.yaml")

    promotion_df = pd.read_csv(matrix_root / "promotion_surface.csv")
    decision = json.loads((matrix_root / "lane_gate_decision.json").read_text(encoding="utf-8"))
    incumbent_row = promotion_df.loc[promotion_df["allocation_lane_id"].eq("incumbent_current")]

    assert decision["measured_dataset_count"] == 1
    assert not incumbent_row.empty
    assert float(incumbent_row.iloc[0]["cross_dataset_stability_score"]) == 1.0
    assert bool(incumbent_row.iloc[0]["passes"]) is True
