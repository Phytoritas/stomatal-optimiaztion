from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np
from numpy.typing import ArrayLike, NDArray

from stomatal_optimiaztion.domains.thorp.allocation import (
    AllocationParams as ThorpAllocationParams,
)
from stomatal_optimiaztion.domains.thorp.allocation import (
    allocation_fractions as core_allocation_fractions,
)


@dataclass(frozen=True, slots=True)
class ThorpObjectiveParams:
    """Objective weights required by THORP allocation equations."""

    sla: float
    tau_l: float
    tau_r: float
    tau_sw: float
    r_m_sw_func: Callable[[float], float]
    r_m_r_func: Callable[[float], float]


@dataclass(frozen=True, slots=True)
class ThorpAllocationFractions:
    """Full THORP allocation fractions."""

    u_l: float
    u_r_h: NDArray[np.floating]
    u_r_v: NDArray[np.floating]
    u_sw: float
    backend: str = "ported"

    @property
    def u_root(self) -> float:
        return float(np.sum(self.u_r_h + self.u_r_v))

    @property
    def u_stem(self) -> float:
        return float(self.u_sw)


@dataclass(frozen=True, slots=True)
class TomatoPartitionFractions:
    """Collapsed tomato fractions (leaf/stem/root)."""

    u_leaf: float
    u_stem: float
    u_root: float
    backend: str = "ported"

    @property
    def uL(self) -> float:  # noqa: N802 - preserve domain shorthand
        return self.u_leaf

    @property
    def uS(self) -> float:  # noqa: N802 - preserve domain shorthand
        return self.u_stem

    @property
    def uR(self) -> float:  # noqa: N802 - preserve domain shorthand
        return self.u_root


def objective_params_from_thorp(thorp_params: object) -> ThorpObjectiveParams:
    """Extract minimum objective fields from a THORP params object."""

    required = ("sla", "tau_l", "tau_r", "tau_sw", "r_m_sw_func", "r_m_r_func")
    missing = [name for name in required if not hasattr(thorp_params, name)]
    if missing:
        raise AttributeError(
            "THORP params missing required allocation fields: "
            + ", ".join(sorted(missing))
            + "."
        )
    return ThorpObjectiveParams(
        sla=float(getattr(thorp_params, "sla")),
        tau_l=float(getattr(thorp_params, "tau_l")),
        tau_r=float(getattr(thorp_params, "tau_r")),
        tau_sw=float(getattr(thorp_params, "tau_sw")),
        r_m_sw_func=getattr(thorp_params, "r_m_sw_func"),
        r_m_r_func=getattr(thorp_params, "r_m_r_func"),
    )


def _resolve_thorp_src() -> Path | None:
    env_value = str(os.environ.get("TTHORP_THORP_SRC", "")).strip()
    if env_value:
        candidate = Path(env_value).expanduser().resolve()
        if candidate.exists():
            return candidate

    for parent in Path(__file__).resolve().parents:
        candidate = parent / "THORP" / "src"
        if candidate.exists():
            return candidate
    return None


def _import_thorp_allocation():
    try:
        from thorp.allocation import allocation_fractions

        return allocation_fractions
    except ModuleNotFoundError:
        pass

    thorp_src = _resolve_thorp_src()
    if thorp_src is None:
        return None

    thorp_src_str = str(thorp_src)
    if thorp_src_str not in sys.path:
        sys.path.insert(0, thorp_src_str)

    try:
        from thorp.allocation import allocation_fractions

        return allocation_fractions
    except ModuleNotFoundError:
        return None


def _as_vector(name: str, values: ArrayLike) -> NDArray[np.floating]:
    arr = np.asarray(values, dtype=float)
    if arr.ndim != 1:
        raise ValueError(f"{name} must be a 1D array, got shape {arr.shape}.")
    if not np.all(np.isfinite(arr)):
        raise ValueError(f"{name} must contain only finite values.")
    return arr


