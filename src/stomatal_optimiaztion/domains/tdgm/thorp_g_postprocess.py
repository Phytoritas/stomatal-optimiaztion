from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from netCDF4 import Dataset
from numpy.typing import NDArray
from scipy.io import loadmat

from stomatal_optimiaztion.domains.tdgm.coupling import (
    immobile_nsc_from_total,
    michaelis_menten_coefficient_nsc,
    mobile_nsc_from_phloem_concentration,
    nsc_limitation_growth,
    realized_growth_rate,
    tree_volume_from_carbon_pools,
)


@dataclass(frozen=True, slots=True)
class ThorpGMatOutputs:
    """Subset of THORP-G MATLAB outputs required for C005 postprocessing."""

    t_ts: NDArray[np.floating]

    c_nsc_ts: NDArray[np.floating]
    c_l_ts: NDArray[np.floating]
    c_sw_ts: NDArray[np.floating]
    c_hw_ts: NDArray[np.floating]
    c_r_h_by_layer_ts: NDArray[np.floating]
    c_r_v_by_layer_ts: NDArray[np.floating]

    u_l_opt_ts: NDArray[np.floating]
    u_sw_opt_ts: NDArray[np.floating]
    u_r_h_opt_ts: NDArray[np.floating]
    u_r_v_opt_ts: NDArray[np.floating]

    u_unloading_ts: NDArray[np.floating]

    psi_s_ts: NDArray[np.floating]
    psi_rc_ts: NDArray[np.floating]


def load_thorp_g_mat_outputs(*, path: Path) -> ThorpGMatOutputs:
    """Load stored THORP-G MATLAB outputs needed for TDGM postprocessing."""

    mat = loadmat(path)

    def _vec(key: str) -> NDArray[np.floating]:
        return np.asarray(mat[key], dtype=float).reshape(-1)

    t_ts = _vec("t_stor")
    c_nsc_ts = _vec("c_NSC_stor")
    c_l_ts = _vec("c_l_stor")
    c_sw_ts = _vec("c_sw_stor")
    c_hw_ts = _vec("c_hw_stor")

    c_r_h_by_layer_ts = np.asarray(mat["c_r_H_stor"], dtype=float)
    c_r_v_by_layer_ts = np.asarray(mat["c_r_V_stor"], dtype=float)
    if c_r_h_by_layer_ts.ndim != 2 or c_r_v_by_layer_ts.ndim != 2:
        raise ValueError("Expected c_r_*_stor arrays to be 2D (layer x time).")

    u_l_opt_ts = _vec("u_l_stor")
    u_sw_opt_ts = _vec("u_sw_stor")
    u_r_h_opt_ts = _vec("u_r_H_stor")
    u_r_v_opt_ts = _vec("u_r_V_stor")
    u_unloading_ts = _vec("U_stor")

    psi_s_ts = _vec("P_x_s_stor")
    psi_rc_ts = _vec("P_x_r_stor")

    n_t = int(t_ts.size)
    for name, arr in [
        ("c_nsc_ts", c_nsc_ts),
        ("c_l_ts", c_l_ts),
        ("c_sw_ts", c_sw_ts),
        ("c_hw_ts", c_hw_ts),
        ("u_l_opt_ts", u_l_opt_ts),
        ("u_sw_opt_ts", u_sw_opt_ts),
        ("u_r_h_opt_ts", u_r_h_opt_ts),
        ("u_r_v_opt_ts", u_r_v_opt_ts),
        ("u_unloading_ts", u_unloading_ts),
        ("psi_s_ts", psi_s_ts),
        ("psi_rc_ts", psi_rc_ts),
    ]:
        if arr.size != n_t:
            raise ValueError(f"Shape mismatch: {name} has {arr.size} != {n_t}.")

    if c_r_h_by_layer_ts.shape[1] != n_t or c_r_v_by_layer_ts.shape[1] != n_t:
        raise ValueError("Shape mismatch: c_r_*_by_layer_ts must have time axis matching t_ts.")

    return ThorpGMatOutputs(
        t_ts=np.asarray(t_ts, dtype=float),
        c_nsc_ts=np.asarray(c_nsc_ts, dtype=float),
        c_l_ts=np.asarray(c_l_ts, dtype=float),
        c_sw_ts=np.asarray(c_sw_ts, dtype=float),
        c_hw_ts=np.asarray(c_hw_ts, dtype=float),
        c_r_h_by_layer_ts=np.asarray(c_r_h_by_layer_ts, dtype=float),
        c_r_v_by_layer_ts=np.asarray(c_r_v_by_layer_ts, dtype=float),
        u_l_opt_ts=np.asarray(u_l_opt_ts, dtype=float),
        u_sw_opt_ts=np.asarray(u_sw_opt_ts, dtype=float),
        u_r_h_opt_ts=np.asarray(u_r_h_opt_ts, dtype=float),
        u_r_v_opt_ts=np.asarray(u_r_v_opt_ts, dtype=float),
        u_unloading_ts=np.asarray(u_unloading_ts, dtype=float),
        psi_s_ts=np.asarray(psi_s_ts, dtype=float),
        psi_rc_ts=np.asarray(psi_rc_ts, dtype=float),
    )


