from pathlib import Path

import json

import pytest

from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.haf_harvest_factorial import (
    run_tomics_haf_harvest_family_factorial,
)

from tests.tomics_haf_harvest_fixtures import (
    synthetic_haf_harvest_config,
    write_synthetic_haf_harvest_inputs,
)


def test_haf_harvest_goal3b_blocks_promotion_and_cross_dataset_gate(tmp_path: Path) -> None:
    paths = write_synthetic_haf_harvest_inputs(tmp_path)
    result = run_tomics_haf_harvest_family_factorial(
        synthetic_haf_harvest_config(paths),
        repo_root=tmp_path,
        config_path=tmp_path / "config.yaml",
    )

    metadata = json.loads(Path(result["paths"]["metadata"]).read_text())
    selected = json.loads(Path(result["paths"]["selected"]).read_text())

    assert metadata["promotion_gate_run"] is False
    assert metadata["cross_dataset_gate_run"] is False
    assert metadata["single_dataset_promotion_allowed"] is False
    assert metadata["shipped_TOMICS_incumbent_changed"] is False
    assert selected["latent_allocation_directly_validated"] is False
    assert selected["raw_THORP_allocator_used"] is False


def test_haf_harvest_rejects_failed_latent_guardrails(tmp_path: Path) -> None:
    paths = write_synthetic_haf_harvest_inputs(tmp_path)
    latent_metadata = json.loads(paths["latent_metadata"].read_text())
    latent_metadata["latent_allocation_guardrails_passed"] = False
    paths["latent_metadata"].write_text(json.dumps(latent_metadata), encoding="utf-8")

    with pytest.raises(ValueError, match="guardrails failed"):
        run_tomics_haf_harvest_family_factorial(
            synthetic_haf_harvest_config(paths),
            repo_root=tmp_path,
            config_path=tmp_path / "config.yaml",
        )


def test_haf_harvest_rejects_raw_thorp_allocator_metadata(tmp_path: Path) -> None:
    paths = write_synthetic_haf_harvest_inputs(tmp_path)
    latent_metadata = json.loads(paths["latent_metadata"].read_text())
    latent_metadata["raw_THORP_allocator_used"] = True
    paths["latent_metadata"].write_text(json.dumps(latent_metadata), encoding="utf-8")

    with pytest.raises(ValueError, match="Raw THORP allocator"):
        run_tomics_haf_harvest_family_factorial(
            synthetic_haf_harvest_config(paths),
            repo_root=tmp_path,
            config_path=tmp_path / "config.yaml",
        )
