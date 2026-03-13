from __future__ import annotations

import json
from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass
from importlib.resources import files
from importlib.resources.abc import Traversable
from typing import Any

_GOSM_PACKAGE = "stomatal_optimiaztion.domains.gosm"


@dataclass(frozen=True, slots=True)
class EquationRef:
    eq_id: str
    source_name: str


def model_card_dir() -> Traversable:
    return files(_GOSM_PACKAGE).joinpath("model_card")


def model_card_document_names() -> tuple[str, ...]:
    return tuple(
        sorted(
            resource.name
            for resource in model_card_dir().iterdir()
            if resource.is_file() and resource.name.endswith(".json")
        )
    )


def load_model_card(name: str) -> dict[str, Any]:
    resource = model_card_dir().joinpath(name)
    if not resource.is_file():
        raise FileNotFoundError(name)
    return json.loads(resource.read_text(encoding="utf-8"))


def iter_equation_refs() -> Iterator[EquationRef]:
    for document_name in model_card_document_names():
        document = load_model_card(document_name)
        yield from _iter_equation_refs_from_document(document_name, document)


def equation_id_set() -> set[str]:
    return {equation_ref.eq_id for equation_ref in iter_equation_refs()}


def require_equation_ids(eq_ids: Iterable[str]) -> None:
    available = equation_id_set()
    missing = sorted({equation_id for equation_id in eq_ids if equation_id not in available})
    if missing:
        raise KeyError(f"Missing equation ids in GOSM model_card: {missing}")


def _iter_equation_refs_from_document(
    document_name: str, document: Mapping[str, Any]
) -> Iterator[EquationRef]:
    model_card = document.get("model_card")
    if not isinstance(model_card, Mapping):
        return

    equations = model_card.get("equations")
    if not isinstance(equations, list):
        return

    for equation in equations:
        if not isinstance(equation, Mapping):
            continue

        equation_id = equation.get("id")
        if isinstance(equation_id, str) and equation_id:
            yield EquationRef(eq_id=equation_id, source_name=document_name)

