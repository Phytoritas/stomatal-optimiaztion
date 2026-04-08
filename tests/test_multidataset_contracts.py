from __future__ import annotations

import pytest

from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.datasets.contracts import (
    DatasetBasisContract,
    DatasetCapability,
    DatasetIngestionStatus,
    DatasetMetadataContract,
    DatasetObservationContract,
    DatasetSanitizedFixtureContract,
    classify_blockers,
    derive_ingestion_status,
    is_measured_harvest_runnable,
)


def test_dataset_basis_contract_normalizes_floor_area_basis() -> None:
    contract = DatasetBasisContract(reporting_basis="g/m^2", plants_per_m2=1.8)
    assert contract.reporting_basis == "floor_area_g_m2"
    assert contract.basis_unit_label == "g/m^2"


def test_dataset_metadata_contract_requires_positive_plants_per_m2() -> None:
    with pytest.raises(ValueError):
        DatasetBasisContract(reporting_basis="floor_area_g_m2", plants_per_m2=0.0)


def test_dataset_basis_contract_requires_plants_per_m2_for_per_plant() -> None:
    with pytest.raises(ValueError):
        DatasetBasisContract(reporting_basis="g/plant", plants_per_m2=None)


def test_dataset_metadata_contract_serializes_required_fields() -> None:
    dataset = DatasetMetadataContract(
        dataset_id="demo",
        dataset_kind="measured_harvest",
        display_name="Demo dataset",
        forcing_path="forcing.csv",
        observed_harvest_path="harvest.csv",
        validation_start="2025-01-01",
        validation_end="2025-01-31",
        cultivar="cv",
        greenhouse="gh",
        season="winter",
        basis=DatasetBasisContract(reporting_basis="floor_area_g_m2", plants_per_m2=1.5),
        observation=DatasetObservationContract(
            date_column="date",
            measured_cumulative_column="measured",
        ),
        priority_tags=("long_harvest_wave",),
    )
    payload = dataset.to_payload()
    assert payload["basis"]["reporting_basis"] == "floor_area_g_m2"
    assert payload["observation"]["measured_cumulative_column"] == "measured"
    assert payload["priority_tags"] == ["long_harvest_wave"]


def test_measured_harvest_contract_reports_missing_basis_and_mapping_blockers() -> None:
    dataset = DatasetMetadataContract(
        dataset_id="draft_candidate",
        dataset_kind="traitenv_candidate",
        display_name="Draft candidate",
        capability=DatasetCapability.MEASURED_HARVEST,
        ingestion_status=DatasetIngestionStatus.DRAFT_NEEDS_RAW_FIXTURE,
        forcing_path=None,
        observed_harvest_path=None,
        basis=DatasetBasisContract(reporting_basis="unknown", plants_per_m2=None),
        observation=DatasetObservationContract(),
    )
    blocker_codes = set(classify_blockers(dataset))
    assert "missing_reporting_basis" in blocker_codes
    assert "missing_date_column" in blocker_codes
    assert "missing_measured_cumulative_column" in blocker_codes
    assert "missing_sanitized_fixture" in blocker_codes
    assert is_measured_harvest_runnable(dataset) is False


def test_context_only_dataset_never_counts_as_runnable_measured_harvest() -> None:
    dataset = DatasetMetadataContract(
        dataset_id="context_env",
        dataset_kind="environment_bundle",
        display_name="Context env",
        capability=DatasetCapability.CONTEXT_ONLY,
        ingestion_status=DatasetIngestionStatus.RUNNABLE,
        forcing_path="forcing.csv",
        basis=DatasetBasisContract(reporting_basis="unknown", plants_per_m2=None),
        observation=DatasetObservationContract(),
    )
    assert is_measured_harvest_runnable(dataset) is False


@pytest.mark.parametrize(
    ("blocker_codes", "expected_status"),
    [
        (["missing_raw_fixture", "missing_reporting_basis"], DatasetIngestionStatus.DRAFT_NEEDS_RAW_FIXTURE),
        (["missing_reporting_basis"], DatasetIngestionStatus.DRAFT_NEEDS_BASIS_METADATA),
        (["missing_measured_cumulative_column"], DatasetIngestionStatus.DRAFT_NEEDS_HARVEST_MAPPING),
        (["custom_blocker"], DatasetIngestionStatus.DRAFT_BLOCKED),
        ([], DatasetIngestionStatus.RUNNABLE),
    ],
)
def test_derive_ingestion_status_prioritizes_blocker_classes(
    blocker_codes: list[str],
    expected_status: DatasetIngestionStatus,
) -> None:
    assert derive_ingestion_status(DatasetCapability.MEASURED_HARVEST, blocker_codes) is expected_status


def test_dataset_metadata_contract_normalizes_capability_and_status_strings() -> None:
    dataset = DatasetMetadataContract(
        dataset_id="proxy_candidate",
        dataset_kind="traitenv_candidate",
        display_name="Proxy candidate",
        capability="harvest_proxy",
        ingestion_status="draft_needs_raw_fixture",
        basis=DatasetBasisContract(reporting_basis="unknown", plants_per_m2=None),
        observation=DatasetObservationContract(),
    )

    assert dataset.capability is DatasetCapability.HARVEST_PROXY
    assert dataset.ingestion_status is DatasetIngestionStatus.DRAFT_NEEDS_RAW_FIXTURE


def test_measured_harvest_contract_flags_ambiguous_harvest_semantics() -> None:
    dataset = DatasetMetadataContract(
        dataset_id="ambiguous_semantics",
        dataset_kind="fixture",
        display_name="Ambiguous semantics",
        capability=DatasetCapability.MEASURED_HARVEST,
        ingestion_status=DatasetIngestionStatus.RUNNABLE,
        forcing_path="forcing.csv",
        observed_harvest_path="harvest.csv",
        validation_start="2025-01-01",
        validation_end="2025-01-31",
        basis=DatasetBasisContract(reporting_basis="floor_area_g_m2", plants_per_m2=1.8),
        observation=DatasetObservationContract(
            date_column="date",
            measured_cumulative_column="measured",
            measured_semantics="fruit_buffer_proxy",
        ),
        sanitized_fixture=DatasetSanitizedFixtureContract(
            forcing_fixture_path="forcing.csv",
            observed_harvest_fixture_path="harvest.csv",
        ),
    )

    blocker_codes = set(classify_blockers(dataset))

    assert "ambiguous_harvest_semantics" in blocker_codes
    assert is_measured_harvest_runnable(dataset) is False
