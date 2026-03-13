from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True, slots=True)
class RadiationResult:
    r_abs: float
    r_soil: float
    d_r_abs_dh: float
    d_r_abs_dw: float
    d_r_abs_dla: float


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
    """Radiation model shared by THORP/THORP-G."""

    z_a = float(np.clip(z_a, -np.pi / 2, np.pi / 2))
    sec_z = 1.0 / float(np.cos(z_a)) if np.cos(z_a) != 0 else float("inf")

    dh = max(0.0, h_n - h)
    r_abs = (r_incom * w**2 / la) * np.cos(z_a) * np.exp(-kappa_n * dh * sec_z) * (
        1 - np.exp(-kappa_l * la / w**2 / phi * sec_z)
    )

    r_abs_upper_canopy = r_incom * np.cos(z_a) * np.exp(-kappa_n * dh * sec_z)
    r_soil = r_abs_upper_canopy * np.exp(-kappa_l * la / w**2 / phi * sec_z)

    if r_abs < 0:
        raise ValueError("NEGATIVE LEAF-ABSORBED RADIATION")
    if r_soil < 0:
        raise ValueError("NEGATIVE SOIL-ABSORBED RADIATION")

    d_r_abs_dh = float(kappa_n * r_abs * sec_z)
    if dh == 0:
        d_r_abs_dh = 0.0

    common = r_incom * kappa_l / phi * np.exp(-(kappa_n * dh + kappa_l * la / w**2 / phi) * sec_z)
    d_r_abs_dw = float(2.0 / w * (r_abs - common))
    d_r_abs_dla = float(-1.0 / la * (r_abs - common))

    return RadiationResult(
        r_abs=float(r_abs),
        r_soil=float(r_soil),
        d_r_abs_dh=d_r_abs_dh,
        d_r_abs_dw=d_r_abs_dw,
        d_r_abs_dla=d_r_abs_dla,
    )

