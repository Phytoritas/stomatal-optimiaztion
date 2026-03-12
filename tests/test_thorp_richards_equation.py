from __future__ import annotations

import numpy as np

from stomatal_optimiaztion.domains.thorp.defaults import default_params
from stomatal_optimiaztion.domains.thorp.implements import implemented_equations
from stomatal_optimiaztion.domains.thorp.soil_dynamics import (
    RichardsEquationParams,
    richards_equation,
)
from stomatal_optimiaztion.domains.thorp.soil_initialization import (
    SoilInitializationParams,
    initial_soil_and_roots,
)


def _legacy_default_like_params() -> SoilInitializationParams:
    return default_params().soil_initialization


def _richards_params() -> RichardsEquationParams:
    return default_params().richards


def test_richards_equation_exposes_expected_equation_ids() -> None:
    assert implemented_equations(richards_equation) == (
        "E_S2_1",
        "E_S2_10",
        "E_S2_13",
        "E_S2_14",
        "E_S2_15",
        "E_S2_16",
        "E_S2_17",
        "E_S2_18",
        "E_S2_19",
        "E_S2_20",
        "E_S2_21",
        "E_S2_22",
        "E_S2_23",
        "E_S2_24",
        "E_S2_25",
        "E_S2_26",
    )


def test_richards_equation_matches_legacy_snapshot() -> None:
    init = initial_soil_and_roots(params=_legacy_default_like_params(), c_r_i=1.0, z_i=3.0)
    f = np.linspace(-2.0e-8, 3.0e-8, init.grid.n_soil, dtype=float)

    psi_new, q_bttm = richards_equation(
        params=_richards_params(),
        grid=init.grid,
        q_top=1.5e-7,
        f=f,
        psi_soil_by_layer=init.psi_soil_by_layer,
    )

    np.testing.assert_allclose(
        psi_new,
        np.array(
            [
                -0.743731887744,
                -0.739297104874,
                -0.734044024112,
                -0.728079779475,
                -0.721592460027,
                -0.714721557817,
                -0.707310452885,
                -0.698680930269,
                -0.68766782867,
                -0.672859019015,
                -0.652624919511,
                -0.624845487042,
                -0.586527820747,
                -0.533185016128,
                -0.457109513213,
            ],
            dtype=float,
        ),
        rtol=1e-9,
    )
    assert np.isclose(q_bttm, -1.7961954716762443e-11, rtol=1e-9)


def test_richards_equation_preserves_shape() -> None:
    init = initial_soil_and_roots(params=_legacy_default_like_params(), c_r_i=1.0, z_i=3.0)
    f = np.zeros(init.grid.n_soil, dtype=float)

    psi_new, q_bttm = richards_equation(
        params=_richards_params(),
        grid=init.grid,
        q_top=0.0,
        f=f,
        psi_soil_by_layer=init.psi_soil_by_layer,
    )

    assert psi_new.shape == init.psi_soil_by_layer.shape
    assert np.isfinite(q_bttm)
