from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from stomatal_optimiaztion.domains.gosm.utils.traceability import implements


@dataclass(frozen=True)
class StomataModelSolution:
    g_c: float
    lambda_wue: float
    hc_vec: np.ndarray | None = None
    lambda_wue_model_vec: np.ndarray | None = None

    @property
    def HC_vec(self) -> np.ndarray | None:  # noqa: N802 - legacy alias
        return self.hc_vec


def _interp_at_zero_crossing(
    *,
    g_c_vec: np.ndarray,
    lambda_wue_vec: np.ndarray,
    diff_lambda_vec: np.ndarray,
) -> StomataModelSolution:
    zero_diff_vec = np.concatenate((np.abs(np.diff(np.sign(diff_lambda_vec))) / 2, [0]))
    ind_zero = np.where(zero_diff_vec == 1)[0]
    if ind_zero.size == 0:
        return StomataModelSolution(g_c=float("nan"), lambda_wue=float("nan"))

    ind = int(np.min(ind_zero))
    g_c_lb = float(g_c_vec[ind])
    g_c_ub = float(g_c_vec[ind + 1])
    if g_c_lb == float(np.max(g_c_vec)):
        g_c_ub = float(np.max(g_c_vec))

    diff_lb = float(diff_lambda_vec[ind])
    diff_ub = float(diff_lambda_vec[ind + 1])
    g_c = g_c_lb + (g_c_ub - g_c_lb) * (0 - diff_lb) / (diff_ub - diff_lb)

    lambda_wue_lb = float(lambda_wue_vec[ind])
    lambda_wue_ub = float(lambda_wue_vec[ind + 1])
    lambda_wue = lambda_wue_lb + (lambda_wue_ub - lambda_wue_lb) * (g_c - g_c_lb) / (g_c_ub - g_c_lb)
    return StomataModelSolution(g_c=g_c, lambda_wue=lambda_wue)


@implements("Eq.S5.10", "Eq.S5.11")
def _leaf_water_potential(
    *,
    e_vec: np.ndarray,
    psi_s_vec: np.ndarray,
    alpha_l: float,
    beta_l: float,
    k_l: float,
) -> np.ndarray:
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        log_arg = np.exp(-alpha_l * beta_l) + np.exp(-alpha_l * psi_s_vec) - np.exp(-alpha_l * psi_s_vec + alpha_l * e_vec / k_l)
        psi_l_complex = psi_s_vec - e_vec / k_l + beta_l + (1 / alpha_l) * np.log(log_arg.astype(complex))
    psi_l = np.real(psi_l_complex)
    psi_l[np.abs(np.imag(psi_l_complex)) > 0] = -np.inf
    return psi_l


@implements("Eq.S5.12")
def _psi_l_and_d_psi_l_d_e(
    *,
    e_vec: np.ndarray,
    psi_rc_vec: np.ndarray,
    psi_s_vec: np.ndarray,
    alpha_r: float,
    beta_r: float,
    k_r: float,
    alpha_sw: float,
    beta_sw: float,
    k_sw: float,
    alpha_l: float,
    beta_l: float,
    k_l: float,
    la: float,
    h: float,
    z: float,
    rho: float,
    g: float,
) -> tuple[np.ndarray, np.ndarray]:
    psi_l_vec = _leaf_water_potential(e_vec=e_vec, psi_s_vec=psi_s_vec, alpha_l=alpha_l, beta_l=beta_l, k_l=k_l)

    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        d_psi_rc_d_e_vec = -la / k_r + la / alpha_r / (rho * g * z * k_r / 1e6 + la * e_vec) * (
            (rho * g * z * k_r / 1e6) / (rho * g * z * k_r / 1e6 + la * e_vec)
            * np.exp(-alpha_r * psi_rc_vec + alpha_r * beta_r - alpha_r * rho * g * z / 1e6 - alpha_r * la * e_vec / k_r)
            - (
                (rho * g * z * k_r / 1e6) / (rho * g * z * k_r / 1e6 + la * e_vec) + alpha_r * la * e_vec / k_r
            )
            * np.exp(-alpha_r * psi_rc_vec + alpha_r * beta_r)
        )

        d_psi_s_d_e_vec = d_psi_rc_d_e_vec - la / k_sw + la / alpha_sw / (rho * g * h * k_sw / 1e6 + la * e_vec) * (
            (
                (rho * g * h * k_sw / 1e6) / (rho * g * h * k_sw / 1e6 + la * e_vec) - alpha_sw * e_vec * d_psi_rc_d_e_vec
            )
            * np.exp(-alpha_sw * psi_s_vec + alpha_sw * beta_sw - alpha_sw * rho * g * h / 1e6 - alpha_sw * la * e_vec / k_sw)
            - (
                (rho * g * h * k_sw / 1e6) / (rho * g * h * k_sw / 1e6 + la * e_vec)
                + alpha_sw * la * e_vec / k_sw
                - alpha_sw * e_vec * d_psi_rc_d_e_vec
            )
            * np.exp(-alpha_sw * psi_s_vec + alpha_sw * beta_sw)
        )

        d_psi_l_d_e_vec = (d_psi_s_d_e_vec - 1 / k_l) * (1 + np.exp(-alpha_l * (psi_l_vec - beta_l))) - d_psi_s_d_e_vec * np.exp(
            -alpha_l * (psi_l_vec - beta_l) - alpha_l * e_vec / k_l
        )
    return psi_l_vec, d_psi_l_d_e_vec


