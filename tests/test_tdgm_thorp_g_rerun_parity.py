from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from stomatal_optimiaztion.domains.tdgm.examples.adapter import (
    DEFAULT_LEGACY_TDGM_THORP_G_DIR,
)
from stomatal_optimiaztion.domains.tdgm.thorp_g.allocation import (
    allocation_fractions,
    initial_mean_allocation_fractions,
    update_mean_allocation_fractions,
)
from stomatal_optimiaztion.domains.tdgm.thorp_g import default_params, load_mat, run
from stomatal_optimiaztion.domains.tdgm.thorp_g.forcing import load_forcing
from stomatal_optimiaztion.domains.tdgm.thorp_g.growth import grow
from stomatal_optimiaztion.domains.tdgm.thorp_g.hydraulics import stomata
from stomatal_optimiaztion.domains.tdgm.thorp_g.radiation import radiation
from stomatal_optimiaztion.domains.tdgm.thorp_g.simulate import _initial_allometry
from stomatal_optimiaztion.domains.tdgm.thorp_g.soil import (
    initial_soil_and_roots,
    soil_moisture,
)


def _as_1d(x: object) -> np.ndarray:
    return np.asarray(x).reshape(-1)


def _control_matlab_and_params() -> tuple[dict[str, object], object]:
    matlab_path = DEFAULT_LEGACY_TDGM_THORP_G_DIR / "THORP_data_Control_Turgor.mat"
    matlab = load_mat(matlab_path)
    params0 = default_params(forcing_rh_scale=1.0, forcing_precip_scale=1.0)
    return matlab, replace(params0, gamma_turgor_shift=0.0)


def _legacy_store_index(matlab: dict[str, object], *, day: float) -> int:
    t_days = _as_1d(matlab["t_stor"]) / 86400.0
    matches = np.where(np.isclose(t_days, day))[0]
    assert matches.size == 1
    return int(matches[0])


