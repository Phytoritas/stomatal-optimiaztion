from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from stomatal_optimiaztion.domains.tdgm.implements import implements


@dataclass(frozen=True, slots=True)
class ThorpGCouplingStepInputs:
    """Inputs needed for the C005 THORP-G coupling primitives."""

    c_nsc: float
    c_p: float
    g_potential: float
    u_mod_t: float

    c_w: float
    c_r: float
    c_l: float

    rho_c_s: float
    rho_c_l: float

    c_mm: float
    alpha: float = 1.0 / 12.0


@dataclass(frozen=True, slots=True)
class ThorpGCouplingStepOutputs:
    tree_volume: float
    c_nsc_mobile: float
    c_nsc_immobile: float
    k_mm: float
    theta_g: float
    g_rate: float


def compute_thorp_g_coupling_step(*, inputs: ThorpGCouplingStepInputs) -> ThorpGCouplingStepOutputs:
    """Compute the C005 coupling terms once PTM and turgor terms are available."""

    tree_volume = float(
        tree_volume_from_carbon_pools(
            c_w=inputs.c_w,
            c_r=inputs.c_r,
            c_l=inputs.c_l,
            rho_c_s=inputs.rho_c_s,
            rho_c_l=inputs.rho_c_l,
        ).reshape(())
    )

    c_nsc_mobile = float(
        mobile_nsc_from_phloem_concentration(
            c_p=inputs.c_p,
            tree_volume=tree_volume,
            alpha=inputs.alpha,
        ).reshape(())
    )

    c_nsc_immobile = float(
        immobile_nsc_from_total(c_nsc=inputs.c_nsc, c_nsc_mobile=c_nsc_mobile).reshape(())
    )

    k_mm = float(
        michaelis_menten_coefficient_nsc(
            c_mm=inputs.c_mm,
            tree_volume=tree_volume,
            alpha=inputs.alpha,
        ).reshape(())
    )

    theta_g = float(nsc_limitation_growth(c_nsc_immobile=c_nsc_immobile, k_mm=k_mm).reshape(()))
    g_rate = float(
        realized_growth_rate(
            g_potential=inputs.g_potential,
            u_mod_t=inputs.u_mod_t,
            theta_g=theta_g,
        ).reshape(())
    )

    return ThorpGCouplingStepOutputs(
        tree_volume=tree_volume,
        c_nsc_mobile=c_nsc_mobile,
        c_nsc_immobile=c_nsc_immobile,
        k_mm=k_mm,
        theta_g=theta_g,
        g_rate=g_rate,
    )


@implements("Eq.S.3.3")
def tree_volume_from_carbon_pools(
    *,
    c_w: np.ndarray | float,
    c_r: np.ndarray | float,
    c_l: np.ndarray | float,
    rho_c_s: float,
    rho_c_l: float,
) -> np.ndarray:
    """Estimate total tree volume from carbon pools."""

    c_w = np.asarray(c_w, dtype=float)
    c_r = np.asarray(c_r, dtype=float)
    c_l = np.asarray(c_l, dtype=float)

    tree_volume = (c_w + c_r) / float(rho_c_s) + c_l / float(rho_c_l)
    return np.asarray(tree_volume, dtype=float)


@implements("Eq.S.3.2")
def mobile_nsc_from_phloem_concentration(
    *,
    c_p: np.ndarray | float,
    tree_volume: np.ndarray | float,
    alpha: float = 1.0 / 12.0,
) -> np.ndarray:
    """Estimate mobile NSC pool from phloem sugar concentration."""

    c_p = np.asarray(c_p, dtype=float)
    tree_volume = np.asarray(tree_volume, dtype=float)

    c_nsc_mobile = (c_p / float(alpha)) * tree_volume
    return np.asarray(c_nsc_mobile, dtype=float)


@implements("Eq.S.3.1")
def immobile_nsc_from_total(
    *,
    c_nsc: np.ndarray | float,
    c_nsc_mobile: np.ndarray | float,
) -> np.ndarray:
    """Compute immobile NSC pool C_S - C_S,M."""

    c_nsc = np.asarray(c_nsc, dtype=float)
    c_nsc_mobile = np.asarray(c_nsc_mobile, dtype=float)
    c_nsc_immobile = c_nsc - c_nsc_mobile
    return np.asarray(c_nsc_immobile, dtype=float)


@implements("Eq.S.3.6")
def michaelis_menten_coefficient_nsc(
    *,
    c_mm: np.ndarray | float,
    tree_volume: np.ndarray | float,
    alpha: float = 1.0 / 12.0,
) -> np.ndarray:
    """Size-dependent Michaelis-Menten coefficient."""

    c_mm = np.asarray(c_mm, dtype=float)
    tree_volume = np.asarray(tree_volume, dtype=float)

    k_mm = (c_mm / float(alpha)) * tree_volume
    return np.asarray(k_mm, dtype=float)


@implements("Eq.S.3.5")
def nsc_limitation_growth(
    *,
    c_nsc_immobile: np.ndarray | float,
    k_mm: np.ndarray | float,
) -> np.ndarray:
    """Michaelis-Menten limitation factor g_NSC."""

    c_nsc_immobile = np.asarray(c_nsc_immobile, dtype=float)
    k_mm = np.asarray(k_mm, dtype=float)

    with np.errstate(divide="ignore", invalid="ignore"):
        theta_g = c_nsc_immobile / (c_nsc_immobile + k_mm)
    return np.asarray(theta_g, dtype=float)


@implements("Eq.S.3.4")
def realized_growth_rate(
    *,
    g_potential: np.ndarray | float,
    u_mod_t: np.ndarray | float,
    theta_g: np.ndarray | float,
) -> np.ndarray:
    """Realized growth G = g_T * g_NSC * G'."""

    g_potential = np.asarray(g_potential, dtype=float)
    u_mod_t = np.asarray(u_mod_t, dtype=float)
    theta_g = np.asarray(theta_g, dtype=float)

    g_rate = u_mod_t * theta_g * g_potential
    return np.asarray(g_rate, dtype=float)


