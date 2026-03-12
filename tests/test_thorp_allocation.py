from __future__ import annotations

import numpy as np

from stomatal_optimiaztion.domains.thorp.allocation import (
    AllocationParams,
    allocation_fractions,
)
from stomatal_optimiaztion.domains.thorp.defaults import default_params
from stomatal_optimiaztion.domains.thorp.implements import implemented_equations


def _allocation_params() -> AllocationParams:
    return default_params().allocation


def test_allocation_fractions_exposes_expected_equation_ids() -> None:
    assert implemented_equations(allocation_fractions) == (
        "E_S8_1",
        "E_S8_2",
        "E_S8_3",
        "E_S8_4",
        "E_S8_5",
        "E_S8_6",
        "E_S8_7",
        "E_S8_8",
        "E_S8_9",
        "E_S8_10",
        "E_S8_11",
        "E_S8_12",
    )


def test_allocation_fractions_matches_legacy_snapshot() -> None:
    res = allocation_fractions(
        params=_allocation_params(),
        a_n=2.0e-4,
        lambda_wue=8.0e3,
        d_a_n_d_r_abs=5.0e-4,
        d_e_d_la=4.0e-7,
        d_e_d_d=1.0e-6,
        d_e_d_c_r_h=np.array([4.0e-7, 7.0e-7, 9.0e-7], dtype=float),
        d_e_d_c_r_v=np.array([3.0e-7, 5.0e-7, 8.0e-7], dtype=float),
        d_r_abs_d_h=5.0e-3,
        d_r_abs_d_w=-2.0e-3,
        d_r_abs_d_la=8.0e-3,
        h=9.0,
        w=3.0,
        d=0.7,
        c_w=1800.0,
        c_l=30.0,
        c0=0.6411,
        c1=0.625,
        t_a=25.0,
        t_soil=20.0,
    )

    assert np.isclose(res.u_l, 0.008950899416306649, rtol=1e-9)
    np.testing.assert_allclose(
        res.u_r_h,
        np.array([0.110060123417, 0.192605321847, 0.247635454133], dtype=float),
        rtol=1e-9,
    )
    np.testing.assert_allclose(
        res.u_r_v,
        np.array([0.082545057274, 0.13757518956, 0.22012038799], dtype=float),
        rtol=1e-9,
    )
    assert np.isclose(res.u_sw, 0.0005075663633865423, rtol=1e-9)
    assert np.isclose(res.u_l + np.sum(res.u_r_h) + np.sum(res.u_r_v) + res.u_sw, 1.0, rtol=1e-9)


def test_allocation_fractions_zero_leaf_matches_legacy_behavior() -> None:
    res = allocation_fractions(
        params=_allocation_params(),
        a_n=1.0e-6,
        lambda_wue=0.2,
        d_a_n_d_r_abs=1.0e-9,
        d_e_d_la=2.0e-9,
        d_e_d_d=3.0e-9,
        d_e_d_c_r_h=np.array([1.0e-9, 2.0e-9], dtype=float),
        d_e_d_c_r_v=np.array([3.0e-9, 4.0e-9], dtype=float),
        d_r_abs_d_h=5.0e-6,
        d_r_abs_d_w=6.0e-6,
        d_r_abs_d_la=7.0e-6,
        h=5.0,
        w=2.0,
        d=0.5,
        c_w=100.0,
        c_l=0.0,
        c0=0.6,
        c1=0.5,
        t_a=20.0,
        t_soil=18.0,
    )

    assert res.u_l == 1.0
    np.testing.assert_allclose(res.u_r_h, np.zeros(2, dtype=float))
    np.testing.assert_allclose(res.u_r_v, np.zeros(2, dtype=float))
    assert res.u_sw == 0.0


def test_allocation_fractions_zero_sum_matches_legacy_behavior() -> None:
    res = allocation_fractions(
        params=_allocation_params(),
        a_n=-1.0e-6,
        lambda_wue=0.0,
        d_a_n_d_r_abs=0.0,
        d_e_d_la=0.0,
        d_e_d_d=0.0,
        d_e_d_c_r_h=np.zeros(3, dtype=float),
        d_e_d_c_r_v=np.zeros(3, dtype=float),
        d_r_abs_d_h=0.0,
        d_r_abs_d_w=0.0,
        d_r_abs_d_la=0.0,
        h=8.0,
        w=2.5,
        d=0.6,
        c_w=1200.0,
        c_l=20.0,
        c0=0.6411,
        c1=0.625,
        t_a=22.0,
        t_soil=18.0,
    )

    assert np.isnan(res.u_l)
    np.testing.assert_allclose(
        res.u_r_h,
        np.array([np.nan, np.nan, np.nan], dtype=float),
        equal_nan=True,
    )
    np.testing.assert_allclose(
        res.u_r_v,
        np.array([np.nan, np.nan, np.nan], dtype=float),
        equal_nan=True,
    )
    assert np.isnan(res.u_sw)
