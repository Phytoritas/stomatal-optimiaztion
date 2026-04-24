from __future__ import annotations

from pathlib import Path

import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.alloc.core import load_config
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.current_vs_promoted import (
    prepare_knu_bundle,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.init_search import (
    build_reconstruction_candidates,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.state_reconstruction import (
    reconstruct_hidden_state,
)

from .tomics_knu_test_helpers import write_minimal_current_base_config, write_minimal_knu_fairness_config


def test_state_reconstruction_returns_supported_mode_and_initial_state(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    config_path = write_minimal_knu_fairness_config(tmp_path, repo_root=repo_root)
    config = load_config(config_path)
    prepared_bundle = prepare_knu_bundle(config, repo_root=repo_root, config_path=config_path)
    base_config_path = write_minimal_current_base_config(tmp_path, repo_root=repo_root)
    base_config = load_config(base_config_path)
    architecture_row = {
        "architecture_id": "shipped_tomics_control",
        "partition_policy": "tomics",
        "allocation_scheme": "4pool",
        "wet_root_cap": 0.10,
        "dry_root_cap": 0.18,
        "lai_target_center": 2.75,
        "leaf_fraction_of_shoot_base": 0.70,
        "fruit_load_multiplier": 1.0,
        "thorp_root_blend": 1.0,
    }
    result = reconstruct_hidden_state(
        architecture_row=architecture_row,
        base_config=base_config,
        forcing_csv_path=prepared_bundle.scenarios["moderate"].forcing_csv_path,
        theta_center=float(prepared_bundle.scenarios["moderate"].summary.get("theta_mean", 0.65)),
        observed_df=prepared_bundle.observed_df,
        calibration_end=prepared_bundle.calibration_end,
        repo_root=repo_root,
        unit_label=prepared_bundle.data.observation_unit_label,
    )
    assert result.mode in {"minimal_scalar_init", "cohort_aware_init", "buffer_aware_init"}
    assert "W_fr_harvested" in result.initial_state_overrides
    assert "W_lv" in result.initial_state_overrides
    assert result.metrics["init_fit_score"] == result.metrics["init_fit_score"]


def test_cohort_reconstruction_seeds_harvest_ready_oldest_truss() -> None:
    observed_df = pd.DataFrame(
        {
            "date": pd.to_datetime(["2025-01-01", "2025-01-02"]),
            "measured_cumulative_total_fruit_dry_weight_floor_area": [5.0, 8.0],
            "measured_daily_increment_floor_area": [pd.NA, 3.0],
        }
    )

    candidates = build_reconstruction_candidates(observed_df, modes=("cohort_aware_init",))
    cohort_candidates = [candidate for candidate in candidates if candidate.mode == "cohort_aware_init"]
    assert cohort_candidates

    truss_cohorts = cohort_candidates[0].initial_state_overrides["truss_cohorts"]
    oldest = max(truss_cohorts, key=lambda row: float(row["tdvs"]))
    assert float(oldest["tdvs"]) >= 1.0
    assert oldest["harvest_ready_flag"] is True
