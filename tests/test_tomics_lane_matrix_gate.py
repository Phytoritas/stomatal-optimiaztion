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


def test_lane_matrix_gate_excludes_review_only_derived_dw_from_promotion_denominator(tmp_path: Path) -> None:
    matrix_root = tmp_path / "out" / "tomics" / "validation" / "lane-matrix"
    matrix_root.mkdir(parents=True, exist_ok=True)
    base_row = {
        "scenario_id": "incumbent_current__incumbent_harvest_profile__knu_actual",
        "allocation_lane_id": "incumbent_current",
        "harvest_profile_id": "incumbent_harvest_profile",
        "dataset_id": "knu_actual",
        "dataset_role": "measured_harvest",
        "evidence_grade": "direct_measured_harvest",
        "decision_weight": "promotion_gate",
        "proxy_caveat": "",
        "promotion_eligible": True,
        "reference_only": False,
        "reporting_basis_in": "floor_area_g_m2",
        "reporting_basis_canonical": "floor_area_g_m2",
        "basis_normalization_resolved": True,
        "rmse_cumulative_offset": 1.0,
        "r2_cumulative_offset": 0.8,
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
    }
    public_row = {
        **base_row,
        "scenario_id": "incumbent_current__incumbent_harvest_profile__public_rda__yield",
        "dataset_id": "public_rda__yield",
        "evidence_grade": "review_only_derived_dw",
        "decision_weight": "review_only_robustness",
        "proxy_caveat": "derived DW from measured fresh shipment",
        "rmse_cumulative_offset": 0.2,
        "r2_cumulative_offset": 0.95,
    }
    pd.DataFrame([base_row, public_row]).to_csv(matrix_root / "lane_scorecard.csv", index=False)
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
    promotion_decision = json.loads((matrix_root / "promotion_gate_decision.json").read_text(encoding="utf-8"))

    assert int(decision["measured_dataset_count"]) == 1
    assert json.loads(promotion_df.loc[0, "dataset_ids"]) == ["knu_actual"]
    assert "public_rda__yield" not in promotion_df.loc[0, "dataset_ids"]
    assert promotion_decision["primary_measured_dataset_ids"] == ["knu_actual"]
    assert promotion_decision["review_only_dataset_ids"] == ["public_rda__yield"]
    assert promotion_decision["public_proxy_lanes_can_promote_a4"] is False


def test_lane_matrix_gate_promotion_decision_matches_legacy_scorecard_denominator(tmp_path: Path) -> None:
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
            }
        ]
    )
    scorecard_df.to_csv(matrix_root / "lane_scorecard.csv", index=False)
    config = {
        "validation": {
            "lane_matrix_gate": {
                "matrix_root": str(matrix_root),
                "output_root": str(matrix_root),
                "min_dataset_count": 1,
            }
        }
    }

    run_lane_matrix_gate(config, repo_root=tmp_path, config_path=tmp_path / "gate.yaml")

    lane_decision = json.loads((matrix_root / "lane_gate_decision.json").read_text(encoding="utf-8"))
    promotion_decision = json.loads((matrix_root / "promotion_gate_decision.json").read_text(encoding="utf-8"))
    assert lane_decision["measured_dataset_count"] == 1
    assert promotion_decision["primary_measured_dataset_ids"] == ["ds1"]


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


