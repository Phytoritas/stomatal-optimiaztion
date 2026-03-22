from __future__ import annotations

import pytest

from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.datasets.contracts import (
    DatasetBasisContract,
    DatasetMetadataContract,
    DatasetObservationContract,
)


def test_dataset_basis_contract_normalizes_floor_area_basis() -> None:
    contract = DatasetBasisContract(reporting_basis="g/m^2", plants_per_m2=1.8)
    assert contract.reporting_basis == "floor_area_g_m2"
    assert contract.basis_unit_label == "g/m^2"


def test_dataset_metadata_contract_requires_positive_plants_per_m2() -> None:
    with pytest.raises(ValueError):
        DatasetBasisContract(reporting_basis="floor_area_g_m2", plants_per_m2=0.0)


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
