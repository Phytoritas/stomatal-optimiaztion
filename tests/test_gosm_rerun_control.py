from __future__ import annotations

import warnings

import numpy as np
import pytest
import scipy.io

from stomatal_optimiaztion.domains.gosm.examples import (
    DEFAULT_LEGACY_GOSM_EXAMPLE_DIR,
    run_control_plot_data,
)

LEGACY_CONTROL_PATH = DEFAULT_LEGACY_GOSM_EXAMPLE_DIR / "Example_Growth_Opt__control.mat"


@pytest.mark.skipif(not LEGACY_CONTROL_PATH.exists(), reason="legacy GOSM example MAT not available")
def test_example_control_matches_matlab_baseline() -> None:
    mat = scipy.io.loadmat(str(LEGACY_CONTROL_PATH))

    Y_mat = mat["Y_plot_data"]
    g_c_mat = mat["g_c_vect"]

    with warnings.catch_warnings():
        warnings.simplefilter("error", RuntimeWarning)
        Y_py, g_c_py = run_control_plot_data()

    atol = 1e-6
    rtol = 0.0

    np.testing.assert_allclose(g_c_py, g_c_mat, atol=atol, rtol=rtol, equal_nan=True)

    for i in range(4):
        for j in range(2):
            a = Y_mat[i, j]
            b = Y_py[i, j]
            if a.size == 0 and b.size == 0:
                continue
            assert a.shape == b.shape
            np.testing.assert_allclose(b, a, atol=atol, rtol=rtol, equal_nan=True)
