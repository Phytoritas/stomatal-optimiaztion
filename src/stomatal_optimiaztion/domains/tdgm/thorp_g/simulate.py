from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from stomatal_optimiaztion.domains.tdgm.thorp_g.allocation import (
    allocation_fractions,
    initial_mean_allocation_fractions,
    update_mean_allocation_fractions,
)
from stomatal_optimiaztion.domains.tdgm.thorp_g.config import (
    ThorpGParams,
    default_params,
)
from stomatal_optimiaztion.domains.tdgm.thorp_g.forcing import Forcing, load_forcing
from stomatal_optimiaztion.domains.tdgm.thorp_g.growth import grow
from stomatal_optimiaztion.domains.tdgm.thorp_g.hydraulics import stomata
from stomatal_optimiaztion.domains.tdgm.thorp_g.matlab_io import save_mat
from stomatal_optimiaztion.domains.tdgm.thorp_g.radiation import radiation
from stomatal_optimiaztion.domains.tdgm.thorp_g.soil import (
    SoilGrid,
    initial_soil_and_roots,
    soil_moisture,
)


@dataclass(frozen=True, slots=True)
class SimulationOutputs:
    t_ts: NDArray[np.floating]
    c_nsc_ts: NDArray[np.floating]
    c_l_ts: NDArray[np.floating]
    c_sw_ts: NDArray[np.floating]
    c_hw_ts: NDArray[np.floating]
    c_r_h_by_layer_ts: NDArray[np.floating]
    c_r_v_by_layer_ts: NDArray[np.floating]
    u_l_ts: NDArray[np.floating]
    u_sw_ts: NDArray[np.floating]
    u_r_h_ts: NDArray[np.floating]
    u_r_v_ts: NDArray[np.floating]
    d_ts: NDArray[np.floating]
    d_hw_ts: NDArray[np.floating]
    h_ts: NDArray[np.floating]
    w_ts: NDArray[np.floating]
    psi_l_ts: NDArray[np.floating]
    psi_s_ts: NDArray[np.floating]
    psi_rc_ts: NDArray[np.floating]
    psi_rc0_ts: NDArray[np.floating]
    psi_soil_by_layer_ts: NDArray[np.floating]
    r_abs_ts: NDArray[np.floating]
    e_ts: NDArray[np.floating]
    evap_ts: NDArray[np.floating]
    g_w_ts: NDArray[np.floating]
    a_n_ts: NDArray[np.floating]
    r_d_ts: NDArray[np.floating]
    r_m_ts: NDArray[np.floating]
    u_ts: NDArray[np.floating]

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


class _Store:
    def __init__(self, params: ThorpGParams, grid: SoilGrid, t_bgn: float, t_end: float) -> None:
        self._params = params
        self._grid = grid
        self._t_bgn = float(t_bgn)
        self._t_end = float(t_end)

        self._t_sav_data: float | None = None
        self._t_sav_file: float | None = None

        self._t: list[float] = []
        self._c_nsc: list[float] = []
        self._c_l: list[float] = []
        self._c_sw: list[float] = []
        self._c_hw: list[float] = []
        self._c_r_h: list[NDArray[np.floating]] = []
        self._c_r_v: list[NDArray[np.floating]] = []

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
        self._psi_soil_by_layer: list[NDArray[np.floating]] = []

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
        c_r_h: NDArray[np.floating],
        c_r_v: NDArray[np.floating],
        u_l: float,
        u_sw: float,
        u_r_h: NDArray[np.floating],
        u_r_v: NDArray[np.floating],
        d: float,
        d_hw: float,
        h: float,
        w: float,
        psi_l: float,
        psi_s: float,
        psi_rc: float,
        psi_rc0: float,
        psi_soil_by_layer: NDArray[np.floating],
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
        self._c_r_h.append(c_r_h.astype(float).copy())
        self._c_r_v.append(c_r_v.astype(float).copy())

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
        self._psi_soil_by_layer.append(psi_soil_by_layer.astype(float).copy())

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
        c_r_h: NDArray[np.floating],
        c_r_v: NDArray[np.floating],
        d: float,
        d_hw: float,
        h: float,
        w: float,
        psi_l: float,
        psi_s: float,
        psi_rc: float,
        psi_rc0: float,
        psi_soil_by_layer: NDArray[np.floating],
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
        c_r_h: NDArray[np.floating],
        c_r_v: NDArray[np.floating],
        u_l: float,
        u_sw: float,
        u_r_h: NDArray[np.floating],
        u_r_v: NDArray[np.floating],
        d: float,
        d_hw: float,
        h: float,
        w: float,
        psi_l: float,
        psi_s: float,
        psi_rc: float,
        psi_rc0: float,
        psi_soil_by_layer: NDArray[np.floating],
        r_abs: float,
        e: float,
        evap: float,
        g_w: float,
        a_n: float,
        r_d: float,
        r_m: float,
        u: float,
        save_mat_path: Path | None,
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
                save_mat(save_mat_path, self.to_outputs().as_mat_dict())
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