@implements("Eq.S2.4b", "Eq.S7.1")
def stomata_cowan_and_farquhar_1977(
    *,
    e_vec: np.ndarray,
    g_c_vec: np.ndarray,
    lambda_wue_vec: np.ndarray,
) -> StomataModelSolution:
    m_wue = 1e-3
    cowan_lambda_wue_vec = m_wue * np.ones_like(lambda_wue_vec)
    d_e_vec = np.concatenate(([0.0], np.diff(e_vec)))
    cowan_hc_vec = np.cumsum(cowan_lambda_wue_vec * d_e_vec)

    diff = cowan_lambda_wue_vec - lambda_wue_vec

    if not np.any(g_c_vec[g_c_vec > 0]):
        return StomataModelSolution(g_c=float("nan"), lambda_wue=float("nan"), hc_vec=cowan_hc_vec, lambda_wue_model_vec=cowan_lambda_wue_vec)
    if np.sum(np.sign(diff)) == -g_c_vec.size:
        return StomataModelSolution(g_c=float("nan"), lambda_wue=float("nan"), hc_vec=cowan_hc_vec, lambda_wue_model_vec=cowan_lambda_wue_vec)

    sol = _interp_at_zero_crossing(g_c_vec=g_c_vec, lambda_wue_vec=lambda_wue_vec, diff_lambda_vec=diff)
    return StomataModelSolution(g_c=sol.g_c, lambda_wue=sol.lambda_wue, hc_vec=cowan_hc_vec, lambda_wue_model_vec=cowan_lambda_wue_vec)


@implements("Eq.S2.4b", "Eq.S7.2", "Eq.S7.3", "Eq.S7.4")
def stomata_prentice_2014(
    *,
    a_n_vec: np.ndarray,
    e_vec: np.ndarray,
    g_c_vec: np.ndarray,
    lambda_wue_vec: np.ndarray,
    v_cmax_func=None,
    V_cmax_func=None,  # noqa: N803 - legacy alias
    t_l_vec: np.ndarray,
) -> StomataModelSolution:
    beta_prentice2014 = 145.0
    if v_cmax_func is None:
        v_cmax_func = V_cmax_func
    if v_cmax_func is None:
        raise TypeError("Missing required argument: v_cmax_func")

    v_cmax_vec = v_cmax_func(t_l_vec)
    prentice_lambda_wue_vec = a_n_vec / (e_vec + beta_prentice2014 * v_cmax_vec)
    d_e_vec = np.concatenate(([0.0], np.diff(e_vec)))
    prentice_hc_vec = np.cumsum(prentice_lambda_wue_vec * d_e_vec)

    diff = prentice_lambda_wue_vec - lambda_wue_vec

    if not np.any(g_c_vec[g_c_vec > 0]):
        return StomataModelSolution(g_c=float("nan"), lambda_wue=float("nan"), hc_vec=prentice_hc_vec, lambda_wue_model_vec=prentice_lambda_wue_vec)
    if np.sum(np.sign(diff)) == -g_c_vec.size:
        return StomataModelSolution(g_c=float("nan"), lambda_wue=float("nan"), hc_vec=prentice_hc_vec, lambda_wue_model_vec=prentice_lambda_wue_vec)

    sol = _interp_at_zero_crossing(g_c_vec=g_c_vec, lambda_wue_vec=lambda_wue_vec, diff_lambda_vec=diff)
    return StomataModelSolution(g_c=sol.g_c, lambda_wue=sol.lambda_wue, hc_vec=prentice_hc_vec, lambda_wue_model_vec=prentice_lambda_wue_vec)


