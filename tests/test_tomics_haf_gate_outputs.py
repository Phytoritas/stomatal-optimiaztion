import json
from pathlib import Path

from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.haf_gate_outputs import (
    duplicate_casefold_keys,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.haf_promotion_gate import (
    run_haf_promotion_gate,
)
from tests.tomics_haf_gate_fixtures import write_haf_gate_fixture


def test_haf_gate_outputs_write_expected_private_artifacts(tmp_path):
    fixture = write_haf_gate_fixture(tmp_path)

    run_haf_promotion_gate(
        fixture["promotion_config"],
        repo_root=fixture["repo_root"],
        config_path=fixture["config_path"],
    )
    output_root = Path(fixture["promotion_root"])
    expected = [
        "promotion_gate_scorecard.csv",
        "promotion_gate_summary.csv",
        "promotion_gate_summary.md",
        "promotion_gate_metadata.json",
        "promotion_gate_blockers.csv",
        "promotion_candidate_for_future_gate.json",
        "new_phytologist_readiness_matrix.csv",
        "new_phytologist_readiness_matrix.md",
        "new_phytologist_readiness_metadata.json",
        "claim_register.csv",
        "claim_register.md",
        "claim_register.json",
    ]

    for filename in expected:
        assert (output_root / filename).exists(), filename
    metadata_text = (output_root / "promotion_gate_metadata.json").read_text(encoding="utf-8")
    assert duplicate_casefold_keys(metadata_text) == []
    metadata = json.loads(metadata_text)
    assert metadata["promotion_gate_run"] is True
    assert metadata["cross_dataset_gate_run"] is True
    assert metadata["shipped_TOMICS_incumbent_changed"] is False
    assert metadata["promoted_candidate_id"] is None
    cross_root = fixture["repo_root"] / "out" / "tomics" / "validation" / "multi-dataset" / "haf_2025_2c"
    for filename in [
        "cross_dataset_scorecard.csv",
        "cross_dataset_gate_summary.csv",
        "cross_dataset_gate_summary.md",
        "cross_dataset_metadata.json",
        "cross_dataset_blockers.csv",
    ]:
        assert (cross_root / filename).exists(), filename
