from __future__ import annotations

from pathlib import Path

from stomatal_optimiaztion.domains.tomato.tomics.alloc.core import load_config
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.current_vs_promoted import (
    prepare_knu_bundle,
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
