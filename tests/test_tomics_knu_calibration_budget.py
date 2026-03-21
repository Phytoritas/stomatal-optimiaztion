from __future__ import annotations

import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.parameter_budget import (
    CalibrationCandidate,
    build_calibration_budget,
    build_calibration_budget_manifest,
    SplitWindow,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.artifact_sync import CanonicalWinnerIds


def test_calibration_budget_keeps_equal_free_parameter_count_across_candidates() -> None:
    shipped = build_calibration_budget(
        candidate_label="shipped_tomics",
        candidate_row={"architecture_id": "shipped_tomics_control", "partition_policy": "tomics"},
    )
    current = build_calibration_budget(
        candidate_label="current_selected",
        candidate_row={
            "architecture_id": "kuijpers_hybrid_candidate__wet_root_cap_0p08",
            "partition_policy": "tomics_alloc_research",
            "storage_capacity_g_ch2o_m2": 15.0,
            "storage_carryover_fraction": 0.8,
        },
    )
    promoted = build_calibration_budget(
        candidate_label="promoted_selected",
        candidate_row={
            "architecture_id": "constrained_full_plus_feedback__buffer_capacity_g_m2_12p0",
            "partition_policy": "tomics_promoted_research",
            "beta": 3.0,
            "tau_alloc_days": 3.0,
            "buffer_capacity_g_m2": 12.0,
        },
    )
    assert shipped.max_free_parameter_count == current.max_free_parameter_count == promoted.max_free_parameter_count == 2
    assert shipped.free_parameters == current.free_parameters == promoted.free_parameters
    assert current.hidden_state_mode_budget == promoted.hidden_state_mode_budget == 3
    assert "lai_target_center" not in current.architecture_specific_parameters
    assert "lai_target_center" not in promoted.architecture_specific_parameters


def test_calibration_budget_manifest_does_not_mark_shared_parameters_as_frozen() -> None:
    winners = CanonicalWinnerIds(
        current_selected_architecture_id="kuijpers_hybrid_candidate",
        promoted_selected_architecture_id="constrained_full_plus_feedback__buffer_capacity_g_m2_12p0",
    )
    candidates = [
        CalibrationCandidate(
            candidate_label="shipped_tomics",
            architecture_id="shipped_tomics_control",
            candidate_role="incumbent",
            calibratable=True,
            row={
                "architecture_id": "shipped_tomics_control",
                "partition_policy": "tomics",
                "policy_family": "incumbent",
                "allocation_scheme": "4pool",
                "lai_target_center": 2.75,
                "fruit_load_multiplier": 1.0,
                "wet_root_cap": 0.10,
            },
        )
    ]
    splits = [
        SplitWindow(
            split_id="blocked_primary",
            split_kind="blocked_holdout",
            calibration_start=pd.Timestamp("2024-08-08"),
            calibration_end=pd.Timestamp("2024-08-19"),
            holdout_start=pd.Timestamp("2024-08-20"),
            holdout_end=pd.Timestamp("2024-08-31"),
        )
    ]
    manifest = build_calibration_budget_manifest(
        winners=winners,
        candidates=candidates,
        splits=splits,
    )
    frozen = manifest["architecture_specific_parameters_frozen"]["shipped_tomics"]
    assert "lai_target_center" not in frozen
    assert "fruit_load_multiplier" not in frozen
