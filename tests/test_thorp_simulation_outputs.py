from __future__ import annotations

import numpy as np
from numpy.testing import assert_allclose

from stomatal_optimiaztion.domains.thorp.simulation import SimulationOutputs


def _outputs() -> SimulationOutputs:
    t_ts = np.array([0.0, 1.0, 2.0], dtype=float)
    c_nsc_ts = np.array([10.0, 11.0, 12.0], dtype=float)
    c_l_ts = np.array([20.0, 21.0, 22.0], dtype=float)
    c_sw_ts = np.array([30.0, 31.0, 32.0], dtype=float)
    c_hw_ts = np.array([40.0, 41.0, 42.0], dtype=float)
    c_r_h_by_layer_ts = np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]], dtype=float)
    c_r_v_by_layer_ts = np.array([[0.5, 1.5, 2.5], [3.5, 4.5, 5.5]], dtype=float)
    u_l_ts = np.array([50.0, 51.0, 52.0], dtype=float)
    u_sw_ts = np.array([60.0, 61.0, 62.0], dtype=float)
    u_r_h_ts = np.array([70.0, 71.0, 72.0], dtype=float)
    u_r_v_ts = np.array([80.0, 81.0, 82.0], dtype=float)
    d_ts = np.array([0.10, 0.11, 0.12], dtype=float)
    d_hw_ts = np.array([0.01, 0.02, 0.03], dtype=float)
    h_ts = np.array([1.0, 1.1, 1.2], dtype=float)
    w_ts = np.array([0.4, 0.5, 0.6], dtype=float)
    psi_l_ts = np.array([-1.1, -1.2, -1.3], dtype=float)
    psi_s_ts = np.array([-0.7, -0.8, -0.9], dtype=float)
    psi_rc_ts = np.array([-0.5, -0.6, -0.7], dtype=float)
    psi_rc0_ts = np.array([-0.4, -0.5, -0.6], dtype=float)
    psi_soil_by_layer_ts = np.array(
        [[-0.2, -0.3, -0.4], [-0.5, -0.6, -0.7]],
        dtype=float,
    )
    r_abs_ts = np.array([100.0, 101.0, 102.0], dtype=float)
    e_ts = np.array([0.001, 0.002, 0.003], dtype=float)
    evap_ts = np.array([0.01, 0.02, 0.03], dtype=float)
    g_w_ts = np.array([0.2, 0.3, 0.4], dtype=float)
    a_n_ts = np.array([5.0, 5.1, 5.2], dtype=float)
    r_d_ts = np.array([0.05, 0.06, 0.07], dtype=float)
    r_m_ts = np.array([0.15, 0.16, 0.17], dtype=float)
    u_ts = np.array([6.0, 6.1, 6.2], dtype=float)

    return SimulationOutputs(
        t_ts=t_ts,
        c_nsc_ts=c_nsc_ts,
        c_l_ts=c_l_ts,
        c_sw_ts=c_sw_ts,
        c_hw_ts=c_hw_ts,
        c_r_h_by_layer_ts=c_r_h_by_layer_ts,
        c_r_v_by_layer_ts=c_r_v_by_layer_ts,
        u_l_ts=u_l_ts,
        u_sw_ts=u_sw_ts,
        u_r_h_ts=u_r_h_ts,
        u_r_v_ts=u_r_v_ts,
        d_ts=d_ts,
        d_hw_ts=d_hw_ts,
        h_ts=h_ts,
        w_ts=w_ts,
        psi_l_ts=psi_l_ts,
        psi_s_ts=psi_s_ts,
        psi_rc_ts=psi_rc_ts,
        psi_rc0_ts=psi_rc0_ts,
        psi_soil_by_layer_ts=psi_soil_by_layer_ts,
        r_abs_ts=r_abs_ts,
        e_ts=e_ts,
        evap_ts=evap_ts,
        g_w_ts=g_w_ts,
        a_n_ts=a_n_ts,
        r_d_ts=r_d_ts,
        r_m_ts=r_m_ts,
        u_ts=u_ts,
    )


def test_simulation_outputs_as_mat_dict_matches_legacy_key_order() -> None:
    outputs = _outputs()
    mat = outputs.as_mat_dict()

    assert list(mat.keys()) == [
        "t_stor",
        "c_NSC_stor",
        "c_l_stor",
        "c_sw_stor",
        "c_hw_stor",
        "c_r_H_stor",
        "c_r_V_stor",
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
        "P_soil_stor",
        "R_abs_stor",
        "E_stor",
        "Evap_stor",
        "G_w_stor",
        "A_n_stor",
        "R_d_stor",
        "R_m_stor",
        "U_stor",
    ]


def test_simulation_outputs_as_mat_dict_preserves_array_references() -> None:
    outputs = _outputs()
    mat = outputs.as_mat_dict()

    assert mat["t_stor"] is outputs.t_ts
    assert mat["c_r_H_stor"] is outputs.c_r_h_by_layer_ts
    assert mat["c_r_V_stor"] is outputs.c_r_v_by_layer_ts
    assert mat["P_soil_stor"] is outputs.psi_soil_by_layer_ts

    assert_allclose(mat["A_n_stor"], outputs.a_n_ts)
    assert_allclose(mat["R_abs_stor"], outputs.r_abs_ts)
    assert_allclose(mat["P_x_r0_stor"], outputs.psi_rc0_ts)
    assert_allclose(mat["U_stor"], outputs.u_ts)