def forcing_t_a_at_times(
    *,
    forcing_path: Path,
    t_ts: NDArray[np.floating],
    dt_s: float = 6 * 3600,
    n_years_chunk: int = 10,
    samples_per_day: int = 4,
    rh_scale: float = 1.0,
    precip_scale: float = 1.0,
) -> NDArray[np.floating]:
    """Return air temperature aligned to the THORP-G time axis."""

    dt_s = float(dt_s)
    if dt_s <= 0:
        raise ValueError("dt_s must be > 0.")

    with Dataset(forcing_path) as ds:
        raw = np.asarray(ds.variables["data"][:], dtype=float).T

    if raw.ndim != 2 or raw.shape[1] != 6:
        raise ValueError(f"Unexpected forcing shape: {raw.shape}")

    t_a = np.asarray(raw[:, 0], dtype=float)
    precip = np.asarray(raw[:, 2], dtype=float) * float(precip_scale)
    rh = np.clip(np.asarray(raw[:, 3], dtype=float), 0.0, 1.0) * float(rh_scale)
    _ = precip, rh

    n_chunk = int(n_years_chunk) * 365 * int(samples_per_day)
    t_a = t_a[:n_chunk]

    max_idx = int(np.max(np.rint(np.asarray(t_ts, dtype=float) / dt_s)))
    n_required = max_idx + 1
    q = int(np.ceil(n_required / t_a.size))
    t_a = np.tile(t_a, q)[:n_required]

    idx = np.rint(np.asarray(t_ts, dtype=float) / dt_s).astype(int)
    return np.asarray(t_a[idx], dtype=float)


def temperature_limitation_growth(*, t_a_c: NDArray[np.floating] | float) -> NDArray[np.floating]:
    """Temperature limitation to growth g_T."""

    t_a_c = np.asarray(t_a_c, dtype=float)
    with np.errstate(over="ignore"):
        u_mod_t = 1.0 / (1.0 + np.exp(-0.185 * (t_a_c - 18.4)))
    u_mod_t = np.where(t_a_c < 7.0, 0.0, u_mod_t)
    return np.asarray(u_mod_t, dtype=float)


def phloem_sucrose_concentration_from_psi_s(
    *,
    psi_s: NDArray[np.floating] | float,
    rho_w: float = 998.0,
    v_s: float = 2.155e-4,
) -> NDArray[np.floating]:
    """Compute phloem sucrose concentration from stem apex water potential."""

    psi_s = np.asarray(psi_s, dtype=float)
    m_p = 0.48 - 0.13 * psi_s
    with np.errstate(divide="ignore", invalid="ignore"):
        c_p = m_p * float(rho_w) / (1.0 - m_p * float(rho_w) * float(v_s))
    return np.asarray(c_p, dtype=float)


