from __future__ import annotations

import numpy as np

from stomatal_optimiaztion.domains.gosm.params.defaults import BaselineInputs
from stomatal_optimiaztion.domains.gosm.utils.traceability import implements


@implements("Eq.S1.4", "Eq.S1.8")
def sigma_nsc_limitation(*, c_nsc: float | np.ndarray, gamma: float, c_struct: float) -> np.ndarray:
    """NSC limitation function for growth or respiration."""

    c_nsc = np.asarray(c_nsc, dtype=float)
    return c_nsc / (c_nsc + float(gamma) * float(c_struct))


@implements("Eq.S1.5")
def maintenance_respiration_potential(*, inputs: BaselineInputs) -> float:
    """Potential stem and root maintenance respiration."""

    return float(inputs.r_m_w(inputs.t_a) * inputs.c_w + inputs.r_m_r(inputs.t_a) * inputs.c_r)


@implements("Eq.S1.3")
def maintenance_respiration(*, c_nsc: float, R_M_0: float, inputs: BaselineInputs) -> float:
    """Substrate-limited maintenance respiration."""

    return float(inputs.theta_r(c_nsc) * R_M_0)


@implements("Eq.S1.7")
def growth_rate(*, c_nsc: float, g0: float, inputs: BaselineInputs) -> float:
    """Whole-tree growth rate under NSC limitation."""

    return float(inputs.theta_g(c_nsc) * g0)


@implements("Eq.S1.6")
def growth_respiration(*, G: float, f_c: float) -> float:
    """Growth respiration."""

    return float(f_c / (1.0 - f_c) * G)


@implements("Eq.S1.2")
def total_respiration(*, a_L: float, R_d: float, R_M: float, R_G: float) -> float:
    """Whole-tree respiration."""

    return float(a_L * R_d + R_M + R_G)


@implements("Eq.S1.1")
def nsc_rate_of_change_full(*, a_L: float, a_n: float, R_d: float, G: float, R: float) -> float:
    """NSC storage rate of change using the explicit respiration partitioning form."""

    return float(a_L * (a_n + R_d) - G - R)


@implements("Eq.S1.9")
def nsc_rate_of_change(*, inputs: BaselineInputs, c_nsc: float, a_n: float, g0: float, R_M_0: float) -> float:
    """NSC storage rate of change using the compact form."""

    return float(inputs.la * a_n - inputs.theta_r(c_nsc) * R_M_0 - inputs.theta_g(c_nsc) * g0 / (1.0 - inputs.f_c))
