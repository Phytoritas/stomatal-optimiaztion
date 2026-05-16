from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.haf_new_phytologist_readiness import (
    build_new_phytologist_readiness_matrix,
)


def test_new_phytologist_readiness_blocks_gate_categories_without_universal_claim():
    frame = build_new_phytologist_readiness_matrix(
        promotion_metadata={
            "promotion_gate_run": True,
            "promotion_gate_passed": False,
            "promotion_gate_status": "blocked_cross_dataset_evidence_insufficient",
        },
        cross_dataset_metadata={
            "cross_dataset_gate_run": True,
            "cross_dataset_gate_passed": False,
            "cross_dataset_gate_status": "blocked_insufficient_measured_datasets",
        },
        plotkit_manifest_exists=True,
        rendered_plot_count=0,
        claim_register_exists=True,
        reproducibility_manifest_exists=True,
    )

    statuses = dict(zip(frame["category"], frame["status"], strict=False))
    assert statuses["promotion_gate"] == "blocked"
    assert statuses["cross_dataset_gate"] == "blocked"
    assert statuses["plotkit_figures"] == "partial"
    assert statuses["architecture_novelty"] == "pass"
    assert not frame["paper_safe_claim"].str.contains("universal", case=False).any()


def test_new_phytologist_readiness_blocks_core_categories_when_guardrails_fail():
    frame = build_new_phytologist_readiness_matrix(
        promotion_metadata={
            "promotion_gate_run": True,
            "promotion_gate_passed": False,
            "promotion_gate_status": "blocked_guardrail_failure",
            "canonical_fruit_DMC_fraction": 0.056,
            "DMC_fixed_for_2025_2C": True,
            "DMC_sensitivity_enabled": False,
            "dry_yield_is_dmc_estimated": True,
            "direct_dry_yield_measured": False,
            "radiation_daynight_primary_source": "dataset1",
            "radiation_column_used": "env_inside_radiation_wm2",
            "fixed_clock_daynight_primary": False,
            "latent_allocation_directly_validated": True,
            "raw_THORP_allocator_used": True,
            "THORP_used_as_bounded_prior": True,
            "fruit_diameter_p_values_allowed": False,
            "fruit_diameter_allocation_calibration_target": False,
            "fruit_diameter_model_promotion_target": True,
            "harvest_family_factorial_run": True,
        },
        cross_dataset_metadata={
            "cross_dataset_gate_run": True,
            "cross_dataset_gate_passed": False,
            "cross_dataset_gate_status": "blocked_insufficient_measured_datasets",
        },
        plotkit_manifest_exists=True,
        rendered_plot_count=0,
        claim_register_exists=True,
        reproducibility_manifest_exists=True,
    )

    statuses = dict(zip(frame["category"], frame["status"], strict=False))
    assert statuses["latent_allocation_inference"] == "blocked"
    assert statuses["paper_claim_safety"] == "blocked"