def _ported_allocation_fractions(
    *,
    objective_params: ThorpObjectiveParams,
    a_n: float,
    lambda_wue: float,
    d_a_n_d_r_abs: float,
    d_e_d_la: float,
    d_e_d_d: float,
    d_e_d_c_r_h: NDArray[np.floating],
    d_e_d_c_r_v: NDArray[np.floating],
    d_r_abs_d_h: float,
    d_r_abs_d_w: float,
    d_r_abs_d_la: float,
    h: float,
    w: float,
    d: float,
    c_w: float,
    c_l: float,
    c0: float,
    c1: float,
    t_a: float,
    t_soil: float,
) -> ThorpAllocationFractions:
    if c_l == 0:
        return ThorpAllocationFractions(
            u_l=1.0,
            u_r_h=np.zeros_like(d_e_d_c_r_h, dtype=float),
            u_r_v=np.zeros_like(d_e_d_c_r_v, dtype=float),
            u_sw=0.0,
            backend="ported",
        )

    if d <= 0:
        raise ValueError(f"d must be > 0, got {d!r}.")
    if c_w <= 0:
        raise ValueError(f"c_w must be > 0, got {c_w!r}.")

    raw = core_allocation_fractions(
        params=ThorpAllocationParams(
            sla=objective_params.sla,
            tau_l=objective_params.tau_l,
            tau_r=objective_params.tau_r,
            tau_sw=objective_params.tau_sw,
            r_m_sw_func=objective_params.r_m_sw_func,
            r_m_r_func=objective_params.r_m_r_func,
        ),
        a_n=float(a_n),
        lambda_wue=float(lambda_wue),
        d_a_n_d_r_abs=float(d_a_n_d_r_abs),
        d_e_d_la=float(d_e_d_la),
        d_e_d_d=float(d_e_d_d),
        d_e_d_c_r_h=d_e_d_c_r_h,
        d_e_d_c_r_v=d_e_d_c_r_v,
        d_r_abs_d_h=float(d_r_abs_d_h),
        d_r_abs_d_w=float(d_r_abs_d_w),
        d_r_abs_d_la=float(d_r_abs_d_la),
        h=float(h),
        w=float(w),
        d=float(d),
        c_w=float(c_w),
        c_l=float(c_l),
        c0=float(c0),
        c1=float(c1),
        t_a=float(t_a),
        t_soil=float(t_soil),
    )
    return ThorpAllocationFractions(
        u_l=float(raw.u_l),
        u_r_h=np.asarray(raw.u_r_h, dtype=float),
        u_r_v=np.asarray(raw.u_r_v, dtype=float),
        u_sw=float(raw.u_sw),
        backend="ported",
    )


