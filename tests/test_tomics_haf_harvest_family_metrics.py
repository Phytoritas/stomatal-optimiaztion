from pathlib import Path

import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.haf_harvest_factorial import (
    run_tomics_haf_harvest_family_factorial,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.haf_harvest_metrics import (
    compute_haf_harvest_metrics,
)

from tests.tomics_haf_harvest_fixtures import (
    synthetic_haf_harvest_config,
    write_synthetic_haf_harvest_inputs,
)


def test_haf_harvest_metrics_outputs_by_loadcell_mean_sd_and_pooled(tmp_path: Path) -> None:
    paths = write_synthetic_haf_harvest_inputs(tmp_path)
    config = synthetic_haf_harvest_config(paths)

    result = run_tomics_haf_harvest_family_factorial(
        config,
        repo_root=tmp_path,
        config_path=tmp_path / "config.yaml",
    )

    by_loadcell = pd.read_csv(result["paths"]["metrics_by_loadcell"])
    mean_sd = pd.read_csv(result["paths"]["metrics_mean_sd"])
    pooled = pd.read_csv(result["paths"]["metrics_pooled"])

    assert not by_loadcell.empty
    assert not mean_sd.empty
    assert not pooled.empty
    assert {"loadcell_id", "rmse_cumulative_DW_g_m2_floor"}.issubset(
        by_loadcell.columns
    )
    assert "mean_rmse_cumulative_DW_g_m2_floor" in mean_sd.columns


def test_haf_pooled_final_bias_sums_loadcell_final_values() -> None:
    overlay = pd.DataFrame(
        {
            "date": pd.to_datetime(["2025-11-01", "2025-11-01"]),
            "loadcell_id": ["1", "4"],
            "treatment": ["Control", "Drought"],
            "candidate_id": ["candidate", "candidate"],
            "stage": ["HF0", "HF0"],
            "allocator_family": ["shipped_tomics", "shipped_tomics"],
            "latent_allocation_prior_family": ["none", "none"],
            "fruit_harvest_family": ["tomsim_truss_incumbent", "tomsim_truss_incumbent"],
            "leaf_harvest_family": ["leaf_harvest_tomsim_legacy", "leaf_harvest_tomsim_legacy"],
            "observation_operator": ["fresh_to_dry_dmc_0p056", "fresh_to_dry_dmc_0p056"],
            "fdmc_mode": ["constant_0p056", "constant_0p056"],
            "measured_cumulative_fruit_DW_g_m2_floor_dmc_0p056": [10.0, 100.0],
            "model_cumulative_fruit_DW_g_m2_floor": [12.0, 90.0],
            "measured_daily_increment_DW_g_m2_floor_dmc_0p056": [10.0, 100.0],
            "model_daily_increment_DW_g_m2_floor": [12.0, 90.0],
            "residual_DW_g_m2_floor": [2.0, -10.0],
            "mass_balance_error": [0.0, 0.0],
            "leaf_harvest_mass_balance_error": [0.0, 0.0],
            "budget_units_used": [0, 0],
            "budget_parity_group": ["none", "none"],
            "invalid_run_flag": [False, False],
        }
    )

    _by_loadcell, pooled, _mean_sd = compute_haf_harvest_metrics(overlay)

    assert pooled["final_cumulative_bias_DW_g_m2_floor"].iloc[0] == -8.0
