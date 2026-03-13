from __future__ import annotations

from stomatal_optimiaztion.domains.tdgm.equation_registry import (
    build_mapping,
    iter_annotated_callables,
)


def test_iter_annotated_callables_discovers_migrated_tdgm_runtime_functions() -> None:
    discovered = {callable_obj.__qualname__ for callable_obj in iter_annotated_callables()}

    assert any(name.endswith("phloem_transport_concentration") for name in discovered)
    assert any(name.endswith("turgor_driven_growth_rate") for name in discovered)
    assert any(name.endswith("tree_volume_from_carbon_pools") for name in discovered)


def test_build_mapping_groups_equations_for_migrated_tdgm_modules() -> None:
    mapping = build_mapping()

    assert "Eq_S1.26" in mapping.equation_to_callables
    assert any(
        name.endswith("phloem_transport_concentration")
        for name in mapping.equation_to_callables["Eq_S1.26"]
    )

    assert "Eq_S2.12" in mapping.equation_to_callables
    assert any(
        name.endswith("turgor_driven_growth_rate")
        for name in mapping.equation_to_callables["Eq_S2.12"]
    )

    assert "Eq.S.3.3" in mapping.equation_to_callables
    assert any(
        name.endswith("tree_volume_from_carbon_pools")
        for name in mapping.equation_to_callables["Eq.S.3.3"]
    )
