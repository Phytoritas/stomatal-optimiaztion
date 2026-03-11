from __future__ import annotations

import math
from dataclasses import dataclass

from stomatal_optimiaztion.domains.thorp.implements import implements


@dataclass(frozen=True, slots=True)
class RadiationResult:
    r_abs: float
    r_soil: float
    d_r_abs_dh: float
    d_r_abs_dw: float
    d_r_abs_dla: float


@implements("E_S5_1", "E_S5_2", "E_S5_3", "E_S5_4", "E_S5_5")
def radiation(
    *,
    r_incom: float,
    z_a: float,
    la: float,
    w: float,
    h: float,
    h_n: float,
    kappa_l: float,
    kappa_n: float,
    phi: float,
) -> RadiationResult:
    """Compute absorbed leaf and soil radiation for the THORP canopy seam."""

    z_a = max(-math.pi / 2, min(math.pi / 2, float(z_a)))
    cos_z = math.cos(z_a)
    sec_z = 1.0 / cos_z if cos_z != 0.0 else float("inf")

    dh = max(0.0, h_n - h)
    r_abs = (r_incom * w**2 / la) * cos_z * math.exp(-kappa_n * dh * sec_z) * (
        1 - math.exp(-kappa_l * la / w**2 / phi * sec_z)
    )

    r_abs_upper_canopy = r_incom * cos_z * math.exp(-kappa_n * dh * sec_z)
    r_soil = r_abs_upper_canopy * math.exp(-kappa_l * la / w**2 / phi * sec_z)

    if r_abs < 0:
        raise ValueError("NEGATIVE LEAF-ABSORBED RADIATION")
    if r_soil < 0:
        raise ValueError("NEGATIVE SOIL-ABSORBED RADIATION")

    d_r_abs_dh = kappa_n * r_abs * sec_z
    if dh == 0:
        d_r_abs_dh = 0.0

    common = r_incom * kappa_l / phi * math.exp(
        -(kappa_n * dh + kappa_l * la / w**2 / phi) * sec_z
    )
    d_r_abs_dw = 2.0 / w * (r_abs - common)
    d_r_abs_dla = -1.0 / la * (r_abs - common)

    return RadiationResult(
        r_abs=float(r_abs),
        r_soil=float(r_soil),
        d_r_abs_dh=float(d_r_abs_dh),
        d_r_abs_dw=float(d_r_abs_dw),
        d_r_abs_dla=float(d_r_abs_dla),
    )
