from __future__ import annotations

import stomatal_optimiaztion.domains.tdgm as tdgm


def test_tdgm_package_import_surface_exposes_foundation_helpers() -> None:
    assert tdgm.model_card_document_names() == tuple(f"C{index:03d}.json" for index in range(1, 7))
    assert tdgm.implements.__name__ == "implements"

