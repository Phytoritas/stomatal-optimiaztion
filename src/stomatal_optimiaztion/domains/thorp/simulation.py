from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from stomatal_optimiaztion.domains.thorp.params import THORPParams
from stomatal_optimiaztion.domains.thorp.soil_initialization import SoilGrid

SaveMatCallback = Callable[[Path, dict[str, Any]], None]


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


@dataclass(frozen=True, slots=True)
class InitialAllometry:
    d: float
    h: float
    w: float
    z_i: float
    c_l: float
    c_sw: float
    c_hw: float
    d_hw: float
    c_nsc: float
    c_r_i: float


def _initial_allometry(*, params: THORPParams) -> InitialAllometry:
    d = 0.015
    h = params.b0 * (d / params.d_ref) ** params.c0
    w = params.b1 * (d / params.d_ref) ** params.c1
    z_i = 3.0
    la = 0.4 * params.phi * w**2
    c_l = la / params.sla
    c_w = params.rho_cw * params.xi * d**2 * h
    rmf = 0.3
    c_r_i = (c_l + c_w) * rmf / (1 - rmf)
    c_sw = 0.94 * c_w
    c_hw = c_w - c_sw
    d_hw = (c_hw / (params.rho_cw * params.xi * h)) ** 0.5
    c_nsc = (0.20 * c_l + 0.04 * c_w) / 0.8

    return InitialAllometry(
        d=float(d),
        h=float(h),
        w=float(w),
        z_i=float(z_i),
        c_l=float(c_l),
        c_sw=float(c_sw),
        c_hw=float(c_hw),
        d_hw=float(d_hw),
        c_nsc=float(c_nsc),
        c_r_i=float(c_r_i),
    )


