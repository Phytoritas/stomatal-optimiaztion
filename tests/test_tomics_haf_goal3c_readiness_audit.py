import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.haf_pre_gate_artifacts import (
    BUDGET_PARITY_BASIS,
    WALL_CLOCK_LIMITATION,
    build_goal3c_readiness_payload,
)


def _metadata(**overrides):
    payload = {
        "production_observer_ready": True,
        "latent_allocation_ready": True,
        "harvest_family_factorial_run": True,
        "candidate_count": 3,
        "canonical_fruit_DMC_fraction": 0.056,
        "fruit_DMC_fraction": 0.056,
        "default_fruit_dry_matter_content": 0.056,
        "promotion_gate_run": False,
        "cross_dataset_gate_run": False,
        "single_dataset_promotion_allowed": False,
        "dry_yield_is_dmc_estimated": True,
        "direct_dry_yield_measured": False,
        "latent_allocation_directly_validated": False,
        "raw_THORP_allocator_used": False,
        "fruit_diameter_promotion_target": False,
        "fruit_diameter_model_promotion_target": False,
        "shipped_TOMICS_incumbent_changed": False,
        "budget_parity_basis": BUDGET_PARITY_BASIS,
        "wall_clock_compute_budget_parity_evaluated": False,
        "wall_clock_compute_budget_parity_required_for_goal_3b": False,
        "budget_parity_limitations": WALL_CLOCK_LIMITATION,
    }
    payload.update(overrides)
    return payload


def _stale_audit(warnings: int = 0) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "status": "pass",
                "upstream_metadata_warning_count": warnings,
            }
        ]
    )


def _readiness(**metadata_overrides):
    return build_goal3c_readiness_payload(
        metadata=_metadata(**metadata_overrides),
        stale_audit=_stale_audit(),
        plotkit_specs_exist=True,
        plotkit_rendered_or_manifested=True,
        reproducibility_manifest_exists=True,
        repo_branch="feat/tomics-haf-2025-2c-harvest-family-eval",
    )


def test_goal3c_readiness_passes_when_hard_preconditions_pass() -> None:
    payload = _readiness()

    assert payload["goal3c_ready"] is True
    assert payload["blockers"] == []


def test_goal3c_readiness_fails_if_stale_dmc_warning_remains() -> None:
    payload = build_goal3c_readiness_payload(
        metadata=_metadata(),
        stale_audit=_stale_audit(warnings=1),
        plotkit_specs_exist=True,
        plotkit_rendered_or_manifested=True,
        reproducibility_manifest_exists=True,
        repo_branch="feat/tomics-haf-2025-2c-harvest-family-eval",
    )

    assert payload["goal3c_ready"] is False
    assert "stale_dmc_warning_zero" in payload["blockers"]


def test_goal3c_readiness_fails_if_promotion_gate_already_ran() -> None:
    payload = _readiness(promotion_gate_run=True)

    assert payload["goal3c_ready"] is False
    assert "promotion_gate_run_false" in payload["blockers"]


def test_goal3c_readiness_fails_if_raw_thorp_allocator_used() -> None:
    payload = _readiness(raw_THORP_allocator_used=True)

    assert payload["goal3c_ready"] is False
    assert "raw_THORP_allocator_used_false" in payload["blockers"]


def test_goal3c_readiness_fails_if_shipped_tomics_incumbent_changed() -> None:
    payload = _readiness(shipped_TOMICS_incumbent_changed=True)

    assert payload["goal3c_ready"] is False
    assert "shipped_TOMICS_incumbent_changed_false" in payload["blockers"]


def test_goal3c_readiness_fails_if_plotkit_manifest_missing() -> None:
    payload = build_goal3c_readiness_payload(
        metadata=_metadata(),
        stale_audit=_stale_audit(),
        plotkit_specs_exist=True,
        plotkit_rendered_or_manifested=False,
        reproducibility_manifest_exists=True,
        repo_branch="feat/tomics-haf-2025-2c-harvest-family-eval",
    )

    assert payload["goal3c_ready"] is False
    assert "plotkit_rendered_or_manifested" in payload["blockers"]


def test_goal3c_readiness_fails_if_wall_clock_parity_marked_required() -> None:
    payload = _readiness(wall_clock_compute_budget_parity_required_for_goal_3b=True)

    assert payload["goal3c_ready"] is False
    assert "budget_parity_limitations_documented" in payload["blockers"]
