from __future__ import annotations

import json

import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.cross_dataset_scorecard import (
    build_cross_dataset_scorecard,
)


def test_cross_dataset_scorecard_aggregates_dataset_rows() -> None:
    dataset_rankings = [
        pd.DataFrame(
            [
                {
                    "dataset_id": "knu_a",
                    "fruit_harvest_family": "dekoning_fds",
                    "leaf_harvest_family": "vegetative_unit_pruning",
                    "fdmc_mode": "dekoning_fds",
                    "mean_score": -10.0,
                    "mean_rmse_cumulative_offset": 5.0,
                    "mean_rmse_daily_increment": 2.0,
                    "max_harvest_mass_balance_error": 0.0,
                    "max_canopy_collapse_days": 3,
                    "mean_native_family_state_fraction": 0.8,
                    "mean_proxy_family_state_fraction": 0.2,
                    "mean_shared_tdvs_proxy_fraction": 0.1,
                    "family_state_mode_distribution": json.dumps({"native_payload": 0.8}),
                    "proxy_mode_used_distribution": json.dumps({"false": 0.8, "true": 0.2}),
                }
            ]
        ),
        pd.DataFrame(
            [
                {
                    "dataset_id": "knu_b",
                    "fruit_harvest_family": "dekoning_fds",
                    "leaf_harvest_family": "vegetative_unit_pruning",
                    "fdmc_mode": "dekoning_fds",
                    "mean_score": -8.0,
                    "mean_rmse_cumulative_offset": 4.0,
                    "mean_rmse_daily_increment": 1.5,
                    "max_harvest_mass_balance_error": 0.0,
                    "max_canopy_collapse_days": 2,
                    "mean_native_family_state_fraction": 0.7,
                    "mean_proxy_family_state_fraction": 0.3,
                    "mean_shared_tdvs_proxy_fraction": 0.2,
                    "family_state_mode_distribution": json.dumps({"native_payload": 0.7}),
                    "proxy_mode_used_distribution": json.dumps({"false": 0.7, "true": 0.3}),
                }
            ]
        ),
    ]
    selected_payloads = [
        {
            "dataset_id": "knu_a",
            "selected_fruit_harvest_family": "dekoning_fds",
            "selected_leaf_harvest_family": "vegetative_unit_pruning",
            "selected_fdmc_mode": "dekoning_fds",
        },
        {
            "dataset_id": "knu_b",
            "selected_fruit_harvest_family": "dekoning_fds",
            "selected_leaf_harvest_family": "vegetative_unit_pruning",
            "selected_fdmc_mode": "dekoning_fds",
        },
    ]
    scorecard = build_cross_dataset_scorecard(dataset_rankings, selected_payloads)
    row = scorecard.iloc[0]
    assert row["dataset_count"] == 2
    assert row["dataset_win_count"] == 2
    assert row["cross_dataset_stability_score"] == 1.0
    assert row["mean_native_family_state_fraction"] == 0.75
