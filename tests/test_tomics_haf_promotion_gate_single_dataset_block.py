import shutil

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


def test_haf_promotion_gate_can_consume_two_unique_measured_datasets(tmp_path):
    fixture = write_haf_gate_fixture(tmp_path)
    second_root = fixture["repo_root"] / "out" / "tomics" / "validation" / "harvest-family" / "haf_2025_2c_replication"
    second_root.mkdir(parents=True)
    shutil.copyfile(
        fixture["harvest_root"] / "harvest_family_metadata.json",
        second_root / "harvest_family_metadata.json",
    )
    shutil.copyfile(
        fixture["harvest_root"] / "harvest_family_rankings.csv",
        second_root / "harvest_family_rankings.csv",
    )
    fixture["promotion_config"]["cross_dataset_gate"] = {
        "current_dataset_id": "haf_2025_2c",
        "require_measured_dataset_count_min": 2,
        "available_dataset_outputs": [
            {
                "dataset_id": "haf_2025_2c",
                "dataset_type": "haf_measured_actual",
                "measured_or_proxy": "measured",
                "harvest_family_metadata": str(fixture["harvest_root"] / "harvest_family_metadata.json"),
                "harvest_family_rankings": str(fixture["harvest_root"] / "harvest_family_rankings.csv"),
                "contributes_to_promotion_gate": True,
            },
            {
                "dataset_id": "haf_2025_2c_replication",
                "dataset_type": "haf_measured_actual",
                "measured_or_proxy": "measured",
                "harvest_family_metadata": str(second_root / "harvest_family_metadata.json"),
                "harvest_family_rankings": str(second_root / "harvest_family_rankings.csv"),
                "contributes_to_promotion_gate": True,
            },
        ],
        "allow_legacy_or_public_proxy_for_promotion": False,
        "proxy_dataset_use": "diagnostic_only",
        "single_dataset_promotion_allowed": False,
    }

    result = run_haf_promotion_gate(
        fixture["promotion_config"],
        repo_root=fixture["repo_root"],
        config_path=fixture["config_path"],
    )
    metadata = result["metadata"]

    assert metadata["cross_dataset_gate_passed"] is True
    assert metadata["measured_dataset_count"] == 2
    assert metadata["promotion_gate_passed"] is True
    assert metadata["promoted_candidate_id"] == SELECTED_CANDIDATE_ID
