from __future__ import annotations

import warnings

import numpy as np
import pytest

from stomatal_optimiaztion.domains.gosm.model import (
    rad_hydr_grow_temp_cassimilation,
    solve_mult_phi_given_assumed_nsc,
)
from stomatal_optimiaztion.domains.gosm.params import BaselineInputs


def _matlab_runtime_kwargs() -> dict[str, object]:
    inputs = BaselineInputs.matlab_default()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        runtime = rad_hydr_grow_temp_cassimilation(np.arange(0.0, 1e-2 + 1e-5, 1e-5), inputs=inputs)
    return {
        "inputs": inputs,
        "lambda_wue_vec": runtime[6],
        "g0_vec": runtime[3],
        "d_g0_d_e_vec": runtime[7],
        "a_n_vec": runtime[1],
        "e_vec": runtime[0],
        "g_c_vec": runtime[5],
        "vpd_vec": runtime[12],
        "psi_s_vec": runtime[9],
        "psi_rc_vec": runtime[10],
        "runtime": runtime,
    }


def test_gosm_steady_state_inversion_matches_matlab_style_search_contract() -> None:
    kwargs = _matlab_runtime_kwargs()
    inputs = kwargs["inputs"]
    runtime = kwargs["runtime"]
    assert isinstance(inputs, BaselineInputs)

    r_m_0 = float(inputs.r_m_w(inputs.t_a) * inputs.c_w + inputs.r_m_r(inputs.t_a) * inputs.c_r)
    c_nsc_assumed = 10.0
    r_m_known = float(inputs.theta_r(c_nsc_assumed) * r_m_0 * 0.2)
    g_known = float(inputs.theta_g(c_nsc_assumed) * runtime[3][1])

    result = solve_mult_phi_given_assumed_nsc(
        c_nsc_assumed=c_nsc_assumed,
        r_m_known=r_m_known,
        g_known=g_known,
        inputs=inputs,
        lambda_wue_vec=kwargs["lambda_wue_vec"],
        g0_vec=kwargs["g0_vec"],
        d_g0_d_e_vec=kwargs["d_g0_d_e_vec"],
        a_n_vec=kwargs["a_n_vec"],
        e_vec=kwargs["e_vec"],
        g_c_vec=kwargs["g_c_vec"],
        vpd_vec=kwargs["vpd_vec"],
        psi_s_vec=kwargs["psi_s_vec"],
        psi_rc_vec=kwargs["psi_rc_vec"],
    )

    mult_phi, c_nsc_ss, lambda_wue_ss, r_m_0_ss, g0_ss, g_c_ss = result
    g0_known = g_known / float(inputs.theta_g(c_nsc_assumed))

    assert np.isclose(mult_phi, 1.3024051167253685)
    assert np.isclose(c_nsc_ss, 6.820664740395695)
    assert np.isclose(lambda_wue_ss, 0.0031420392910766377)
    assert np.isclose(r_m_0_ss, 0.0021977025448791567)
    assert np.isclose(g0_ss, g0_known, rtol=3e-3)
    assert np.isclose(g_c_ss, 0.04147523901449758)


def test_gosm_steady_state_inversion_rejects_nonpositive_known_terms() -> None:
    kwargs = _matlab_runtime_kwargs()
    inputs = kwargs["inputs"]
    assert isinstance(inputs, BaselineInputs)

    with pytest.raises(ValueError, match="r_m_known must be > 0"):
        solve_mult_phi_given_assumed_nsc(
            c_nsc_assumed=10.0,
            r_m_known=0.0,
            g_known=1e-6,
            inputs=inputs,
            lambda_wue_vec=kwargs["lambda_wue_vec"],
            g0_vec=kwargs["g0_vec"],
            d_g0_d_e_vec=kwargs["d_g0_d_e_vec"],
            a_n_vec=kwargs["a_n_vec"],
            e_vec=kwargs["e_vec"],
            g_c_vec=kwargs["g_c_vec"],
            vpd_vec=kwargs["vpd_vec"],
            psi_s_vec=kwargs["psi_s_vec"],
            psi_rc_vec=kwargs["psi_rc_vec"],
        )

    with pytest.raises(ValueError, match="g_known must be > 0"):
        solve_mult_phi_given_assumed_nsc(
            c_nsc_assumed=10.0,
            r_m_known=1e-6,
            g_known=0.0,
            inputs=inputs,
            lambda_wue_vec=kwargs["lambda_wue_vec"],
            g0_vec=kwargs["g0_vec"],
            d_g0_d_e_vec=kwargs["d_g0_d_e_vec"],
            a_n_vec=kwargs["a_n_vec"],
            e_vec=kwargs["e_vec"],
            g_c_vec=kwargs["g_c_vec"],
            vpd_vec=kwargs["vpd_vec"],
            psi_s_vec=kwargs["psi_s_vec"],
            psi_rc_vec=kwargs["psi_rc_vec"],
        )
