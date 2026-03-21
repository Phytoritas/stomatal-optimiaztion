from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime

import pytest

from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.partitioning import (
    Organ,
    build_partition_policy,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.contracts import EnvStep


@dataclass(slots=True)
class _State:
    root_frac_of_total_veg: float = 0.15 / 1.15
    co2_flux_g_m2_s: float = 0.02
    reserve_ch2o_g: float = 8.0
    research_buffer_pool_g: float = 0.0
    buffer_pool_g: float = 0.0
    W_lv: float = 50.0
    W_st: float = 20.0
    theta_substrate: float = 0.65
    water_supply_stress: float = 0.85
    LAI: float = 2.5
    dt_seconds: float = 3600.0
    truss_count: float = 8.0
    active_trusses: float = 4.0
    VPD: float = 1.2
    rootzone_multistress: float = 0.10
    rootzone_saturation: float = 0.05


def _env() -> EnvStep:
    return EnvStep(
        t=datetime(2026, 1, 1, 12, 0, 0),
        dt_s=3600.0,
        T_air_C=25.0,
        PAR_umol=500.0,
        CO2_ppm=420.0,
        RH_percent=60.0,
        wind_speed_ms=1.0,
    )


def _sinks() -> dict[str, float]:
    return {"S_fr_g_d": 6.0, "S_veg_g_d": 4.0}


def test_promoted_policy_preserves_fraction_invariants_and_keeps_fruit_anchor() -> None:
    promoted = build_partition_policy("tomics_promoted_research")
    legacy = build_partition_policy("legacy")
    state = _State()
    params = {
        "optimizer_mode": "prior_weighted_softmax_plus_lowpass",
        "vegetative_prior_mode": "current_tomics_prior",
        "leaf_marginal_mode": "canopy_plus_weak_sink_penalty",
        "stem_marginal_mode": "support_transport_positioning",
        "root_marginal_mode": "greenhouse_multistress_gate_plus_saturation",
        "fruit_feedback_mode": "off",
        "reserve_buffer_mode": "tomsim_storage_pool",
        "canopy_governor_mode": "lai_band_plus_leaf_floor",
        "temporal_mode": "subdaily_signal_daily_integral_alloc_lowpass",
        "thorp_root_correction_mode": "bounded",
        "allocation_scheme": "4pool",
        "beta": 3.0,
        "tau_alloc_days": 3.0,
    }

    promoted_fracs = promoted.compute(env=_env(), state=state, sinks=_sinks(), scheme="4pool", params=params)
    legacy_fracs = legacy.compute(env=_env(), state=_State(), sinks=_sinks(), scheme="4pool", params={})

    values = list(promoted_fracs.values.values())
    assert set(promoted_fracs.values) == {Organ.FRUIT, Organ.LEAF, Organ.STEM, Organ.ROOT}
    assert all(math.isfinite(value) for value in values)
    assert all(value >= 0.0 for value in values)
    assert sum(values) == pytest.approx(1.0, abs=1e-9)
    assert promoted_fracs.values[Organ.FRUIT] == pytest.approx(legacy_fracs.values[Organ.FRUIT], abs=1e-9)


def test_shipped_tomics_policy_key_stays_distinct_from_promoted_research() -> None:
    shipped = build_partition_policy("tomics")
    promoted = build_partition_policy("tomics_promoted_research")

    assert shipped.name == "tomics"
    assert promoted.name == "tomics_promoted_research"
