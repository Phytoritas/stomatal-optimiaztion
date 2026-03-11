from __future__ import annotations

from stomatal_optimiaztion.domains.thorp.implements import implements, implemented_equations
from stomatal_optimiaztion.domains.thorp.traceability import build_mapping, iter_annotated_callables


@implements("E_S5_1", "E_S5_1", "E_S5_2")
def radiation_stub() -> None:
    return None


class SoilHydraulicsStub:
    @implements("E_S2_4")
    def k_soil(self) -> None:
        return None


def test_implements_deduplicates_equation_ids() -> None:
    assert implemented_equations(radiation_stub) == ("E_S5_1", "E_S5_2")


def test_iter_annotated_callables_finds_functions_and_methods() -> None:
    namespace = {
        "radiation_stub": radiation_stub,
        "SoilHydraulicsStub": SoilHydraulicsStub,
    }

    discovered = {callable_obj.__qualname__ for callable_obj in iter_annotated_callables(namespace)}
    assert discovered == {"radiation_stub", "SoilHydraulicsStub.k_soil"}


def test_build_mapping_groups_equations_by_callable() -> None:
    mapping = build_mapping([radiation_stub, SoilHydraulicsStub.k_soil])

    assert set(mapping.equation_to_callables) == {"E_S5_1", "E_S5_2", "E_S2_4"}
    assert any(name.endswith("radiation_stub") for name in mapping.equation_to_callables["E_S5_1"])
    assert any(name.endswith("SoilHydraulicsStub.k_soil") for name in mapping.equation_to_callables["E_S2_4"])
