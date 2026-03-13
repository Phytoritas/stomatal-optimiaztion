from __future__ import annotations

import numpy as np

from stomatal_optimiaztion.domains.gosm.utils.traceability import implements


@implements("Eq.S3.2")
def radiation_absorbed(
    *,
    r_incom: float,
    z_a: float,
    la: float,
    w: float,
    kappa_l: float,
    phi_l: float,
) -> float:
    """Average leaf-area-specific absorbed radiation, matching MATLAB baseline.

    Baseline: `example/FUNCTION_Radiation.m`
    """

    # Clamp solar zenith angle to [-pi/2, pi/2]
    z_a = float(np.clip(z_a, -np.pi / 2, np.pi / 2))

    r_abs = (r_incom * w**2 / la) * np.cos(z_a) * (1 - np.exp(-kappa_l * la / w**2 / phi_l * (1 / np.cos(z_a))))

    if r_abs < 0:
        raise ValueError("NEGATIVE LEAF-ABSORBED RADIATION!!!")

    return float(r_abs)
