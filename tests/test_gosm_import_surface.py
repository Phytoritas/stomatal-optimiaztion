from __future__ import annotations

from importlib import import_module

import stomatal_optimiaztion.domains.gosm as gosm


def test_gosm_package_import_surface_exposes_foundation_helpers() -> None:
    utils_pkg = import_module("stomatal_optimiaztion.domains.gosm.utils")

    assert gosm.__version__ == "0.1.0"
    assert gosm.BaselineInputs.matlab_default().c_nsc == 175.0
    assert gosm.implements is utils_pkg.implements
    assert gosm.model_card_document_names() == tuple(f"C{index:03d}.json" for index in range(1, 11))

