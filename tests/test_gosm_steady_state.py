from __future__ import annotations

import warnings

import numpy as np
import pytest

from stomatal_optimiaztion.domains.gosm import implemented_equations
from stomatal_optimiaztion.domains.gosm.model import (
    rad_hydr_grow_temp_cassimilation,
    steady_state_nsc_and_cue,
)
from stomatal_optimiaztion.domains.gosm.params import BaselineInputs


def _baseline_runtime_kwargs() -> dict[str, object]:
    inputs = BaselineInputs.matlab_default()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        runtime = rad_hydr_grow_temp_cassimilation(np.linspace(0.0, 4e-4, 9), inputs=inputs)
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
    }


def test_gosm_steady_state_has_equation_tags() -> None:
    assert implemented_equations(steady_state_nsc_and_cue) == ("Eq.S1.9", "Eq.S2.4b")


def test_gosm_steady_state_preserves_no_crossing_runtime_contract() -> None:
    result = steady_state_nsc_and_cue(**_baseline_runtime_kwargs())

    assert np.isnan(result[0])
    assert np.isnan(result[1])
    assert np.isnan(result[2])
    assert np.isclose(result[10], 5.0047343076847656e-05)
    assert np.allclose(
        result[7],
        np.array([0.52794774, 0.52205779, 0.51611781, 0.51018135, 0.50430263, 0.49852955, 0.49289267, 0.48740731, 0.48206544]),
    )
    assert np.allclose(
        result[8],
        np.array([0.0, 9.43957397e-05, 1.92799458e-04, 2.93756748e-04, 3.95580411e-04, 4.96555358e-04, 5.95322784e-04, 6.90894359e-04, 7.83007482e-04]),
    )


def test_gosm_steady_state_quadratic_nsc_matches_newton_branch() -> None:
    kwargs = _baseline_runtime_kwargs()
    newton = steady_state_nsc_and_cue(**kwargs)
    quadratic = steady_state_nsc_and_cue(use_quadratic_nsc=True, **kwargs)

    assert np.allclose(newton[7], quadratic[7], atol=2e-5)
    assert np.allclose(newton[8], quadratic[8], atol=1e-6)
    assert np.allclose(newton[13], quadratic[13], atol=8e-2)


def test_gosm_steady_state_requires_zero_conductance_anchor() -> None:
    inputs = BaselineInputs.matlab_default()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        with pytest.raises(RuntimeError, match="g_c == 0"):
            steady_state_nsc_and_cue(
                inputs=inputs,
                lambda_wue_vec=np.array([0.02, 0.01]),
                g0_vec=np.array([0.1, 0.2]),
                d_g0_d_e_vec=np.array([-0.1, -0.05]),
                a_n_vec=np.array([1.0, 2.0]),
                e_vec=np.array([0.1, 0.2]),
                g_c_vec=np.array([0.1, 0.2]),
                vpd_vec=np.array([1.0, 1.1]),
                psi_s_vec=np.array([-0.1, -0.2]),
                psi_rc_vec=np.array([-0.01, -0.02]),
            )
