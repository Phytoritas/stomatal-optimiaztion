from __future__ import annotations

import numpy as np
import pytest

from stomatal_optimiaztion.domains.thorp.examples.adapter import (
    DEFAULT_LEGACY_THORP_SUPPORT_DIR,
)
from stomatal_optimiaztion.domains.thorp.matlab_io import load_mat
from stomatal_optimiaztion.domains.thorp.simulation import run

MATLAB_0_6RH_PATH = DEFAULT_LEGACY_THORP_SUPPORT_DIR / "THORP_data_0.6RH.mat"


def _as_1d(x: object) -> np.ndarray:
    return np.asarray(x).reshape(-1)


@pytest.mark.skipif(not MATLAB_0_6RH_PATH.exists(), reason="legacy THORP 0.6RH MAT not available")
def test_regression_matches_matlab_first_2_weeks() -> None:
    out = run(max_steps=60)
    m = load_mat(MATLAB_0_6RH_PATH)

    expected_t = _as_1d(m["t_stor"])[:3]
    assert np.array_equal(out.t_ts, expected_t)

    py = out.as_mat_dict()
    for key in [
        "c_l_stor",
        "c_sw_stor",
        "c_hw_stor",
        "c_NSC_stor",
        "D_stor",
        "H_stor",
        "W_stor",
        "P_x_l_stor",
        "P_x_s_stor",
        "P_x_r_stor",
        "P_x_r0_stor",
        "R_abs_stor",
        "E_stor",
        "A_n_stor",
        "R_d_stor",
        "R_m_stor",
        "U_stor",
    ]:
        assert np.allclose(_as_1d(py[key])[:3], _as_1d(m[key])[:3], rtol=0, atol=1e-12), key

    for key in ["c_r_H_stor", "c_r_V_stor", "P_soil_stor"]:
        assert np.allclose(np.asarray(py[key])[:, :3], np.asarray(m[key])[:, :3], rtol=0, atol=1e-12), key
