from __future__ import annotations

from pathlib import Path

import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.cross_dataset_gate import (
    build_cross_dataset_guardrail_summary,
    cross_dataset_proxy_guardrail,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.datasets.contracts import (
    DatasetBasisContract,
    DatasetCapability,
    DatasetIngestionStatus,
    DatasetMetadataContract,
    DatasetObservationContract,
    DatasetSanitizedFixtureContract,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.datasets.registry import (
    DatasetRegistry,
)


def _runnable_measured_dataset(tmp_path: Path, dataset_id: str, *, dataset_family: str) -> DatasetMetadataContract:
    forcing_path = tmp_path / f"{dataset_id}_forcing.csv"
    harvest_path = tmp_path / f"{dataset_id}_harvest.csv"
    forcing_path.write_text("datetime,T_air_C\n2025-01-01,24\n", encoding="utf-8")
    harvest_path.write_text("date,measured\n2025-01-01,1.0\n", encoding="utf-8")
    return DatasetMetadataContract(
        dataset_id=dataset_id,
        dataset_kind="fixture",
        display_name=dataset_id,
        dataset_family=dataset_family,
        observation_family="yield",
        capability=DatasetCapability.MEASURED_HARVEST,
        ingestion_status=DatasetIngestionStatus.RUNNABLE,
        forcing_path=forcing_path,
        observed_harvest_path=harvest_path,
        validation_start="2025-01-01",
        validation_end="2025-01-31",
        basis=DatasetBasisContract(reporting_basis="floor_area_g_m2", plants_per_m2=1.7),
        observation=DatasetObservationContract(date_column="date", measured_cumulative_column="measured"),
        sanitized_fixture=DatasetSanitizedFixtureContract(
            forcing_fixture_path=forcing_path,
            observed_harvest_fixture_path=harvest_path,
        ),
    )


def test_cross_dataset_proxy_guardrail_blocks_single_dataset_proxy_heavy_winner() -> None:
    candidate = pd.Series(
        {
            "dataset_count": 1,
            "mean_native_family_state_fraction": 0.3,
            "mean_proxy_family_state_fraction": 0.7,
            "mean_shared_tdvs_proxy_fraction": 0.8,
            "cross_dataset_stability_score": 1.0,
        }
    )
    guardrail = cross_dataset_proxy_guardrail(
        candidate,
        native_state_coverage_min=0.5,
        shared_tdvs_proxy_fraction_max=0.5,
        cross_dataset_stability_score_min=0.5,
        min_dataset_count=2,
    )
    assert guardrail["winner_proxy_heavy_flag"] is True
    assert guardrail["winner_not_promotion_grade_due_to_cross_dataset_instability"] is True
    assert guardrail["passes"] is False


def test_cross_dataset_guardrail_summary_blocks_without_registry_evidence() -> None:
    scorecard = pd.DataFrame(
        [
            {
                "fruit_harvest_family": "dekoning_fds",
                "leaf_harvest_family": "vegetative_unit_pruning",
                "fdmc_mode": "dekoning_fds",
                "dataset_count": 3,
                "mean_native_family_state_fraction": 1.0,
                "mean_proxy_family_state_fraction": 0.0,
                "mean_shared_tdvs_proxy_fraction": 0.0,
                "cross_dataset_stability_score": 0.67,
            }
        ]
    )
    summary = build_cross_dataset_guardrail_summary(scorecard)
    assert summary["selected_candidate"]["passes"] is False
    assert summary["selected_candidate"]["missing_dataset_registry_flag"] is True
    assert "dataset registry" in summary["recommendation"]


def test_cross_dataset_guardrail_summary_selects_top_candidate_with_registry_evidence(tmp_path: Path) -> None:
    registry = DatasetRegistry(
        datasets=(
            _runnable_measured_dataset(tmp_path, "measured_a", dataset_family="public_rda"),
            _runnable_measured_dataset(tmp_path, "measured_b", dataset_family="school_trait_bundle"),
        ),
        default_dataset_ids=("measured_a", "measured_b"),
    )
    scorecard = pd.DataFrame(
        [
            {
                "fruit_harvest_family": "dekoning_fds",
                "leaf_harvest_family": "vegetative_unit_pruning",
                "fdmc_mode": "dekoning_fds",
                "dataset_count": 2,
                "mean_native_family_state_fraction": 1.0,
                "mean_proxy_family_state_fraction": 0.0,
                "mean_shared_tdvs_proxy_fraction": 0.0,
                "cross_dataset_stability_score": 1.0,
            }
        ]
    )

    summary = build_cross_dataset_guardrail_summary(scorecard, registry=registry)

    assert summary["selected_candidate"]["passes"] is True
    assert summary["selected_candidate"]["missing_dataset_registry_flag"] is False
    assert "Promotion-grade" in summary["recommendation"]


def test_cross_dataset_guardrail_blocks_when_only_one_measured_dataset_is_runnable(tmp_path: Path) -> None:
    registry = DatasetRegistry(
        datasets=(
            _runnable_measured_dataset(tmp_path, "measured_a", dataset_family="public_rda"),
            DatasetMetadataContract(
                dataset_id="proxy_b",
                dataset_kind="traitenv_candidate",
                display_name="Proxy B",
                dataset_family="public_bigdata_platform",
                observation_family="yield_environment",
                capability=DatasetCapability.HARVEST_PROXY,
                ingestion_status=DatasetIngestionStatus.DRAFT_NEEDS_RAW_FIXTURE,
                blocker_codes=("missing_raw_fixture",),
            ),
        ),
        default_dataset_ids=("measured_a",),
    )
    summary = build_cross_dataset_guardrail_summary(pd.DataFrame(), registry=registry, min_dataset_count=2)
    assert summary["measured_dataset_count"] == 1
    assert summary["selected_candidate"] == {}
    assert "at least two runnable measured-harvest datasets" in summary["recommendation"]


def test_cross_dataset_guardrail_ignores_malformed_runnable_registry_rows(tmp_path: Path) -> None:
    malformed_forcing_path = tmp_path / "measured_b_forcing.csv"
    malformed_harvest_path = tmp_path / "measured_b_harvest.csv"
    malformed_forcing_path.write_text("datetime,T_air_C\n2025-02-01,24\n", encoding="utf-8")
    malformed_harvest_path.write_text("date,measured\n2025-02-01,1.0\n", encoding="utf-8")
    registry = DatasetRegistry(
        datasets=(
            _runnable_measured_dataset(tmp_path, "measured_a", dataset_family="public_rda"),
            DatasetMetadataContract(
                dataset_id="measured_b_malformed",
                dataset_kind="fixture",
                display_name="Measured B malformed",
                dataset_family="school_trait_bundle",
                observation_family="yield",
                capability=DatasetCapability.MEASURED_HARVEST,
                ingestion_status=DatasetIngestionStatus.RUNNABLE,
                forcing_path=malformed_forcing_path,
                observed_harvest_path=malformed_harvest_path,
                validation_start="2025-02-01",
                validation_end="2025-02-28",
                basis=DatasetBasisContract(reporting_basis="floor_area_g_m2", plants_per_m2=2.0),
                observation=DatasetObservationContract(date_column="date", measured_cumulative_column=None),
                sanitized_fixture=DatasetSanitizedFixtureContract(
                    forcing_fixture_path=malformed_forcing_path,
                    observed_harvest_fixture_path=malformed_harvest_path,
                ),
            ),
        ),
        default_dataset_ids=("measured_a",),
    )

    summary = build_cross_dataset_guardrail_summary(pd.DataFrame(), registry=registry, min_dataset_count=2)

    assert summary["measured_dataset_count"] == 1
    assert summary["measured_dataset_ids"] == ["measured_a"]
    assert summary["selected_candidate"] == {}
    assert "at least two runnable measured-harvest datasets" in summary["recommendation"]


def test_cross_dataset_guardrail_blocks_when_zero_measured_datasets_are_runnable() -> None:
    registry = DatasetRegistry(
        datasets=(
            DatasetMetadataContract(
                dataset_id="proxy_b",
                dataset_kind="traitenv_candidate",
                display_name="Proxy B",
                dataset_family="public_bigdata_platform",
                observation_family="yield_environment",
                capability=DatasetCapability.HARVEST_PROXY,
                ingestion_status=DatasetIngestionStatus.DRAFT_NEEDS_RAW_FIXTURE,
                blocker_codes=("missing_raw_fixture",),
            ),
            DatasetMetadataContract(
                dataset_id="context_c",
                dataset_kind="traitenv_candidate",
                display_name="Context C",
                dataset_family="school_greenhouse_environment",
                observation_family="environment",
                capability=DatasetCapability.CONTEXT_ONLY,
                ingestion_status=DatasetIngestionStatus.RUNNABLE,
                basis=DatasetBasisContract(reporting_basis="unknown", plants_per_m2=None),
                observation=DatasetObservationContract(),
            ),
        ),
        default_dataset_ids=(),
    )

    summary = build_cross_dataset_guardrail_summary(pd.DataFrame(), registry=registry, min_dataset_count=2)

    assert summary["measured_dataset_count"] == 0
    assert summary["measured_dataset_ids"] == []
    assert summary["selected_candidate"] == {}
    assert "at least two runnable measured-harvest datasets" in summary["recommendation"]


def test_cross_dataset_guardrail_passes_with_two_runnable_measured_datasets_only(tmp_path: Path) -> None:
    registry = DatasetRegistry(
        datasets=(
            _runnable_measured_dataset(tmp_path, "measured_a", dataset_family="public_rda"),
            _runnable_measured_dataset(tmp_path, "measured_b", dataset_family="school_trait_bundle"),
            DatasetMetadataContract(
                dataset_id="proxy_c",
                dataset_kind="traitenv_candidate",
                display_name="Proxy C",
                dataset_family="public_bigdata_platform",
                observation_family="yield_environment",
                capability=DatasetCapability.HARVEST_PROXY,
                ingestion_status=DatasetIngestionStatus.DRAFT_NEEDS_RAW_FIXTURE,
                blocker_codes=("missing_raw_fixture",),
            ),
            DatasetMetadataContract(
                dataset_id="context_d",
                dataset_kind="traitenv_candidate",
                display_name="Context D",
                dataset_family="school_greenhouse_environment",
                observation_family="environment",
                capability=DatasetCapability.CONTEXT_ONLY,
                ingestion_status=DatasetIngestionStatus.RUNNABLE,
                basis=DatasetBasisContract(reporting_basis="unknown", plants_per_m2=None),
                observation=DatasetObservationContract(),
            ),
        ),
        default_dataset_ids=("measured_a", "measured_b"),
    )
    scorecard = pd.DataFrame(
        [
            {
                "fruit_harvest_family": "dekoning_fds",
                "leaf_harvest_family": "vegetative_unit_pruning",
                "fdmc_mode": "dekoning_fds",
                "dataset_count": 2,
                "mean_native_family_state_fraction": 0.9,
                "mean_proxy_family_state_fraction": 0.1,
                "mean_shared_tdvs_proxy_fraction": 0.0,
                "cross_dataset_stability_score": 1.0,
            }
        ]
    )

    summary = build_cross_dataset_guardrail_summary(scorecard, registry=registry, min_dataset_count=2)

    assert summary["measured_dataset_count"] == 2
    assert summary["measured_dataset_ids"] == ["measured_a", "measured_b"]
    assert summary["selected_candidate"]["selected_candidate_dataset_count"] == 2
    assert summary["selected_candidate"]["passes"] is True
    assert summary["selected_candidate"]["single_dataset_only_flag"] is False


def test_cross_dataset_guardrail_ignores_registry_rows_marked_runnable_without_real_evidence() -> None:
    registry_df = pd.DataFrame(
        [
            {
                "dataset_id": "paper_only",
                "capability": "measured_harvest",
                "ingestion_status": "runnable",
                "is_runnable_measured_harvest": True,
                "basis_normalization_resolved": True,
                "validation_start": "2025-01-01",
                "validation_end": "2025-01-31",
                "date_column": "date",
                "measured_cumulative_column": "measured",
                "forcing_path": "missing_forcing.csv",
                "observed_harvest_path": "missing_harvest.csv",
                "sanitized_fixture_path": "missing_fixture_dir",
            }
        ]
    )
    summary = build_cross_dataset_guardrail_summary(pd.DataFrame(), registry_df=registry_df, min_dataset_count=2)
    assert summary["measured_dataset_count"] == 0
    assert summary["measured_dataset_ids"] == []
