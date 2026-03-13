from __future__ import annotations

import numpy as np

from stomatal_optimiaztion.domains.gosm.params.defaults import BaselineInputs
from stomatal_optimiaztion.domains.gosm.utils.math import polylog2
from stomatal_optimiaztion.domains.gosm.utils.traceability import implements


@implements(
    "Eq.S5.1",
    "Eq.S5.2",
    "Eq.S5.3",
    "Eq.S5.4",
    "Eq.S5.5",
    "Eq.S5.6",
    "Eq.S5.7",
    "Eq.S5.8",
    "Eq.S5.9",
    "Eq.S5.10",
    "Eq.S5.11",
    "Eq.S5.12",
    "Eq.S6.1",
    "Eq.S6.2",
    "Eq.S6.3",
    "Eq.S6.4",
    "Eq.S6.5",
    "Eq.S6.6",
    "Eq.S6.7",
    "Eq.S6.8",
    "Eq.S6.9",
    "Eq.S6.10",
    "Eq.S6.11",
    "Eq.S6.12",
    "Eq.S6.13",
    "Eq.S6.14",
    "Eq.S6.15",
)
def hydraulics(
    e_vec: np.ndarray,
    *,
    inputs: BaselineInputs,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, float]:
    """Xylem hydraulics plus turgor-limited potential growth."""

    e_vec = np.asarray(e_vec, dtype=float)

    rho = inputs.rho
    g = inputs.g
    psi_soil = inputs.psi_soil
    la = inputs.la
    h = inputs.h
    z = inputs.z

    k_sw = inputs.k_sw
    alpha_sw = inputs.alpha_sw
    beta_sw = inputs.beta_sw

    k_r = inputs.k_r
    alpha_r = inputs.alpha_r
    beta_r = inputs.beta_r

    c_m1 = inputs.c_m1
    c_m2 = inputs.c_m2
    c_pi1 = inputs.c_pi1
    c_pi2 = inputs.c_pi2
    r_gas = inputs.r_gas
    t_a = inputs.t_a
    c_w = inputs.c_w
    u_w = inputs.u_w
    phi_extens_effective = inputs.phi_extens_effective
    p_turgor_crit = inputs.p_turgor_crit

    def _scaled_complex_log(log_arg: np.ndarray, alpha: float) -> np.ndarray:
        log_val = np.log(log_arg.astype(complex))
        return (np.real(log_val) / alpha) + (1j * (np.imag(log_val) / alpha))

    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        denom_r = rho * g * z * k_r / 1e6 + la * e_vec
        log_arg_r = (
            (rho * g * z * k_r / 1e6 + la * e_vec) * np.exp(-alpha_r * beta_r)
            + la * e_vec * np.exp(-alpha_r * psi_soil)
            - la * e_vec * np.exp(-alpha_r * psi_soil + alpha_r * rho * g * z / 1e6 + alpha_r * la * e_vec / k_r)
        ) / denom_r
        psi_rc_complex = (
            psi_soil
            - rho * g * z / 1e6
            + beta_r
            - la * e_vec / k_r
            + _scaled_complex_log(log_arg_r, alpha_r)
        )

        denom_s = rho * g * h * k_sw / 1e6 + la * e_vec
        log_arg_s = (
            (rho * g * h * k_sw / 1e6 + la * e_vec) * np.exp(-alpha_sw * beta_sw)
            + la * e_vec * np.exp(-alpha_sw * psi_rc_complex)
            - la
            * e_vec
            * np.exp(-alpha_sw * psi_rc_complex + alpha_sw * rho * g * h / 1e6 + alpha_sw * la * e_vec / k_sw)
        ) / denom_s
        psi_s_complex = (
            psi_rc_complex
            - rho * g * h / 1e6
            + beta_sw
            - la * e_vec / k_sw
            + _scaled_complex_log(log_arg_s, alpha_sw)
        )

    psi_rc_vec = np.real(psi_rc_complex)
    psi_rc_vec[np.abs(np.imag(psi_rc_complex)) > 0] = -np.inf

    psi_s_vec = np.real(psi_s_complex)
    psi_s_vec[np.abs(np.imag(psi_s_complex)) > 0] = -np.inf

    m_p_vec = c_m1 - c_m2 * psi_s_vec
    pi_vec = -1e-6 * rho * r_gas * (t_a + 273.15) * (c_pi1 * m_p_vec + c_pi2 * m_p_vec**2)
    d_pi_d_psi_s_vec = c_m2 * 1e-6 * rho * r_gas * (t_a + 273.15) * (c_pi1 + 2 * c_pi2 * m_p_vec)
    turgor_turgid = float(1e-6 * rho * r_gas * (t_a + 273.15) * (c_pi1 * c_m1 + c_pi2 * c_m1**2))

    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        z_norm_plus_vec = (
            k_sw
            / (rho * g * h * k_sw / 1e6 + la * e_vec)
            * (
                p_turgor_crit
                + pi_vec
                - psi_s_vec
                + (1 / alpha_sw)
                * np.log(
                    (
                        (rho * g * h * k_sw / 1e6 + la * e_vec) * np.exp(-alpha_sw * beta_sw)
                        + la * e_vec * np.exp(-alpha_sw * (p_turgor_crit + pi_vec))
                    )
                    / (
                        (rho * g * h * k_sw / 1e6 + la * e_vec) * np.exp(-alpha_sw * beta_sw)
                        + la * e_vec * np.exp(-alpha_sw * psi_s_vec)
                    )
                )
            )
        )
    z_norm_plus_vec = np.minimum(z_norm_plus_vec, 1.0)
    z_norm_plus_vec = np.maximum(z_norm_plus_vec, 0.0)

    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        d_psi_rc_d_e_vec = -la / k_r + la / alpha_r / (rho * g * z * k_r / 1e6 + la * e_vec) * (
            (rho * g * z * k_r / 1e6) / (rho * g * z * k_r / 1e6 + la * e_vec)
            * np.exp(-alpha_r * psi_rc_vec + alpha_r * beta_r - alpha_r * rho * g * z / 1e6 - alpha_r * la * e_vec / k_r)
            - (
                (rho * g * z * k_r / 1e6) / (rho * g * z * k_r / 1e6 + la * e_vec) + alpha_r * la * e_vec / k_r
            )
            * np.exp(-alpha_r * psi_rc_vec + alpha_r * beta_r)
        )
    d_psi_rc_d_e_vec[psi_rc_vec == -np.inf] = -np.inf

    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
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
    d_psi_s_d_e_vec[psi_s_vec == -np.inf] = -np.inf

    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        dz_norm_plusdE_vec = 1 / (rho * g * h * k_sw / 1e6 + la * e_vec) * (
            k_sw * (d_pi_d_psi_s_vec - 1) * d_psi_s_d_e_vec
            - la * z_norm_plus_vec
            + k_sw
            / alpha_sw
            * (
                (
                    la * np.exp(-alpha_sw * beta_sw)
                    + la * (1 - alpha_sw * e_vec * d_pi_d_psi_s_vec * d_psi_s_d_e_vec) * np.exp(-alpha_sw * p_turgor_crit - alpha_sw * pi_vec)
                )
                / (
                    (rho * g * h * k_sw / 1e6 + la * e_vec) * np.exp(-alpha_sw * beta_sw)
                    + la * e_vec * np.exp(-alpha_sw * p_turgor_crit - alpha_sw * pi_vec)
                )
                - (
                    la * np.exp(-alpha_sw * beta_sw)
                    + la * (1 - alpha_sw * e_vec * d_psi_s_d_e_vec) * np.exp(-alpha_sw * psi_s_vec)
                )
                / ((rho * g * h * k_sw / 1e6 + la * e_vec) * np.exp(-alpha_sw * beta_sw) + la * e_vec * np.exp(-alpha_sw * psi_s_vec))
            )
        )
    dz_norm_plusdE_vec[z_norm_plus_vec == 0] = 0
    dz_norm_plusdE_vec[z_norm_plus_vec == 1] = 0

    e_min_allow = 1e-7

    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        theta_1_vec = np.exp(alpha_sw / k_sw * (rho * g * h * k_sw / 1e6 + la * e_vec)) * (
            1 + (rho * g * h * k_sw / 1e6 / la / e_vec + 1) * np.exp(alpha_sw * psi_s_vec - alpha_sw * beta_sw)
        )
    mask_e0 = e_vec == 0
    theta_1_vec[mask_e0] = np.exp(alpha_sw / k_sw * (rho * g * h * k_sw / 1e6 + la * e_min_allow)) * (
        1 + (rho * g * h * k_sw / 1e6 / la / e_min_allow + 1) * np.exp(alpha_sw * psi_s_vec[mask_e0] - alpha_sw * beta_sw)
    )

    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        theta_plus_vec = np.exp(z_norm_plus_vec * alpha_sw / k_sw * (rho * g * h * k_sw / 1e6 + la * e_vec)) * (
            1 + (rho * g * h * k_sw / 1e6 / la / e_vec + 1) * np.exp(alpha_sw * psi_s_vec - alpha_sw * beta_sw)
        )
    theta_plus_vec[mask_e0] = np.exp(
        z_norm_plus_vec[mask_e0] * alpha_sw / k_sw * (rho * g * h * k_sw / 1e6 + la * e_min_allow)
    ) * (
        1 + (rho * g * h * k_sw / 1e6 / la / e_min_allow + 1) * np.exp(alpha_sw * psi_s_vec[mask_e0] - alpha_sw * beta_sw)
    )

    omega_plus_vec = (
        polylog2(2 - theta_1_vec)
        - polylog2(2 - theta_plus_vec)
        - 0.5 * (polylog2(2 * theta_1_vec - theta_1_vec**2) - polylog2(2 * theta_plus_vec - theta_plus_vec**2))
    )
    omega_plus_vec = np.real(omega_plus_vec)
    omega_plus_vec[theta_1_vec == theta_plus_vec] = 0

    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        i_vec = (1 - z_norm_plus_vec) * (
            beta_sw - pi_vec - p_turgor_crit - (1 / alpha_sw) * np.log(rho * g * h * k_sw / 1e6 / la / e_vec + 1)
        ) + k_sw / alpha_sw**2 / (rho * g * h * k_sw / 1e6 + la * e_vec) * omega_plus_vec
    i_vec[mask_e0] = (1 - z_norm_plus_vec[mask_e0]) * (psi_s_vec[mask_e0] - pi_vec[mask_e0] - p_turgor_crit) + rho * g * h / 1e6 / 2 * (
        1 - z_norm_plus_vec[mask_e0] ** 2
    )
    i_vec[psi_s_vec == -np.inf] = 0

    g0_vec = phi_extens_effective(t_a) * c_w / u_w * i_vec

    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        theta_0_vec = 1 + (rho * g * h * k_sw / 1e6 / la / e_vec + 1) * np.exp(alpha_sw * psi_s_vec - alpha_sw * beta_sw)
    theta_0_vec[mask_e0] = 1 + (rho * g * h * k_sw / 1e6 / la / e_min_allow + 1) * np.exp(
        alpha_sw * psi_s_vec[mask_e0] - alpha_sw * beta_sw
    )

    omega_0_vec = (
        polylog2(2 - theta_1_vec)
        - polylog2(2 - theta_0_vec)
        - 0.5 * (polylog2(2 * theta_1_vec - theta_1_vec**2) - polylog2(2 * theta_0_vec - theta_0_vec**2))
    )
    omega_0_vec = np.real(omega_0_vec)
    omega_0_vec[theta_1_vec == theta_0_vec] = 0

    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        psi_x_ave_vec = (beta_sw - (1 / alpha_sw) * np.log(rho * g * h * k_sw / 1e6 / la / e_vec + 1)) + k_sw / alpha_sw**2 / (
            rho * g * h * k_sw / 1e6 + la * e_vec
        ) * omega_0_vec
    psi_x_ave_vec[mask_e0] = psi_s_vec[mask_e0] + rho * g * h / 2 / 1e6

    inf_nsc_turgor_ave_vec = psi_x_ave_vec - pi_vec

    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        dtheta_1d_e_vec = (
            np.exp(alpha_sw / k_sw * (rho * g * h * k_sw / 1e6 + la * e_vec))
            / e_vec
            * (
                1
                / la
                * ((rho * g * h * k_sw / 1e6 + la * e_vec) * alpha_sw * d_psi_s_d_e_vec - rho * g * h * k_sw / 1e6 / e_vec)
                * np.exp(alpha_sw * psi_s_vec - alpha_sw * beta_sw)
                + alpha_sw
                / k_sw
                * (la * e_vec + (rho * g * h * k_sw / 1e6 + la * e_vec) * np.exp(alpha_sw * psi_s_vec - alpha_sw * beta_sw))
            )
        )
    dtheta_1d_e_vec[mask_e0] = (
        np.exp(alpha_sw / k_sw * (rho * g * h * k_sw / 1e6 + la * e_min_allow))
        / e_min_allow
        * (
            1
            / la
            * (
                (rho * g * h * k_sw / 1e6 + la * e_min_allow) * alpha_sw * d_psi_s_d_e_vec[mask_e0]
                - rho * g * h * k_sw / 1e6 / e_min_allow
            )
            * np.exp(alpha_sw * psi_s_vec[mask_e0] - alpha_sw * beta_sw)
            + alpha_sw
            / k_sw
            * (
                la * e_min_allow
                + (rho * g * h * k_sw / 1e6 + la * e_min_allow) * np.exp(alpha_sw * psi_s_vec[mask_e0] - alpha_sw * beta_sw)
            )
        )
    )

    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        dtheta_plusd_e_vec = (
            np.exp(z_norm_plus_vec * alpha_sw / k_sw * (rho * g * h * k_sw / 1e6 + la * e_vec))
            / la
            / e_vec
            * (
                ((rho * g * h * k_sw / 1e6 + la * e_vec) * alpha_sw * d_psi_s_d_e_vec - rho * g * h * k_sw / 1e6 / e_vec)
                * np.exp(alpha_sw * psi_s_vec - alpha_sw * beta_sw)
                + alpha_sw
                / k_sw
                * (
                    la * e_vec
                    + (rho * g * h * k_sw / 1e6 + la * e_vec) * np.exp(alpha_sw * psi_s_vec - alpha_sw * beta_sw)
                )
                * (la * z_norm_plus_vec + (rho * g * h * k_sw / 1e6 + la * e_vec) * dz_norm_plusdE_vec)
            )
        )
    dtheta_plusd_e_vec[mask_e0] = (
        np.exp(z_norm_plus_vec[mask_e0] * alpha_sw / k_sw * (rho * g * h * k_sw / 1e6 + la * e_min_allow))
        / la
        / e_min_allow
        * (
            (
                (rho * g * h * k_sw / 1e6 + la * e_min_allow) * alpha_sw * d_psi_s_d_e_vec[mask_e0]
                - rho * g * h * k_sw / 1e6 / e_min_allow
            )
            * np.exp(alpha_sw * psi_s_vec[mask_e0] - alpha_sw * beta_sw)
            + alpha_sw
            / k_sw
            * (
                la * e_min_allow
                + (rho * g * h * k_sw / 1e6 + la * e_min_allow) * np.exp(alpha_sw * psi_s_vec[mask_e0] - alpha_sw * beta_sw)
            )
            * (la * z_norm_plus_vec[mask_e0] + (rho * g * h * k_sw / 1e6 + la * e_min_allow) * dz_norm_plusdE_vec[mask_e0])
        )
    )

    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        d_i_d_e_vec = (
            -dz_norm_plusdE_vec
            * (
                beta_sw
                - pi_vec
                - p_turgor_crit
                - (1 / alpha_sw) * np.log(1 + rho * g * h * k_sw / 1e6 / la / e_vec)
            )
            + (1 - z_norm_plus_vec)
            * (rho * g * h * k_sw / 1e6 / (rho * g * h * k_sw / 1e6 + la * e_vec) / alpha_sw / e_vec - d_pi_d_psi_s_vec * d_psi_s_d_e_vec)
            - la * k_sw * omega_plus_vec / (alpha_sw**2) / ((rho * g * h * k_sw / 1e6 + la * e_vec) ** 2)
            + k_sw
            * np.log(theta_1_vec - 1)
            / (alpha_sw**2)
            / (rho * g * h * k_sw / 1e6 + la * e_vec)
            / theta_1_vec
            * dtheta_1d_e_vec
            - k_sw
            * np.log(theta_plus_vec - 1)
            / (alpha_sw**2)
            / (rho * g * h * k_sw / 1e6 + la * e_vec)
            / theta_plus_vec
            * dtheta_plusd_e_vec
        )
    d_i_d_e_vec[mask_e0] = (
        -dz_norm_plusdE_vec[mask_e0]
        * (
            beta_sw
            - pi_vec[mask_e0]
            - p_turgor_crit
            - (1 / alpha_sw) * np.log(1 + rho * g * h * k_sw / 1e6 / la / e_min_allow)
        )
        + (1 - z_norm_plus_vec[mask_e0])
        * (
            rho * g * h * k_sw / 1e6 / (rho * g * h * k_sw / 1e6 + la * e_min_allow) / alpha_sw / e_min_allow
            - d_pi_d_psi_s_vec[mask_e0] * d_psi_s_d_e_vec[mask_e0]
        )
        - la
        * k_sw
        * omega_plus_vec[mask_e0]
        / (alpha_sw**2)
        / ((rho * g * h * k_sw / 1e6 + la * e_min_allow) ** 2)
        + k_sw
        * np.log(theta_1_vec[mask_e0] - 1)
        / (alpha_sw**2)
        / (rho * g * h * k_sw / 1e6 + la * e_min_allow)
        / theta_1_vec[mask_e0]
        * dtheta_1d_e_vec[mask_e0]
        - k_sw
        * np.log(theta_plus_vec[mask_e0] - 1)
        / (alpha_sw**2)
        / (rho * g * h * k_sw / 1e6 + la * e_min_allow)
        / theta_plus_vec[mask_e0]
        * dtheta_plusd_e_vec[mask_e0]
    )
    d_i_d_e_vec[psi_s_vec == -np.inf] = 0

    d_g0_d_e_vec = phi_extens_effective(t_a) * c_w / u_w * d_i_d_e_vec

    return (
        e_vec,
        psi_rc_vec,
        psi_s_vec,
        np.asarray(g0_vec, dtype=float),
        np.asarray(d_g0_d_e_vec, dtype=float),
        np.asarray(inf_nsc_turgor_ave_vec, dtype=float),
        np.asarray(z_norm_plus_vec, dtype=float),
        turgor_turgid,
    )
