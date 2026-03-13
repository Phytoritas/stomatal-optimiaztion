from __future__ import annotations

import pytest

from stomatal_optimiaztion.domains.gosm.model_card import (
    equation_id_set,
    load_model_card,
    model_card_document_names,
    require_equation_ids,
)


def test_model_card_snapshot_contains_expected_documents() -> None:
    assert model_card_document_names() == tuple(f"C{index:03d}.json" for index in range(1, 11))


def test_model_card_has_core_equations() -> None:
    require_equation_ids(
        [
            "Eq.S1.1",
            "Eq.S2.4b",
            "Eq.S3.2",
            "Eq.S5.10",
            "Eq.S7.18",
            "Eq.S8.2",
            "Eq.S10.1",
        ]
    )


def test_equation_id_set_is_nonempty() -> None:
    assert len(equation_id_set()) > 30


def test_can_load_packaged_model_card_document() -> None:
    assert load_model_card("C001.json")["model_card"]["name"] == "S1 Whole-tree carbon dynamics"


def test_require_equation_ids_reports_missing_ids() -> None:
    with pytest.raises(KeyError) as exc_info:
        require_equation_ids(["Eq.S999.1"])

    assert "Eq.S999.1" in str(exc_info.value)

