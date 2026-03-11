from __future__ import annotations

import numpy as np

from stomatal_optimiaztion.domains.thorp.implements import implemented_equations
from stomatal_optimiaztion.domains.thorp.soil_dynamics import (
    RichardsEquationParams,
    SoilMoistureParams,
    soil_moisture,
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
        soil=SoilHydraulics(
            n_vg=2.70,
            alpha_vg=1.4642,
            l_vg=0.5,
            e_z_n=13.6,
            e_z_k_s_sat=3.2,
        ),
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
        soil=SoilHydraulics(
            n_vg=2.70,
            alpha_vg=1.4642,
            l_vg=0.5,
            e_z_n=13.6,
            e_z_k_s_sat=3.2,
        ),
    )


def _soil_moisture_params() -> SoilMoistureParams:
    return SoilMoistureParams(
        richards=_richards_params(),
        m_h2o=18.01528e-3,
        r_gas=8.314,
    )


def test_soil_moisture_exposes_expected_equation_ids() -> None:
    assert implemented_equations(soil_moisture) == (
        "E_S2_3",
        "E_S2_9",
        "E_S2_11",
        "E_S2_12",
    )


def test_soil_moisture_matches_legacy_snapshot() -> None:
    init = initial_soil_and_roots(params=_legacy_default_like_params(), c_r_i=1.0, z_i=3.0)
    e_soil = np.linspace(2.0e-8, 9.0e-8, init.grid.n_soil, dtype=float)

    psi_new, evap = soil_moisture(
        params=_soil_moisture_params(),
        grid=init.grid,
        psi_soil_by_layer=init.psi_soil_by_layer,
        t_a=23.5,
        t_soil=19.0,
        rh=0.58,
        u10=2.4,
        precip=0.0,
        e_soil=e_soil,
        la=2.8,
        w=0.35,
    )

    np.testing.assert_allclose(
        psi_new,
        np.array(
            [
                -0.724746382349,
                -0.723464513999,
                -0.721741394133,
                -0.719429772846,
                -0.716329150385,
                -0.712159589631,
                -0.706523289824,
                -0.698856884808,
                -0.688380017144,
                -0.674032325222,
                -0.654375120965,
                -0.627444896569,
                -0.59055385189,
                -0.540019340893,
                -0.470796140108,
            ],
            dtype=float,
        ),
        rtol=1e-9,
    )
    assert np.isclose(evap, 6.478907185751277e-09, rtol=1e-9)


def test_soil_moisture_precipitation_branch_matches_legacy_behavior() -> None:
    init = initial_soil_and_roots(params=_legacy_default_like_params(), c_r_i=1.0, z_i=3.0)
    e_soil = np.full(init.grid.n_soil, 4.0e-8, dtype=float)

    psi_new, evap = soil_moisture(
        params=_soil_moisture_params(),
        grid=init.grid,
        psi_soil_by_layer=init.psi_soil_by_layer,
        t_a=18.0,
        t_soil=18.0,
        rh=0.92,
        u10=1.5,
        precip=1.2e-7,
        e_soil=e_soil,
        la=2.4,
        w=0.4,
    )

    np.testing.assert_allclose(
        psi_new,
        np.array(
            [
                -0.708667913141,
                -0.710154706354,
                -0.711503826413,
                -0.712330190004,
                -0.712079195313,
                -0.71009729718,
                -0.705781204182,
                -0.698680807107,
                -0.688355530231,
                -0.674029867441,
                -0.65437420987,
                -0.627444042788,
                -0.590552955073,
                -0.540018290537,
                -0.470794672267,
            ],
            dtype=float,
        ),
        rtol=1e-9,
    )
    assert np.isnan(evap)
