from __future__ import annotations

import numpy as np

from stomatal_optimiaztion.domains.gosm.model.carbon_assimilation import carbon_assimilation
from stomatal_optimiaztion.domains.gosm.model.conductance_temperature import conductances_and_temperature
from stomatal_optimiaztion.domains.gosm.model.hydraulics import hydraulics
from stomatal_optimiaztion.domains.gosm.model.radiation import radiation_absorbed
from stomatal_optimiaztion.domains.gosm.params.defaults import BaselineInputs
from stomatal_optimiaztion.domains.gosm.utils.traceability import implements


@implements("S3", "S4", "S5", "S6")
def rad_hydr_grow_temp_cassimilation(
    e_vec: np.ndarray,
    *,
    inputs: BaselineInputs,
) -> tuple[
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    float,
    np.ndarray,
    np.ndarray,
    float,
]:
    """Full baseline runtime pipeline."""

    e_vec = np.asarray(e_vec, dtype=float)

    r_abs = radiation_absorbed(
        r_incom=inputs.r_incom,
        z_a=inputs.z_a,
        la=inputs.la,
        w=inputs.w,
        kappa_l=inputs.kappa_l,
        phi_l=inputs.phi_l,
    )

    (
        e_vec,
        psi_rc_vec,
        psi_s_vec,
        g0_vec,
        d_g0_d_e_vec,
        inf_nsc_turgor_ave_vec,
        z_norm_plus_vec,
        turgor_turgid,
    ) = hydraulics(e_vec, inputs=inputs)

    (
        t_l_vec,
        g_w_vec,
        g_c_vec,
        vpd_vec,
        d_e_d_g_w_vec,
        d_g_w_d_g_c_vec,
        d_g0_d_g_c_vec,
        latent_heat,
    ) = conductances_and_temperature(e_vec, d_g0_d_e_vec, inputs=inputs, r_abs=r_abs)

    a_n_vec, r_d_vec, lambda_wue_vec = carbon_assimilation(
        g_c_vec,
        t_l_vec,
        inputs=inputs,
        r_abs=r_abs,
        L=latent_heat,
        d_e_d_g_w_vec=d_e_d_g_w_vec,
        d_g_w_d_g_c_vec=d_g_w_d_g_c_vec,
    )

    return (
        e_vec,
        a_n_vec,
        r_d_vec,
        g0_vec,
        g_w_vec,
        g_c_vec,
        lambda_wue_vec,
        d_g0_d_e_vec,
        d_g0_d_g_c_vec,
        psi_s_vec,
        psi_rc_vec,
        t_l_vec,
        vpd_vec,
        float(r_abs),
        inf_nsc_turgor_ave_vec,
        z_norm_plus_vec,
        float(turgor_turgid),
    )
