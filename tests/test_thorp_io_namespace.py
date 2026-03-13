from __future__ import annotations

import stomatal_optimiaztion.domains.thorp.forcing as forcing_module
import stomatal_optimiaztion.domains.thorp.io as io_pkg
import stomatal_optimiaztion.domains.thorp.matlab_io as matlab_io_module


def test_io_package_reexports_grouped_helpers() -> None:
    assert io_pkg.Forcing is forcing_module.Forcing
    assert io_pkg.load_forcing is forcing_module.load_forcing
    assert io_pkg.load_mat is matlab_io_module.load_mat
    assert io_pkg.save_mat is matlab_io_module.save_mat
