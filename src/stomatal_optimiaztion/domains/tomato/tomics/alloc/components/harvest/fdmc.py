from __future__ import annotations

import math


def fdmc_constant_mean(value: float) -> float:
    return max(float(value), 1e-6)


def fdmc_dekoning_fds(fds: float, fdmc0: float = 10.2, fdmc1: float = 5.3) -> float:
    fds_value = max(float(fds), 0.0)
    out = fdmc0 + (fdmc1 - fdmc0) * 2.0 * fds_value + (fdmc0 - fdmc1) * (fds_value**2)
    return max(out, 1e-6)


def fdmc_dekoning_harvest(dayno: float, ec: float, tf: float, r_fdmc: float = 1.0) -> float:
    seasonal = 5.39 - 0.743 * math.cos(2.0 * math.pi * (float(dayno) - 16.0) / 365.0)
    value = float(r_fdmc) * (seasonal + 1.7 * (float(ec) - 0.3) + 0.07 * (float(tf) - 23.0))
    return max(value, 1e-6)


def fdmc_family_dispatch(
    mode: str,
    *,
    fds: float | None = None,
    dayno: float | None = None,
    ec: float = 0.3,
    tf: float = 23.0,
    r_fdmc: float = 1.0,
    constant_value: float = 6.5,
) -> float:
    key = str(mode).strip().lower()
    if key in {"constant_observed_mean", "constant_mean"}:
        return fdmc_constant_mean(constant_value)
    if key in {"dekoning_fds", "fds"}:
        return fdmc_dekoning_fds(0.0 if fds is None else fds)
    if key in {"dekoning_harvest_temp_ec", "dekoning_fds_temp_ec", "dekoning_harvest"}:
        return fdmc_dekoning_harvest(1.0 if dayno is None else dayno, ec=ec, tf=tf, r_fdmc=r_fdmc)
    raise KeyError(f"Unsupported FDMC mode: {mode!r}")


__all__ = [
    "fdmc_constant_mean",
    "fdmc_dekoning_fds",
    "fdmc_dekoning_harvest",
    "fdmc_family_dispatch",
]