@implements("Eq.S2.4b", "Eq.S7.5", "Eq.S7.6", "Eq.S7.7", "Eq.S7.8")
def stomata_sperry_2017(
    *,
    a_n_vec: np.ndarray,
    e_vec: np.ndarray,
    g_c_vec: np.ndarray,
    lambda_wue_vec: np.ndarray,
    psi_rc_vec: np.ndarray,
    psi_s_vec: np.ndarray,
    alpha_r: float,
    beta_r: float,
    k_r: float,
    alpha_sw: float,
    beta_sw: float,
    k_sw: float,
    alpha_l: float,
    beta_l: float,
    k_l: float,
    la: float,
    h: float,
    z: float,
    rho: float,
    g: float,
) -> StomataModelSolution:
    _psi_l_vec, d_psi_l_d_e_vec = _psi_l_and_d_psi_l_d_e(
        e_vec=e_vec,
        psi_rc_vec=psi_rc_vec,
        psi_s_vec=psi_s_vec,
        alpha_r=alpha_r,
        beta_r=beta_r,
        k_r=k_r,
        alpha_sw=alpha_sw,
        beta_sw=beta_sw,
        k_sw=k_sw,
        alpha_l=alpha_l,
        beta_l=beta_l,
        k_l=k_l,
        la=la,
        h=h,
        z=z,
        rho=rho,
        g=g,
    )

    with np.errstate(divide="ignore", invalid="ignore"):
        k_canopy_vec = -1 / d_psi_l_d_e_vec
    k_canopy_max = float(k_canopy_vec[e_vec == 0][0])
    try:
        a_n_max = float(np.nanmax(a_n_vec))
    except ValueError:
        return StomataModelSolution(g_c=float("nan"), lambda_wue=float("nan"))

    with np.errstate(divide="ignore", invalid="ignore"):
        d2_psi_l_d_e2_vec = np.concatenate(([0.0], np.diff(d_psi_l_d_e_vec) / np.diff(e_vec)))
        sperry_lambda_wue_vec = -a_n_max / k_canopy_max * d2_psi_l_d_e2_vec / (d_psi_l_d_e_vec**2)
    sperry_hc_vec = a_n_max * (1.0 - k_canopy_vec / k_canopy_max)

    diff = sperry_lambda_wue_vec - lambda_wue_vec
    if not np.any(g_c_vec[g_c_vec > 0]):
        return StomataModelSolution(g_c=float("nan"), lambda_wue=float("nan"), hc_vec=sperry_hc_vec, lambda_wue_model_vec=sperry_lambda_wue_vec)
    if np.sum(np.sign(diff)) == -g_c_vec.size:
        return StomataModelSolution(g_c=float("nan"), lambda_wue=float("nan"), hc_vec=sperry_hc_vec, lambda_wue_model_vec=sperry_lambda_wue_vec)

    sol = _interp_at_zero_crossing(g_c_vec=g_c_vec, lambda_wue_vec=lambda_wue_vec, diff_lambda_vec=diff)
    return StomataModelSolution(g_c=sol.g_c, lambda_wue=sol.lambda_wue, hc_vec=sperry_hc_vec, lambda_wue_model_vec=sperry_lambda_wue_vec)


