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
from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.partitioning.organ import Organ
from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.partitioning.research_modes import (
    ResearchArchitectureConfig,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.partitioning.root_modes import (
    apply_root_mode,
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
    return float(min(max(value, low), high))


def _normalized_shoot_split(*, leaf_fraction: float, stem_fraction: float) -> tuple[float, float]:
    leaf = max(float(leaf_fraction), 0.0)
    stem = max(float(stem_fraction), 0.0)
    total = leaf + stem
    if total <= 1e-12:
        return 0.70, 0.30
    return leaf / total, stem / total


@dataclass(frozen=True, slots=True)
class TomicsArchitectureResearchPolicy:
    """Research-only architecture policy preserving stable TOMICS defaults."""

    name: str = "tomics_alloc_research"

    def compute(
        self,
        *,
        env: EnvStep,
        state: object,
        sinks: Mapping[str, float],
        scheme: str,
        params: Mapping[str, object] | None = None,
    ) -> AllocationFractions:
        config = ResearchArchitectureConfig.from_params(params, scheme=scheme)
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
        stable_leaf = float(stable.values[Organ.LEAF])
        stable_stem = float(stable.values[Organ.STEM])
        stable_root = float(stable.values[Organ.ROOT])
        thorp_root = float(thorp.values[Organ.ROOT])

        supply_proxy = max(_finite(getattr(state, "co2_flux_g_m2_s", 0.0), default=0.0) * max(env.dt_s, 0.0), 0.0)
        reserve_proxy = max(_finite(getattr(state, "reserve_ch2o_g", 0.0), default=0.0), 0.0) + max(
            _finite(getattr(state, "buffer_pool_g", 0.0), default=0.0),
            0.0,
        )
        demand_proxy = max(
            _finite(sinks.get("S_fr_g_d", 0.0), default=0.0) + _finite(sinks.get("S_veg_g_d", 0.0), default=0.0),
            1e-9,
        )
        supply_demand_ratio = min((supply_proxy + reserve_proxy) / demand_proxy, 1.5)
        fruit_load_pressure = _finite(sinks.get("S_fr_g_d", 0.0), default=0.0) / demand_proxy

        feedback = apply_fruit_feedback_mode(
            config=config,
            fruit_fraction=legacy_fruit,
            supply_demand_ratio=supply_demand_ratio,
            fruit_load_pressure=fruit_load_pressure,
        )
        fruit_fraction = max(feedback.fruit_fraction, 0.0)
        vegetative_total = max(1.0 - fruit_fraction, 0.0)

        water_supply_stress = _finite(getattr(state, "water_supply_stress", 1.0), default=1.0)
        root_mode = apply_root_mode(
            config=config,
            root_fraction=stable_root,
            legacy_root_fraction=legacy_root,
            thorp_root_fraction=thorp_root,
            water_supply_stress=water_supply_stress,
            state=state,
        )
        root_fraction = min(root_mode.root_fraction, vegetative_total)
        shoot_total = max(vegetative_total - root_fraction, 0.0)

        lai = _finite(getattr(state, "LAI", config.lai_target_center), default=config.lai_target_center)
        leaf_share = _leaf_share_from_modes(
            config=config,
            lai=lai,
            stable_leaf=stable_leaf,
            stable_stem=stable_stem,
            vegetative_total=vegetative_total,
        )

        leaf_fraction = shoot_total * leaf_share
        stem_fraction = max(shoot_total - leaf_fraction, 0.0) + root_mode.stem_fraction_bonus

        total = fruit_fraction + leaf_fraction + stem_fraction + root_fraction
        if total <= 1e-12:
            fruit_fraction, leaf_fraction, stem_fraction, root_fraction = 0.0, 0.7, 0.3, 0.0
            total = 1.0
        fruit_fraction /= total
        leaf_fraction /= total
        stem_fraction /= total
        root_fraction /= total

        _remember_last_research_state(
            state=state,
            architecture_id=config.architecture_id,
            fruit_abort_fraction=feedback.fruit_abort_fraction,
            fruit_set_feedback_events=feedback.fruit_set_feedback_events,
            canopy_lai_floor=config.canopy_lai_floor,
            leaf_fraction_floor=config.leaf_fraction_floor,
            root_fraction=root_fraction,
            supply_demand_ratio=supply_demand_ratio,
        )

        scheme_key = str(scheme).strip().lower()
        if scheme_key == "4pool":
            return AllocationFractions(
                values={
                    Organ.FRUIT: fruit_fraction,
                    Organ.LEAF: leaf_fraction,
                    Organ.STEM: stem_fraction,
                    Organ.ROOT: root_fraction,
                }
            )
        if scheme_key == "3pool":
            return AllocationFractions.from_4pool_to_3pool(
                fruit=fruit_fraction,
                leaf=leaf_fraction,
                stem=stem_fraction,
                root=root_fraction,
            )
        raise ValueError(f"Unsupported partition scheme {scheme!r}; expected '4pool' or '3pool'.")


def _leaf_share_from_modes(
    *,
    config: ResearchArchitectureConfig,
    lai: float,
    stable_leaf: float,
    stable_stem: float,
    vegetative_total: float,
) -> float:
    stable_shoot = max(stable_leaf + stable_stem, 1e-9)
    leaf_share = stable_leaf / stable_shoot

    if config.canopy_governor_mode != "off":
        delta = (config.lai_target_center - lai) / max(config.lai_target_half_band, 1e-6)
        if delta >= 0.0:
            leaf_share += _clamp(delta, 0.0, 1.0) * 0.10
        else:
            leaf_share += _clamp(delta, -1.0, 0.0) * 0.08

    if config.vegetative_demand_mode == "dekoning_vegetative_unit":
        leaf_share += 0.03
    elif config.vegetative_demand_mode == "tomgro_dynamic_age":
        leaf_share -= 0.02

    if config.canopy_governor_mode == "lai_band_plus_leaf_floor" and vegetative_total > 1e-9:
        leaf_share = max(leaf_share, config.leaf_fraction_floor / vegetative_total)

    return _clamp(
        leaf_share,
        config.min_leaf_fraction_of_shoot,
        config.max_leaf_fraction_of_shoot,
    )


def _remember_last_research_state(
    *,
    state: object,
    architecture_id: str,
    fruit_abort_fraction: float,
    fruit_set_feedback_events: int,
    canopy_lai_floor: float,
    leaf_fraction_floor: float,
    root_fraction: float,
    supply_demand_ratio: float,
) -> None:
    values = {
        "research_architecture_id": architecture_id,
        "research_fruit_abort_fraction": float(fruit_abort_fraction),
        "research_fruit_set_feedback_events": float(fruit_set_feedback_events),
        "research_canopy_lai_floor": float(canopy_lai_floor),
        "research_leaf_fraction_floor": float(leaf_fraction_floor),
        "research_root_fraction": float(root_fraction),
        "research_supply_demand_ratio": float(supply_demand_ratio),
    }
    for key, value in values.items():
        try:
            setattr(state, key, value)
        except Exception:
            continue
