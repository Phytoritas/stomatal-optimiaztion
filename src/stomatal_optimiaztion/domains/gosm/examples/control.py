from __future__ import annotations

import numpy as np

from stomatal_optimiaztion.domains.gosm.model.pipeline import (
    rad_hydr_grow_temp_cassimilation,
)
from stomatal_optimiaztion.domains.gosm.model.steady_state import (
    steady_state_nsc_and_cue,
)
from stomatal_optimiaztion.domains.gosm.params import BaselineInputs

__all__ = [
    "build_control_E_vec",
    "build_control_e_vec",
    "run_control_plot_data",
]


def build_control_e_vec() -> np.ndarray:
    """Match the MATLAB control-example transpiration grid."""

    return np.arange(0.0, 1e-2 + 1e-5, 1e-5, dtype=float)


def build_control_E_vec() -> np.ndarray:  # noqa: N802 - legacy alias
    return build_control_e_vec()


def run_control_plot_data(
    *,
    inputs: BaselineInputs | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Reproduce `Example_Growth_Opt__control.mat` contents."""

    inputs = inputs or BaselineInputs.matlab_default()
    e_vec = build_control_e_vec()

    (
        e_vec,
        a_n_vec,
        _r_d_vec,
        g0_vec,
        _g_w_vec,
        g_c_vec,
        lambda_wue_vec,
        d_g0_d_e_vec,
        _d_g0_d_g_c_vec,
        psi_s_vec,
        psi_rc_vec,
        t_l_vec,
        vpd_vec,
        _r_abs,
        *_rest,
    ) = rad_hydr_grow_temp_cassimilation(e_vec, inputs=inputs)

    alpha_l = inputs.alpha_l
    beta_l = inputs.beta_l
    k_l = inputs.k_l

    log_arg_l = (
        np.exp(-alpha_l * beta_l)
        + np.exp(-alpha_l * psi_s_vec)
        - np.exp(-alpha_l * psi_s_vec + alpha_l * e_vec / k_l)
    )
    psi_l_complex = (
        psi_s_vec
        - e_vec / k_l
        + beta_l
        + (1 / alpha_l) * np.log(log_arg_l.astype(complex))
    )
    psi_l_vec = np.real(psi_l_complex)
    psi_l_vec[np.abs(np.imag(psi_l_complex)) > 0] = -np.inf

    (
        _a_n,
        _e,
        _lambda_wue,
        _g0,
        _g_c,
        _psi_s,
        _psi_rc,
        _eta_ss_vec,
        _lambda_ss_vec,
        _c_nsc_ss,
        _r_m_0,
        _vpd,
        _eta_ss,
        c_nsc_ss_vec,
    ) = steady_state_nsc_and_cue(
        inputs=inputs,
        lambda_wue_vec=lambda_wue_vec,
        g0_vec=g0_vec,
        d_g0_d_e_vec=d_g0_d_e_vec,
        a_n_vec=a_n_vec,
        e_vec=e_vec,
        g_c_vec=g_c_vec,
        vpd_vec=vpd_vec,
        psi_s_vec=psi_s_vec,
        psi_rc_vec=psi_rc_vec,
    )

    g_vec = g0_vec * inputs.theta_g(c_nsc_ss_vec)

    n_points = e_vec.size
    empty = np.empty((0, 0), dtype=float)
    y_plot_data = np.empty((4, 2), dtype=object)
    y_plot_data[0, 0] = np.vstack((1e6 * g0_vec, 1e6 * g_vec))
    y_plot_data[0, 1] = c_nsc_ss_vec.reshape(1, n_points)
    y_plot_data[1, 0] = np.vstack((1e6 * a_n_vec, 1e3 * e_vec))
    y_plot_data[1, 1] = empty
    y_plot_data[2, 0] = t_l_vec.reshape(1, n_points)
    y_plot_data[2, 1] = vpd_vec.reshape(1, n_points)
    y_plot_data[3, 0] = np.vstack((-psi_l_vec, -psi_s_vec, -psi_rc_vec))
    y_plot_data[3, 1] = empty

    return y_plot_data, g_c_vec.reshape(1, n_points)
