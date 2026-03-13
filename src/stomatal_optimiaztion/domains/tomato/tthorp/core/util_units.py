from __future__ import annotations

import math

PAR_UMOL_PER_WM2 = 4.6
PAR_UMOL_PER_W_M2 = PAR_UMOL_PER_WM2


def _validate_factor(par_umol_per_w_m2: float) -> float:
    factor = float(par_umol_per_w_m2)
    if not math.isfinite(factor) or factor <= 0:
        raise ValueError(f"par_umol_per_w_m2 must be a positive finite value, got {par_umol_per_w_m2!r}.")
    return factor


def par_umol_to_w_m2(
    par_umol: float,
    *,
    par_umol_per_w_m2: float = PAR_UMOL_PER_WM2,
) -> float:
    factor = _validate_factor(par_umol_per_w_m2)
    return float(par_umol) / factor


def w_m2_to_par_umol(
    w_m2: float,
    *,
    par_umol_per_w_m2: float = PAR_UMOL_PER_WM2,
) -> float:
    factor = _validate_factor(par_umol_per_w_m2)
    return float(w_m2) * factor


__all__ = [
    "PAR_UMOL_PER_WM2",
    "PAR_UMOL_PER_W_M2",
    "par_umol_to_w_m2",
    "w_m2_to_par_umol",
]
