from __future__ import annotations

from pathlib import Path

import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation import (
    run_current_vs_promoted_factorial,
)

from .tomics_knu_test_helpers import write_minimal_knu_config


def test_promoted_factorial_knu_runner_writes_required_outputs(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    config_path = write_minimal_knu_config(tmp_path, repo_root=repo_root, mode="promoted")

    summary = run_current_vs_promoted_factorial(config_path=config_path, mode="promoted")
    output_root = Path(summary["promoted"]["output_root"])

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

    design_df = pd.read_csv(output_root / "design_table.csv")
    assert design_df["stage"].value_counts().to_dict()["p0"] == 5
    assert design_df["stage"].value_counts().to_dict()["p2"] == 13

    metrics_df = pd.read_csv(output_root / "run_metrics.csv")
    promoted_rows = metrics_df[metrics_df["policy_family"].eq("promoted")]
    assert {
        "optimizer_mode",
        "vegetative_prior_mode",
        "leaf_marginal_mode",
        "stem_marginal_mode",
        "root_marginal_mode",
    }.issubset(promoted_rows.columns)
