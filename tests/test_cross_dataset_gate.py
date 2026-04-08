from __future__ import annotations

import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.cross_dataset_gate import (
    build_cross_dataset_guardrail_summary,
    cross_dataset_proxy_guardrail,
)


def test_cross_dataset_proxy_guardrail_blocks_single_dataset_proxy_heavy_winner() -> None:
    candidate = pd.Series(
        {
            "dataset_count": 1,
            "mean_native_family_state_fraction": 0.3,
            "mean_proxy_family_state_fraction": 0.7,
            "mean_shared_tdvs_proxy_fraction": 0.8,
            "cross_dataset_stability_score": 1.0,
        }
    )
    guardrail = cross_dataset_proxy_guardrail(
        candidate,
        native_state_coverage_min=0.5,
        shared_tdvs_proxy_fraction_max=0.5,
        cross_dataset_stability_score_min=0.5,
        min_dataset_count=2,
    )
    assert guardrail["winner_proxy_heavy_flag"] is True
    assert guardrail["winner_not_promotion_grade_due_to_cross_dataset_instability"] is True
    assert guardrail["passes"] is False


def test_cross_dataset_guardrail_summary_selects_top_candidate() -> None:
    scorecard = pd.DataFrame(
        [
            {
                "fruit_harvest_family": "dekoning_fds",
                "leaf_harvest_family": "vegetative_unit_pruning",
                "fdmc_mode": "dekoning_fds",
                "dataset_count": 3,
                "mean_native_family_state_fraction": 1.0,
                "mean_proxy_family_state_fraction": 0.0,
                "mean_shared_tdvs_proxy_fraction": 0.0,
                "cross_dataset_stability_score": 0.67,
            }
        ]
    )
    summary = build_cross_dataset_guardrail_summary(scorecard)
    assert summary["selected_candidate"]["passes"] is True
    assert "multiple measured datasets" in summary["recommendation"] or "Promotion-grade" in summary["recommendation"]
