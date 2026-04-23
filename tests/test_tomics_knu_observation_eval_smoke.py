from __future__ import annotations

import json
from pathlib import Path

import pytest

from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.current_vs_promoted import (
    run_current_vs_promoted_factorial,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.observation_eval import (
    run_knu_observation_eval,
)

from .tomics_knu_test_helpers import write_minimal_fairness_config, write_minimal_knu_config


@pytest.mark.slow
def test_observation_eval_runner_writes_harvest_outputs(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    bootstrap_config = write_minimal_knu_config(tmp_path, repo_root=repo_root, mode="both")
    run_current_vs_promoted_factorial(config_path=bootstrap_config, mode="both")

    config_path = write_minimal_fairness_config(
        tmp_path,
        repo_root=repo_root,
        filename="knu_observation_eval.yaml",
        section_name="observation_eval",
        section_payload={
            "cumulative_overlay_spec": "configs/plotkit/tomics/knu_cumulative_overlay.yaml",
            "daily_overlay_spec": "configs/plotkit/tomics/knu_daily_increment_overlay.yaml",
        },
    )
    result = run_knu_observation_eval(config_path=config_path)
    output_root = Path(result["output_root"])

    assert (output_root / "observation_fit_summary.csv").exists()
    assert (output_root / "cumulative_overlay.png").exists()
    assert (output_root / "daily_increment_overlay.png").exists()
    manifest = json.loads((output_root / "observation_operator_manifest.json").read_text(encoding="utf-8"))
    assert manifest["observation_operator"]["measured_target"] == "cumulative_harvested_fruit_dry_weight_floor_area"
