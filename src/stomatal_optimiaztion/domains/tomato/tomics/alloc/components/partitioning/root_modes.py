from __future__ import annotations

import math
from dataclasses import dataclass

from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.partitioning.research_modes import (
    ResearchArchitectureConfig,
)


@dataclass(frozen=True, slots=True)
class RootModeResult:
    root_fraction: float
    stem_fraction_bonus: float
    hysteretic_root_target: float


def apply_root_mode(
    *,
    config: ResearchArchitectureConfig,
    root_fraction: float,
    legacy_root_fraction: float,
    thorp_root_fraction: float,
    water_supply_stress: float,
    state: object,
) -> RootModeResult:
    root_fraction = max(float(root_fraction), 0.0)
    legacy_root = max(float(legacy_root_fraction), 0.0)
    thorp_root = max(float(thorp_root_fraction), 0.0)
    stress = min(max(float(water_supply_stress), 0.0), 1.0)
    stem_bonus = 0.0

    if config.thorp_root_correction_mode == "off":
        target = legacy_root
    elif config.thorp_root_correction_mode == "bounded":
        target = root_fraction
    else:
        previous = _state_attr(state, "_tomics_research_prev_root_target", legacy_root)
        alpha = math.exp(-1.0 / max(config.smoothing_tau_days, 1e-6))
        proposed = root_fraction + (1.0 - stress) * config.hysteresis_gain * max(thorp_root - legacy_root, 0.0)
        target = alpha * previous + (1.0 - alpha) * proposed
        _try_set_state_attr(state, "_tomics_research_prev_root_target", target)

    if config.root_representation_mode == "implicit_small_root":
        target = min(target, max(legacy_root, config.wet_root_cap))
    elif config.root_representation_mode == "stem_root_lumped_vanthoor":
        target = min(target * 0.5, max(config.wet_root_cap * 0.8, 0.06))
        stem_bonus = max(root_fraction - target, 0.0)

    target = min(max(target, 0.0), 1.0)
    return RootModeResult(
        root_fraction=target,
        stem_fraction_bonus=stem_bonus,
        hysteretic_root_target=target,
    )


def _state_attr(state: object, name: str, default: float) -> float:
    raw = getattr(state, name, default)
    try:
        return float(raw)
    except (TypeError, ValueError):
        return float(default)


def _try_set_state_attr(state: object, name: str, value: float) -> None:
    try:
        setattr(state, name, float(value))
    except Exception:
        return
