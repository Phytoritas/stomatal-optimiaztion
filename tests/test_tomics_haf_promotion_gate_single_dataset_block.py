from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.haf_promotion_gate import (
    run_haf_promotion_gate,
)
from tests.tomics_haf_gate_fixtures import SELECTED_CANDIDATE_ID, write_haf_gate_fixture


def test_haf_promotion_gate_blocks_single_dataset_promotion(tmp_path):
    fixture = write_haf_gate_fixture(tmp_path)

    result = run_haf_promotion_gate(
        fixture["promotion_config"],
        repo_root=fixture["repo_root"],
        config_path=fixture["config_path"],
    )
    metadata = result["metadata"]

    assert metadata["promotion_gate_run"] is True
    assert metadata["promotion_gate_passed"] is False
    assert metadata["promotion_gate_status"] == "blocked_cross_dataset_evidence_insufficient"
    assert "cross_dataset_evidence_insufficient" in metadata["promotion_block_reasons"]
    assert metadata["measured_dataset_count"] == 1
    assert metadata["required_measured_dataset_count"] == 2
    assert metadata["single_dataset_promotion_allowed"] is False
    assert metadata["selected_candidate_for_future_cross_dataset_gate"] == SELECTED_CANDIDATE_ID
    assert metadata["promoted_candidate_id"] is None
