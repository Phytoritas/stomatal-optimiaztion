from __future__ import annotations

from pathlib import Path

import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation import (
    run_current_vs_promoted_factorial,
)

from .tomics_knu_test_helpers import write_minimal_knu_config


def test_current_factorial_knu_runner_writes_required_outputs(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    config_path = write_minimal_knu_config(tmp_path, repo_root=repo_root, mode="current")

    summary = run_current_vs_promoted_factorial(config_path=config_path, mode="current")
    output_root = Path(summary["current"]["output_root"])

    required = {
        "design_table.csv",
        "run_metrics.csv",
        "interaction_summary.csv",
        "candidate_ranking.csv",
        "selected_architecture.json",
        "decision_bundle.md",
        "validation_vs_measured.csv",
        "summary_plot.png",
        "main_effects.png",
    }
    assert all((output_root / name).exists() for name in required)
    assert (output_root / "validation_plots" / "yield_fit_overlay.png").exists()

    metrics_df = pd.read_csv(output_root / "run_metrics.csv")
    assert {
        "reporting_basis",
        "theta_proxy_mode",
        "theta_proxy_scenario",
        "yield_rmse_offset_adjusted",
        "final_fruit_dry_weight_floor_area",
    }.issubset(metrics_df.columns)
    assert metrics_df["reporting_basis"].eq("floor_area_g_m2").all()
