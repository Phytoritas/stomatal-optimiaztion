from __future__ import annotations

from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.datasets.contracts import (
    DatasetBasisContract,
)


def test_dataset_basis_contract_normalizes_per_plant_basis() -> None:
    contract = DatasetBasisContract(reporting_basis="g/plant", plants_per_m2=2.0)
    assert contract.reporting_basis == "g_per_plant"
    assert contract.basis_unit_label == "g/plant"