@implements("Eq.S2.4b", "Eq.S7.12b", "Eq.S7.13")
def stomata_anderegg_2018(
    *,
    e_vec: np.ndarray,
    g_c_vec: np.ndarray,
    lambda_wue_vec: np.ndarray,
    psi_rc_vec: np.ndarray,
    psi_s_vec: np.ndarray,
    alpha_r: float,
    beta_r: float,
    k_r: float,
    alpha_sw: float,
    beta_sw: float,
    k_sw: float,
    alpha_l: float,
    beta_l: float,
    k_l: float,
    la: float,
    h: float,
    z: float,
    rho: float,
    g: float,
) -> StomataModelSolution:
    psi_l_vec, d_psi_l_d_e_vec = _psi_l_and_d_psi_l_d_e(
        e_vec=e_vec,
        psi_rc_vec=psi_rc_vec,
        psi_s_vec=psi_s_vec,
        alpha_r=alpha_r,
        beta_r=beta_r,
        k_r=k_r,
        alpha_sw=alpha_sw,
        beta_sw=beta_sw,
        k_sw=k_sw,
        alpha_l=alpha_l,
        beta_l=beta_l,
        k_l=k_l,
        la=la,
        h=h,
        z=z,
        rho=rho,
        g=g,
    )

    beta_1 = 4e-6
    beta_2 = 0.0
    beta_3 = 0.0
    with np.errstate(divide="ignore", invalid="ignore"):
        anderegg_hc_vec = (beta_1 / 2.0) * psi_l_vec**2 + beta_2 * psi_l_vec + beta_3
        anderegg_lambda_wue_vec = d_psi_l_d_e_vec * (beta_1 * psi_l_vec + beta_2)

    diff = anderegg_lambda_wue_vec - lambda_wue_vec
    if not np.any(g_c_vec[g_c_vec > 0]):
        return StomataModelSolution(g_c=float("nan"), lambda_wue=float("nan"), hc_vec=anderegg_hc_vec, lambda_wue_model_vec=anderegg_lambda_wue_vec)
    if np.sum(np.sign(diff)) == -g_c_vec.size:
        return StomataModelSolution(g_c=float("nan"), lambda_wue=float("nan"), hc_vec=anderegg_hc_vec, lambda_wue_model_vec=anderegg_lambda_wue_vec)
    if np.sum(np.sign(diff)) == g_c_vec.size:
        return StomataModelSolution(g_c=float("nan"), lambda_wue=float("nan"), hc_vec=anderegg_hc_vec, lambda_wue_model_vec=anderegg_lambda_wue_vec)

    idx0_candidates = np.where(g_c_vec == 0)[0]
    idx0 = int(idx0_candidates[0]) if idx0_candidates.size else 0
    if float(anderegg_lambda_wue_vec[idx0]) > float(lambda_wue_vec[idx0]):
        return StomataModelSolution(g_c=0.0, lambda_wue=float(lambda_wue_vec[idx0]), hc_vec=anderegg_hc_vec, lambda_wue_model_vec=anderegg_lambda_wue_vec)

    sol = _interp_at_zero_crossing(g_c_vec=g_c_vec, lambda_wue_vec=lambda_wue_vec, diff_lambda_vec=diff)
    return StomataModelSolution(g_c=sol.g_c, lambda_wue=sol.lambda_wue, hc_vec=anderegg_hc_vec, lambda_wue_model_vec=anderegg_lambda_wue_vec)


