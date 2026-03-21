from __future__ import annotations

from pathlib import Path

from stomatal_optimiaztion.domains.tomato.tomics.alloc.core import load_config
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.calibration import (
    run_calibration_suite,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.current_vs_promoted import (
    run_current_vs_promoted_factorial,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.identifiability import (
    run_identifiability_analysis,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.promotion_gate import (
    run_promotion_gate,
)

from .tomics_knu_test_helpers import write_minimal_knu_config, write_minimal_knu_fairness_config


def test_promotion_gate_pipeline_writes_guardrail_outputs(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    bootstrap_config = write_minimal_knu_config(tmp_path, repo_root=repo_root, mode="both")
    run_current_vs_promoted_factorial(config_path=bootstrap_config, mode="both")

    fairness_config_path = write_minimal_knu_fairness_config(tmp_path, repo_root=repo_root)
    fairness_config = load_config(fairness_config_path)
    artifacts = run_calibration_suite(fairness_config, repo_root=repo_root, config_path=fairness_config_path)
    run_identifiability_analysis(fairness_config, repo_root=repo_root, config_path=fairness_config_path)
    decision = run_promotion_gate(fairness_config, repo_root=repo_root, config_path=fairness_config_path)

    assert (artifacts.output_root / "calibration_manifest.json").exists()
    assert (artifacts.output_root / "holdout_results.csv").exists()
    assert (artifacts.output_root / "winner_stability.csv").exists()
    assert (artifacts.output_root / "parameter_stability.csv").exists()
    promotion_root = Path(decision["output_root"])
    assert (promotion_root / "promotion_scorecard.csv").exists()
    assert (promotion_root / "promotion_decision.md").exists()
    assert (promotion_root / "promotion_guardrails.json").exists()
    assert (promotion_root / "promotion_holdout_overlay.png").exists()
    assert (promotion_root / "winner_stability.csv").exists()
    assert decision["incumbent"] in {"shipped_tomics", "current_selected", "promoted_selected"}
