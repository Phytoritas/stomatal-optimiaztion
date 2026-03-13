from __future__ import annotations

import numpy as np

from stomatal_optimiaztion.domains.gosm import implemented_equations
from stomatal_optimiaztion.domains.gosm.model import rad_hydr_grow_temp_cassimilation
from stomatal_optimiaztion.domains.gosm.params import BaselineInputs


def test_gosm_pipeline_has_stage_equation_tags() -> None:
    assert implemented_equations(rad_hydr_grow_temp_cassimilation) == ("S3", "S4", "S5", "S6")


def test_gosm_pipeline_matches_baseline_snapshot() -> None:
    inputs = BaselineInputs.matlab_default()
    result = rad_hydr_grow_temp_cassimilation(np.array([1e-5, 2e-5]), inputs=inputs)

    (
        e_vec,
        a_n_vec,
        r_d_vec,
        g0_vec,
        g_w_vec,
        g_c_vec,
        lambda_wue_vec,
        d_g0_d_e_vec,
        d_g0_d_g_c_vec,
        psi_s_vec,
        psi_rc_vec,
        t_l_vec,
        vpd_vec,
        r_abs,
        inf_nsc_turgor_ave_vec,
        z_norm_plus_vec,
        turgor_turgid,
    ) = result

    assert np.allclose(e_vec, np.array([1.0e-5, 2.0e-5]))
    assert np.allclose(a_n_vec, np.array([2.04636045e-07, 4.07289305e-07]))
    assert np.allclose(r_d_vec, np.array([1.07655023e-06, 1.07611806e-06]))
    assert np.allclose(g0_vec, np.array([6.75484201e-05, 6.73209135e-05]))
    assert np.allclose(g_w_vec, np.array([9.03350000e-04, 1.80876000e-03]))
    assert np.allclose(g_c_vec, np.array([5.64410000e-04, 1.12975000e-03]))
    assert np.allclose(lambda_wue_vec, np.array([0.02036628, 0.02016294]))
    assert np.allclose(d_g0_d_e_vec, np.array([-0.02274908, -0.02275223]))
    assert np.allclose(d_g0_d_g_c_vec, np.array([-0.00040273, -0.00040213]))
    assert np.allclose(psi_s_vec, np.array([-0.16915447, -0.17187300]))
    assert np.allclose(psi_rc_vec, np.array([-0.03154853, -0.03372630]))
    assert np.allclose(t_l_vec, np.array([20.34864434, 20.34285155]))
    assert np.allclose(vpd_vec, np.array([1.12207713, 1.12122285]))
    assert np.isclose(r_abs, 81.40834442605605)
    assert np.allclose(inf_nsc_turgor_ave_vec, np.array([1.19450152, 1.19300441]))
    assert np.allclose(z_norm_plus_vec, np.array([0.0, 0.0]))
    assert np.isclose(turgor_turgid, 1.2358066082517578)
