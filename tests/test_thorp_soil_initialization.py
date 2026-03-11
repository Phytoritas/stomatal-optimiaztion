from __future__ import annotations

import numpy as np
import pytest

from stomatal_optimiaztion.domains.thorp.soil_hydraulics import SoilHydraulics
from stomatal_optimiaztion.domains.thorp.soil_initialization import (
    InitialSoilAndRoots,
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


def test_initial_soil_and_roots_matches_legacy_snapshot() -> None:
    out = initial_soil_and_roots(params=_legacy_default_like_params(), c_r_i=1.0, z_i=3.0)

    np.testing.assert_allclose(
        out.grid.dz,
        np.array(
            [
                0.09966816,
                0.13654095,
                0.18705502,
                0.25625706,
                0.35106077,
                0.48093763,
                0.65886316,
                0.90261322,
                1.23653995,
                1.69400471,
                2.32071109,
                3.17927095,
                4.35545976,
                5.96678609,
                8.17423149,
            ],
            dtype=float,
        ),
        rtol=1e-7,
    )
    np.testing.assert_allclose(
        out.psi_soil_by_layer,
        np.array(
            [
                -0.72400023,
                -0.72284394,
                -0.72125987,
                -0.71908978,
                -0.71611684,
                -0.71204405,
                -0.70646451,
                -0.69882079,
                -0.68834922,
                -0.67400365,
                -0.65435085,
                -0.6274274,
                -0.59054346,
                -0.5400141,
                -0.47079114,
            ],
            dtype=float,
        ),
        rtol=1e-7,
    )
    np.testing.assert_allclose(
        out.vwc,
        np.array(
            [
                0.24465022,
                0.24289015,
                0.24049925,
                0.23726156,
                0.23289589,
                0.22704372,
                0.21926159,
                0.20902614,
                0.19576482,
                0.1789328,
                0.15816094,
                0.13349355,
                0.10569986,
                0.0765592,
                0.04889254,
            ],
            dtype=float,
        ),
        rtol=1e-7,
    )
    np.testing.assert_allclose(
        out.c_r_h,
        np.array(
            [
                1.61044018e-01,
                1.56382792e-01,
                1.50829737e-01,
                1.40694677e-01,
                1.18274178e-01,
                7.98004229e-02,
                3.97866625e-02,
                1.34523763e-02,
                2.70569704e-03,
                2.69820473e-04,
                1.05230346e-05,
                1.18992137e-07,
                2.65245645e-10,
                6.88085774e-14,
                9.91475591e-19,
            ],
            dtype=float,
        ),
        rtol=1e-7,
    )
    np.testing.assert_allclose(
        out.c_r_v,
        np.array(
            [
                3.58557495e-04,
                2.33059149e-02,
                3.45438738e-02,
                3.16782324e-02,
                2.08811845e-02,
                1.29197941e-02,
                7.85808849e-03,
                3.79426363e-03,
                1.19460166e-03,
                2.00264333e-04,
                1.39088231e-05,
                2.91808068e-07,
                1.23611440e-09,
                6.16664502e-13,
                1.71811254e-17,
            ],
            dtype=float,
        ),
        rtol=1e-7,
    )
    assert out.grid.n_soil == 15


def test_initial_soil_and_roots_returns_expected_shapes() -> None:
    out = initial_soil_and_roots(params=_legacy_default_like_params(), c_r_i=1.0, z_i=3.0)

    assert isinstance(out, InitialSoilAndRoots)
    assert out.grid.dz.shape == (15,)
    assert out.grid.z_bttm.shape == (15,)
    assert out.grid.z_mid.shape == (15,)
    assert out.grid.dz_c.shape == (16,)
    assert out.psi_soil_by_layer.shape == (15,)
    assert out.vwc.shape == (15,)
    assert out.c_r_h.shape == (15,)
    assert out.c_r_v.shape == (15,)


def test_initial_soil_and_roots_rejects_nonpositive_rooting_depth() -> None:
    with pytest.raises(ValueError, match="Initial rooting depth Z_i must be > 0"):
        initial_soil_and_roots(params=_legacy_default_like_params(), c_r_i=1.0, z_i=0.0)
