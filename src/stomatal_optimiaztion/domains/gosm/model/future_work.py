from __future__ import annotations

import numpy as np

from stomatal_optimiaztion.domains.gosm.utils.traceability import implements


@implements("Eq.S10.1")
def growth_from_turgor_profile(
    *,
    p_turgor: np.ndarray,
    z_norm: np.ndarray | None = None,
    phi_tilde: float,
    c_w: float,
    u_s: float,
    p_turgor_crit: float | None = None,
    Gamma: float | None = None,  # noqa: N803 - legacy alias
) -> float:
    """Compute a future-work growth integral directly from a turgor profile."""

    if p_turgor_crit is None:
        p_turgor_crit = Gamma
    if p_turgor_crit is None:
        raise TypeError("Missing required argument: p_turgor_crit")

    p_turgor = np.asarray(p_turgor, dtype=float)
    if z_norm is None:
        z_norm = np.linspace(0.0, 1.0, p_turgor.size, dtype=float)
    else:
        z_norm = np.asarray(z_norm, dtype=float)
        if z_norm.shape != p_turgor.shape:
            raise ValueError("z_norm must have the same shape as p_turgor")

    integrand = np.maximum(p_turgor - float(p_turgor_crit), 0.0)
    return float(phi_tilde * (c_w / u_s) * np.trapezoid(integrand, z_norm))


@implements("Eq.S10.2")
def augmented_lagrangian(
    *,
    G: float,
    etas: np.ndarray,
    X_dot: np.ndarray,
    F: np.ndarray,
) -> float:
    """Compute the multi-pool augmented Lagrangian future-work helper."""

    etas = np.asarray(etas, dtype=float)
    X_dot = np.asarray(X_dot, dtype=float)
    F = np.asarray(F, dtype=float)
    if etas.shape != X_dot.shape or etas.shape != F.shape:
        raise ValueError("etas, X_dot, and F must have the same shape")
    return float(G - np.sum(etas * (X_dot - F)))
