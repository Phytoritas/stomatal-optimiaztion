from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Mapping

import numpy as np

from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.partitioning.fractions import (
    AllocationFractions,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.partitioning.organ import Organ
from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.partitioning.policy import (
    PartitionPolicy,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.partitioning.thorp_opt import (
    ThorpObjectiveParams,
    tomato_partitioning,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.contracts import EnvStep


def _constant(value: float):
    def _fn(_t: float) -> float:
        return float(value)

    return _fn


def _finite(value: object, *, default: float) -> float:
    try:
        x = float(value)
    except (TypeError, ValueError):
        return float(default)
    if not math.isfinite(x):
        return float(default)
    return float(x)


def _default_objective_params() -> ThorpObjectiveParams:
    return ThorpObjectiveParams(
        sla=0.08,
        tau_l=200.0,
        tau_r=365.0,
        tau_sw=400.0,
        r_m_sw_func=_constant(0.01),
        r_m_r_func=_constant(0.008),
    )


def _fruit_fraction_from_sinks(*, s_fr_g_d: float, s_veg_g_d: float) -> float:
    s_fr = max(0.0, float(s_fr_g_d))
    s_veg = max(1e-9, float(s_veg_g_d))
    s_total = s_fr + s_veg
    if s_total > 1e-9:
        return s_fr / s_total
    return 0.0


@dataclass(frozen=True, slots=True)
class ThorpVegetativePolicy(PartitionPolicy):
    """Fruit from sinks, vegetative split from THORP allocation rule (ported)."""

    name: str = "thorp_veg"

    lambda_wue: float = 1.2
    d_a_n_d_r_abs: float = 0.03
    d_e_d_la: float = 0.015
    d_e_d_d: float = 0.004
    d_e_d_c_r_h: tuple[float, ...] = (0.006, 0.004)
    d_e_d_c_r_v: tuple[float, ...] = (0.003, 0.002)
    d_r_abs_d_h: float = 20.0
    d_r_abs_d_w: float = 8.0
    d_r_abs_d_la: float = 0.2
    h: float = 1.5
    w: float = 0.08
    d: float = 0.02
    c0: float = 0.6411
    c1: float = 0.625
    t_soil_c: float = 23.0

    def compute(
        self,
        *,
        env: EnvStep,
        state: object,
        sinks: Mapping[str, float],
        scheme: str,
        params: Mapping[str, object] | None = None,
    ) -> AllocationFractions:
        del params

        s_fr_g_d = float(sinks.get("S_fr_g_d", 0.0))
        s_veg_g_d = float(sinks.get("S_veg_g_d", 0.0))
        f_fr = _fruit_fraction_from_sinks(s_fr_g_d=s_fr_g_d, s_veg_g_d=s_veg_g_d)
        f_veg = 1.0 - f_fr

        a_n = max(0.0, _finite(getattr(state, "co2_flux_g_m2_s", 0.0), default=0.0))

        # Map tomato dry-matter pools to THORP carbon pools as a first-order proxy.
        c_l = max(0.0, _finite(getattr(state, "W_lv", 0.0), default=0.0))
        c_w = max(1e-6, _finite(getattr(state, "W_st", 1.0), default=1.0))

        split = tomato_partitioning(
            a_n=a_n,
            lambda_wue=self.lambda_wue,
            d_a_n_d_r_abs=self.d_a_n_d_r_abs,
            d_e_d_la=self.d_e_d_la,
            d_e_d_d=self.d_e_d_d,
            d_e_d_c_r_h=np.asarray(self.d_e_d_c_r_h, dtype=float),
            d_e_d_c_r_v=np.asarray(self.d_e_d_c_r_v, dtype=float),
            d_r_abs_d_h=self.d_r_abs_d_h,
            d_r_abs_d_w=self.d_r_abs_d_w,
            d_r_abs_d_la=self.d_r_abs_d_la,
            h=self.h,
            w=self.w,
            d=self.d,
            c_w=c_w,
            c_l=c_l,
            c0=self.c0,
            c1=self.c1,
            t_a=float(env.T_air_C),
            t_soil=float(self.t_soil_c),
            objective_params=_default_objective_params(),
            prefer_thorp=True,
            allow_port_fallback=True,
        )

        u_leaf = max(0.0, float(split.u_leaf))
        u_stem = max(0.0, float(split.u_stem))
        u_root = max(0.0, float(split.u_root))
        u_sum = u_leaf + u_stem + u_root
        if (not math.isfinite(u_sum)) or u_sum <= 0.0:
            u_leaf, u_stem, u_root = 0.7, 0.3, 0.0
            u_sum = 1.0
        u_leaf /= u_sum
        u_stem /= u_sum
        u_root /= u_sum

        scheme_key = str(scheme).strip().lower()
        if scheme_key == "4pool":
            return AllocationFractions(
                values={
                    Organ.FRUIT: f_fr,
                    Organ.LEAF: f_veg * u_leaf,
                    Organ.STEM: f_veg * u_stem,
                    Organ.ROOT: f_veg * u_root,
                }
            )

        if scheme_key == "3pool":
            return AllocationFractions(
                values={
                    Organ.FRUIT: f_fr,
                    Organ.SHOOT: f_veg * (u_leaf + u_stem),
                    Organ.ROOT: f_veg * u_root,
                }
            )

        raise ValueError(f"Unsupported partition scheme {scheme!r}; expected '4pool' or '3pool'.")


@dataclass(frozen=True, slots=True)
class ThorpFruitVegPolicy(ThorpVegetativePolicy):
    """THORP vegetative split, plus fruit-weighted sink fraction."""

    name: str = "thorp_fruit_veg"
    w_fruit: float = 0.0

    def compute(
        self,
        *,
        env: EnvStep,
        state: object,
        sinks: Mapping[str, float],
        scheme: str,
        params: Mapping[str, object] | None = None,
    ) -> AllocationFractions:
        s_fr_g_d = float(sinks.get("S_fr_g_d", 0.0))
        s_veg_g_d = float(sinks.get("S_veg_g_d", 0.0))

        w = max(0.0, _finite(self.w_fruit, default=0.0))
        f_fr_base = _fruit_fraction_from_sinks(s_fr_g_d=s_fr_g_d, s_veg_g_d=s_veg_g_d)
        if w <= 0.0:
            f_fr = f_fr_base
        else:
            s_fr_eff = max(0.0, s_fr_g_d) * (1.0 + w)
            f_fr = _fruit_fraction_from_sinks(s_fr_g_d=s_fr_eff, s_veg_g_d=s_veg_g_d)

        base = super(ThorpFruitVegPolicy, self).compute(
            env=env,
            state=state,
            sinks=sinks,
            scheme=scheme,
            params=params,
        )
        scheme_key = str(scheme).strip().lower()

        if scheme_key == "4pool":
            leaf = float(base.values[Organ.LEAF])
            stem = float(base.values[Organ.STEM])
            root = float(base.values[Organ.ROOT])
            veg_sum = max(0.0, leaf + stem + root)
            if veg_sum <= 0.0:
                leaf, stem, root = 0.7, 0.3, 0.0
                veg_sum = 1.0
            leaf /= veg_sum
            stem /= veg_sum
            root /= veg_sum
            f_veg = 1.0 - f_fr
            return AllocationFractions(
                values={
                    Organ.FRUIT: f_fr,
                    Organ.LEAF: f_veg * leaf,
                    Organ.STEM: f_veg * stem,
                    Organ.ROOT: f_veg * root,
                }
            )

        if scheme_key == "3pool":
            shoot = float(base.values[Organ.SHOOT])
            root = float(base.values[Organ.ROOT])
            veg_sum = max(0.0, shoot + root)
            if veg_sum <= 0.0:
                shoot, root = 1.0, 0.0
                veg_sum = 1.0
            shoot /= veg_sum
            root /= veg_sum
            f_veg = 1.0 - f_fr
            return AllocationFractions(
                values={
                    Organ.FRUIT: f_fr,
                    Organ.SHOOT: f_veg * shoot,
                    Organ.ROOT: f_veg * root,
                }
            )

        raise ValueError(f"Unsupported partition scheme {scheme!r}; expected '4pool' or '3pool'.")


__all__ = ["ThorpFruitVegPolicy", "ThorpVegetativePolicy"]
