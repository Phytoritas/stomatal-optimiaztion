from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.haf_claim_register import (
    FORBIDDEN_CLAIMS,
    build_claim_register,
)


def test_haf_claim_register_marks_unsafe_claims_forbidden_with_rewrites():
    frame = build_claim_register(
        promotion_gate_passed=False,
        cross_dataset_gate_passed=False,
        selected_for_future_cross_dataset_gate=False,
        evidence_path="promotion_gate_metadata.json",
    )

    forbidden = frame[frame["claim_text"].isin(FORBIDDEN_CLAIMS)]
    assert not forbidden.empty
    assert forbidden["status"].eq("forbidden").all()
    assert forbidden["safe_rewrite"].astype(str).str.len().gt(0).all()
    assert (
        frame.loc[
            frame["claim_text"].str.contains("bounded architecture-discrimination", regex=False),
            "status",
        ]
        .eq("allowed")
        .any()
    )
    assert not frame["claim_text"].str.contains("selected candidates for future cross-dataset testing").any()


def test_haf_claim_register_conditions_allowed_claims_on_metadata_guardrails():
    frame = build_claim_register(
        promotion_gate_passed=False,
        cross_dataset_gate_passed=False,
        selected_for_future_cross_dataset_gate=False,
        evidence_path="promotion_gate_metadata.json",
        promotion_metadata={
            "canonical_fruit_DMC_fraction": 0.056,
            "DMC_fixed_for_2025_2C": True,
            "DMC_sensitivity_enabled": False,
            "dry_yield_is_dmc_estimated": True,
            "direct_dry_yield_measured": False,
            "radiation_daynight_primary_source": "dataset1",
            "radiation_column_used": "env_inside_radiation_wm2",
            "fixed_clock_daynight_primary": False,
            "latent_allocation_directly_validated": False,
            "THORP_used_as_bounded_prior": True,
            "raw_THORP_allocator_used": True,
            "harvest_family_factorial_run": True,
            "promotion_gate_run": True,
            "cross_dataset_gate_run": True,
        },
    )

    thorp_claim = frame.loc[
        frame["claim_text"].str.contains("bounded mechanistic prior/correction", regex=False),
        "status",
    ]
    assert thorp_claim.tolist() == ["conditional"]
