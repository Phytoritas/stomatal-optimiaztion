from __future__ import annotations

import numpy as np

from stomatal_optimiaztion.domains.thorp.defaults import default_params
from stomatal_optimiaztion.domains.thorp.implements import implemented_equations
from stomatal_optimiaztion.domains.thorp.soil_dynamics import (
    RichardsEquationParams,
    SoilMoistureParams,
    soil_moisture,
)
from stomatal_optimiaztion.domains.thorp.soil_initialization import (
    SoilInitializationParams,
    initial_soil_and_roots,
)


def _legacy_default_like_params() -> SoilInitializationParams:
    return default_params().soil_initialization


def _richards_params() -> RichardsEquationParams:
    return default_params().richards


def _soil_moisture_params() -> SoilMoistureParams:
    return default_params().soil_moisture


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