def _simulate_single_resume_payload_window(*, end_day: float) -> dict[float, dict[str, np.ndarray | float]]:
    matlab, params = _control_matlab_and_params()
    forcing = load_forcing(params)

    # The shipped control payload becomes legacy-compatible again if one
    # external rerun is inserted after the 787 d file-save boundary:
    # LOAD_data resumes from the last weekly checkpoint at 784.5 d and leaves
    # the mean-allocation history at its fresh-run initialization.
    start_idx = _legacy_store_index(matlab, day=784.5)
    legacy_t_days = _as_1d(matlab["t_stor"]) / 86400.0
    tracked_days = {
        round(float(day), 10)
        for day in legacy_t_days[(legacy_t_days >= 791.5) & (legacy_t_days <= end_day)]
    }

    (_, _, _, z_i, _, _, _, _, _, c_r_i0) = _initial_allometry(params)
    init = initial_soil_and_roots(params=params, c_r_i=c_r_i0, z_i=z_i)
    u_sw_mean, u_l_mean, u_r_h_mean, u_r_v_mean = initial_mean_allocation_fractions(
        c_r_h=init.c_r_h,
        c_r_v=init.c_r_v,
    )

    grid = init.grid
    n_soil = grid.n_soil

    t = float(_as_1d(matlab["t_stor"])[start_idx])
    c_nsc = float(_as_1d(matlab["c_NSC_stor"])[start_idx])
    c_l = float(_as_1d(matlab["c_l_stor"])[start_idx])
    c_sw = float(_as_1d(matlab["c_sw_stor"])[start_idx])
    c_hw = float(_as_1d(matlab["c_hw_stor"])[start_idx])
    c_r_h = np.asarray(matlab["c_r_H_stor"], dtype=float)[:, start_idx].copy()
    c_r_v = np.asarray(matlab["c_r_V_stor"], dtype=float)[:, start_idx].copy()
    d = float(_as_1d(matlab["D_stor"])[start_idx])
    d_hw = float(_as_1d(matlab["D_hw_stor"])[start_idx])
    h = float(_as_1d(matlab["H_stor"])[start_idx])
    w = float(_as_1d(matlab["W_stor"])[start_idx])
    psi_soil_by_layer = np.asarray(matlab["P_soil_stor"], dtype=float)[:, start_idx].copy()
    u_l = float(_as_1d(matlab["u_l_stor"])[start_idx])
    u_sw = float(_as_1d(matlab["u_sw_stor"])[start_idx])
    u_r_h = np.zeros(n_soil, dtype=float)
    u_r_v = np.zeros(n_soil, dtype=float)
    t_allocate = 3600.0 * (24.0 * np.floor(t / 3600.0 / 24.0) + 12.0)

    step = int(round(t / params.dt))
    records: dict[float, dict[str, np.ndarray | float]] = {}

    while step < (forcing.t.size - 1) and forcing.t[step] <= (end_day * 86400.0):
        t = float(forcing.t[step])
        t_a = float(forcing.t_a[step])
        t_soil = float(forcing.t_soil[step])
        rh = float(forcing.rh[step])
        precip = float(forcing.precip[step])
        u10 = float(forcing.u10[step])
        r_incom = float(forcing.r_incom[step])
        z_a = float(forcing.z_a[step])

        la_area = float(params.sla * c_l)
        rad = radiation(
            r_incom=r_incom,
            z_a=z_a,
            la=la_area,
            w=w,
            h=h,
            h_n=params.h_n,
            kappa_l=params.kappa_l,
            kappa_n=params.kappa_n,
            phi=params.phi,
        )
        stom = stomata(
            params=params,
            psi_soil_by_layer=psi_soil_by_layer,
            n_soil=n_soil,
            dz=grid.dz,
            z_soil_mid=grid.z_mid,
            t_a=t_a,
            rh=rh,
            r_abs=rad.r_abs,
            la=la_area,
            c_r_h=c_r_h,
            c_r_v=c_r_v,
            h=h,
            w=w,
            d=d,
            d_hw=d_hw,
            d_r_abs_d_h=rad.d_r_abs_dh,
            d_r_abs_d_w=rad.d_r_abs_dw,
            d_r_abs_d_la=rad.d_r_abs_dla,
        )

        if t >= t_allocate:
            alloc = allocation_fractions(
                params=params,
                a_n=stom.a_n,
                lambda_wue=stom.lambda_wue,
                d_a_n_d_r_abs=stom.d_a_n_d_r_abs,
                d_e_d_la=stom.d_e_d_la,
                d_e_d_d=stom.d_e_d_d,
                d_e_d_c_r_h=stom.d_e_d_c_r_h,
                d_e_d_c_r_v=stom.d_e_d_c_r_v,
                d_r_abs_d_h=rad.d_r_abs_dh,
                d_r_abs_d_w=rad.d_r_abs_dw,
                d_r_abs_d_la=rad.d_r_abs_dla,
                h=h,
                w=w,
                d=d,
                c_w=float(c_sw + c_hw),
                c_l=c_l,
                c0=params.c0,
                c1=params.c1,
                t_a=t_a,
                t_soil=t_soil,
            )
            u_l = alloc.u_l
            u_r_h = alloc.u_r_h
            u_r_v = alloc.u_r_v
            u_sw = alloc.u_sw
            u_l_mean, u_sw_mean, u_r_h_mean, u_r_v_mean = update_mean_allocation_fractions(
                u_l_mean=u_l_mean,
                u_l=u_l,
                u_r_h_mean=u_r_h_mean,
                u_r_h=u_r_h,
                u_r_v_mean=u_r_v_mean,
                u_r_v=u_r_v,
                u_sw_mean=u_sw_mean,
                u_sw=u_sw,
                dt_allocate=float(params.dt_allocate),
            )
            t_allocate = float(t_allocate + float(params.dt_allocate))

        psi_soil_by_layer, evap = soil_moisture(
            params=params,
            grid=grid,
            psi_soil_by_layer=psi_soil_by_layer,
            t_a=t_a,
            t_soil=t_soil,
            rh=rh,
            u10=u10,
            precip=precip,
            e_soil=stom.e_soil,
            la=la_area,
            w=w,
        )
        gstate = grow(
            params=params,
            u_l=u_l_mean,
            u_r_h=u_r_h_mean,
            u_r_v=u_r_v_mean,
            u_sw=u_sw_mean,
            a_n=stom.a_n,
            r_d=stom.r_d,
            c_l=c_l,
            c_r_h=c_r_h,
            c_r_v=c_r_v,
            c_sw=c_sw,
            c_hw=c_hw,
            c_nsc=c_nsc,
            t_a=t_a,
            t_soil=t_soil,
            psi_s=stom.psi_s,
            psi_rc=stom.psi_rc,
        )
        c_l = gstate.c_l
        c_r_h = gstate.c_r_h
        c_r_v = gstate.c_r_v
        c_sw = gstate.c_sw
        c_hw = gstate.c_hw
        c_nsc = gstate.c_nsc
        h = gstate.h
        w = gstate.w
        d = gstate.d
        d_hw = gstate.d_hw

        day_key = round(t / 86400.0, 10)
        if day_key in tracked_days:
            records[day_key] = {
                "A_n_stor": float(stom.a_n),
                "E_stor": float(stom.e),
                "u_l_stor": float(u_l),
                "u_sw_stor": float(u_sw),
                "u_r_H_stor": float(np.sum(u_r_h)),
                "u_r_V_stor": float(np.sum(u_r_v)),
                "c_l_stor": float(c_l),
                "c_sw_stor": float(c_sw),
                "c_hw_stor": float(c_hw),
                "H_stor": float(h),
                "D_stor": float(d),
                "P_x_l_stor": float(stom.psi_l),
                "P_x_s_stor": float(stom.psi_s),
                "P_x_r_stor": float(stom.psi_rc),
                "P_soil_stor": psi_soil_by_layer.copy(),
            }

        step += 1

    return records


