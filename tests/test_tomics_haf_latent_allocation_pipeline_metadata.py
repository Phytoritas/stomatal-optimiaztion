import json
from pathlib import Path

import pandas as pd
import yaml

from tomics_haf_latent_fixtures import feature_frame, latent_config, observer_metadata

from scripts.run_tomics_haf_latent_allocation import main
from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.latent_allocation.pipeline import (
    run_tomics_haf_latent_allocation,
)


def _write_config(
    tmp_path: Path,
    *,
    row_cap_applied: bool = False,
    metadata_overrides: dict | None = None,
    empty_feature_frame: bool = False,
) -> Path:
    feature_path = tmp_path / "feature.csv"
    metadata_path = tmp_path / "metadata.json"
    output_root = tmp_path / "latent_out"
    frame = feature_frame()
    if empty_feature_frame:
        frame = frame.iloc[0:0]
    frame.to_csv(feature_path, index=False)
    metadata = observer_metadata(row_cap_applied=row_cap_applied)
    metadata.update(metadata_overrides or {})
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
    config = latent_config(output_root)
    config["paths"]["repo_root"] = str(tmp_path)
    config["tomics_haf"]["observer_feature_frame"] = str(feature_path)
    config["tomics_haf"]["observer_metadata"] = str(metadata_path)
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    return config_path


def test_latent_allocation_pipeline_metadata_contract(tmp_path: Path) -> None:
    result = run_tomics_haf_latent_allocation(
        _write_config(
            tmp_path,
            metadata_overrides={
                "event_bridged_ET_calibration_status": "calibrated_to_legacy_daily_event_total",
                "harvest_yield_available": True,
                "fresh_yield_available": True,
                "fresh_yield_source": "legacy_v1_3_derived_output",
                "dry_yield_available": True,
                "dry_yield_source": "legacy_v1_3_derived_output",
                "dry_yield_is_dmc_estimated": True,
                "direct_dry_yield_measured": False,
                "legacy_yield_bridge_used": True,
                "legacy_yield_bridge_provenance": "legacy_v1_3_derived_output",
                "default_fruit_dry_matter_content_from_legacy": 0.056,
                "configured_default_fruit_dry_matter_content": 0.065,
            },
        )
    )
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
    assert metadata["event_bridged_ET_calibration_status"] == "calibrated_to_legacy_daily_event_total"
    assert metadata["dry_yield_is_dmc_estimated"] is True
    assert metadata["direct_dry_yield_measured"] is False
    assert metadata["legacy_yield_bridge_provenance"] == "legacy_v1_3_derived_output"
    assert metadata["latent_allocation_directly_validated"] is False
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


def test_pipeline_guardrails_fail_on_forbidden_upstream_metadata(tmp_path: Path) -> None:
    result = run_tomics_haf_latent_allocation(
        _write_config(tmp_path, metadata_overrides={"raw_THORP_allocator_used": True})
    )
    metadata = result["metadata"]

    assert metadata["latent_allocation_guardrails_passed"] is False
    assert metadata["no_raw_THORP_guard_passed"] is False


def test_runner_returns_nonzero_when_guardrails_fail(tmp_path: Path) -> None:
    config_path = _write_config(
        tmp_path,
        metadata_overrides={"fruit_diameter_model_promotion_target": True},
    )

    assert main(["--config", str(config_path)]) == 1


def test_pipeline_fails_safely_on_empty_input_state(tmp_path: Path) -> None:
    result = run_tomics_haf_latent_allocation(_write_config(tmp_path, empty_feature_frame=True))
    metadata = result["metadata"]
    guardrails = pd.read_csv(result["outputs"]["guardrails"])

    assert metadata["production_observer_precondition_passed"] is True
    assert metadata["latent_allocation_inference_run"] is False
    assert metadata["latent_allocation_ready"] is False
    assert guardrails.iloc[0]["guardrail_name"] == "latent_allocation_input_state"


def test_pipeline_guardrails_fail_on_fruit_promotion_target(tmp_path: Path) -> None:
    result = run_tomics_haf_latent_allocation(
        _write_config(tmp_path, metadata_overrides={"fruit_diameter_model_promotion_target": True})
    )
    metadata = result["metadata"]

    assert metadata["latent_allocation_guardrails_passed"] is False
    assert metadata["no_fruit_diameter_calibration_guard_passed"] is False
