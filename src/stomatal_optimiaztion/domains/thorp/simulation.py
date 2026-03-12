from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from numpy.typing import NDArray


@dataclass(frozen=True, slots=True)
class SimulationOutputs:
    t_ts: NDArray[float]
    c_nsc_ts: NDArray[float]
    c_l_ts: NDArray[float]
    c_sw_ts: NDArray[float]
    c_hw_ts: NDArray[float]
    c_r_h_by_layer_ts: NDArray[float]
    c_r_v_by_layer_ts: NDArray[float]
    u_l_ts: NDArray[float]
    u_sw_ts: NDArray[float]
    u_r_h_ts: NDArray[float]
    u_r_v_ts: NDArray[float]
    d_ts: NDArray[float]
    d_hw_ts: NDArray[float]
    h_ts: NDArray[float]
    w_ts: NDArray[float]
    psi_l_ts: NDArray[float]
    psi_s_ts: NDArray[float]
    psi_rc_ts: NDArray[float]
    psi_rc0_ts: NDArray[float]
    psi_soil_by_layer_ts: NDArray[float]
    r_abs_ts: NDArray[float]
    e_ts: NDArray[float]
    evap_ts: NDArray[float]
    g_w_ts: NDArray[float]
    a_n_ts: NDArray[float]
    r_d_ts: NDArray[float]
    r_m_ts: NDArray[float]
    u_ts: NDArray[float]

    def as_mat_dict(self) -> dict[str, Any]:
        return {
            "t_stor": self.t_ts,
            "c_NSC_stor": self.c_nsc_ts,
            "c_l_stor": self.c_l_ts,
            "c_sw_stor": self.c_sw_ts,
            "c_hw_stor": self.c_hw_ts,
            "c_r_H_stor": self.c_r_h_by_layer_ts,
            "c_r_V_stor": self.c_r_v_by_layer_ts,
            "u_l_stor": self.u_l_ts,
            "u_sw_stor": self.u_sw_ts,
            "u_r_H_stor": self.u_r_h_ts,
            "u_r_V_stor": self.u_r_v_ts,
            "D_stor": self.d_ts,
            "D_hw_stor": self.d_hw_ts,
            "H_stor": self.h_ts,
            "W_stor": self.w_ts,
            "P_x_l_stor": self.psi_l_ts,
            "P_x_s_stor": self.psi_s_ts,
            "P_x_r_stor": self.psi_rc_ts,
            "P_x_r0_stor": self.psi_rc0_ts,
            "P_soil_stor": self.psi_soil_by_layer_ts,
            "R_abs_stor": self.r_abs_ts,
            "E_stor": self.e_ts,
            "Evap_stor": self.evap_ts,
            "G_w_stor": self.g_w_ts,
            "A_n_stor": self.a_n_ts,
            "R_d_stor": self.r_d_ts,
            "R_m_stor": self.r_m_ts,
            "U_stor": self.u_ts,
        }
