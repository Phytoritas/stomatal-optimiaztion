from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from stomatal_optimiaztion.domains.tdgm.examples.adapter import (
    DEFAULT_LEGACY_TDGM_THORP_G_DIR,
)
from stomatal_optimiaztion.domains.tdgm.thorp_g import default_params, load_mat, run


def _as_1d(x: object) -> np.ndarray:
    return np.asarray(x).reshape(-1)


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
