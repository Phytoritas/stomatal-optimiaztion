from __future__ import annotations

from stomatal_optimiaztion.domains.tdgm import implemented_equations, implements
from stomatal_optimiaztion.domains.tdgm.traceability import build_mapping, iter_annotated_callables


@implements("Eq.S.3.1", "Eq.S.3.1", "Eq.S.3.2")
def _root_annotated() -> None:
    return None


class _ExampleNamespace:
    @implements("Eq.S.2.12")
    def method(self) -> None:
        return None


def test_implements_deduplicates_equation_ids() -> None:
    assert implemented_equations(_root_annotated) == ("Eq.S.3.1", "Eq.S.3.2")


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

    assert "Eq.S.3.1" in mapping.equation_to_callables
    assert any(name.endswith("._root_annotated") for name in mapping.equation_to_callables["Eq.S.3.1"])
    assert "Eq.S.2.12" in mapping.equation_to_callables
    assert any(
        name.endswith("._ExampleNamespace.method")
        for name in mapping.equation_to_callables["Eq.S.2.12"]
    )

