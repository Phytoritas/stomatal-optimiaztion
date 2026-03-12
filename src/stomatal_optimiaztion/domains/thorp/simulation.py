from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from stomatal_optimiaztion.domains.thorp.allocation import (
    AllocationParams,
    allocation_fractions,
)
from stomatal_optimiaztion.domains.thorp.forcing import Forcing, load_forcing
from stomatal_optimiaztion.domains.thorp.growth import GrowthParams, grow
from stomatal_optimiaztion.domains.thorp.hydraulics import (
    RootUptakeParams,
    StomataParams,
    stomata,
)
from stomatal_optimiaztion.domains.thorp.params import (
    THORPParams,
    thorp_params_from_defaults,
)
from stomatal_optimiaztion.domains.thorp.radiation import radiation
from stomatal_optimiaztion.domains.thorp.soil_dynamics import (
    RichardsEquationParams,
    SoilMoistureParams,
    soil_moisture,
)
from stomatal_optimiaztion.domains.thorp.soil_initialization import (
    SoilGrid,
    SoilInitializationParams,
    initial_soil_and_roots,
)

SaveMatCallback = Callable[[Path, dict[str, Any]], None]


@dataclass(frozen=True, slots=True)
class _RunSeamParams:
    soil_initialization: SoilInitializationParams
    soil_moisture: SoilMoistureParams
    stomata: StomataParams
    allocation: AllocationParams
    growth: GrowthParams


def _run_seam_params(*, params: THORPParams) -> _RunSeamParams:
    soil_initialization = SoilInitializationParams(
        rho=params.rho,
        g=params.g,
        z_wt=params.z_wt,
        z_soil=params.z_soil,
        n_soil=params.n_soil,
        bc_bttm=params.bc_bttm,
        soil=params.soil,
        vc_r=params.vc_r,
        beta_r_h=params.beta_r_h,
        beta_r_v=params.beta_r_v,
    )
    richards = RichardsEquationParams(
        dt=params.dt,
        rho=params.rho,
        g=params.g,
        bc_bttm=params.bc_bttm,
        z_wt=params.z_wt,
        p_bttm=params.p_bttm,
        soil=params.soil,
    )
    soil_moisture_params = SoilMoistureParams(
        richards=richards,
        m_h2o=params.m_h2o,
        r_gas=params.r_gas,
    )
    root_uptake = RootUptakeParams(
        beta_r_h=params.beta_r_h,
        beta_r_v=params.beta_r_v,
        vc_r=params.vc_r,
        rho=params.rho,
        g=params.g,
    )
    stomata_params = StomataParams(
        root_uptake=root_uptake,
        g_wmin=params.g_wmin,
        c_prime1=params.c_prime1,
        c_prime2=params.c_prime2,
        d_ref=params.d_ref,
        c0=params.c0,
        c1=params.c1,
        b2=params.b2,
        c2=params.c2,
        k_l=params.k_l,
        vc_sw=params.vc_sw,
        vc_l=params.vc_l,
        v_cmax_func=params.v_cmax_func,
        j_max_func=params.j_max_func,
        gamma_star_func=params.gamma_star_func,
        k_c_func=params.k_c_func,
        k_o_func=params.k_o_func,
        r_d_func=params.r_d_func,
        var_kappa=params.var_kappa,
        c_a=params.c_a,
        o_a=params.o_a,
    )
    allocation_params = AllocationParams(
        sla=params.sla,
        r_m_sw_func=params.r_m_sw_func,
        r_m_r_func=params.r_m_r_func,
        tau_l=params.tau_l,
        tau_sw=params.tau_sw,
        tau_r=params.tau_r,
    )
    growth_params = GrowthParams(
        allocation=allocation_params,
        dt=params.dt,
        f_c=params.f_c,
        rho_cw=params.rho_cw,
        xi=params.xi,
        b0=params.b0,
        d_ref=params.d_ref,
        c0=params.c0,
        b1=params.b1,
        c1=params.c1,
    )
    return _RunSeamParams(
        soil_initialization=soil_initialization,
        soil_moisture=soil_moisture_params,
        stomata=stomata_params,
        allocation=allocation_params,
        growth=growth_params,
    )


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


def run(
    params: THORPParams | None = None,
    *,
    forcing: Forcing | None = None,
    max_steps: int | None = None,
    save_mat_path: str | Path | None = None,
    save_mat_callback: SaveMatCallback | None = None,
) -> SimulationOutputs:
    params = thorp_params_from_defaults() if params is None else params
    forcing = load_forcing(params=params) if forcing is None else forcing
    seam_params = _run_seam_params(params=params)

    initial = _initial_allometry(params=params)
    init = initial_soil_and_roots(
        params=seam_params.soil_initialization,
        c_r_i=initial.c_r_i,
        z_i=initial.z_i,
    )
    grid = init.grid
    n_soil = grid.n_soil

    c_l = initial.c_l
    c_sw = initial.c_sw
    c_hw = initial.c_hw
    c_nsc = initial.c_nsc
    c_r_h = init.c_r_h
    c_r_v = init.c_r_v
    h = initial.h
    w = initial.w
    d = initial.d
    d_hw = initial.d_hw
    psi_soil_by_layer = init.psi_soil_by_layer

    u_l = 0.0
    u_r_h = np.zeros(n_soil, dtype=float)
    u_r_v = np.zeros(n_soil, dtype=float)
    u_sw = 0.0

    t_allocate = 3600.0 * (24.0 * np.floor(0.0 / 3600.0 / 24.0) + 12.0)
    store = _Store(
        params=params,
        grid=grid,
        t_bgn=float(forcing.t[0]),
        t_end=float(forcing.t_end),
        save_mat_callback=save_mat_callback,
    )
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
            params=seam_params.stomata,
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
                params=seam_params.allocation,
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
            t_allocate = float(t_allocate + 24 * 3600.0)

        psi_soil_by_layer, evap = soil_moisture(
            params=seam_params.soil_moisture,
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
            params=seam_params.growth,
            u_l=u_l,
            u_r_h=u_r_h,
            u_r_v=u_r_v,
            u_sw=u_sw,
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
