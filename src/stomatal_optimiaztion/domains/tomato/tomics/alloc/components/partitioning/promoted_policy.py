from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Mapping

from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.partitioning.fractions import (
    AllocationFractions,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.partitioning.fruit_feedback import (
    apply_fruit_feedback_mode,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.partitioning.marginal_terms import (
    compute_promoted_marginals,
    resolve_vegetative_prior,
    update_prior_memory,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.partitioning.organ import Organ
from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.partitioning.prior_optimizer import (
    lowpass_allocation,
    normalize_prior,
    prior_weighted_softmax,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.partitioning.promoted_modes import (
    PromotedAllocatorConfig,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.partitioning.sink_based import (
    SinkBasedTomatoPolicy,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.partitioning.thorp_policies import (
    ThorpVegetativePolicy,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.partitioning.tomics_policy import (
    TomicsPolicy,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.contracts import EnvStep


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


def _normalized_shoot_split(*, leaf_fraction: float, stem_fraction: float) -> tuple[float, float]:
    leaf = max(float(leaf_fraction), 0.0)
    stem = max(float(stem_fraction), 0.0)
    total = leaf + stem
    if total <= 1e-12:
        return 0.70, 0.30
    return leaf / total, stem / total


def _root_cap_for_stress(*, stress: float, wet_root_cap: float, dry_root_cap: float, vegetative_total: float) -> float:
    dryness = 1.0 - _clamp(stress, 0.0, 1.0)
    cap = min(wet_root_cap, dry_root_cap) + dryness * abs(dry_root_cap - wet_root_cap)
    return _clamp(cap, 0.0, max(vegetative_total, 0.0))


def _feedback_alias(mode: str) -> str:
    key = str(mode).strip().lower()
    if key == "dekoning_source_demand_proxy":
        return "dekoning_source_demand_abort_proxy"
    return key


def _integrate_deltas(
    *,
    state: object,
    deltas: tuple[float, float, float],
    dt_days: float,
    temporal_mode: str,
    tau_days: float,
) -> tuple[float, float, float]:
    if temporal_mode == "daily_marginal_daily_alloc":
        return deltas
    effective_tau = max(tau_days if temporal_mode.endswith("lowpass") else 1.0, 1e-6)
    alpha = 1.0 - math.exp(-max(dt_days, 0.0) / effective_tau)
    integrated = []
    for name, value in zip(
        ("_promoted_delta_leaf", "_promoted_delta_stem", "_promoted_delta_root"),
        deltas,
        strict=True,
    ):
        previous = _finite(getattr(state, name, value), default=value)
        current = previous + alpha * (value - previous)
        _remember_state(state, name, current)
        integrated.append(current)
    return tuple(integrated)  # type: ignore[return-value]


@dataclass(frozen=True, slots=True)
class TomicsPromotedResearchPolicy:
    name: str = "tomics_promoted_research"

    def compute(
        self,
        *,
        env: EnvStep,
        state: object,
        sinks: Mapping[str, float],
        scheme: str,
        params: Mapping[str, object] | None = None,
    ) -> AllocationFractions:
        config = PromotedAllocatorConfig.from_params(params, scheme=scheme)
        base_leaf_fraction, base_stem_fraction = _normalized_shoot_split(
            leaf_fraction=config.leaf_fraction_of_shoot_base,
            stem_fraction=config.stem_fraction_of_shoot_base,
        )
        legacy = SinkBasedTomatoPolicy(
            leaf_fraction_of_shoot=base_leaf_fraction,
            stem_fraction_of_shoot=base_stem_fraction,
        ).compute(env=env, state=state, sinks=sinks, scheme="4pool", params=params)
        stable = TomicsPolicy(
            wet_root_cap=config.wet_root_cap,
            dry_root_cap=config.dry_root_cap,
            lai_target_center=config.lai_target_center,
            lai_target_half_band=config.lai_target_half_band,
            leaf_fraction_of_shoot_base=base_leaf_fraction,
            stem_fraction_of_shoot_base=base_stem_fraction,
            min_leaf_fraction_of_shoot=config.min_leaf_fraction_of_shoot,
            max_leaf_fraction_of_shoot=config.max_leaf_fraction_of_shoot,
            thorp_root_blend=config.thorp_root_blend,
        ).compute(env=env, state=state, sinks=sinks, scheme="4pool", params=params)
        thorp = ThorpVegetativePolicy().compute(env=env, state=state, sinks=sinks, scheme="4pool", params=params)

        legacy_fruit = float(legacy.values[Organ.FRUIT])
        legacy_root = float(legacy.values[Organ.ROOT])
        vegetative_total = max(1.0 - legacy_fruit, 0.0)
        if vegetative_total <= 1e-12:
            return _coerce_scheme(
                scheme=scheme,
                fruit=1.0,
                leaf=0.0,
                stem=0.0,
                root=0.0,
            )

        water_supply_stress = getattr(state, "water_supply_stress", None)
        if water_supply_stress is None:
            return _coerce_scheme(
                scheme=scheme,
                fruit=legacy_fruit,
                leaf=float(legacy.values[Organ.LEAF]),
                stem=float(legacy.values[Organ.STEM]),
                root=float(legacy.values[Organ.ROOT]),
            )
        stress = _clamp(_finite(water_supply_stress, default=1.0), 0.0, 1.0)

        stable_leaf_share, stable_stem_share, stable_root_share = normalize_prior(
            (
                float(stable.values[Organ.LEAF]) / max(vegetative_total, 1e-9),
                float(stable.values[Organ.STEM]) / max(vegetative_total, 1e-9),
                float(stable.values[Organ.ROOT]) / max(vegetative_total, 1e-9),
            )
        )
        update_prior_memory(
            state=state,
            leaf_share=stable_leaf_share,
            stem_share=stable_stem_share,
            root_share=stable_root_share,
        )
        prior = resolve_vegetative_prior(
            config=config,
            stable_leaf_share=stable_leaf_share,
            stable_stem_share=stable_stem_share,
            stable_root_share=stable_root_share,
            legacy_root_share=legacy_root / max(vegetative_total, 1e-9),
            state=state,
        )
        deltas, diagnostics = compute_promoted_marginals(
            config=config,
            state=state,
            sinks={str(key): float(value) for key, value in sinks.items()},
            stable_leaf_share=stable_leaf_share,
            stable_stem_share=stable_stem_share,
            stable_root_share=stable_root_share,
        )
        dt_days = max(float(env.dt_s) / 86400.0, 1e-6)
        deltas = _integrate_deltas(
            state=state,
            deltas=deltas,
            dt_days=dt_days,
            temporal_mode=config.temporal_mode,
            tau_days=config.tau_alloc_days,
        )
        fruit_feedback = apply_fruit_feedback_mode(
            config=_feedback_config(config),
            fruit_fraction=legacy_fruit,
            supply_demand_ratio=getattr(diagnostics, "supply_demand_ratio", 1.0),
            fruit_load_pressure=getattr(diagnostics, "fruit_load_pressure", 0.0),
        )
        if config.fruit_feedback_mode != "off":
            abort = fruit_feedback.fruit_abort_fraction
            deltas = (
                deltas[0] + 0.20 * abort,
                deltas[1] - 0.35 * abort,
                deltas[2] + 0.05 * abort,
            )

        if config.optimizer_mode == "bounded_static_current":
            vegetative_shares = prior
        else:
            target = prior_weighted_softmax(prior=prior, deltas=deltas, beta=config.beta)
            if config.optimizer_mode == "prior_weighted_softmax_plus_lowpass":
                current = normalize_prior(
                    (
                        _finite(getattr(state, "_promoted_alloc_leaf_share", prior[0]), default=prior[0]),
                        _finite(getattr(state, "_promoted_alloc_stem_share", prior[1]), default=prior[1]),
                        _finite(getattr(state, "_promoted_alloc_root_share", prior[2]), default=prior[2]),
                    )
                )
                vegetative_shares = lowpass_allocation(
                    current=current,
                    target=target,
                    dt_days=dt_days,
                    tau_days=config.tau_alloc_days,
                )
            else:
                vegetative_shares = target

        proposed_root = vegetative_total * vegetative_shares[2]
        thorp_root = float(thorp.values[Organ.ROOT])
        thorp_bonus = (1.0 - stress) * max(thorp_root - float(stable.values[Organ.ROOT]), 0.0) * config.thorp_root_blend
        root_cap = _root_cap_for_stress(
            stress=stress,
            wet_root_cap=config.wet_root_cap,
            dry_root_cap=config.dry_root_cap,
            vegetative_total=vegetative_total,
        )
        if config.thorp_root_correction_mode == "off":
            root_total = min(proposed_root, root_cap)
        elif config.thorp_root_correction_mode == "bounded":
            root_total = min(max(proposed_root, proposed_root + thorp_bonus), root_cap)
        else:
            prev_root = _finite(getattr(state, "_promoted_root_target", proposed_root), default=proposed_root)
            target_root = min(max(proposed_root, proposed_root + thorp_bonus), root_cap)
            root_total = lowpass_allocation(
                current=(0.0, 0.0, prev_root / max(vegetative_total, 1e-9)),
                target=(0.0, 0.0, target_root / max(vegetative_total, 1e-9)),
                dt_days=dt_days,
                tau_days=config.tau_alloc_days,
            )[2] * vegetative_total
            _remember_state(state, "_promoted_root_target", root_total)

        shoot_total = max(vegetative_total - root_total, 0.0)
        leaf_stem_total = max(vegetative_shares[0] + vegetative_shares[1], 1e-9)
        leaf_share_of_shoot = vegetative_shares[0] / leaf_stem_total
        if config.canopy_governor_mode == "lai_band_plus_leaf_floor" and vegetative_total > 1e-9:
            leaf_share_of_shoot = max(leaf_share_of_shoot, config.leaf_fraction_floor / vegetative_total)
        leaf_share_of_shoot = _clamp(
            leaf_share_of_shoot,
            config.min_leaf_fraction_of_shoot,
            config.max_leaf_fraction_of_shoot,
        )
        leaf_total = shoot_total * leaf_share_of_shoot
        stem_total = max(shoot_total - leaf_total, 0.0)

        _remember_diagnostics(
            state=state,
            config=config,
            prior=prior,
            vegetative_shares=vegetative_shares,
            diagnostics=diagnostics,
            root_total=root_total,
            fruit_abort_fraction=fruit_feedback.fruit_abort_fraction,
            fruit_set_feedback_events=float(fruit_feedback.fruit_set_feedback_events),
        )
        return _coerce_scheme(
            scheme=scheme,
            fruit=legacy_fruit,
            leaf=leaf_total,
            stem=stem_total,
            root=root_total,
        )


def _coerce_scheme(*, scheme: str, fruit: float, leaf: float, stem: float, root: float) -> AllocationFractions:
    key = str(scheme).strip().lower()
    if key == "4pool":
        return AllocationFractions(
            values={
                Organ.FRUIT: fruit,
                Organ.LEAF: leaf,
                Organ.STEM: stem,
                Organ.ROOT: root,
            }
        )
    if key == "3pool":
        return AllocationFractions.from_4pool_to_3pool(fruit=fruit, leaf=leaf, stem=stem, root=root)
    raise ValueError(f"Unsupported partition scheme {scheme!r}; expected '4pool' or '3pool'.")


def _remember_state(state: object, name: str, value: float) -> None:
    try:
        setattr(state, name, float(value))
    except Exception:
        return


def _feedback_config(config: PromotedAllocatorConfig) -> object:
    return type(
        "FeedbackConfig",
        (),
        {
            "fruit_feedback_mode": _feedback_alias(config.fruit_feedback_mode),
            "fruit_abort_threshold": config.fruit_abort_threshold,
            "fruit_abort_slope": config.fruit_abort_slope,
        },
    )()


def _remember_diagnostics(
    *,
    state: object,
    config: PromotedAllocatorConfig,
    prior: tuple[float, float, float],
    vegetative_shares: tuple[float, float, float],
    diagnostics: object,
    root_total: float,
    fruit_abort_fraction: float,
    fruit_set_feedback_events: float,
) -> None:
    values = {
        "_promoted_alloc_leaf_share": float(vegetative_shares[0]),
        "_promoted_alloc_stem_share": float(vegetative_shares[1]),
        "_promoted_alloc_root_share": float(vegetative_shares[2]),
        "promoted_leaf_canopy_return_proxy": _finite(getattr(diagnostics, "leaf_canopy_return_proxy", 0.0), default=0.0),
        "promoted_stem_support_signal": _finite(getattr(diagnostics, "stem_support_signal", 0.0), default=0.0),
        "promoted_root_gate_activation": _finite(getattr(diagnostics, "root_gate_activation", 0.0), default=0.0),
        "promoted_supply_demand_ratio": _finite(getattr(diagnostics, "supply_demand_ratio", 1.0), default=1.0),
        "promoted_fruit_load_pressure": _finite(getattr(diagnostics, "fruit_load_pressure", 0.0), default=0.0),
        "promoted_low_sink_penalty": _finite(getattr(diagnostics, "low_sink_penalty", 0.0), default=0.0),
        "promoted_prior_leaf_share": float(prior[0]),
        "promoted_prior_stem_share": float(prior[1]),
        "promoted_prior_root_share": float(prior[2]),
        "promoted_root_fraction": float(root_total),
        "fruit_abort_fraction": float(fruit_abort_fraction),
        "fruit_set_feedback_events": float(fruit_set_feedback_events),
        "promoted_canopy_lai_floor": float(config.canopy_lai_floor),
        "promoted_leaf_fraction_floor": float(config.leaf_fraction_floor),
    }
    for key, value in values.items():
        _remember_state(state, key, float(value))


__all__ = ["TomicsPromotedResearchPolicy"]