CASES: list[tuple[str, float, float, float]] = [
    # name, forcing_rh_scale, forcing_precip_scale, gamma_turgor_shift
    ("THORP_data_Control_Turgor.mat", 1.0, 1.0, 0.0),
    ("THORP_data_0.9RH_Turgor.mat", 0.9, 1.0, 0.0),
    ("THORP_data_0.8RH_Turgor.mat", 0.8, 1.0, 0.0),
    ("THORP_data_0.9Prec_Turgor.mat", 1.0, 0.9, 0.0),
    ("THORP_data_0.8Prec_Turgor.mat", 1.0, 0.8, 0.0),
    ("THORP_data_0.9Prec_0.9RH_Turgor.mat", 0.9, 0.9, 0.0),
    ("THORP_data_Control_Turgor_Gamma_minus_0.1MPa.mat", 1.0, 1.0, -0.1),
    ("THORP_data_Control_Turgor_Gamma_minus_0.05MPa.mat", 1.0, 1.0, -0.05),
    ("THORP_data_Control_Turgor_Gamma_plus_0.05MPa.mat", 1.0, 1.0, 0.05),
    ("THORP_data_Control_Turgor_Gamma_plus_0.1MPa.mat", 1.0, 1.0, 0.1),
]


@pytest.mark.parametrize("mat_name,rh_scale,precip_scale,gamma_shift", CASES, ids=[c[0] for c in CASES])
@pytest.mark.skipif(not DEFAULT_LEGACY_TDGM_THORP_G_DIR.exists(), reason="legacy TDGM THORP-G dir not available")
def test_thorp_g_v14_regression_cases_match_matlab_first_2_weeks(
    mat_name: str,
    rh_scale: float,
    precip_scale: float,
    gamma_shift: float,
) -> None:
    matlab_path = DEFAULT_LEGACY_TDGM_THORP_G_DIR / mat_name
    matlab = load_mat(matlab_path)

    params0 = default_params(forcing_repeat_q=1, forcing_rh_scale=rh_scale, forcing_precip_scale=precip_scale)
    params = replace(params0, gamma_turgor_shift=float(gamma_shift))

    out = run(params=params, max_steps=60)
    py = out.as_mat_dict()

    expected_t = _as_1d(matlab["t_stor"])[:3]
    assert np.array_equal(out.t_ts, expected_t)

    for key in [
        "c_NSC_stor",
        "c_l_stor",
        "c_sw_stor",
        "c_hw_stor",
        "u_l_stor",
        "u_sw_stor",
        "u_r_H_stor",
        "u_r_V_stor",
        "D_stor",
        "D_hw_stor",
        "H_stor",
        "W_stor",
        "P_x_l_stor",
        "P_x_s_stor",
        "P_x_r_stor",
        "P_x_r0_stor",
        "R_abs_stor",
        "E_stor",
        "Evap_stor",
        "G_w_stor",
        "A_n_stor",
        "R_d_stor",
        "R_m_stor",
        "U_stor",
    ]:
        assert np.allclose(_as_1d(py[key])[:3], _as_1d(matlab[key])[:3], rtol=0, atol=1e-12, equal_nan=True), key

    for key in ["c_r_H_stor", "c_r_V_stor", "P_soil_stor"]:
        assert np.allclose(
            np.asarray(py[key], dtype=float)[:, :3],
            np.asarray(matlab[key], dtype=float)[:, :3],
            rtol=0,
            atol=1e-12,
            equal_nan=True,
        ), key