class _Store:
    def __init__(
        self,
        *,
        params: THORPParams,
        grid: SoilGrid,
        t_bgn: float,
        t_end: float,
        save_mat_callback: SaveMatCallback | None = None,
    ) -> None:
        self._params = params
        self._grid = grid
        self._t_bgn = float(t_bgn)
        self._t_end = float(t_end)
        self._save_mat_callback = save_mat_callback

        self._t_sav_data: float | None = None
        self._t_sav_file: float | None = None

        self._t: list[float] = []
        self._c_nsc: list[float] = []
        self._c_l: list[float] = []
        self._c_sw: list[float] = []
        self._c_hw: list[float] = []
        self._c_r_h: list[NDArray[float]] = []
        self._c_r_v: list[NDArray[float]] = []

        self._u_l: list[float] = []
        self._u_sw: list[float] = []
        self._u_r_h: list[float] = []
        self._u_r_v: list[float] = []

        self._d: list[float] = []
        self._d_hw: list[float] = []
        self._h: list[float] = []
        self._w: list[float] = []

        self._psi_l: list[float] = []
        self._psi_s: list[float] = []
        self._psi_rc: list[float] = []
        self._psi_rc0: list[float] = []
        self._psi_soil_by_layer: list[NDArray[float]] = []

        self._r_abs: list[float] = []
        self._e: list[float] = []
        self._evap: list[float] = []
        self._g_w: list[float] = []

        self._a_n: list[float] = []
        self._r_d: list[float] = []
        self._r_m: list[float] = []
        self._u: list[float] = []

    def _append(
        self,
        *,
        t: float,
        c_nsc: float,
        c_l: float,
        c_sw: float,
        c_hw: float,
        c_r_h: NDArray[float],
        c_r_v: NDArray[float],
        u_l: float,
        u_sw: float,
        u_r_h: NDArray[float],
        u_r_v: NDArray[float],
        d: float,
        d_hw: float,
        h: float,
        w: float,
        psi_l: float,
        psi_s: float,
        psi_rc: float,
        psi_rc0: float,
        psi_soil_by_layer: NDArray[float],
        r_abs: float,
        e: float,
        evap: float,
        g_w: float,
        a_n: float,
        r_d: float,
        r_m: float,
        u: float,
    ) -> None:
        self._t.append(float(t))
        self._c_nsc.append(float(c_nsc))
        self._c_l.append(float(c_l))
        self._c_sw.append(float(c_sw))
        self._c_hw.append(float(c_hw))
        self._c_r_h.append(np.asarray(c_r_h, dtype=float).copy())
        self._c_r_v.append(np.asarray(c_r_v, dtype=float).copy())

        self._u_l.append(float(u_l))
        self._u_sw.append(float(u_sw))
        self._u_r_h.append(float(np.sum(u_r_h)))
        self._u_r_v.append(float(np.sum(u_r_v)))

        self._d.append(float(d))
        self._d_hw.append(float(d_hw))
        self._h.append(float(h))
        self._w.append(float(w))

        self._psi_l.append(float(psi_l))
        self._psi_s.append(float(psi_s))
        self._psi_rc.append(float(psi_rc))
        self._psi_rc0.append(float(psi_rc0))
        self._psi_soil_by_layer.append(np.asarray(psi_soil_by_layer, dtype=float).copy())

        self._r_abs.append(float(r_abs))
        self._e.append(float(e))
        self._evap.append(float(evap))
        self._g_w.append(float(g_w))

        self._a_n.append(float(a_n))
        self._r_d.append(float(r_d))
        self._r_m.append(float(r_m))
        self._u.append(float(u))

    def initialize(
        self,
        *,
        t: float,
        c_nsc: float,
        c_l: float,
        c_sw: float,
        c_hw: float,
        c_r_h: NDArray[float],
        c_r_v: NDArray[float],
        d: float,
        d_hw: float,
        h: float,
        w: float,
        psi_l: float,
        psi_s: float,
        psi_rc: float,
        psi_rc0: float,
        psi_soil_by_layer: NDArray[float],
        r_abs: float,
        e: float,
        evap: float,
        g_w: float,
        a_n: float,
        r_d: float,
        r_m: float,
        u: float,
    ) -> None:
        self._t_sav_data = self._t_bgn + 12 * 3600.0
        self._t_sav_file = float(self._params.dt_sav_data)

        self._append(
            t=t,
            c_nsc=c_nsc,
            c_l=c_l,
            c_sw=c_sw,
            c_hw=c_hw,
            c_r_h=c_r_h,
            c_r_v=c_r_v,
            u_l=0.0,
            u_sw=0.0,
            u_r_h=np.zeros_like(c_r_h, dtype=float),
            u_r_v=np.zeros_like(c_r_v, dtype=float),
            d=d,
            d_hw=d_hw,
            h=h,
            w=w,
            psi_l=psi_l,
            psi_s=psi_s,
            psi_rc=psi_rc,
            psi_rc0=psi_rc0,
            psi_soil_by_layer=psi_soil_by_layer,
            r_abs=r_abs,
            e=e,
            evap=evap,
            g_w=g_w,
            a_n=a_n,
            r_d=r_d,
            r_m=r_m,
            u=u,
        )

        self._t_sav_data = float(self._t_sav_data + self._params.dt_sav_data)

    def maybe_store(
        self,
        *,
        t: float,
        c_nsc: float,
        c_l: float,
        c_sw: float,
        c_hw: float,
        c_r_h: NDArray[float],
        c_r_v: NDArray[float],
        u_l: float,
        u_sw: float,
        u_r_h: NDArray[float],
        u_r_v: NDArray[float],
        d: float,
        d_hw: float,
        h: float,
        w: float,
        psi_l: float,
        psi_s: float,
        psi_rc: float,
        psi_rc0: float,
        psi_soil_by_layer: NDArray[float],
        r_abs: float,
        e: float,
        evap: float,
        g_w: float,
        a_n: float,
        r_d: float,
        r_m: float,
        u: float,
        save_mat_path: Path | str | None,
    ) -> None:
        if self._t_sav_data is None or self._t_sav_file is None:
            raise RuntimeError("Store not initialized")

        if (t == self._t_sav_data) or (abs(t - self._t_end) < self._params.dt):
            if t == self._t_sav_data:
                t_noon = (24 * 3600.0) * np.floor(t / (24 * 3600.0)) + 12 * 3600.0
                if (t - t_noon) != 0:
                    raise RuntimeError("Not noon")

            self._append(
                t=t,
                c_nsc=c_nsc,
                c_l=c_l,
                c_sw=c_sw,
                c_hw=c_hw,
                c_r_h=c_r_h,
                c_r_v=c_r_v,
                u_l=u_l,
                u_sw=u_sw,
                u_r_h=u_r_h,
                u_r_v=u_r_v,
                d=d,
                d_hw=d_hw,
                h=h,
                w=w,
                psi_l=psi_l,
                psi_s=psi_s,
                psi_rc=psi_rc,
                psi_rc0=psi_rc0,
                psi_soil_by_layer=psi_soil_by_layer,
                r_abs=r_abs,
                e=e,
                evap=evap,
                g_w=g_w,
                a_n=a_n,
                r_d=r_d,
                r_m=r_m,
                u=u,
            )

            self._t_sav_data = float(self._t_sav_data + self._params.dt_sav_data)

        if (t == self._t_sav_file) or (abs(t - self._t_end) < self._params.dt):
            if save_mat_path is not None:
                if self._save_mat_callback is None:
                    raise RuntimeError("Store save callback not configured")
                self._save_mat_callback(Path(save_mat_path), self.to_outputs().as_mat_dict())
            self._t_sav_file = float(self._t_sav_file + self._params.dt_sav_file)

    def to_outputs(self) -> SimulationOutputs:
        c_r_h = np.stack(self._c_r_h, axis=1)
        c_r_v = np.stack(self._c_r_v, axis=1)
        psi_soil_by_layer = np.stack(self._psi_soil_by_layer, axis=1)

        return SimulationOutputs(
            t_ts=np.asarray(self._t, dtype=float),
            c_nsc_ts=np.asarray(self._c_nsc, dtype=float),
            c_l_ts=np.asarray(self._c_l, dtype=float),
            c_sw_ts=np.asarray(self._c_sw, dtype=float),
            c_hw_ts=np.asarray(self._c_hw, dtype=float),
            c_r_h_by_layer_ts=c_r_h,
            c_r_v_by_layer_ts=c_r_v,
            u_l_ts=np.asarray(self._u_l, dtype=float),
            u_sw_ts=np.asarray(self._u_sw, dtype=float),
            u_r_h_ts=np.asarray(self._u_r_h, dtype=float),
            u_r_v_ts=np.asarray(self._u_r_v, dtype=float),
            d_ts=np.asarray(self._d, dtype=float),
            d_hw_ts=np.asarray(self._d_hw, dtype=float),
            h_ts=np.asarray(self._h, dtype=float),
            w_ts=np.asarray(self._w, dtype=float),
            psi_l_ts=np.asarray(self._psi_l, dtype=float),
            psi_s_ts=np.asarray(self._psi_s, dtype=float),
            psi_rc_ts=np.asarray(self._psi_rc, dtype=float),
            psi_rc0_ts=np.asarray(self._psi_rc0, dtype=float),
            psi_soil_by_layer_ts=psi_soil_by_layer,
            r_abs_ts=np.asarray(self._r_abs, dtype=float),
            e_ts=np.asarray(self._e, dtype=float),
            evap_ts=np.asarray(self._evap, dtype=float),
            g_w_ts=np.asarray(self._g_w, dtype=float),
            a_n_ts=np.asarray(self._a_n, dtype=float),
            r_d_ts=np.asarray(self._r_d, dtype=float),
            r_m_ts=np.asarray(self._r_m, dtype=float),
            u_ts=np.asarray(self._u, dtype=float),
        )
