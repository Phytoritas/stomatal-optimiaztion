from __future__ import annotations

from dataclasses import replace

from numpy.testing import assert_allclose

from stomatal_optimiaztion.domains.thorp.params import thorp_params_from_defaults
from stomatal_optimiaztion.domains.thorp.simulation import InitialAllometry, _initial_allometry


def test_initial_allometry_matches_legacy_snapshot() -> None:
    res = _initial_allometry(params=thorp_params_from_defaults())

    assert isinstance(res, InitialAllometry)
    assert_allclose(res.d, 0.015)
    assert_allclose(res.h, 4.374461757393807)
    assert_allclose(res.w, 0.6158514419627071)
    assert_allclose(res.z_i, 3.0)
    assert_allclose(res.c_l, 6.333859076078014)
    assert_allclose(res.c_sw, 6.4763906318215305)
    assert_allclose(res.c_hw, 0.4133866360737155)
    assert_allclose(res.d_hw, 0.0036742346141747702)
    assert_allclose(res.c_nsc, 1.9279536324142659)
    assert_allclose(res.c_r_i, 5.667272718845683)


def test_initial_allometry_respects_parameter_formulas() -> None:
    params = replace(
        thorp_params_from_defaults(),
        d_ref=0.5,
        b0=50.0,
        c0=0.7,
        b1=6.0,
        c1=0.55,
        phi=2.5,
        sla=0.1,
        rho_cw=10000.0,
        xi=0.25,
    )

    res = _initial_allometry(params=params)

    d = 0.015
    h = params.b0 * (d / params.d_ref) ** params.c0
    w = params.b1 * (d / params.d_ref) ** params.c1
    la = 0.4 * params.phi * w**2
    c_l = la / params.sla
    c_w = params.rho_cw * params.xi * d**2 * h
    c_r_i = (c_l + c_w) * 0.3 / 0.7
    c_sw = 0.94 * c_w
    c_hw = c_w - c_sw
    d_hw = (c_hw / (params.rho_cw * params.xi * h)) ** 0.5
    c_nsc = (0.20 * c_l + 0.04 * c_w) / 0.8

    assert_allclose(res.d, d)
    assert_allclose(res.h, h)
    assert_allclose(res.w, w)
    assert_allclose(res.z_i, 3.0)
    assert_allclose(res.c_l, c_l)
    assert_allclose(res.c_sw, c_sw)
    assert_allclose(res.c_hw, c_hw)
    assert_allclose(res.d_hw, d_hw)
    assert_allclose(res.c_nsc, c_nsc)
    assert_allclose(res.c_r_i, c_r_i)