@implements("Eq.S2.4b", "Eq.S7.15", "Eq.S7.16")
def stomata_dewar_2018(
    *,
    a_n_vec: np.ndarray,
    e_vec: np.ndarray,
    g_c_vec: np.ndarray,
    lambda_wue_vec: np.ndarray,
    psi_rc_vec: np.ndarray,
    psi_s_vec: np.ndarray,
    alpha_r: float,
    beta_r: float,
    k_r: float,
    alpha_sw: float,
    beta_sw: float,
    k_sw: float,
    alpha_l: float,
    beta_l: float,
    k_l: float,
    la: float,
    h: float,
    z: float,
    rho: float,
    g: float,
) -> StomataModelSolution:
    psi_l_vec, d_psi_l_d_e_vec = _psi_l_and_d_psi_l_d_e(
        e_vec=e_vec,
        psi_rc_vec=psi_rc_vec,
        psi_s_vec=psi_s_vec,
        alpha_r=alpha_r,
        beta_r=beta_r,
        k_r=k_r,
        alpha_sw=alpha_sw,
        beta_sw=beta_sw,
        k_sw=k_sw,
        alpha_l=alpha_l,
        beta_l=beta_l,
        k_l=k_l,
        la=la,
        h=h,
        z=z,
        rho=rho,
        g=g,
    )

    psi_l_crit = -2.0
    dewar_lambda_wue_vec = -a_n_vec / (psi_l_vec - psi_l_crit) * d_psi_l_d_e_vec
    dewar_lambda_wue_vec[psi_l_vec < psi_l_crit] = 0
    d_e_vec = np.concatenate(([0.0], np.diff(e_vec)))
    dewar_hc_vec = np.cumsum(dewar_lambda_wue_vec * d_e_vec)

    diff = dewar_lambda_wue_vec - lambda_wue_vec
    if not np.any(g_c_vec[g_c_vec > 0]):
        return StomataModelSolution(g_c=float("nan"), lambda_wue=float("nan"), hc_vec=dewar_hc_vec, lambda_wue_model_vec=dewar_lambda_wue_vec)

    sum_sign = float(np.nansum(np.sign(diff)))
    len_non_nan = int(np.sum(~np.isnan(dewar_lambda_wue_vec)))
    if sum_sign == -len_non_nan:
        return StomataModelSolution(g_c=float("nan"), lambda_wue=float("nan"), hc_vec=dewar_hc_vec, lambda_wue_model_vec=dewar_lambda_wue_vec)

    sol = _interp_at_zero_crossing(g_c_vec=g_c_vec, lambda_wue_vec=lambda_wue_vec, diff_lambda_vec=diff)
    return StomataModelSolution(g_c=sol.g_c, lambda_wue=sol.lambda_wue, hc_vec=dewar_hc_vec, lambda_wue_model_vec=dewar_lambda_wue_vec)


@implements("Eq.S2.4b", "Eq.S7.9", "Eq.S7.10", "Eq.S7.11", "Eq.S7.12a")
def stomata_eller_2018(
    *,
    a_n_vec: np.ndarray,
    e_vec: np.ndarray,
    g_c_vec: np.ndarray,
    lambda_wue_vec: np.ndarray,
    psi_rc_vec: np.ndarray,
    psi_s_vec: np.ndarray,
    alpha_r: float,
    beta_r: float,
    k_r: float,
    alpha_sw: float,
    beta_sw: float,
    k_sw: float,
    alpha_l: float,
    beta_l: float,
    k_l: float,
    la: float,
    h: float,
    z: float,
    rho: float,
    g: float,
) -> StomataModelSolution:
    psi_l_vec, d_psi_l_d_e_vec = _psi_l_and_d_psi_l_d_e(
        e_vec=e_vec,
        psi_rc_vec=psi_rc_vec,
        psi_s_vec=psi_s_vec,
        alpha_r=alpha_r,
        beta_r=beta_r,
        k_r=k_r,
        alpha_sw=alpha_sw,
        beta_sw=beta_sw,
        k_sw=k_sw,
        alpha_l=alpha_l,
        beta_l=beta_l,
        k_l=k_l,
        la=la,
        h=h,
        z=z,
        rho=rho,
        g=g,
    )
    d_psi_l_d_e_vec = np.asarray(d_psi_l_d_e_vec, dtype=float)
    d_psi_l_d_e_vec[psi_l_vec == -np.inf] = -np.inf

    with np.errstate(divide="ignore", invalid="ignore"):
        k_canopy_vec = -1 / d_psi_l_d_e_vec
        k_canopy_vec[d_psi_l_d_e_vec == -np.inf] = 0

        k_canopy_max = 1.0 / (1 / k_sw + 1 / k_r + 1 / (la * k_l))
        d2_psi_l_d_e2_vec = np.concatenate(([0.0], np.diff(d_psi_l_d_e_vec) / np.diff(e_vec)))

        eller_lambda_wue_vec = lambda_wue_vec * (1 - k_canopy_vec / k_canopy_max) - d2_psi_l_d_e2_vec / (d_psi_l_d_e_vec**2) * a_n_vec / k_canopy_max
        eller_hc_vec = a_n_vec * (1.0 - k_canopy_vec / k_canopy_max)

    diff = eller_lambda_wue_vec - lambda_wue_vec
    if not np.any(g_c_vec[g_c_vec > 0]):
        return StomataModelSolution(g_c=float("nan"), lambda_wue=float("nan"), hc_vec=eller_hc_vec, lambda_wue_model_vec=eller_lambda_wue_vec)

    sum_sign = float(np.nansum(np.sign(diff)))
    len_non_nan = int(np.sum(~np.isnan(eller_lambda_wue_vec)))
    if sum_sign == -len_non_nan:
        return StomataModelSolution(g_c=float("nan"), lambda_wue=float("nan"), hc_vec=eller_hc_vec, lambda_wue_model_vec=eller_lambda_wue_vec)

    sol = _interp_at_zero_crossing(g_c_vec=g_c_vec, lambda_wue_vec=lambda_wue_vec, diff_lambda_vec=diff)
    return StomataModelSolution(g_c=sol.g_c, lambda_wue=sol.lambda_wue, hc_vec=eller_hc_vec, lambda_wue_model_vec=eller_lambda_wue_vec)


