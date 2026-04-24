from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation import (
    run_current_vs_promoted_factorial,
)

from .tomics_knu_test_helpers import write_minimal_knu_config


@pytest.mark.slow
def test_current_vs_promoted_summary_bundle_is_written_smoke(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    config_path = write_minimal_knu_config(tmp_path, repo_root=repo_root, mode="both")

    summary = run_current_vs_promoted_factorial(config_path=config_path, mode="both")
    output_root = Path(summary["comparison"]["output_root"])

    required = {
        "comparison_summary.csv",
        "architecture_promotion_scorecard.csv",
        "current_vs_promoted_plot.png",
        "yield_fit_overlay.png",
        "allocation_behavior_overlay.png",
        "theta_proxy_diagnostics.png",
        "canonical_winners.json",
        "promotion_recommendation.md",
    }
    assert all((output_root / name).exists() for name in required)

    scorecard = pd.read_csv(output_root / "architecture_promotion_scorecard.csv")
    assert {"candidate_label", "mean_yield_rmse_offset_adjusted"}.issubset(scorecard.columns)
    assert {"shipped_tomics", "current_selected", "promoted_selected"}.issubset(
        set(scorecard["candidate_label"])
    )
    winners = json.loads((output_root / "canonical_winners.json").read_text(encoding="utf-8"))
    assert winners["current_selected_architecture_id"] == summary["current"]["selected_architecture_id"]
    assert winners["promoted_selected_architecture_id"] == summary["promoted"]["selected_architecture_id"]