def _initial_allometry(
    params: ThorpGParams,
) -> tuple[float, float, float, float, float, float, float, float, float, float]:
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

    # THORP-G MATLAB v1.4 initializes NSC using a calibration-scope `c_r` coming
    # from `INPUTS_0_Constants.m` (not `c_r_i` from `INPUTS_1_Initial_Allometry.m`).
    # This looks like a workspace carryover, but it affects baseline `.mat` outputs,
    # so we reproduce it exactly for numerical parity.
    rmf_cal = 0.2
    smf_cal = 0.7
    h_cal = 14.0

    d_cal = params.d_ref * (h_cal / params.b0) ** (1 / params.c0)
    c_w_cal = params.rho_cw * params.xi * d_cal**2 * h_cal
    c_r_cal = rmf_cal * (c_w_cal / smf_cal)

    v = (c_w + c_r_cal) / params.rho_cw + c_l / params.rho_cl_init
    c_nsc_mob = 12.0 * params.c_sucrose_p_init * v
    c_nsc_immob = 3.0 * c_nsc_mob
    c_nsc = c_nsc_mob + c_nsc_immob

    return (
        float(d),
        float(h),
        float(w),
        float(z_i),
        float(c_l),
        float(c_sw),
        float(c_hw),
        float(d_hw),
        float(c_nsc),
        float(c_r_i),
    )