@implements("Eq.S2.4b", "Eq.S7.17", "Eq.S7.18")
def stomata_wang_2020(
    *,
    a_n_vec: np.ndarray,
    e_vec: np.ndarray,
    g_c_vec: np.ndarray,
    lambda_wue_vec: np.ndarray,
    psi_s_vec: np.ndarray,
    alpha_l: float,
    beta_l: float,
    k_l: float,
) -> StomataModelSolution:
    psi_l_vec = _leaf_water_potential(e_vec=e_vec, psi_s_vec=psi_s_vec, alpha_l=alpha_l, beta_l=beta_l, k_l=k_l)

    e_crit = float(np.max(e_vec[psi_l_vec > -np.inf]))
    wang_hc_vec = a_n_vec * e_vec / e_crit
    wang_lambda_wue_vec = (e_vec * lambda_wue_vec + a_n_vec) / e_crit

    diff = wang_lambda_wue_vec - lambda_wue_vec
    if not np.any(g_c_vec[g_c_vec > 0]):
        return StomataModelSolution(g_c=float("nan"), lambda_wue=float("nan"), hc_vec=wang_hc_vec, lambda_wue_model_vec=wang_lambda_wue_vec)
    if np.sum(np.sign(diff)) == -g_c_vec.size:
        return StomataModelSolution(g_c=float("nan"), lambda_wue=float("nan"), hc_vec=wang_hc_vec, lambda_wue_model_vec=wang_lambda_wue_vec)

    sol = _interp_at_zero_crossing(g_c_vec=g_c_vec, lambda_wue_vec=lambda_wue_vec, diff_lambda_vec=diff)
    return StomataModelSolution(g_c=sol.g_c, lambda_wue=sol.lambda_wue, hc_vec=wang_hc_vec, lambda_wue_model_vec=wang_lambda_wue_vec)


@implements("Eq.S7.14")
def stomata_maximize_assimilation(
    *,
    a_n_vec: np.ndarray,
    g_c_vec: np.ndarray,
    lambda_wue_vec: np.ndarray,
) -> StomataModelSolution:
    """Choose the conductance that maximizes assimilation over the supplied sweep."""

    a_n_vec = np.asarray(a_n_vec, dtype=float)
    g_c_vec = np.asarray(g_c_vec, dtype=float)
    lambda_wue_vec = np.asarray(lambda_wue_vec, dtype=float)

    mask = (g_c_vec >= 0) & np.isfinite(a_n_vec)
    if not np.any(mask):
        return StomataModelSolution(g_c=float("nan"), lambda_wue=float("nan"))

    idx = int(np.nanargmax(a_n_vec[mask]))
    idx_full = np.where(mask)[0][idx]
    return StomataModelSolution(g_c=float(g_c_vec[idx_full]), lambda_wue=float(lambda_wue_vec[idx_full]))
