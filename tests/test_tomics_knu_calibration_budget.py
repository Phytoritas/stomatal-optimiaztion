from __future__ import annotations

from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.parameter_budget import (
    build_calibration_budget,
)


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
