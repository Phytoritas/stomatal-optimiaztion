from pathlib import Path

import json

from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.haf_harvest_factorial import (
    run_tomics_haf_harvest_family_factorial,
)

from tests.tomics_haf_harvest_fixtures import (
    synthetic_haf_harvest_config,
    write_synthetic_haf_harvest_inputs,
)


def test_haf_reproducibility_manifest_records_inputs_hashes_and_gate_flags(
    tmp_path: Path,
) -> None:
    paths = write_synthetic_haf_harvest_inputs(tmp_path)
    config_path = tmp_path / "config.yaml"
    config_path.write_text("synthetic: true\n", encoding="utf-8")

    result = run_tomics_haf_harvest_family_factorial(
        synthetic_haf_harvest_config(paths),
        repo_root=tmp_path,
        config_path=config_path,
    )
    manifest = json.loads(
        Path(result["paths"]["reproducibility_json"]).read_text(encoding="utf-8")
    )

    assert manifest["repo_branch"]
    assert manifest["repo_head_sha"]
    assert manifest["config_path"]
    assert str(config_path) in manifest["command_run"]
    assert manifest["config_sha256"]
    assert manifest["dmc_basis"] == 0.056
    assert manifest["DMC_sensitivity_enabled"] is False
    assert manifest["promotion_gate_run"] is False
    assert manifest["cross_dataset_gate_run"] is False
    assert manifest["raw_data_committed"] is False
    assert manifest["out_committed"] is False
    assert manifest["observer_metadata_sha256"]
    assert manifest["latent_metadata_sha256"]
    assert all(
        record["input_file_sha256_status"] in {"computed", "skipped_large_file", "unavailable"}
        for record in manifest["input_files"]
    )