def run(
    params: ThorpGParams | None = None,
    *,
    forcing: Forcing | None = None,
    max_steps: int | None = None,
    save_mat_path: str | Path | None = None,
) -> SimulationOutputs:
    params = default_params() if params is None else params
    forcing = load_forcing(params) if forcing is None else forcing

    d, h, w, z_i, c_l, c_sw, c_hw, d_hw, c_nsc, c_r_i = _initial_allometry(params)

    init = initial_soil_and_roots(params=params, c_r_i=c_r_i, z_i=z_i)
    grid = init.grid
    n_soil = grid.n_soil

    psi_soil_by_layer = init.psi_soil_by_layer
    c_r_h = init.c_r_h
    c_r_v = init.c_r_v

    u_sw_mean, u_l_mean, u_r_h_mean, u_r_v_mean = initial_mean_allocation_fractions(c_r_h=c_r_h, c_r_v=c_r_v)

    u_l = 0.0
    u_r_h = np.zeros(n_soil, dtype=float)
    u_r_v = np.zeros(n_soil, dtype=float)
    u_sw = 0.0

    t_allocate = 3600.0 * (24.0 * np.floor(0.0 / 3600.0 / 24.0) + 12.0)

    store = _Store(params=params, grid=grid, t_bgn=float(forcing.t[0]), t_end=float(forcing.t_end))

    save_path = Path(save_mat_path) if save_mat_path is not None else None

    n_steps = forcing.t.size - 1
    if max_steps is not None:
        n_steps = min(n_steps, int(max_steps))

    for step in range(n_steps):
        t = float(forcing.t[step])

        t_a = float(forcing.t_a[step])
        t_soil = float(forcing.t_soil[step])
        rh = float(forcing.rh[step])
        precip = float(forcing.precip[step])
        u10 = float(forcing.u10[step])
        r_incom = float(forcing.r_incom[step])
        z_a = float(forcing.z_a[step])

        la_area = float(params.sla * c_l)

        rad = radiation(
            r_incom=r_incom,
            z_a=z_a,
            la=la_area,
            w=w,
            h=h,
            h_n=params.h_n,
            kappa_l=params.kappa_l,
            kappa_n=params.kappa_n,
            phi=params.phi,
        )

        stom = stomata(
            params=params,
            psi_soil_by_layer=psi_soil_by_layer,
            n_soil=n_soil,
            dz=grid.dz,
            z_soil_mid=grid.z_mid,
            t_a=t_a,
            rh=rh,
            r_abs=rad.r_abs,
            la=la_area,
            c_r_h=c_r_h,
            c_r_v=c_r_v,
            h=h,
            w=w,
            d=d,
            d_hw=d_hw,
            d_r_abs_d_h=rad.d_r_abs_dh,
            d_r_abs_d_w=rad.d_r_abs_dw,
            d_r_abs_d_la=rad.d_r_abs_dla,
        )

        if t >= t_allocate:
            alloc = allocation_fractions(
                params=params,
                a_n=stom.a_n,
                lambda_wue=stom.lambda_wue,
                d_a_n_d_r_abs=stom.d_a_n_d_r_abs,
                d_e_d_la=stom.d_e_d_la,
                d_e_d_d=stom.d_e_d_d,
                d_e_d_c_r_h=stom.d_e_d_c_r_h,
                d_e_d_c_r_v=stom.d_e_d_c_r_v,
                d_r_abs_d_h=rad.d_r_abs_dh,
                d_r_abs_d_w=rad.d_r_abs_dw,
                d_r_abs_d_la=rad.d_r_abs_dla,
                h=h,
                w=w,
                d=d,
                c_w=float(c_sw + c_hw),
                c_l=c_l,
                c0=params.c0,
                c1=params.c1,
                t_a=t_a,
                t_soil=t_soil,
            )
            u_l = alloc.u_l
            u_r_h = alloc.u_r_h
            u_r_v = alloc.u_r_v
            u_sw = alloc.u_sw

            if float(u_l + np.sum(u_r_h + u_r_v) + u_sw) == 0.0:
                raise RuntimeError("Allocation fractions sum to zero")
            u_l_mean, u_sw_mean, u_r_h_mean, u_r_v_mean = update_mean_allocation_fractions(
                u_l_mean=u_l_mean,
                u_l=u_l,
                u_r_h_mean=u_r_h_mean,
                u_r_h=u_r_h,
                u_r_v_mean=u_r_v_mean,
                u_r_v=u_r_v,
                u_sw_mean=u_sw_mean,
                u_sw=u_sw,
                dt_allocate=float(params.dt_allocate),
            )

            t_allocate = float(t_allocate + float(params.dt_allocate))

        psi_soil_by_layer, evap = soil_moisture(
            params=params,
            grid=grid,
            psi_soil_by_layer=psi_soil_by_layer,
            t_a=t_a,
            t_soil=t_soil,
            rh=rh,
            u10=u10,
            precip=precip,
            e_soil=stom.e_soil,
            la=la_area,
            w=w,
        )

        gstate = grow(
            params=params,
            u_l=u_l_mean,
            u_r_h=u_r_h_mean,
            u_r_v=u_r_v_mean,
            u_sw=u_sw_mean,
            a_n=stom.a_n,
            r_d=stom.r_d,
            c_l=c_l,
            c_r_h=c_r_h,
            c_r_v=c_r_v,
            c_sw=c_sw,
            c_hw=c_hw,
            c_nsc=c_nsc,
            t_a=t_a,
            t_soil=t_soil,
            psi_s=stom.psi_s,
            psi_rc=stom.psi_rc,
        )

        c_l = gstate.c_l
        c_r_h = gstate.c_r_h
        c_r_v = gstate.c_r_v
        c_sw = gstate.c_sw
        c_hw = gstate.c_hw
        c_nsc = gstate.c_nsc

        h = gstate.h
        w = gstate.w
        d = gstate.d
        d_hw = gstate.d_hw

        if step == 0:
            store.initialize(
                t=t,
                c_nsc=c_nsc,
                c_l=c_l,
                c_sw=c_sw,
                c_hw=c_hw,
                c_r_h=c_r_h,
                c_r_v=c_r_v,
                d=d,
                d_hw=d_hw,
                h=h,
                w=w,
                psi_l=stom.psi_l,
                psi_s=stom.psi_s,
                psi_rc=stom.psi_rc,
                psi_rc0=stom.psi_rc0,
                psi_soil_by_layer=psi_soil_by_layer,
                r_abs=rad.r_abs,
                e=stom.e,
                evap=evap,
                g_w=stom.g_w,
                a_n=stom.a_n,
                r_d=stom.r_d,
                r_m=gstate.r_m,
                u=gstate.u,
            )
        else:
            store.maybe_store(
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
                psi_l=stom.psi_l,
                psi_s=stom.psi_s,
                psi_rc=stom.psi_rc,
                psi_rc0=stom.psi_rc0,
                psi_soil_by_layer=psi_soil_by_layer,
                r_abs=rad.r_abs,
                e=stom.e,
                evap=evap,
                g_w=stom.g_w,
                a_n=stom.a_n,
                r_d=stom.r_d,
                r_m=gstate.r_m,
                u=gstate.u,
                save_mat_path=save_path,
            )

    return store.to_outputs()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run the THORP-G (MATLAB v1.4) Python port.")
    parser.add_argument("--max-steps", type=int, default=60, help="Max time steps (default: 60).")
    parser.add_argument(
        "--full",
        action="store_true",
        help="Run the full forcing horizon (can take a long time).",
    )
    parser.add_argument(
        "--save-mat",
        type=str,
        default=None,
        help="Optional output .mat path (e.g., out/THORP_data_Control_Turgor_Gamma_minus_0.1MPa.mat).",
    )
    args = parser.parse_args()

    out = run(max_steps=None if args.full else args.max_steps, save_mat_path=args.save_mat)
    print(f"Stored {out.t_ts.size} points (last t={out.t_ts[-1]} s).")
