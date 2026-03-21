from __future__ import annotations

import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.harvest.contracts import (
    FruitHarvestEvent,
    HarvestState,
    LeafHarvestEvent,
)


def _sum_positive(frame: pd.DataFrame, column: str) -> float:
    if column not in frame.columns or frame.empty:
        return 0.0
    values = pd.to_numeric(frame[column], errors="coerce").fillna(0.0)
    return float(values.clip(lower=0.0).sum())


def harvest_mass_balance_error(
    before_state: HarvestState,
    after_state: HarvestState,
    fruit_events: list[FruitHarvestEvent],
    leaf_events: list[LeafHarvestEvent],
) -> float:
    before_fruit = _sum_positive(before_state.fruit_entities, "fruit_dm_g_m2")
    after_fruit = _sum_positive(after_state.fruit_entities, "fruit_dm_g_m2")
    fruit_flux = sum(max(float(event.dry_weight_g_m2), 0.0) for event in fruit_events)
    fruit_error = abs(before_fruit - after_fruit - fruit_flux)

    before_leaf = _sum_positive(before_state.leaf_entities, "leaf_dm_g_m2")
    after_leaf = _sum_positive(after_state.leaf_entities, "leaf_dm_g_m2")
    leaf_flux = sum(max(float(event.leaf_harvest_flux_g_m2), 0.0) for event in leaf_events)
    leaf_error = abs(before_leaf - after_leaf - leaf_flux)
    return float(max(fruit_error, leaf_error))


def duplicate_harvest_flag(events: list[FruitHarvestEvent]) -> bool:
    entity_ids = [event.entity_id for event in events]
    return len(entity_ids) != len(set(entity_ids))


def negative_mass_flag(state: HarvestState) -> bool:
    fruit_negative = (pd.to_numeric(state.fruit_entities.get("fruit_dm_g_m2"), errors="coerce").fillna(0.0) < -1e-9).any()
    leaf_negative = (pd.to_numeric(state.leaf_entities.get("leaf_dm_g_m2"), errors="coerce").fillna(0.0) < -1e-9).any()
    return bool(fruit_negative or leaf_negative)


def mass_balance_metrics(
    before_state: HarvestState,
    after_state: HarvestState,
    *,
    fruit_events: list[FruitHarvestEvent],
    leaf_events: list[LeafHarvestEvent],
) -> dict[str, float | bool]:
    return {
        "harvest_mass_balance_error": harvest_mass_balance_error(before_state, after_state, fruit_events, leaf_events),
        "latent_fruit_residual_end": _sum_positive(after_state.fruit_entities, "fruit_dm_g_m2"),
        "leaf_harvest_mass_balance_error": abs(
            _sum_positive(before_state.leaf_entities, "leaf_dm_g_m2")
            - _sum_positive(after_state.leaf_entities, "leaf_dm_g_m2")
            - sum(max(float(event.leaf_harvest_flux_g_m2), 0.0) for event in leaf_events)
        ),
        "duplicate_harvest_flag": duplicate_harvest_flag(fruit_events),
        "negative_mass_flag": negative_mass_flag(after_state),
    }


def cumulative_monotonic_flag(series: pd.Series) -> bool:
    values = pd.to_numeric(series, errors="coerce").dropna()
    if values.empty:
        return True
    diffs = values.diff().dropna()
    return bool((diffs >= -1e-9).all())


__all__ = [
    "cumulative_monotonic_flag",
    "duplicate_harvest_flag",
    "harvest_mass_balance_error",
    "mass_balance_metrics",
    "negative_mass_flag",
]
