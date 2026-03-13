from __future__ import annotations

import numpy as np

from stomatal_optimiaztion.domains.gosm.utils.traceability import implements


@implements("Eq.S2.1")
def objective_total_growth(*, G: np.ndarray, dt: float | np.ndarray) -> float:
    """Discrete approximation of the indefinite-horizon objective."""

    G = np.asarray(G, dtype=float)
    dt = np.asarray(dt, dtype=float)
    return float(np.sum(G * dt))


@implements("Eq.S2.2")
def lagrangian(*, G: float, C_dot: float, F_C: float, eta: float) -> float:
    """Augmented Lagrangian for the NSC constraint."""

    return float(G - eta * (C_dot - F_C))


@implements("Eq.S2.3")
def eta_from_marginals(*, dGdE: float | np.ndarray, lambda_wue: float | np.ndarray, a_L: float, f_c: float) -> np.ndarray:
    """Carbon-use efficiency from marginal terms."""

    dGdE = np.asarray(dGdE, dtype=float)
    lambda_wue = np.asarray(lambda_wue, dtype=float)
    num = (1.0 - f_c) * np.abs(dGdE)
    denom = np.abs(dGdE) + (1.0 - f_c) * float(a_L) * lambda_wue
    with np.errstate(divide="ignore", invalid="ignore"):
        out = num / denom
    return out


@implements("Eq.S2.4a")
def chi_w(*, eta: float, dGdE: float | np.ndarray, a_L: float, f_c: float) -> np.ndarray:
    """Marginal water cost for a given eta."""

    dGdE = np.asarray(dGdE, dtype=float)
    return (1.0 / (1.0 - f_c) - 1.0 / float(eta)) * dGdE / float(a_L)


@implements("Eq.S2.5")
def theta_cost(*, eta: float, G: float | np.ndarray, a_L: float, f_c: float) -> np.ndarray:
    """Hydraulic or marginal-cost objective term for reporting."""

    G = np.asarray(G, dtype=float)
    return (1.0 / (1.0 - f_c) - 1.0 / float(eta)) * G / float(a_L)


@implements("Eq.S2.6")
def eta_dot(*, eta: float, dR_MdC: float | np.ndarray, dGdC: float | np.ndarray, f_c: float) -> np.ndarray:
    """Time evolution of eta for the NSC state."""

    dR_MdC = np.asarray(dR_MdC, dtype=float)
    dGdC = np.asarray(dGdC, dtype=float)
    eta_ = float(eta)
    return eta_ * dR_MdC + (eta_ / (1.0 - f_c) - 1.0) * dGdC
