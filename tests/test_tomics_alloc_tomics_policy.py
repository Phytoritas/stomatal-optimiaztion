from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime

import pytest

from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.partitioning import (
    Organ,
    SinkBasedTomatoPolicy,
    ThorpVegetativePolicy,
    TomicsPolicy,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.contracts import EnvStep


@dataclass(frozen=True, slots=True)
class _TomatoState:
    root_frac_of_total_veg: float = 0.15 / 1.15
    co2_flux_g_m2_s: float = 0.02
    W_lv: float = 50.0
    W_st: float = 20.0
    theta_substrate: float = 0.33
    LAI: float = 2.4

    @staticmethod
    def moisture_response_fn(theta: float) -> float:
        return theta / 0.4


@dataclass(frozen=True, slots=True)
class _FallbackState:
    root_frac_of_total_veg: float = 0.15 / 1.15
    co2_flux_g_m2_s: float = 0.02
    W_lv: float = 50.0
    W_st: float = 20.0
    LAI: float = 2.4


def _env() -> EnvStep:
    return EnvStep(
        t=datetime(2026, 1, 1, 12, 0, 0),
        dt_s=3600.0,
        T_air_C=25.0,
        PAR_umol=400.0,
        CO2_ppm=420.0,
        RH_percent=60.0,
        wind_speed_ms=1.0,
    )


def _sinks() -> dict[str, float]:
    return {"S_fr_g_d": 6.0, "S_veg_g_d": 4.0}


@pytest.mark.parametrize("scheme", ["4pool", "3pool"])
def test_tomics_policy_invariants(scheme: str) -> None:
    fracs = TomicsPolicy().compute(
        env=_env(),
        state=_TomatoState(theta_substrate=0.33, LAI=2.4),
        sinks=_sinks(),
        scheme=scheme,
        params=None,
    )

    values = list(fracs.values.values())
    assert values
    assert all(math.isfinite(value) for value in values)
    assert all(value >= 0.0 for value in values)
    assert sum(values) == pytest.approx(1.0, abs=1e-9)


def test_tomics_policy_anchors_fruit_fraction_to_legacy_sink_law() -> None:
    env = _env()
    state = _TomatoState(theta_substrate=0.33, LAI=2.4)
    sinks = _sinks()

    legacy = SinkBasedTomatoPolicy().compute(
        env=env,
        state=state,
        sinks=sinks,
        scheme="4pool",
        params=None,
    )
    tomics = TomicsPolicy().compute(
        env=env,
        state=state,
        sinks=sinks,
        scheme="4pool",
        params=None,
    )

    assert tomics.values[Organ.FRUIT] == pytest.approx(legacy.values[Organ.FRUIT], abs=1e-12)


def test_tomics_policy_moderates_root_and_protects_leaf_under_wet_conditions() -> None:
    env = _env()
    sinks = _sinks()
    wet_state = _TomatoState(theta_substrate=0.50, LAI=2.0)

    tomics = TomicsPolicy().compute(
        env=env,
        state=wet_state,
        sinks=sinks,
        scheme="4pool",
        params={"wet_root_cap": 0.10, "dry_root_cap": 0.18, "lai_target_center": 2.5},
    )
    thorp = ThorpVegetativePolicy().compute(
        env=env,
        state=wet_state,
        sinks=sinks,
        scheme="4pool",
        params=None,
    )

    assert tomics.values[Organ.ROOT] <= 0.10 + 1e-12
    assert tomics.values[Organ.ROOT] < thorp.values[Organ.ROOT]
    assert tomics.values[Organ.LEAF] > thorp.values[Organ.LEAF]


def test_tomics_policy_falls_back_to_legacy_like_behavior_when_stress_inputs_are_missing() -> None:
    env = _env()
    state = _FallbackState()
    sinks = _sinks()

    legacy = SinkBasedTomatoPolicy().compute(
        env=env,
        state=state,
        sinks=sinks,
        scheme="4pool",
        params=None,
    )
    tomics = TomicsPolicy().compute(
        env=env,
        state=state,
        sinks=sinks,
        scheme="4pool",
        params={"wet_root_cap": 0.08, "dry_root_cap": 0.15},
    )

    assert tomics.values == legacy.values
