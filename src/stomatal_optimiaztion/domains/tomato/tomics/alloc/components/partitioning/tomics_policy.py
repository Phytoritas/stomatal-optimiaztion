from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Mapping

from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.partitioning.fractions import (
    AllocationFractions,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.partitioning.organ import Organ
from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.partitioning.sink_based import (
    SinkBasedTomatoPolicy,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.partitioning.thorp_policies import (
    ThorpVegetativePolicy,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.contracts import (
    EnvStep,
    water_supply_stress_from_theta,
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
    return float(min(max(value, low), high))


def _resolve_param(
    params: Mapping[str, object] | None,
    key: str,
    *,
    default: float,
) -> float:
    if not isinstance(params, Mapping) or key not in params:
        return float(default)
    return _finite(params.get(key), default=default)


def _root_cap_for_stress(
    *,
    water_supply_stress: float,
    wet_root_cap: float,
    dry_root_cap: float,
    f_veg: float,
) -> float:
    low = min(wet_root_cap, dry_root_cap)
    high = max(wet_root_cap, dry_root_cap)
    dryness = 1.0 - _clamp(water_supply_stress, 0.0, 1.0)
    cap = low + dryness * (high - low)
    return _clamp(cap, 0.0, max(f_veg, 0.0))


def _shoot_leaf_share(
    *,
    lai: float | None,
    lai_target_center: float,
    lai_target_half_band: float,
    base_leaf_fraction: float,
    min_leaf_fraction: float,
    max_leaf_fraction: float,
    thorp_leaf_fraction: float,
) -> float:
    leaf_share = float(base_leaf_fraction)
    if lai is not None and math.isfinite(lai):
        half_band = max(float(lai_target_half_band), 1e-6)
        lai_delta = (float(lai_target_center) - float(lai)) / half_band
        if lai_delta >= 0.0:
            leaf_share += _clamp(lai_delta, 0.0, 1.0) * 0.12
        else:
            leaf_share += _clamp(lai_delta, -1.0, 0.0) * 0.08

    leaf_share += 0.25 * (float(thorp_leaf_fraction) - float(base_leaf_fraction))
    return _clamp(leaf_share, float(min_leaf_fraction), float(max_leaf_fraction))


def _resolve_water_supply_stress(
    state: object,
    *,
    default_theta: float = 0.33,
) -> float | None:
    theta = getattr(state, "theta_substrate", None)
    moisture_response_fn = getattr(state, "moisture_response_fn", None)
    if callable(moisture_response_fn):
        return water_supply_stress_from_theta(
            _clamp(_finite(theta, default=default_theta), 0.0, 1.0),
            moisture_response_fn,
        )

    water_supply_stress = getattr(state, "water_supply_stress", None)
    if water_supply_stress is None:
        return None
    return _clamp(_finite(water_supply_stress, default=1.0), 0.0, 1.0)


@dataclass(frozen=True, slots=True)
class TomicsPolicy:
    """Bounded TOMICS hybrid policy over the legacy tomato partitioning path."""

    name: str = "tomics"
    wet_root_cap: float = 0.10
    dry_root_cap: float = 0.18
    lai_target_center: float = 2.75
    lai_target_half_band: float = 0.5
    leaf_fraction_of_shoot_base: float = 0.70
    stem_fraction_of_shoot_base: float = 0.30
    min_leaf_fraction_of_shoot: float = 0.58
    max_leaf_fraction_of_shoot: float = 0.85
    thorp_root_blend: float = 1.0

    def compute(
        self,
        *,
        env: EnvStep,
        state: object,
        sinks: Mapping[str, float],
        scheme: str,
        params: Mapping[str, object] | None = None,
    ) -> AllocationFractions:
        legacy = SinkBasedTomatoPolicy(
            leaf_fraction_of_shoot=self.leaf_fraction_of_shoot_base,
            stem_fraction_of_shoot=self.stem_fraction_of_shoot_base,
        ).compute(
            env=env,
            state=state,
            sinks=sinks,
            scheme="4pool",
            params=params,
        )

        legacy_fruit = float(legacy.values[Organ.FRUIT])
        legacy_leaf = float(legacy.values[Organ.LEAF])
        legacy_stem = float(legacy.values[Organ.STEM])
        legacy_root = float(legacy.values[Organ.ROOT])
        f_veg = max(1.0 - legacy_fruit, 0.0)

        if f_veg <= 1e-12:
            if str(scheme).strip().lower() == "3pool":
                return AllocationFractions(
                    values={Organ.FRUIT: 1.0, Organ.SHOOT: 0.0, Organ.ROOT: 0.0}
                )
            if str(scheme).strip().lower() == "4pool":
                return AllocationFractions(
                    values={
                        Organ.FRUIT: 1.0,
                        Organ.LEAF: 0.0,
                        Organ.STEM: 0.0,
                        Organ.ROOT: 0.0,
                    }
                )
            raise ValueError(
                f"Unsupported partition scheme {scheme!r}; expected '4pool' or '3pool'."
            )

        water_supply_stress = _resolve_water_supply_stress(state)
        if water_supply_stress is None:
            if str(scheme).strip().lower() == "3pool":
                return AllocationFractions.from_4pool_to_3pool(
                    fruit=legacy_fruit,
                    leaf=legacy_leaf,
                    stem=legacy_stem,
                    root=legacy_root,
                )
            if str(scheme).strip().lower() == "4pool":
                return legacy
            raise ValueError(
                f"Unsupported partition scheme {scheme!r}; expected '4pool' or '3pool'."
            )

        try:
            thorp = ThorpVegetativePolicy().compute(
                env=env,
                state=state,
                sinks=sinks,
                scheme="4pool",
                params=params,
            )
        except Exception:
            thorp = legacy

        thorp_leaf = max(float(thorp.values.get(Organ.LEAF, legacy_leaf)), 0.0)
        thorp_stem = max(float(thorp.values.get(Organ.STEM, legacy_stem)), 0.0)
        thorp_root = max(float(thorp.values.get(Organ.ROOT, legacy_root)), 0.0)
        thorp_shoot = thorp_leaf + thorp_stem
        thorp_leaf_fraction = 0.70
        if thorp_shoot > 1e-12:
            thorp_leaf_fraction = thorp_leaf / thorp_shoot

        wet_root_cap = _resolve_param(params, "wet_root_cap", default=self.wet_root_cap)
        dry_root_cap = _resolve_param(params, "dry_root_cap", default=self.dry_root_cap)
        lai_target_center = _resolve_param(
            params,
            "lai_target_center",
            default=self.lai_target_center,
        )
        lai_target_half_band = _resolve_param(
            params,
            "lai_target_half_band",
            default=self.lai_target_half_band,
        )
        base_leaf_fraction = _resolve_param(
            params,
            "leaf_fraction_of_shoot_base",
            default=self.leaf_fraction_of_shoot_base,
        )
        min_leaf_fraction = _resolve_param(
            params,
            "min_leaf_fraction_of_shoot",
            default=self.min_leaf_fraction_of_shoot,
        )
        max_leaf_fraction = _resolve_param(
            params,
            "max_leaf_fraction_of_shoot",
            default=self.max_leaf_fraction_of_shoot,
        )
        thorp_root_blend = _resolve_param(
            params,
            "thorp_root_blend",
            default=self.thorp_root_blend,
        )

        root_cap_total = _root_cap_for_stress(
            water_supply_stress=water_supply_stress,
            wet_root_cap=wet_root_cap,
            dry_root_cap=dry_root_cap,
            f_veg=f_veg,
        )
        blended_root = legacy_root + (1.0 - water_supply_stress) * max(
            (thorp_root - legacy_root) * thorp_root_blend,
            0.0,
        )
        root_total = min(root_cap_total, max(legacy_root, blended_root))
        root_total = _clamp(root_total, 0.0, f_veg)

        shoot_total = max(f_veg - root_total, 0.0)
        lai_raw = getattr(state, "LAI", None)
        lai = None if lai_raw is None else _finite(lai_raw, default=lai_target_center)
        leaf_share = _shoot_leaf_share(
            lai=lai,
            lai_target_center=lai_target_center,
            lai_target_half_band=lai_target_half_band,
            base_leaf_fraction=base_leaf_fraction,
            min_leaf_fraction=min_leaf_fraction,
            max_leaf_fraction=max_leaf_fraction,
            thorp_leaf_fraction=thorp_leaf_fraction,
        )
        stem_share = max(1.0 - leaf_share, 0.0)

        leaf_total = shoot_total * leaf_share
        stem_total = shoot_total * stem_share

        scheme_key = str(scheme).strip().lower()
        if scheme_key == "4pool":
            return AllocationFractions(
                values={
                    Organ.FRUIT: legacy_fruit,
                    Organ.LEAF: leaf_total,
                    Organ.STEM: stem_total,
                    Organ.ROOT: root_total,
                }
            )

        if scheme_key == "3pool":
            return AllocationFractions(
                values={
                    Organ.FRUIT: legacy_fruit,
                    Organ.SHOOT: shoot_total,
                    Organ.ROOT: root_total,
                }
            )

        raise ValueError(f"Unsupported partition scheme {scheme!r}; expected '4pool' or '3pool'.")


__all__ = ["TomicsPolicy"]