@pytest.mark.skipif(not DEFAULT_LEGACY_TDGM_THORP_G_DIR.exists(), reason="legacy TDGM THORP-G dir not available")
def test_thorp_g_control_case_matches_matlab_through_last_pre_resume_checkpoint() -> None:
    matlab, params = _control_matlab_and_params()

    # The continuous Python rerun remains source-exact through the last weekly
    # checkpoint before the shipped payload's one-off resume artifact reopens.
    out = run(params=params, max_steps=3150)
    py = out.as_mat_dict()

    expected_t = _as_1d(matlab["t_stor"])[: out.t_ts.size]
    assert np.array_equal(out.t_ts, expected_t)

    for key in [
        "A_n_stor",
        "E_stor",
        "P_x_l_stor",
        "P_x_s_stor",
        "P_x_r_stor",
        "u_l_stor",
        "u_sw_stor",
        "c_NSC_stor",
        "c_l_stor",
        "c_sw_stor",
        "H_stor",
        "D_stor",
        "U_stor",
    ]:
        assert np.allclose(
            _as_1d(py[key]),
            _as_1d(matlab[key])[: out.t_ts.size],
            rtol=0,
            atol=1e-12,
            equal_nan=True,
        ), key

    for key in ["c_r_H_stor", "c_r_V_stor", "P_soil_stor"]:
        assert np.allclose(
            np.asarray(py[key], dtype=float),
            np.asarray(matlab[key], dtype=float)[:, : out.t_ts.size],
            rtol=0,
            atol=1e-12,
            equal_nan=True,
        ), key


@pytest.mark.skipif(not DEFAULT_LEGACY_TDGM_THORP_G_DIR.exists(), reason="legacy TDGM THORP-G dir not available")
def test_thorp_g_control_payload_post_791d_is_explained_by_single_resume_artifact() -> None:
    matlab, _ = _control_matlab_and_params()
    records = _simulate_single_resume_payload_window(end_day=819.5)

    scalar_keys = [
        "A_n_stor",
        "E_stor",
        "u_l_stor",
        "u_sw_stor",
        "u_r_H_stor",
        "u_r_V_stor",
        "c_l_stor",
        "c_sw_stor",
        "c_hw_stor",
        "H_stor",
        "D_stor",
    ]
    psi_keys = ["P_x_l_stor", "P_x_s_stor", "P_x_r_stor"]

    assert set(records) == {791.5, 798.5, 805.5, 812.5, 819.5}

    for day in sorted(records):
        idx = _legacy_store_index(matlab, day=day)
        for key in scalar_keys:
            assert np.allclose(
                records[day][key],
                float(_as_1d(matlab[key])[idx]),
                rtol=0,
                atol=3e-5,
                equal_nan=True,
            ), (day, key)
        for key in psi_keys:
            assert np.allclose(
                records[day][key],
                float(_as_1d(matlab[key])[idx]),
                rtol=0,
                atol=3e-6,
                equal_nan=True,
            ), (day, key)
        assert np.allclose(
            np.asarray(records[day]["P_soil_stor"], dtype=float),
            np.asarray(matlab["P_soil_stor"], dtype=float)[:, idx],
            rtol=0,
            atol=3e-6,
            equal_nan=True,
        ), day