@dataclass(frozen=True, slots=True)
class ThorpGCouplingPostprocessOutputs:
    t_ts: NDArray[np.floating]

    tree_volume_ts: NDArray[np.floating]
    c_p_ts: NDArray[np.floating]
    c_nsc_mobile_ts: NDArray[np.floating]
    c_nsc_immobile_ts: NDArray[np.floating]
    k_mm_ts: NDArray[np.floating]
    theta_g_ts: NDArray[np.floating]

    u_mod_t_ts: NDArray[np.floating]
    g_rate_ts: NDArray[np.floating]
    g_potential_ts: NDArray[np.floating]
    g_rate_from_eq_ts: NDArray[np.floating]


def postprocess_thorp_g_coupling(
    *,
    thorp: ThorpGMatOutputs,
    t_a_ts: NDArray[np.floating],
    rho_c_s: float = 1.4e4,
    rho_c_l: float = 2e4,
    c_mm: float = 300.0,
    alpha: float = 1.0 / 12.0,
    f_c: float = 0.28,
) -> ThorpGCouplingPostprocessOutputs:
    """Compute coupling terms from stored THORP-G outputs."""

    t_ts = np.asarray(thorp.t_ts, dtype=float)
    t_a_ts = np.asarray(t_a_ts, dtype=float)
    if t_a_ts.shape != t_ts.shape:
        raise ValueError("t_a_ts must match thorp.t_ts shape.")

    c_w_ts = np.asarray(thorp.c_sw_ts + thorp.c_hw_ts, dtype=float)
    c_r_ts = np.asarray(np.sum(thorp.c_r_h_by_layer_ts + thorp.c_r_v_by_layer_ts, axis=0), dtype=float)
    c_l_ts = np.asarray(thorp.c_l_ts, dtype=float)

    tree_volume_ts = tree_volume_from_carbon_pools(
        c_w=c_w_ts,
        c_r=c_r_ts,
        c_l=c_l_ts,
        rho_c_s=rho_c_s,
        rho_c_l=rho_c_l,
    )

    c_p_ts = phloem_sucrose_concentration_from_psi_s(psi_s=thorp.psi_s_ts)
    c_nsc_mobile_ts = mobile_nsc_from_phloem_concentration(
        c_p=c_p_ts,
        tree_volume=tree_volume_ts,
        alpha=alpha,
    )
    c_nsc_immobile_ts = immobile_nsc_from_total(c_nsc=thorp.c_nsc_ts, c_nsc_mobile=c_nsc_mobile_ts)
    k_mm_ts = michaelis_menten_coefficient_nsc(c_mm=c_mm, tree_volume=tree_volume_ts, alpha=alpha)
    theta_g_ts = nsc_limitation_growth(c_nsc_immobile=c_nsc_immobile_ts, k_mm=k_mm_ts)

    u_mod_t_ts = temperature_limitation_growth(t_a_c=t_a_ts)
    g_rate_ts = np.asarray(thorp.u_unloading_ts * (1.0 - float(f_c)), dtype=float)

    denom = np.asarray(u_mod_t_ts * theta_g_ts, dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        g_potential_ts = np.where(denom > 0, g_rate_ts / denom, 0.0)
    g_rate_from_eq_ts = realized_growth_rate(
        g_potential=g_potential_ts,
        u_mod_t=u_mod_t_ts,
        theta_g=theta_g_ts,
    )

    return ThorpGCouplingPostprocessOutputs(
        t_ts=t_ts,
        tree_volume_ts=np.asarray(tree_volume_ts, dtype=float),
        c_p_ts=np.asarray(c_p_ts, dtype=float),
        c_nsc_mobile_ts=np.asarray(c_nsc_mobile_ts, dtype=float),
        c_nsc_immobile_ts=np.asarray(c_nsc_immobile_ts, dtype=float),
        k_mm_ts=np.asarray(k_mm_ts, dtype=float),
        theta_g_ts=np.asarray(theta_g_ts, dtype=float),
        u_mod_t_ts=np.asarray(u_mod_t_ts, dtype=float),
        g_rate_ts=np.asarray(g_rate_ts, dtype=float),
        g_potential_ts=np.asarray(g_potential_ts, dtype=float),
        g_rate_from_eq_ts=np.asarray(g_rate_from_eq_ts, dtype=float),
    )
