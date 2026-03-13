from __future__ import annotations

from stomatal_optimiaztion.domains.thorp.equation_registry import (
    build_mapping,
    iter_annotated_callables,
)


def test_iter_annotated_callables_discovers_migrated_thorp_runtime_functions() -> None:
    discovered = {callable_obj.__qualname__ for callable_obj in iter_annotated_callables()}

    assert any(name.endswith("radiation") for name in discovered)
    assert any(name.endswith("stomata") for name in discovered)
    assert any(name.endswith("SoilHydraulics.k_s") for name in discovered)


def test_build_mapping_groups_equations_for_migrated_thorp_modules() -> None:
    mapping = build_mapping()

    assert "E_S5_1" in mapping.equation_to_callables
    assert any(
        name.endswith("radiation") for name in mapping.equation_to_callables["E_S5_1"]
    )
    assert "E_S2_4" in mapping.equation_to_callables
    assert any(
        name.endswith("SoilHydraulics.k_s")
        for name in mapping.equation_to_callables["E_S2_4"]
    )
