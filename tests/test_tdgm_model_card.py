from __future__ import annotations

import pytest

from stomatal_optimiaztion.domains.tdgm.model_card import (
    equation_id_set,
    load_model_card,
    model_card_document_names,
    require_equation_ids,
)


def test_model_card_snapshot_contains_expected_documents() -> None:
    assert model_card_document_names() == tuple(f"C{index:03d}.json" for index in range(1, 7))


def test_model_card_has_core_equations() -> None:
    require_equation_ids(
        [
            "Eq_S1.26",
            "Eq_S1.38",
            "Eq_S2.12",
            "Eq.S.3.1",
            "Eq.S.3.8",
        ]
    )


def test_equation_id_set_is_nonempty() -> None:
    assert len(equation_id_set()) > 10


def test_can_load_packaged_model_card_document() -> None:
    assert (
        load_model_card("C005.json")["model_card"]["name"]
        == "THORP-G dynamic simulation coupling (TDGM + THORP)"
    )


def test_require_equation_ids_reports_missing_ids() -> None:
    with pytest.raises(KeyError) as exc_info:
        require_equation_ids(["Eq.S.999"])

    assert "Eq.S.999" in str(exc_info.value)
