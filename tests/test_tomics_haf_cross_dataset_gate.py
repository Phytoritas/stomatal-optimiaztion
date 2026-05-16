from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.haf_cross_dataset_gate import (
    run_haf_cross_dataset_gate,
)
from tests.tomics_haf_gate_fixtures import write_haf_gate_fixture


def test_haf_cross_dataset_gate_blocks_one_measured_dataset(tmp_path):
    fixture = write_haf_gate_fixture(tmp_path)

    metadata = run_haf_cross_dataset_gate(
        fixture["cross_config"],
        repo_root=fixture["repo_root"],
        config_path=fixture["config_path"],
    )["metadata"]

    assert metadata["cross_dataset_gate_run"] is True
    assert metadata["cross_dataset_gate_passed"] is False
    assert metadata["cross_dataset_gate_status"] == "blocked_insufficient_measured_datasets"
    assert metadata["measured_dataset_count"] == 1
    assert metadata["required_measured_dataset_count"] == 2


def test_haf_cross_dataset_gate_diagnostic_proxy_does_not_count(tmp_path):
    fixture = write_haf_gate_fixture(tmp_path)
    proxy = dict(fixture["cross_config"]["cross_dataset_gate"]["available_dataset_outputs"][0])
    proxy.update(
        {
            "dataset_id": "legacy_proxy",
            "dataset_type": "legacy_public_proxy",
            "measured_or_proxy": "proxy",
            "contributes_to_promotion_gate": False,
        }
    )
    fixture["cross_config"]["cross_dataset_gate"]["available_dataset_outputs"].append(proxy)

    metadata = run_haf_cross_dataset_gate(
        fixture["cross_config"],
        repo_root=fixture["repo_root"],
        config_path=fixture["config_path"],
    )["metadata"]

    assert metadata["measured_dataset_count"] == 1
    assert metadata["cross_dataset_gate_passed"] is False


def test_haf_cross_dataset_gate_duplicate_measured_artifact_does_not_count_twice(tmp_path):
    fixture = write_haf_gate_fixture(tmp_path)
    duplicate = dict(fixture["cross_config"]["cross_dataset_gate"]["available_dataset_outputs"][0])
    duplicate["dataset_id"] = "haf_2025_2c_duplicate_label"
    fixture["cross_config"]["cross_dataset_gate"]["available_dataset_outputs"].append(duplicate)

    result = run_haf_cross_dataset_gate(
        fixture["cross_config"],
        repo_root=fixture["repo_root"],
        config_path=fixture["config_path"],
    )
    metadata = result["metadata"]

    assert metadata["measured_dataset_count"] == 1
    assert metadata["measured_dataset_ids"] == ["haf_2025_2c"]
    assert metadata["cross_dataset_gate_passed"] is False
