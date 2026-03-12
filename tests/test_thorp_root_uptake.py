from __future__ import annotations

import numpy as np

from stomatal_optimiaztion.domains.thorp.defaults import default_params
from stomatal_optimiaztion.domains.thorp.hydraulics import (
    RootUptakeParams,
    e_from_soil_to_root_collar,
)
from stomatal_optimiaztion.domains.thorp.implements import implemented_equations
from stomatal_optimiaztion.domains.thorp.soil_initialization import (
    SoilInitializationParams,
    initial_soil_and_roots,
)


def _legacy_default_like_initialization_params() -> SoilInitializationParams:
    return default_params().soil_initialization


def _root_uptake_params() -> RootUptakeParams:
    return default_params().root_uptake


def test_root_uptake_exposes_expected_equation_ids() -> None:
    assert implemented_equations(e_from_soil_to_root_collar) == (
        "E_S2_2",
        "E_S3_1",
        "E_S3_2",
        "E_S3_3",
        "E_S3_4",
        "E_S3_5",
    )


def test_root_uptake_matches_legacy_snapshot() -> None:
    init = initial_soil_and_roots(
        params=_legacy_default_like_initialization_params(),
        c_r_i=1.0,
        z_i=3.0,
    )

    res = e_from_soil_to_root_collar(
        params=_root_uptake_params(),
        psi_rc=-0.92,
        psi_soil_by_layer=init.psi_soil_by_layer,
        z_soil_mid=init.grid.z_mid,
        dz=init.grid.dz,
        la=2.8,
        c_r_h=init.c_r_h,
        c_r_v=init.c_r_v,
    )

    assert np.isclose(res.e, 6.884642523943817e-06, rtol=1e-9)
    np.testing.assert_allclose(
        res.e_soil,
        np.array(
            [
                1.280442933780e-06,
                1.244268543400e-06,
                1.201254558213e-06,
                1.122026210588e-06,
                9.449354372979e-07,
                6.391281629058e-07,
                3.197223862699e-07,
                1.085922733647e-07,
                2.197465269729e-08,
                2.209270684139e-09,
                8.709372077427e-11,
                9.987552765547e-13,
                2.266632961253e-15,
                6.012325240698e-19,
                8.894765280060e-24,
            ],
            dtype=float,
        ),
        rtol=1e-9,
    )
    np.testing.assert_allclose(
        res.r_r_h,
        np.array(
            [
                2.103866031355e04,
                2.166574948795e04,
                2.246341108006e04,
                2.408158190822e04,
                2.864657746040e04,
                4.245779988867e04,
                8.515794433283e04,
                2.518625932233e05,
                1.252228294335e06,
                1.255705451880e07,
                3.219746493151e08,
                2.847373339395e10,
                1.277363250320e13,
                4.924023303409e16,
                4.189964032392e21,
            ],
            dtype=float,
        ),
        rtol=1e-9,
    )
    np.testing.assert_allclose(
        res.r_r_v,
        np.array(
            [
                2.607439614352e04,
                7.528697266108e02,
                9.532962393053e02,
                1.950971410513e03,
                5.554815545838e03,
                1.684930947798e04,
                5.199166328596e04,
                2.020859178251e05,
                1.204629149619e06,
                1.348608209770e07,
                3.644281784752e08,
                3.260002753075e10,
                1.444340282199e13,
                5.433656334475e16,
                3.660179933224e21,
            ],
            dtype=float,
        ),
        rtol=1e-9,
    )
    np.testing.assert_allclose(
        res.f_r,
        np.array(
            [
                0.739287067722,
                0.739683162319,
                0.740225158896,
                0.740966474178,
                0.741979789953,
                0.743363736536,
                0.745251647189,
                0.747822778616,
                0.751316185958,
                0.756046810515,
                0.762421778909,
                0.770951392441,
                0.782241806065,
                0.796941500755,
                0.815587117471,
            ],
            dtype=float,
        ),
        rtol=1e-9,
    )


def test_root_uptake_handles_zero_root_layers_like_legacy() -> None:
    res = e_from_soil_to_root_collar(
        params=_root_uptake_params(),
        psi_rc=-0.9,
        psi_soil_by_layer=np.array([-0.4, -0.8, -1.2], dtype=float),
        z_soil_mid=np.array([0.1, 0.3, 0.8], dtype=float),
        dz=np.array([0.2, 0.2, 0.4], dtype=float),
        la=2.1,
        c_r_h=np.array([0.05, 0.0, 0.08], dtype=float),
        c_r_v=np.array([0.03, 0.0, 0.04], dtype=float),
    )

    assert np.isclose(res.e, 2.8980452474028086e-06, rtol=1e-9)
    np.testing.assert_allclose(
        res.e_soil,
        np.array([2.898045247403e-06, 0.0, -0.0], dtype=float),
        rtol=1e-9,
    )
    np.testing.assert_allclose(
        res.r_r_h,
        np.array([7.961535390133316e04, np.nan, np.nan], dtype=float),
        rtol=1e-9,
        equal_nan=True,
    )
    np.testing.assert_allclose(
        res.r_r_v,
        np.array([1.254870514191393e03, np.inf, 3.764611542574178e03], dtype=float),
        rtol=1e-9,
        equal_nan=True,
    )
    np.testing.assert_allclose(
        res.f_r,
        np.array([0.839259300135, 0.756167973539, 0.562799719214], dtype=float),
        rtol=1e-9,
    )
