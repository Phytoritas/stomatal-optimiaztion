from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from stomatal_optimiaztion.domains.thorp.allocation import AllocationParams
from stomatal_optimiaztion.domains.thorp.growth import GrowthParams, grow
from stomatal_optimiaztion.domains.thorp.implements import implemented_equations


def _r_m_sw_func(t: float | NDArray[np.floating]) -> float | NDArray[np.floating]:
    return 2.2e-12 * 1.8 ** ((np.asarray(t) - 15.0) / 10.0)


def _r_m_r_func(t: float | NDArray[np.floating]) -> float | NDArray[np.floating]:
    return 7.0e-9 * 1.98 ** ((np.asarray(t) - 15.0) / 10.0)


def _growth_params() -> GrowthParams:
    return GrowthParams(
        allocation=AllocationParams(
            sla=0.08,
            r_m_sw_func=_r_m_sw_func,
            r_m_r_func=_r_m_r_func,
            tau_l=9.5e7,
            tau_sw=1.2e9,
            tau_r=9.6e7,
        ),
        dt=6 * 3600.0,
        f_c=0.28,
        rho_cw=1.4e4,
        xi=0.5,
        b0=64.6,
        d_ref=1.0,
        c0=0.6411,
        b1=8.5,
        c1=0.625,
    )


def test_grow_exposes_expected_equation_ids() -> None:
    assert implemented_equations(grow) == (
        "E_S7_1",
        "E_S7_2",
        "E_S7_3",
        "E_S7_4",
        "E_S7_5",
        "E_S9_1",
        "E_S9_2",
        "E_S9_3",
        "E_S9_4",
        "E_S9_5",
        "E_S9_6",
        "E_S9_7",
        "E_S9_8",
        "E_S9_9",
    )


def test_grow_matches_legacy_snapshot() -> None:
    res = grow(
        params=_growth_params(),
        u_l=0.008950899416306649,
        u_r_h=np.array([0.110060123417, 0.192605321847, 0.247635454133], dtype=float),
        u_r_v=np.array([0.082545057274, 0.13757518956, 0.22012038799], dtype=float),
        u_sw=0.0005075663633865423,
        a_n=2.0e-4,
        r_d=1.2e-6,
        c_l=30.0,
        c_r_h=np.array([5.0, 7.0, 9.0], dtype=float),
        c_r_v=np.array([3.0, 4.0, 6.0], dtype=float),
        c_sw=1200.0,
        c_hw=800.0,
        c_nsc=50.0,
        t_a=25.0,
        t_soil=20.0,
    )

    assert np.isclose(res.c_l, 29.993716442990433, rtol=1e-9)
    np.testing.assert_allclose(
        res.c_r_h,
        np.array([5.005484038013, 7.00999082288, 9.012845346125], dtype=float),
        rtol=1e-9,
    )
    np.testing.assert_allclose(
        res.c_r_v,
        np.array([3.004281776391, 4.007361299636, 6.011868084503], dtype=float),
        rtol=1e-9,
    )
    assert np.isclose(res.c_sw, 1199.9784304790262, rtol=1e-9)
    assert np.isclose(res.c_hw, 800.0216, rtol=1e-9)
    assert np.isclose(res.c_nsc, 60.277261745837585, rtol=1e-9)
    assert np.isclose(res.r_m, 3.2196476852513927e-06, rtol=1e-9)
    assert np.isclose(res.u, 3.861197414860456e-06, rtol=1e-9)
    assert np.isclose(res.la, 2.3994973154392345, rtol=1e-9)
    assert np.isclose(res.h, 17.328068193518018, rtol=1e-9)
    assert np.isclose(res.w, 2.356612855934848, rtol=1e-9)
    assert np.isclose(res.d, 0.1284076526429208, rtol=1e-9)
    assert np.isclose(res.d_hw, 0.08121322600700721, rtol=1e-9)
    assert np.isclose(res.c_w, 2000.0000304790262, rtol=1e-9)


def test_grow_all_nan_allocation_matches_legacy_behavior() -> None:
    res = grow(
        params=_growth_params(),
        u_l=float("nan"),
        u_r_h=np.array([float("nan"), float("nan")], dtype=float),
        u_r_v=np.array([float("nan"), float("nan")], dtype=float),
        u_sw=float("nan"),
        a_n=0.0,
        r_d=1.0e-6,
        c_l=20.0,
        c_r_h=np.array([2.0, 3.0], dtype=float),
        c_r_v=np.array([1.0, 1.5], dtype=float),
        c_sw=500.0,
        c_hw=300.0,
        c_nsc=40.0,
        t_a=10.0,
        t_soil=8.0,
    )

    assert np.isclose(res.c_l, 19.995452631578946, rtol=1e-9)
    np.testing.assert_allclose(res.c_r_h, np.array([1.99955, 2.999325], dtype=float), rtol=1e-9)
    np.testing.assert_allclose(res.c_r_v, np.array([0.999775, 1.4996625], dtype=float), rtol=1e-9)
    assert np.isclose(res.c_sw, 499.991, rtol=1e-9)
    assert np.isclose(res.c_hw, 300.009, rtol=1e-9)
    assert np.isclose(res.c_nsc, 39.99927930313527, rtol=1e-9)
    assert np.isclose(res.r_m, 1.6333655955893297e-06, rtol=1e-9)
    assert np.isclose(res.u, 0.0, rtol=1e-9)
    assert np.isclose(res.la, 1.5996362105263158, rtol=1e-9)
    assert np.isclose(res.h, 13.872485566353639, rtol=1e-9)
    assert np.isclose(res.w, 1.8972221926169024, rtol=1e-9)
    assert np.isclose(res.d, 0.09076508792150462, rtol=1e-9)
    assert np.isclose(res.d_hw, 0.055582871690951344, rtol=1e-9)


def test_grow_partial_nan_allocation_raises() -> None:
    try:
        grow(
            params=_growth_params(),
            u_l=float("nan"),
            u_r_h=np.array([0.1, 0.2], dtype=float),
            u_r_v=np.array([0.1, 0.2], dtype=float),
            u_sw=0.3,
            a_n=0.0,
            r_d=1.0e-6,
            c_l=20.0,
            c_r_h=np.array([2.0, 3.0], dtype=float),
            c_r_v=np.array([1.0, 1.5], dtype=float),
            c_sw=500.0,
            c_hw=300.0,
            c_nsc=40.0,
            t_a=10.0,
            t_soil=8.0,
        )
    except RuntimeError as exc:
        assert "partial NaNs" in str(exc)
    else:
        raise AssertionError("grow should reject partially NaN allocation fractions")
