from __future__ import annotations

import numpy as np

from stomatal_optimiaztion.domains.gosm.utils.traceability import implements


@implements("Eq.S8.1")
def target_npp_gpp_ratio() -> float:
    """Target NPP:GPP ratio used for parameter estimation in the paper."""

    return 0.45


@implements("Eq.S8.2")
def steady_state_npp_gpp_ratio(*, G: float | np.ndarray, R_M: float | np.ndarray, f_c: float) -> np.ndarray:
    """Steady-state NPP:GPP definition used in the paper."""

    G = np.asarray(G, dtype=float)
    R_M = np.asarray(R_M, dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        return G / (R_M + G / (1.0 - f_c))