@implements("Eq.S.3.8")
def allocation_fraction_derivative(
    *,
    u_i: np.ndarray | float,
    v_i: np.ndarray | float,
    upsilon: float = 3.8e-6,
) -> np.ndarray:
    """ODE form of the allocation smoothing filter."""

    u_i = np.asarray(u_i, dtype=float)
    v_i = np.asarray(v_i, dtype=float)
    du_dt = float(upsilon) * (v_i - u_i)
    return np.asarray(du_dt, dtype=float)


def initial_mean_allocation_fractions(
    *,
    c_r_h: np.ndarray | float,
    c_r_v: np.ndarray | float,
) -> tuple[float, float, np.ndarray, np.ndarray]:
    """Initialize THORP-G mean allocation fractions from root biomass pools."""

    c_r_h = np.asarray(c_r_h, dtype=float)
    c_r_v = np.asarray(c_r_v, dtype=float)
    if c_r_h.ndim != 1 or c_r_v.ndim != 1:
        raise ValueError("c_r_h and c_r_v must be 1D arrays")

    total_root = float(np.sum(c_r_h + c_r_v))
    if total_root <= 0:
        raise ValueError("Root carbon pools must sum to a positive value")
    sum_c_r_h = float(np.sum(c_r_h))
    sum_c_r_v = float(np.sum(c_r_v))
    if sum_c_r_h <= 0 or sum_c_r_v <= 0:
        raise ValueError("Horizontal and vertical root pools must both sum to a positive value")

    u_sw_mean = 0.3
    u_l_mean = 0.3
    u_r_mean = 0.4

    u_r_h_mean_total = u_r_mean * sum_c_r_h / total_root
    u_r_v_mean_total = u_r_mean - u_r_h_mean_total

    u_r_h_mean = u_r_h_mean_total * c_r_h / sum_c_r_h
    u_r_v_mean = u_r_v_mean_total * c_r_v / sum_c_r_v

    return (
        float(u_sw_mean),
        float(u_l_mean),
        np.asarray(u_r_h_mean, dtype=float),
        np.asarray(u_r_v_mean, dtype=float),
    )


@implements("Eq.S.3.7")
def update_mean_allocation_fractions(
    *,
    u_l_mean: float,
    u_l: float,
    u_r_h_mean: np.ndarray,
    u_r_h: np.ndarray,
    u_r_v_mean: np.ndarray,
    u_r_v: np.ndarray,
    u_sw_mean: float,
    u_sw: float,
    dt_allocate: float,
) -> tuple[float, float, np.ndarray, np.ndarray]:
    """Update THORP-G memory-filtered mean allocation fractions."""

    t_mem = 14 * 24 * 3600.0
    k_mem = -float(np.log(0.01)) / t_mem

    u_r_h_mean = np.asarray(u_r_h_mean, dtype=float)
    u_r_v_mean = np.asarray(u_r_v_mean, dtype=float)
    u_r_h = np.asarray(u_r_h, dtype=float)
    u_r_v = np.asarray(u_r_v, dtype=float)

    nan_count = int(
        np.isnan(u_l)
        + np.isnan(u_sw)
        + np.sum(np.isnan(u_r_h)).item()
        + np.sum(np.isnan(u_r_v)).item()
    )
    if nan_count != 0:
        return float(u_l_mean), float(u_sw_mean), u_r_h_mean, u_r_v_mean

    u_l_mean = float(u_l_mean + k_mem * (float(u_l) - float(u_l_mean)) * dt_allocate)
    u_sw_mean = float(u_sw_mean + k_mem * (float(u_sw) - float(u_sw_mean)) * dt_allocate)
    u_r_h_mean = (u_r_h_mean + k_mem * (u_r_h - u_r_h_mean) * dt_allocate).astype(float)
    u_r_v_mean = (u_r_v_mean + k_mem * (u_r_v - u_r_v_mean) * dt_allocate).astype(float)

    sum_u_mean = float(np.sum(u_r_h_mean + u_r_v_mean) + u_l_mean + u_sw_mean)
    u_l_mean = float(u_l_mean / sum_u_mean)
    u_sw_mean = float(u_sw_mean / sum_u_mean)
    u_r_h_mean = (u_r_h_mean / sum_u_mean).astype(float)
    u_r_v_mean = (u_r_v_mean / sum_u_mean).astype(float)
    return float(u_l_mean), float(u_sw_mean), u_r_h_mean, u_r_v_mean


@implements("Eq.S.3.7")
def allocation_fraction_from_history(
    *,
    v_i_ts: np.ndarray,
    dt_s: float,
    u_i0: float | None = None,
    upsilon: float = 3.8e-6,
) -> np.ndarray:
    """Discrete-time realization of the allocation-history filter."""

    v_i_ts = np.asarray(v_i_ts, dtype=float)
    if v_i_ts.ndim != 1:
        raise ValueError("v_i_ts must be a 1D time series.")

    dt_s = float(dt_s)
    if dt_s <= 0:
        raise ValueError("dt_s must be > 0.")

    u_i_ts = np.empty_like(v_i_ts, dtype=float)
    u_i_ts[0] = float(v_i_ts[0]) if u_i0 is None else float(u_i0)

    decay = float(np.exp(-float(upsilon) * dt_s))
    gain = 1.0 - decay
    for step_idx in range(1, v_i_ts.size):
        u_i_ts[step_idx] = decay * u_i_ts[step_idx - 1] + gain * v_i_ts[step_idx]
    return u_i_ts
