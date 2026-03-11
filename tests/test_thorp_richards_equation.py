from __future__ import annotations

import numpy as np

from stomatal_optimiaztion.domains.thorp.implements import implemented_equations
from stomatal_optimiaztion.domains.thorp.soil_dynamics import (
    RichardsEquationParams,
    richards_equation,
)
from stomatal_optimiaztion.domains.thorp.soil_hydraulics import SoilHydraulics
from stomatal_optimiaztion.domains.thorp.soil_initialization import (
    SoilInitializationParams,
    initial_soil_and_roots,
)
from stomatal_optimiaztion.domains.thorp.vulnerability import WeibullVC


def _legacy_default_like_params() -> SoilInitializationParams:
    return SoilInitializationParams(
        rho=998.0,
        g=9.81,
        z_wt=74.0,
        z_soil=30.0,
        n_soil=15,
        bc_bttm="FreeDrainage",
        soil=SoilHydraulics(n_vg=2.70, alpha_vg=1.4642, l_vg=0.5, e_z_n=13.6, e_z_k_s_sat=3.2),
        vc_r=WeibullVC(b=1.2949, c=2.6471),
        beta_r_h=3388.15038831676,
        beta_r_v=941.1528856435444,
    )


def _richards_params() -> RichardsEquationParams:
    return RichardsEquationParams(
        dt=6 * 3600.0,
        rho=998.0,
        g=9.81,
        bc_bttm="FreeDrainage",
        z_wt=74.0,
        p_bttm=998.0 * 9.81 * (30.0 - 74.0) / 1e6,
        soil=SoilHydraulics(n_vg=2.70, alpha_vg=1.4642, l_vg=0.5, e_z_n=13.6, e_z_k_s_sat=3.2),
    )


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
