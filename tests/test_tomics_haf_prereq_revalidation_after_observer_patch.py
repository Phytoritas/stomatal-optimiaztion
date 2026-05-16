from stomatal_optimiaztion.domains.tomato.tomics.observers.metadata_contract import metadata_contract_audit
from stomatal_optimiaztion.domains.tomato.tomics.observers.pipeline import _production_requirement_failures


def test_production_requirements_pass_only_for_full_chunked_uncapped_export() -> None:
    failures = _production_requirement_failures(
        mode="production",
        pipeline_config={
            "require_chunk_aggregation": True,
            "require_dataset1_full_processed": True,
            "require_dataset2_full_processed": True,
        },
        row_cap_applied=False,
        chunk_aggregation_used=True,
        full_in_memory_large_dataset_used=False,
        dataset1_load_meta={"rows_processed_fraction": 1.0},
        dataset2_load_meta={"rows_processed_fraction": 1.0},
    )

    assert failures == []


def test_production_requirements_report_all_blocking_failures() -> None:
    failures = _production_requirement_failures(
        mode="production",
        pipeline_config={
            "require_chunk_aggregation": True,
            "require_dataset1_full_processed": True,
            "require_dataset2_full_processed": True,
        },
        row_cap_applied=True,
        chunk_aggregation_used=False,
        full_in_memory_large_dataset_used=True,
        dataset1_load_meta={"rows_processed_fraction": 0.5},
        dataset2_load_meta={"rows_processed_fraction": 0.75},
    )

    assert "require_chunk_aggregation=true but chunk_aggregation_used=false" in failures
    assert "require_dataset1_full_processed=true but dataset1_rows_processed_fraction != 1.0" in failures
    assert "require_dataset2_full_processed=true but dataset2_rows_processed_fraction != 1.0" in failures
    assert "full_in_memory_large_dataset_used=true" in failures
    assert "row_cap_applied=true" in failures


def test_observer_metadata_after_hardening_preserves_latent_prerequisite_contract() -> None:
    metadata = {
        "LAI_available": False,
        "VPD_available": True,
        "Dataset3_mapping_confidence": "direct_loadcell_no_date",
        "fruit_diameter_p_values_allowed": False,
        "fruit_diameter_allocation_calibration_target": False,
        "fruit_diameter_model_promotion_target": False,
        "shipped_TOMICS_incumbent_changed": False,
        "production_export_completed": True,
        "production_ready_for_latent_allocation": True,
        "row_cap_applied": False,
        "chunk_aggregation_used": True,
        "latent_allocation_inference_run": False,
        "harvest_family_factorial_run": False,
        "promotion_gate_run": False,
        "direct_dry_yield_measured": False,
        "dry_yield_is_dmc_estimated": True,
    }

    audit = metadata_contract_audit(metadata)
    assert audit["status"].tolist() == ["pass", "pass"]
    assert metadata["direct_dry_yield_measured"] is False
    assert metadata["dry_yield_is_dmc_estimated"] is True
    assert metadata["latent_allocation_inference_run"] is False