def _diagnostic_context_scorecard_row(
    *,
    dataset_id: str,
    allocation_lane_id: str,
    native_state_coverage: float,
    shared_tdvs_proxy_fraction: float,
    family_separability_score: float,
    any_all_zero_harvest_series: bool = False,
    offplant_with_positive_mass_flag: bool = False,
    canopy_collapse_days: float = 0.0,
) -> dict[str, object]:
    return {
        "scenario_id": f"{allocation_lane_id}__incumbent_harvest_profile__{dataset_id}",
        "allocation_lane_id": allocation_lane_id,
        "harvest_profile_id": "incumbent_harvest_profile",
        "dataset_id": dataset_id,
        "dataset_role": "trait_plus_env_no_harvest",
        "promotion_eligible": False,
        "reference_only": False,
        "reporting_basis_in": "floor_area_g_m2",
        "reporting_basis_canonical": "floor_area_g_m2",
        "basis_normalization_resolved": True,
        "rmse_cumulative_offset": float("nan"),
        "rmse_daily_increment": float("nan"),
        "fruit_anchor_error": 0.0,
        "canopy_collapse_days": canopy_collapse_days,
        "winner_stability_score": float("nan"),
        "native_state_coverage": native_state_coverage,
        "shared_tdvs_proxy_fraction": shared_tdvs_proxy_fraction,
        "family_separability_score": family_separability_score,
        "any_all_zero_harvest_series": any_all_zero_harvest_series,
        "dropped_nonharvested_mass_g_m2": 0.0,
        "offplant_with_positive_mass_flag": offplant_with_positive_mass_flag,
        "runtime_complete_semantics": "explicit_harvested_cumulative_writeback_audited",
        "selected_family_label": "incumbent",
        "selected_family_is_native": True,
        "selected_family_is_proxy": False,
        "execution_status": "diagnostic_runtime_scored",
        "candidate_label": "shipped_tomics",
        "architecture_id": f"{allocation_lane_id}_architecture",
        "partition_policy": "tomics",
        "mean_alloc_frac_fruit": 0.45,
        "mean_proxy_family_state_fraction": shared_tdvs_proxy_fraction,
    }


def test_lane_matrix_gate_ranks_context_only_runtime_rows_by_diagnostic_score(tmp_path: Path) -> None:
    matrix_root = tmp_path / "out" / "tomics" / "validation" / "lane-matrix"
    matrix_root.mkdir(parents=True, exist_ok=True)
    scorecard_df = pd.DataFrame(
        [
            _diagnostic_context_scorecard_row(
                dataset_id="ctx",
                allocation_lane_id="incumbent_current",
                native_state_coverage=0.9,
                shared_tdvs_proxy_fraction=0.1,
                family_separability_score=0.8,
            ),
            _diagnostic_context_scorecard_row(
                dataset_id="ctx",
                allocation_lane_id="research_promoted",
                native_state_coverage=0.3,
                shared_tdvs_proxy_fraction=0.6,
                family_separability_score=0.0,
                any_all_zero_harvest_series=True,
                offplant_with_positive_mass_flag=True,
                canopy_collapse_days=4.0,
            ),
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

    diagnostic_df = pd.read_csv(matrix_root / "diagnostic_surface.csv")
    assert diagnostic_df.iloc[0]["allocation_lane_id"] == "incumbent_current"
    assert float(diagnostic_df.iloc[0]["diagnostic_score"]) > float(diagnostic_df.iloc[1]["diagnostic_score"])


def test_lane_matrix_gate_selects_highest_scoring_diagnostic_record_in_decision_payload(tmp_path: Path) -> None:
    matrix_root = tmp_path / "out" / "tomics" / "validation" / "lane-matrix"
    matrix_root.mkdir(parents=True, exist_ok=True)
    scorecard_df = pd.DataFrame(
        [
            _diagnostic_context_scorecard_row(
                dataset_id="a_ctx",
                allocation_lane_id="incumbent_current",
                native_state_coverage=0.1,
                shared_tdvs_proxy_fraction=0.8,
                family_separability_score=0.1,
            ),
            _diagnostic_context_scorecard_row(
                dataset_id="z_ctx",
                allocation_lane_id="research_current",
                native_state_coverage=0.95,
                shared_tdvs_proxy_fraction=0.05,
                family_separability_score=0.9,
            ),
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

    decision = json.loads((matrix_root / "lane_gate_decision.json").read_text(encoding="utf-8"))
    assert decision["diagnostic_selection_basis"] == "highest_diagnostic_score"
    assert decision["diagnostic_selected"]["dataset_id"] == "z_ctx"
    assert decision["diagnostic_selected"]["allocation_lane_id"] == "research_current"
