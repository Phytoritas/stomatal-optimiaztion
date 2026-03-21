from __future__ import annotations

import math
from dataclasses import dataclass

from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.partitioning.promoted_modes import (
    PromotedAllocatorConfig,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.partitioning.prior_optimizer import (
    normalize_prior,
)


def _finite(raw: object, *, default: float) -> float:
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return float(default)
    if not math.isfinite(value):
        return float(default)
    return float(value)


def _clamp(value: float, low: float, high: float) -> float:
    return float(min(max(float(value), low), high))


@dataclass(frozen=True, slots=True)
class PromotedMarginalDiagnostics:
    leaf_canopy_return_proxy: float
    stem_support_signal: float
    root_gate_activation: float
    supply_demand_ratio: float
    fruit_load_pressure: float
    low_sink_penalty: float


def resolve_vegetative_prior(
    *,
    config: PromotedAllocatorConfig,
    stable_leaf_share: float,
    stable_stem_share: float,
    stable_root_share: float,
    legacy_root_share: float,
    state: object,
) -> tuple[float, float, float]:
    if config.vegetative_prior_mode == "legacy_empirical_prior":
        return normalize_prior(
            (
                config.leaf_fraction_of_shoot_base * max(1.0 - legacy_root_share, 0.0),
                config.stem_fraction_of_shoot_base * max(1.0 - legacy_root_share, 0.0),
                legacy_root_share,
            )
        )

    if config.vegetative_prior_mode == "fit_from_warmup_prior":
        return normalize_prior(
            (
                _finite(getattr(state, "_promoted_prior_leaf_share", stable_leaf_share), default=stable_leaf_share),
                _finite(getattr(state, "_promoted_prior_stem_share", stable_stem_share), default=stable_stem_share),
                _finite(getattr(state, "_promoted_prior_root_share", stable_root_share), default=stable_root_share),
            )
        )

    return normalize_prior((stable_leaf_share, stable_stem_share, stable_root_share))


def update_prior_memory(
    *,
    state: object,
    leaf_share: float,
    stem_share: float,
    root_share: float,
    alpha: float = 0.05,
) -> None:
    prev_leaf = _finite(getattr(state, "_promoted_prior_leaf_share", leaf_share), default=leaf_share)
    prev_stem = _finite(getattr(state, "_promoted_prior_stem_share", stem_share), default=stem_share)
    prev_root = _finite(getattr(state, "_promoted_prior_root_share", root_share), default=root_share)
    mixed = normalize_prior(
        (
            prev_leaf + alpha * (leaf_share - prev_leaf),
            prev_stem + alpha * (stem_share - prev_stem),
            prev_root + alpha * (root_share - prev_root),
        )
    )
    for name, value in zip(
        ("_promoted_prior_leaf_share", "_promoted_prior_stem_share", "_promoted_prior_root_share"),
        mixed,
        strict=True,
    ):
        try:
            setattr(state, name, float(value))
        except Exception:
            continue


def supply_demand_proxies(*, state: object, sinks: dict[str, float], dt_days: float) -> tuple[float, float]:
    supply_proxy = max(
        _finite(getattr(state, "co2_flux_g_m2_s", 0.0), default=0.0) * max(dt_days, 0.0) * 86400.0
        + _finite(getattr(state, "reserve_ch2o_g", 0.0), default=0.0)
        + _finite(getattr(state, "buffer_pool_g", 0.0), default=0.0),
        0.0,
    )
    demand_proxy = max(
        _finite(sinks.get("S_fr_g_d", 0.0), default=0.0) + _finite(sinks.get("S_veg_g_d", 0.0), default=0.0),
        1e-9,
    )
    supply_demand_ratio = _clamp(supply_proxy / demand_proxy, 0.0, 1.5)
    fruit_load_pressure = _clamp(_finite(sinks.get("S_fr_g_d", 0.0), default=0.0) / demand_proxy, 0.0, 1.5)
    return supply_demand_ratio, fruit_load_pressure


def compute_promoted_marginals(
    *,
    config: PromotedAllocatorConfig,
    state: object,
    sinks: dict[str, float],
    stable_leaf_share: float,
    stable_stem_share: float,
    stable_root_share: float,
) -> tuple[tuple[float, float, float], PromotedMarginalDiagnostics]:
    lai = _finite(getattr(state, "LAI", config.lai_target_center), default=config.lai_target_center)
    water_supply_stress = _clamp(_finite(getattr(state, "water_supply_stress", 1.0), default=1.0), 0.0, 1.0)
    rootzone_multistress = _clamp(_finite(getattr(state, "rootzone_multistress", 0.0), default=0.0), 0.0, 1.0)
    rootzone_saturation = _clamp(_finite(getattr(state, "rootzone_saturation", 0.0), default=0.0), 0.0, 1.0)
    vpd_like = _clamp(_finite(getattr(state, "VPD", 0.0), default=0.0) / 3.0, 0.0, 1.0)
    truss_count = max(_finite(getattr(state, "truss_count", 0.0), default=0.0), 0.0)
    active_trusses = max(_finite(getattr(state, "active_trusses", 0.0), default=0.0), 0.0)
    dt_days = max(_finite(getattr(state, "dt_seconds", 0.0), default=0.0) / 86400.0, 1e-6)

    supply_demand_ratio, fruit_load_pressure = supply_demand_proxies(state=state, sinks=sinks, dt_days=dt_days)
    canopy_gap = _clamp((config.lai_target_center - lai) / max(config.lai_target_half_band, 1e-6), -1.0, 1.0)
    canopy_return = canopy_gap
    low_sink_penalty = 0.0
    if config.leaf_marginal_mode != "canopy_only":
        low_sink_penalty = _clamp(config.low_sink_threshold - supply_demand_ratio, 0.0, 1.0) * config.low_sink_slope
    leaf_turnover_cost = 0.0
    if config.leaf_marginal_mode == "canopy_plus_turnover":
        leaf_turnover_cost = _clamp((lai - config.lai_target_center) / max(config.lai_target_half_band, 1e-6), 0.0, 1.0) * 0.18
    delta_leaf = 1.10 * canopy_return - low_sink_penalty - leaf_turnover_cost

    fruit_load_support = _clamp(fruit_load_pressure, 0.0, 1.0)
    transport_demand = _clamp(0.6 * vpd_like + 0.4 * _clamp(active_trusses / max(truss_count, 1.0), 0.0, 1.0), 0.0, 1.0)
    canopy_position_deficit = _clamp((truss_count / 12.0) - 0.5, -1.0, 1.0)
    stem_turnover_cost = _clamp(stable_stem_share - 0.28, 0.0, 0.6) * 0.12
    delta_stem = 0.55 * fruit_load_support
    if config.stem_marginal_mode != "support_only":
        delta_stem += 0.35 * transport_demand
    if config.stem_marginal_mode == "support_transport_positioning":
        delta_stem += 0.20 * canopy_position_deficit
    delta_stem -= stem_turnover_cost

    dryness = 1.0 - water_supply_stress
    root_gate = dryness
    if config.root_marginal_mode != "water_only_gate":
        root_gate += config.rootzone_multistress_weight * rootzone_multistress
        root_gate += config.rootzone_temperature_weight * _clamp(rootzone_multistress - rootzone_saturation, 0.0, 1.0)
    if config.root_marginal_mode == "greenhouse_multistress_gate_plus_saturation":
        root_gate -= config.rootzone_saturation_weight * rootzone_saturation
    root_turnover_cost = _clamp(stable_root_share - config.dry_root_cap, 0.0, 1.0) * 0.10
    delta_root = 0.85 * root_gate - root_turnover_cost

    return (
        (delta_leaf, delta_stem, delta_root),
        PromotedMarginalDiagnostics(
            leaf_canopy_return_proxy=canopy_return,
            stem_support_signal=fruit_load_support + transport_demand,
            root_gate_activation=_clamp(root_gate, 0.0, 1.5),
            supply_demand_ratio=supply_demand_ratio,
            fruit_load_pressure=fruit_load_pressure,
            low_sink_penalty=low_sink_penalty,
        ),
    )


__all__ = [
    "PromotedMarginalDiagnostics",
    "compute_promoted_marginals",
    "resolve_vegetative_prior",
    "supply_demand_proxies",
    "update_prior_memory",
]
