from __future__ import annotations

from stomatal_optimiaztion.domains.gosm import implemented_equations, implements
from stomatal_optimiaztion.domains.gosm.traceability import build_mapping, iter_annotated_callables
from stomatal_optimiaztion.domains.gosm.utils.traceability import (
    implements as utils_implements,
)


@implements("Eq.S1.1", "Eq.S1.1", "Eq.S1.2")
def _root_annotated() -> None:
    return None


class _ExampleNamespace:
    @utils_implements("Eq.S2.4b")
    def method(self) -> None:
        return None


def test_implements_deduplicates_equation_ids() -> None:
    assert implemented_equations(_root_annotated) == ("Eq.S1.1", "Eq.S1.2")


def test_iter_annotated_callables_discovers_functions_and_methods() -> None:
    namespace = {
        "root": _root_annotated,
        "example": _ExampleNamespace,
    }

    discovered = {callable_obj.__qualname__ for callable_obj in iter_annotated_callables(namespace)}

    assert "_root_annotated" in discovered
    assert any(name.endswith("_ExampleNamespace.method") for name in discovered)


def test_build_mapping_groups_equations_by_qualname() -> None:
    namespace = {
        "root": _root_annotated,
        "example": _ExampleNamespace,
    }

    mapping = build_mapping(iter_annotated_callables(namespace))

    assert "Eq.S1.1" in mapping.equation_to_callables
    assert any(name.endswith("._root_annotated") for name in mapping.equation_to_callables["Eq.S1.1"])
    assert "Eq.S2.4b" in mapping.equation_to_callables
    assert any(
        name.endswith("._ExampleNamespace.method")
        for name in mapping.equation_to_callables["Eq.S2.4b"]
    )

