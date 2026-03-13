from importlib import import_module

import stomatal_optimiaztion.domains.gosm as gosm
import stomatal_optimiaztion.domains.tdgm as tdgm
import stomatal_optimiaztion.domains.thorp as thorp

io_pkg = import_module("stomatal_optimiaztion.domains.thorp.io")
model_pkg = import_module("stomatal_optimiaztion.domains.thorp.model")
params_module = import_module("stomatal_optimiaztion.domains.thorp.params")
utils_pkg = import_module("stomatal_optimiaztion.domains.thorp.utils")


def test_smoke() -> None:
    assert len(thorp.model_card_document_names()) == 11
    assert len(gosm.model_card_document_names()) == 10
    assert len(tdgm.model_card_document_names()) == 6


def test_thorp_package_import_surface_smoke() -> None:
    assert thorp.Forcing is io_pkg.Forcing
    assert thorp.load_mat is io_pkg.load_mat
    assert thorp.radiation is model_pkg.radiation
    assert thorp.require_equation_ids is utils_pkg.require_equation_ids
    assert params_module.default_params().run_name == "0.6RH"
