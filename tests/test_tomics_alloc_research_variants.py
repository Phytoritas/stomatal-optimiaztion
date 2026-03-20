from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime

import pytest

from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.partitioning import (
    Organ,
    build_partition_policy,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.partitioning.research_modes import (
    ResearchArchitectureConfig,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.contracts import EnvStep


@dataclass(slots=True)
class _State:
    root_frac_of_total_veg: float = 0.15 / 1.15
    co2_flux_g_m2_s: float = 0.02
    reserve_ch2o_g: float = 8.0
    research_buffer_pool_g: float = 0.0
    W_lv: float = 50.0
    W_st: float = 20.0
    theta_substrate: float = 0.33
    water_supply_stress: float = 0.8
    LAI: float = 2.4


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


def test_research_policy_preserves_fraction_invariants() -> None:
    policy = build_partition_policy("tomics_alloc_research")
    fracs = policy.compute(
        env=_env(),
        state=_State(),
        sinks=_sinks(),
        scheme="4pool",
        params={
            "architecture_id": "unit_test_candidate",
            "fruit_structure_mode": "tomsim_truss_cohort",
            "fruit_partition_mode": "legacy_sink_exact",
            "vegetative_demand_mode": "dekoning_vegetative_unit",
            "reserve_buffer_mode": "tomsim_storage_pool",
            "fruit_feedback_mode": "off",
            "sla_mode": "derived_not_driver",
            "maintenance_mode": "rgr_adjusted",
            "canopy_governor_mode": "lai_band_plus_leaf_floor",
            "root_representation_mode": "bounded_explicit_root",
            "thorp_root_correction_mode": "bounded_hysteretic",
            "temporal_coupling_mode": "buffered_daily",
            "allocation_scheme": "4pool",
            "wet_root_cap": 0.08,
            "dry_root_cap": 0.18,
            "smoothing_tau_days": 3.0,
            "thorp_root_blend": 0.5,
        },
    )

    assert set(fracs.values) == {Organ.FRUIT, Organ.LEAF, Organ.STEM, Organ.ROOT}
    values = list(fracs.values.values())
    assert all(math.isfinite(value) for value in values)
    assert all(value >= 0.0 for value in values)
    assert sum(values) == pytest.approx(1.0, abs=1e-9)


def test_unsupported_research_mode_combination_fails_clearly() -> None:
    with pytest.raises(ValueError, match="buffered_daily"):
        ResearchArchitectureConfig.from_params(
            {
                "reserve_buffer_mode": "vanthoor_carbohydrate_buffer",
                "temporal_coupling_mode": "daily_alloc",
            }
        )
