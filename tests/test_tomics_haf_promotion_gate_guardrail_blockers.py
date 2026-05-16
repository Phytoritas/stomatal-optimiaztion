import pytest

from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.haf_promotion_gate import (
    run_haf_promotion_gate,
)
from tests.tomics_haf_gate_fixtures import write_haf_gate_fixture


@pytest.mark.parametrize(
    ("fixture_kwargs", "expected_blocker"),
    [
        ({"latent_overrides": {"raw_THORP_allocator_used": True}}, "raw_THORP_allocator_used"),
        (
            {"observer_overrides": {"fruit_diameter_model_promotion_target": True}},
            "fruit_diameter_model_promotion_target",
        ),
        (
            {"latent_overrides": {"latent_allocation_directly_validated": True}},
            "latent_allocation_not_direct_validation",
        ),
        (
            {"harvest_overrides": {"shipped_TOMICS_incumbent_changed": True}},
            "shipped_TOMICS_incumbent_changed",
        ),
    ],
)
def test_haf_promotion_gate_blocks_guardrail_violations(tmp_path, fixture_kwargs, expected_blocker):
    fixture = write_haf_gate_fixture(tmp_path, **fixture_kwargs)

    metadata = run_haf_promotion_gate(
        fixture["promotion_config"],
        repo_root=fixture["repo_root"],
        config_path=fixture["config_path"],
    )["metadata"]

    assert metadata["promotion_gate_passed"] is False
    assert expected_blocker in metadata["promotion_block_reasons"]
    assert metadata["promoted_candidate_id"] is None
    assert metadata["promotion_gate_status"] == "blocked_guardrail_failure"
    assert metadata["selected_candidate_for_future_cross_dataset_gate"] is None


def test_haf_promotion_gate_metadata_reflects_guardrail_violation_truth(tmp_path):
    fixture = write_haf_gate_fixture(
        tmp_path,
        latent_overrides={
            "raw_THORP_allocator_used": True,
            "latent_allocation_directly_validated": True,
        },
        observer_overrides={"fruit_diameter_model_promotion_target": True},
        harvest_overrides={"shipped_TOMICS_incumbent_changed": True},
    )

    metadata = run_haf_promotion_gate(
        fixture["promotion_config"],
        repo_root=fixture["repo_root"],
        config_path=fixture["config_path"],
    )["metadata"]

    assert metadata["raw_THORP_allocator_used"] is True
    assert metadata["latent_allocation_directly_validated"] is True
    assert metadata["fruit_diameter_model_promotion_target"] is True
    assert metadata["shipped_TOMICS_incumbent_changed"] is True
    assert metadata["selected_candidate_for_future_cross_dataset_gate"] is None


def test_haf_promotion_gate_blocks_missing_or_blank_required_latent_guardrail(tmp_path):
    fixture = write_haf_gate_fixture(tmp_path)
    guardrails_path = (
        fixture["repo_root"]
        / "out"
        / "tomics"
        / "validation"
        / "latent-allocation"
        / "haf_2025_2c"
        / "latent_allocation_guardrails.csv"
    )
    import pandas as pd

    pd.DataFrame(
        [
            {"guardrail_name": "no_leaf_collapse", "status": "pass", "pass_fail": ""},
        ]
    ).to_csv(guardrails_path, index=False)

    metadata = run_haf_promotion_gate(
        fixture["promotion_config"],
        repo_root=fixture["repo_root"],
        config_path=fixture["config_path"],
    )["metadata"]

    assert metadata["promotion_gate_passed"] is False
    assert "latent_guardrails_pass" in metadata["promotion_block_reasons"]
