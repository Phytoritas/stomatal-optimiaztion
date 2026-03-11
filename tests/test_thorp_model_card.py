from __future__ import annotations

import pytest

from stomatal_optimiaztion.domains.thorp.model_card import (
    equation_id_set,
    model_card_document_names,
    require_equation_ids,
)


def test_model_card_snapshot_contains_expected_documents() -> None:
    assert model_card_document_names() == tuple(f"C{index:03d}.json" for index in range(1, 12))


def test_model_card_has_core_equations() -> None:
    require_equation_ids(
        [
            "E_S2_1",
            "E_S2_11",
            "E_S3_25",
            "E_S4_7",
            "E_S5_1",
            "E_S6_4",
            "E_S7_4",
            "E_S8_5",
            "E_S9_1",
        ]
    )


def test_equation_id_set_is_nonempty() -> None:
    assert len(equation_id_set()) > 50


def test_require_equation_ids_reports_missing_ids() -> None:
    with pytest.raises(KeyError) as exc_info:
        require_equation_ids(["E_S999_1"])

    assert "E_S999_1" in str(exc_info.value)
