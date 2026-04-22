from __future__ import annotations

import json
from pathlib import Path

import pytest

from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.datasets.contracts import (
    DatasetBasisContract,
    DatasetManagementMetadata,
    DatasetMetadataContract,
    DatasetObservationContract,
    DatasetSanitizedFixtureContract,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.datasets.registry import (
    DatasetRegistry,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.lane_matrix import (
    measured_harvest_contract_satisfied,
    resolve_allocation_lanes,
    resolve_dataset_roles,
    resolve_harvest_profiles,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.parameter_budget import (
    CalibrationCandidate,
)


def _calibration_candidates() -> list[CalibrationCandidate]:
    return [
        CalibrationCandidate(
            candidate_label="shipped_tomics",
            architecture_id="shipped_tomics_control",
            candidate_role="incumbent",
            calibratable=True,
            row={
                "architecture_id": "shipped_tomics_control",
                "partition_policy": "tomics",
                "policy_family": "incumbent",
                "allocation_scheme": "4pool",
            },
        ),
        CalibrationCandidate(
            candidate_label="current_selected",
            architecture_id="kuijpers_hybrid_candidate",
            candidate_role="research_current",
            calibratable=True,
            row={
                "architecture_id": "kuijpers_hybrid_candidate",
                "partition_policy": "tomics_alloc_research",
                "policy_family": "current_selected",
                "allocation_scheme": "4pool",
            },
        ),
        CalibrationCandidate(
            candidate_label="promoted_selected",
            architecture_id="constrained_full_plus_feedback__buffer_capacity_g_m2_12p0",
            candidate_role="research_promoted",
            calibratable=True,
            row={
                "architecture_id": "constrained_full_plus_feedback__buffer_capacity_g_m2_12p0",
                "partition_policy": "tomics_promoted_research",
                "policy_family": "promoted_selected",
                "allocation_scheme": "4pool",
            },
        ),
    ]


def _dataset(
    *,
    dataset_id: str,
    dataset_kind: str,
    notes: dict[str, object] | None = None,
) -> DatasetMetadataContract:
    fixture_root = Path("tests") / "fixtures" / "knu_sanitized"
    return DatasetMetadataContract(
        dataset_id=dataset_id,
        dataset_kind=dataset_kind,
        display_name=dataset_id,
        forcing_path=Path("forcing.csv"),
        observed_harvest_path=Path("observed.csv"),
        validation_start="2025-10-20",
        validation_end="2025-12-31",
        cultivar="test",
        greenhouse="testhouse",
        season="test-season",
        basis=DatasetBasisContract(reporting_basis="floor_area_g_m2", plants_per_m2=2.0),
        observation=DatasetObservationContract(
            date_column="Date",
            measured_cumulative_column="Measured",
            estimated_cumulative_column="Estimated",
            measured_semantics="cumulative_harvested_fruit_dry_weight_floor_area",
        ),
        management=DatasetManagementMetadata(),
        sanitized_fixture=DatasetSanitizedFixtureContract(
            forcing_fixture_path=fixture_root / "KNU_Tomato_Env_fixture.csv",
            observed_harvest_fixture_path=fixture_root / "tomato_validation_data_yield_fixture.csv",
        ),
        notes=notes or {},
    )


def test_allocation_lane_registry_resolves_required_policies() -> None:
    lane_map = {lane.lane_id: lane for lane in resolve_allocation_lanes(_calibration_candidates())}
    assert lane_map["legacy_sink_baseline"].partition_policy == "legacy"
    assert lane_map["incumbent_current"].partition_policy == "tomics"
    assert lane_map["research_current"].partition_policy == "tomics_alloc_research"
    assert lane_map["research_promoted"].partition_policy == "tomics_promoted_research"
    assert lane_map["raw_reference_thorp"].partition_policy == "thorp_fruit_veg"
    assert lane_map["legacy_sink_baseline"].architecture_id != lane_map["incumbent_current"].architecture_id
    assert lane_map["raw_reference_thorp"].reference_only is True
    assert lane_map["raw_reference_thorp"].promotion_eligible is False


def test_allocation_lane_registry_rejects_unknown_requested_lane() -> None:
    with pytest.raises(ValueError, match="Unknown allocation lane ids requested: missing_lane"):
        resolve_allocation_lanes(_calibration_candidates(), lane_ids=["incumbent_current", "missing_lane"])


def test_dataset_roles_do_not_auto_promote_yield_environment() -> None:
    registry = DatasetRegistry(
        datasets=(
            _dataset(dataset_id="knu_actual", dataset_kind="knu_measured_harvest"),
            _dataset(
                dataset_id="traitenv_context",
                dataset_kind="traitenv_bundle",
                notes={"dataset_role_hint": "trait_plus_env_no_harvest"},
            ),
            _dataset(
                dataset_id="yield_env_only",
                dataset_kind="public_ai_yield_environment",
                notes={"source_family": "public_ai_competition"},
            ),
        ),
        default_dataset_ids=("knu_actual",),
    )
    role_map = {row.dataset_id: row for row in resolve_dataset_roles(registry)}
    assert role_map["knu_actual"].dataset_role == "measured_harvest"
    assert role_map["traitenv_context"].dataset_role == "trait_plus_env_no_harvest"
    assert role_map["yield_env_only"].dataset_role == "yield_environment_only"
    assert role_map["yield_env_only"].promotion_denominator_eligible is False


def test_dataset_role_registry_rejects_unknown_requested_dataset() -> None:
    registry = DatasetRegistry(
        datasets=(
            _dataset(dataset_id="knu_actual", dataset_kind="knu_measured_harvest"),
        ),
        default_dataset_ids=("knu_actual",),
    )
    with pytest.raises(ValueError, match="Unknown dataset ids requested: missing_dataset"):
        resolve_dataset_roles(registry, dataset_ids=["knu_actual", "missing_dataset"])


def test_measured_harvest_contract_requires_sanitized_fixture_metadata() -> None:
    dataset = DatasetMetadataContract(
        dataset_id="demo",
        dataset_kind="knu_measured_harvest",
        display_name="Demo",
        forcing_path=Path("forcing.csv"),
        observed_harvest_path=Path("observed.csv"),
        validation_start="2025-01-01",
        validation_end="2025-01-31",
        cultivar="cv",
        greenhouse="gh",
        season="winter",
        basis=DatasetBasisContract(reporting_basis="floor_area_g_m2", plants_per_m2=1.8),
        observation=DatasetObservationContract(
            date_column="Date",
            measured_cumulative_column="Measured",
            estimated_cumulative_column="Estimated",
            measured_semantics="cumulative_harvested_fruit_dry_weight_floor_area",
        ),
        management=DatasetManagementMetadata(),
        sanitized_fixture=DatasetSanitizedFixtureContract(),
        notes={"dataset_role_hint": "measured_harvest"},
    )
    assert measured_harvest_contract_satisfied(dataset) is False


def test_harvest_profile_registry_reads_locked_selected_family(tmp_path: Path) -> None:
    selected_path = tmp_path / "out" / "tomics_knu_harvest_family_factorial" / "selected_harvest_family.json"
    selected_path.parent.mkdir(parents=True, exist_ok=True)
    selected_path.write_text(
        json.dumps(
            {
                "selected_harvest_family_id": "dekoning_fds|vegetative_unit_pruning|dekoning_fds",
                "selected_fruit_harvest_family": "dekoning_fds",
                "selected_leaf_harvest_family": "vegetative_unit_pruning",
                "selected_fdmc_mode": "dekoning_fds",
                "harvest_delay_days": 0.0,
                "harvest_readiness_threshold": 1.0,
                "fruit_params": {"fds_harvest_threshold": 1.0, "fdmc_mode": "dekoning_fds"},
                "leaf_params": {"colour_threshold": 0.9},
                "winner_native_state_fraction": 0.8,
                "winner_proxy_state_fraction": 0.2,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    profile_map = {
        profile.harvest_profile_id: profile
        for profile in resolve_harvest_profiles(
            repo_root=tmp_path,
            requested_ids=[
                "incumbent_harvest_profile",
                "locked_research_selected_harvest_profile",
            ],
        )
    }
    assert profile_map["incumbent_harvest_profile"].fruit_harvest_family == "tomsim_truss"
    assert profile_map["locked_research_selected_harvest_profile"].fruit_harvest_family == "dekoning_fds"
    assert profile_map["locked_research_selected_harvest_profile"].selected_family_is_native is True
    assert profile_map["locked_research_selected_harvest_profile"].selected_family_is_proxy is True


def test_harvest_profile_registry_rejects_unknown_requested_profile(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Unknown harvest profile ids requested: missing_profile"):
        resolve_harvest_profiles(repo_root=tmp_path, requested_ids=["incumbent_harvest_profile", "missing_profile"])
