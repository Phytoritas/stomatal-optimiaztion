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


def _sum_onplant_positive(frame: pd.DataFrame, column: str) -> float:
    if frame.empty or column not in frame.columns:
        return 0.0
    onplant_mask = frame.get("onplant_flag", True)
    if not isinstance(onplant_mask, pd.Series):
        onplant_mask = pd.Series([bool(onplant_mask)] * len(frame), index=frame.index)
    values = pd.to_numeric(frame.loc[onplant_mask.fillna(True).astype(bool), column], errors="coerce").fillna(0.0)
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


def offplant_with_positive_mass_flag(state: HarvestState) -> bool:
    if state.fruit_entities.empty or "fruit_dm_g_m2" not in state.fruit_entities.columns:
        return False
    onplant_mask = state.fruit_entities.get("onplant_flag", True)
    if not isinstance(onplant_mask, pd.Series):
        onplant_mask = pd.Series([bool(onplant_mask)] * len(state.fruit_entities), index=state.fruit_entities.index)
    offplant_mask = ~onplant_mask.fillna(True).astype(bool)
    values = pd.to_numeric(state.fruit_entities.loc[offplant_mask, "fruit_dm_g_m2"], errors="coerce").fillna(0.0)
    return bool((values > 1e-12).any())


def mass_balance_metrics(
    before_state: HarvestState,
    after_state: HarvestState,
    *,
    fruit_events: list[FruitHarvestEvent],
    leaf_events: list[LeafHarvestEvent],
) -> dict[str, float | bool]:
    pre_onplant_fruit = _sum_onplant_positive(before_state.fruit_entities, "fruit_dm_g_m2")
    post_onplant_fruit = _sum_onplant_positive(after_state.fruit_entities, "fruit_dm_g_m2")
    harvested_flux = float(sum(max(float(event.dry_weight_g_m2), 0.0) for event in fruit_events))
    partial_event_ids = {event.entity_id for event in fruit_events if bool(getattr(event, "partial_outflow_flag", False))}
    partial_residual = 0.0
    if partial_event_ids and not after_state.fruit_entities.empty:
        partial_mask = after_state.fruit_entities["entity_id"].astype(str).isin({str(value) for value in partial_event_ids})
        partial_residual = float(
            pd.to_numeric(after_state.fruit_entities.loc[partial_mask, "fruit_dm_g_m2"], errors="coerce").fillna(0.0).sum()
        )
    return {
        "harvest_mass_balance_error": harvest_mass_balance_error(before_state, after_state, fruit_events, leaf_events),
        "pre_onplant_fruit_g_m2": pre_onplant_fruit,
        "post_onplant_fruit_g_m2": post_onplant_fruit,
        "harvested_fruit_flux_g_m2": harvested_flux,
        "partial_outflow_mass_residual_g_m2": partial_residual,
        "dropped_nonharvested_mass_g_m2": max(pre_onplant_fruit - post_onplant_fruit - harvested_flux, 0.0),
        "offplant_with_positive_mass_flag": offplant_with_positive_mass_flag(after_state),
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
    "offplant_with_positive_mass_flag",
]
