import json
from pathlib import Path

import pandas as pd
import yaml

from tomics_haf_latent_fixtures import feature_frame, latent_config, observer_metadata

from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.latent_allocation.pipeline import (
    run_tomics_haf_latent_allocation,
)


def _write_config(tmp_path: Path, *, row_cap_applied: bool = False) -> Path:
    feature_path = tmp_path / "feature.csv"
    metadata_path = tmp_path / "metadata.json"
    output_root = tmp_path / "latent_out"
    feature_frame().to_csv(feature_path, index=False)
    metadata_path.write_text(json.dumps(observer_metadata(row_cap_applied=row_cap_applied)), encoding="utf-8")
    config = latent_config(output_root)
    config["paths"]["repo_root"] = str(tmp_path)
    config["tomics_haf"]["observer_feature_frame"] = str(feature_path)
    config["tomics_haf"]["observer_metadata"] = str(metadata_path)
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    return config_path


def test_latent_allocation_pipeline_metadata_contract(tmp_path: Path) -> None:
    result = run_tomics_haf_latent_allocation(_write_config(tmp_path))
    metadata = result["metadata"]

    assert metadata["season_id"] == "2025_2C"
    assert metadata["latent_allocation_inference_run"] is True
    assert metadata["harvest_family_factorial_run"] is False
    assert metadata["promotion_gate_run"] is False
    assert metadata["cross_dataset_gate_run"] is False
    assert metadata["shipped_TOMICS_incumbent_changed"] is False
    assert metadata["raw_THORP_allocator_used"] is False
    assert metadata["THORP_used_as_bounded_prior"] is True
    assert metadata["latent_allocation_promotable_by_itself"] is False
    assert metadata["production_observer_precondition_passed"] is True
    assert Path(result["outputs"]["posteriors"]).exists()
    posteriors = pd.read_csv(result["outputs"]["posteriors"])
    diagnostics = pd.read_csv(result["outputs"]["diagnostics"])
    assert not posteriors.empty
    assert "allocation_identifiability_score" in diagnostics.columns
    assert "diagnostic_statement" in diagnostics.columns


def test_latent_allocation_pipeline_fails_safely_on_row_cap(tmp_path: Path) -> None:
    result = run_tomics_haf_latent_allocation(_write_config(tmp_path, row_cap_applied=True))
    metadata = result["metadata"]

    assert metadata["latent_allocation_inference_run"] is False
    assert metadata["latent_allocation_ready"] is False
    assert metadata["production_observer_precondition_passed"] is False
