from pathlib import Path

import json

from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.haf_harvest_factorial import (
    run_tomics_haf_harvest_family_factorial,
)

from tests.tomics_haf_harvest_fixtures import (
    synthetic_haf_harvest_config,
    write_synthetic_haf_harvest_inputs,
)


def test_haf_harvest_runner_writes_required_outputs(tmp_path: Path) -> None:
    paths = write_synthetic_haf_harvest_inputs(tmp_path)
    result = run_tomics_haf_harvest_family_factorial(
        synthetic_haf_harvest_config(paths),
        repo_root=tmp_path,
        config_path=tmp_path / "config.yaml",
    )

    output_root = Path(result["output_root"])
    expected_filenames = {
        "harvest_family_factorial_design.csv",
        "harvest_family_run_manifest.csv",
        "harvest_family_metrics_pooled.csv",
        "harvest_family_metrics_by_loadcell.csv",
        "harvest_family_metrics_mean_sd.csv",
        "harvest_family_daily_overlay.csv",
        "harvest_family_cumulative_overlay.csv",
        "harvest_family_mass_balance.csv",
        "harvest_family_budget_parity.csv",
        "harvest_family_rankings.csv",
        "harvest_family_selected_research_candidate.json",
        "harvest_family_prerequisite_promotion_summary.csv",
        "harvest_family_prerequisite_promotion_summary.md",
        "harvest_family_metadata.json",
        "observation_operator_dmc_0p056_audit.csv",
        "no_stale_dmc_0p065_primary_audit.csv",
    }
    for filename in expected_filenames:
        assert (output_root / filename).exists()

    metadata = json.loads((output_root / "harvest_family_metadata.json").read_text())
    assert metadata["harvest_family_factorial_run"] is True
    assert metadata["promotion_gate_run"] is False
    assert metadata["cross_dataset_gate_run"] is False
    assert metadata["shipped_TOMICS_incumbent_changed"] is False