def thorp_allocation_fractions(
    *,
    a_n: float,
    lambda_wue: float,
    d_a_n_d_r_abs: float,
    d_e_d_la: float,
    d_e_d_d: float,
    d_e_d_c_r_h: ArrayLike,
    d_e_d_c_r_v: ArrayLike,
    d_r_abs_d_h: float,
    d_r_abs_d_w: float,
    d_r_abs_d_la: float,
    h: float,
    w: float,
    d: float,
    c_w: float,
    c_l: float,
    c0: float,
    c1: float,
    t_a: float,
    t_soil: float,
    objective_params: ThorpObjectiveParams | None = None,
    thorp_params: object | None = None,
    prefer_thorp: bool = True,
    allow_port_fallback: bool = True,
) -> ThorpAllocationFractions:
    """Compute THORP partitioning fractions, using external THORP when available."""

    u_r_h_vec = _as_vector("d_e_d_c_r_h", d_e_d_c_r_h)
    u_r_v_vec = _as_vector("d_e_d_c_r_v", d_e_d_c_r_v)
    if u_r_h_vec.shape != u_r_v_vec.shape:
        raise ValueError(
            "d_e_d_c_r_h and d_e_d_c_r_v must have matching shapes, "
            f"got {u_r_h_vec.shape} and {u_r_v_vec.shape}."
        )

    obj = objective_params
    if obj is None and thorp_params is not None:
        obj = objective_params_from_thorp(thorp_params)
    if obj is None:
        raise ValueError("Provide objective_params or thorp_params.")

    if prefer_thorp and thorp_params is not None:
        allocation_fn = _import_thorp_allocation()
        if allocation_fn is not None:
            raw = allocation_fn(
                params=thorp_params,
                a_n=float(a_n),
                lambda_wue=float(lambda_wue),
                d_a_n_d_r_abs=float(d_a_n_d_r_abs),
                d_e_d_la=float(d_e_d_la),
                d_e_d_d=float(d_e_d_d),
                d_e_d_c_r_h=u_r_h_vec,
                d_e_d_c_r_v=u_r_v_vec,
                d_r_abs_d_h=float(d_r_abs_d_h),
                d_r_abs_d_w=float(d_r_abs_d_w),
                d_r_abs_d_la=float(d_r_abs_d_la),
                h=float(h),
                w=float(w),
                d=float(d),
                c_w=float(c_w),
                c_l=float(c_l),
                c0=float(c0),
                c1=float(c1),
                t_a=float(t_a),
                t_soil=float(t_soil),
            )
            return ThorpAllocationFractions(
                u_l=float(raw.u_l),
                u_r_h=np.asarray(raw.u_r_h, dtype=float),
                u_r_v=np.asarray(raw.u_r_v, dtype=float),
                u_sw=float(raw.u_sw),
                backend="thorp",
            )
        if not allow_port_fallback:
            raise ModuleNotFoundError(
                "THORP package not available. Install/import THORP or set allow_port_fallback=True."
            )

    return _ported_allocation_fractions(
        objective_params=obj,
        a_n=float(a_n),
        lambda_wue=float(lambda_wue),
        d_a_n_d_r_abs=float(d_a_n_d_r_abs),
        d_e_d_la=float(d_e_d_la),
        d_e_d_d=float(d_e_d_d),
        d_e_d_c_r_h=u_r_h_vec,
        d_e_d_c_r_v=u_r_v_vec,
        d_r_abs_d_h=float(d_r_abs_d_h),
        d_r_abs_d_w=float(d_r_abs_d_w),
        d_r_abs_d_la=float(d_r_abs_d_la),
        h=float(h),
        w=float(w),
        d=float(d),
        c_w=float(c_w),
        c_l=float(c_l),
        c0=float(c0),
        c1=float(c1),
        t_a=float(t_a),
        t_soil=float(t_soil),
    )


def tomato_partitioning(
    *,
    a_n: float,
    lambda_wue: float,
    d_a_n_d_r_abs: float,
    d_e_d_la: float,
    d_e_d_d: float,
    d_e_d_c_r_h: ArrayLike,
    d_e_d_c_r_v: ArrayLike,
    d_r_abs_d_h: float,
    d_r_abs_d_w: float,
    d_r_abs_d_la: float,
    h: float,
    w: float,
    d: float,
    c_w: float,
    c_l: float,
    c0: float,
    c1: float,
    t_a: float,
    t_soil: float,
    objective_params: ThorpObjectiveParams | None = None,
    thorp_params: object | None = None,
    prefer_thorp: bool = True,
    allow_port_fallback: bool = True,
) -> TomatoPartitionFractions:
    """Return collapsed leaf/stem/root fractions for tomato partitioning."""

    alloc = thorp_allocation_fractions(
        a_n=a_n,
        lambda_wue=lambda_wue,
        d_a_n_d_r_abs=d_a_n_d_r_abs,
        d_e_d_la=d_e_d_la,
        d_e_d_d=d_e_d_d,
        d_e_d_c_r_h=d_e_d_c_r_h,
        d_e_d_c_r_v=d_e_d_c_r_v,
        d_r_abs_d_h=d_r_abs_d_h,
        d_r_abs_d_w=d_r_abs_d_w,
        d_r_abs_d_la=d_r_abs_d_la,
        h=h,
        w=w,
        d=d,
        c_w=c_w,
        c_l=c_l,
        c0=c0,
        c1=c1,
        t_a=t_a,
        t_soil=t_soil,
        objective_params=objective_params,
        thorp_params=thorp_params,
        prefer_thorp=prefer_thorp,
        allow_port_fallback=allow_port_fallback,
    )

    return TomatoPartitionFractions(
        u_leaf=float(alloc.u_l),
        u_stem=float(alloc.u_sw),
        u_root=float(np.sum(alloc.u_r_h + alloc.u_r_v)),
        backend=alloc.backend,
    )


__all__ = [
    "ThorpAllocationFractions",
    "ThorpObjectiveParams",
    "TomatoPartitionFractions",
    "objective_params_from_thorp",
    "thorp_allocation_fractions",
    "tomato_partitioning",
]
