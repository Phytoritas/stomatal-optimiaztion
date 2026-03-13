from __future__ import annotations

from pathlib import Path
import warnings

import numpy as np
import pytest
import scipy.io

from stomatal_optimiaztion.domains.gosm.examples import (
    DEFAULT_LEGACY_GOSM_EXAMPLE_DIR,
    run_sensitivity_environmental_conditions,
)


def _matlab_str(x: object) -> str:
    arr = np.asarray(x)
    if arr.shape == ():
        return str(arr)
    if arr.size == 1:
        return str(arr.reshape(()))
    return str(arr.squeeze())


def _matlab_cell_str(x: object) -> str:
    if isinstance(x, str):
        return x
    if isinstance(x, np.ndarray):
        if x.shape == ():
            return str(x)
        if x.size == 1:
            return _matlab_cell_str(x.flat[0])
        return str(x)
    return str(x)


def _legend_list(cell: np.ndarray) -> list[str]:
    cell = np.asarray(cell)
    assert cell.dtype == object
    assert cell.ndim == 2
    assert cell.shape[1] == 1
    return [_matlab_cell_str(cell[i, 0]) for i in range(cell.shape[0])]


@pytest.mark.parametrize(
    "baseline_path",
    [
        DEFAULT_LEGACY_GOSM_EXAMPLE_DIR / "Growth_Opt_Stomata__test_sensitivity__RH.mat",
        DEFAULT_LEGACY_GOSM_EXAMPLE_DIR / "Growth_Opt_Stomata__test_sensitivity__c_a.mat",
        DEFAULT_LEGACY_GOSM_EXAMPLE_DIR / "Growth_Opt_Stomata__test_sensitivity__P_soil.mat",
    ],
    ids=lambda p: p.stem,
)
@pytest.mark.skipif(not DEFAULT_LEGACY_GOSM_EXAMPLE_DIR.exists(), reason="legacy GOSM example dir not available")
def test_sensitivity_environmental_conditions_matches_matlab_baseline(baseline_path: Path) -> None:
    mat = scipy.io.loadmat(str(baseline_path))
    param = _matlab_str(mat["PARAM"]).strip()

    with warnings.catch_warnings():
        warnings.simplefilter("error", RuntimeWarning)
        out = run_sensitivity_environmental_conditions(param=param, param_test=mat["PARAM_TEST"], eta_test=mat["eta_test"])

    assert _matlab_str(out["PARAM"]) == _matlab_str(mat["PARAM"])
    assert _legend_list(out["study_legend"]) == _legend_list(mat["study_legend"])

    atol = 1e-6
    rtol = 0.0

    for key, value in mat.items():
        if key.startswith("__"):
            continue
        if key in ("PARAM", "study_legend"):
            continue
        assert key in out, f"Missing key in Python output: {key}"

        a = np.asarray(value)
        b = np.asarray(out[key])
        if a.size == 0 and b.size == 0:
            continue
        assert a.shape == b.shape
        np.testing.assert_allclose(b, a, atol=atol, rtol=rtol, equal_nan=True)
