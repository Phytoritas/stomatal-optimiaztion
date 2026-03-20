from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime

import numpy as np
import pytest

from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.partitioning import (
    AllocationFractions,
    Organ,
    PartitionPolicy,
    SinkBasedTomatoPolicy,
    ThorpFruitVegPolicy,
    ThorpObjectiveParams,
    ThorpVegetativePolicy,
    build_partition_policy,
    coerce_partition_policy,
    objective_params_from_thorp,
    thorp_allocation_fractions,
    tomato_partitioning,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.contracts import EnvStep
from stomatal_optimiaztion.domains.tomato.tomics.alloc.models.tomato_legacy import TomatoModel


@dataclass(frozen=True, slots=True)
class _DummyState:
    root_frac_of_total_veg: float = 0.15 / 1.15
    co2_flux_g_m2_s: float = 0.02
    W_lv: float = 50.0
    W_st: float = 20.0


@dataclass(frozen=True, slots=True)
class _CustomPolicy:
    name: str = "custom"

    def compute(
        self,
        *,
        env: EnvStep,
        state: object,
        sinks: dict[str, float],
        scheme: str,
        params: dict[str, object] | None = None,
    ) -> AllocationFractions:
        del env
        del state
        del sinks
        del scheme
        del params
        return AllocationFractions(
            values={
                Organ.FRUIT: 0.25,
                Organ.LEAF: 0.35,
                Organ.STEM: 0.25,
                Organ.ROOT: 0.15,
            }
        )


def _env() -> EnvStep:
    return EnvStep(
        t=datetime(2026, 1, 1, 0, 0, 0),
        dt_s=3600.0,
        T_air_C=25.0,
        PAR_umol=400.0,
        CO2_ppm=420.0,
        RH_percent=60.0,
        wind_speed_ms=1.0,
    )


def _base_kwargs() -> dict[str, object]:
    return {
        "a_n": 6.0,
        "lambda_wue": 1.2,
        "d_a_n_d_r_abs": 0.03,
        "d_e_d_la": 0.015,
        "d_e_d_d": 0.004,
        "d_e_d_c_r_h": np.array([0.006, 0.004], dtype=float),
        "d_e_d_c_r_v": np.array([0.003, 0.002], dtype=float),
        "d_r_abs_d_h": 20.0,
        "d_r_abs_d_w": 8.0,
        "d_r_abs_d_la": 0.2,
        "h": 1.5,
        "w": 0.08,
        "d": 0.02,
        "c_w": 4.0,
        "c_l": 1.0,
        "c0": 0.6411,
        "c1": 0.625,
        "t_a": 25.0,
        "t_soil": 23.0,
    }


def _objective() -> ThorpObjectiveParams:
    return ThorpObjectiveParams(
        sla=0.08,
        tau_l=200.0,
        tau_r=365.0,
        tau_sw=400.0,
        r_m_sw_func=lambda _t: 0.01,
        r_m_r_func=lambda _t: 0.008,
    )


def test_scheme_roundtrip_3pool_to_4pool_to_3pool() -> None:
    original = AllocationFractions(values={Organ.FRUIT: 0.3, Organ.SHOOT: 0.5, Organ.ROOT: 0.2})
    as_4pool = AllocationFractions.from_3pool_to_4pool(
        fruit=original.values[Organ.FRUIT],
        shoot=original.values[Organ.SHOOT],
        root=original.values[Organ.ROOT],
    )
    back = AllocationFractions.from_4pool_to_3pool(
        fruit=as_4pool.values[Organ.FRUIT],
        leaf=as_4pool.values[Organ.LEAF],
        stem=as_4pool.values[Organ.STEM],
        root=as_4pool.values[Organ.ROOT],
    )

    assert back.values[Organ.FRUIT] == pytest.approx(original.values[Organ.FRUIT], abs=1e-12)
    assert back.values[Organ.SHOOT] == pytest.approx(original.values[Organ.SHOOT], abs=1e-12)
    assert back.values[Organ.ROOT] == pytest.approx(original.values[Organ.ROOT], abs=1e-12)


def test_3pool_to_4pool_default_ratio_matches_legacy_split() -> None:
    fractions = AllocationFractions.from_3pool_to_4pool(fruit=0.4, shoot=0.5, root=0.1)

    assert fractions.values[Organ.FRUIT] == pytest.approx(0.4)
    assert fractions.values[Organ.LEAF] == pytest.approx(0.35)
    assert fractions.values[Organ.STEM] == pytest.approx(0.15)
    assert fractions.values[Organ.ROOT] == pytest.approx(0.1)


@pytest.mark.parametrize("scheme", ["4pool", "3pool"])
def test_sink_based_policy_invariants(scheme: str) -> None:
    fracs = SinkBasedTomatoPolicy().compute(
        env=_env(),
        state=_DummyState(),
        sinks={"S_fr_g_d": 12.0, "S_veg_g_d": 4.0},
        scheme=scheme,
        params=None,
    )

    values = list(fracs.values.values())
    assert values
    assert all(math.isfinite(value) for value in values)
    assert all(0.0 <= value <= 1.0 for value in values)
    assert sum(values) == pytest.approx(1.0, abs=1e-9)


def test_build_partition_policy_supports_sink_based_aliases_only() -> None:
    assert build_partition_policy("sink_based").name == "sink_based"
    assert build_partition_policy("sink-based").name == "sink_based"
    assert build_partition_policy("default").name == "sink_based"
    assert build_partition_policy("thorp_veg").name == "thorp_veg"
    assert build_partition_policy("thorp_opt").name == "thorp_veg"
    assert build_partition_policy("thorp_fruit_veg").name == "thorp_fruit_veg"
    assert build_partition_policy("thorp_4pool").name == "thorp_fruit_veg"


def test_coerce_partition_policy_accepts_protocol_instances() -> None:
    policy = _CustomPolicy()

    out = coerce_partition_policy(policy)

    assert isinstance(out, PartitionPolicy)
    assert out.name == "custom"


def test_tomato_model_defaults_to_sink_based_policy() -> None:
    model = TomatoModel()

    assert model.partition_policy.name == "sink_based"

    explicit = TomatoModel(partition_policy="sink-based")
    assert explicit.partition_policy.name == "sink_based"


def test_ported_allocation_returns_unit_sum() -> None:
    alloc = thorp_allocation_fractions(
        **_base_kwargs(),
        objective_params=_objective(),
        prefer_thorp=False,
    )
    total = alloc.u_l + alloc.u_sw + float(np.sum(alloc.u_r_h + alloc.u_r_v))
    assert alloc.backend == "ported"
    assert np.isclose(total, 1.0, atol=1e-12)
    assert alloc.u_l >= 0.0
    assert alloc.u_sw >= 0.0
    assert np.all(alloc.u_r_h >= 0.0)
    assert np.all(alloc.u_r_v >= 0.0)


def test_tomato_partitioning_collapses_root_components() -> None:
    out = tomato_partitioning(
        **_base_kwargs(),
        objective_params=_objective(),
        prefer_thorp=False,
    )
    assert np.isclose(out.u_leaf + out.u_stem + out.u_root, 1.0, atol=1e-12)
    assert out.uL == out.u_leaf
    assert out.uS == out.u_stem
    assert out.uR == out.u_root


def test_c_l_zero_forces_leaf_allocation() -> None:
    kwargs = _base_kwargs()
    kwargs["c_l"] = 0.0
    alloc = thorp_allocation_fractions(
        **kwargs,
        objective_params=_objective(),
        prefer_thorp=False,
    )
    assert alloc.u_l == 1.0
    assert alloc.u_sw == 0.0
    assert np.allclose(alloc.u_r_h, 0.0)
    assert np.allclose(alloc.u_r_v, 0.0)


@dataclass(frozen=True, slots=True)
class _DummyThorpParams:
    sla: float = 0.08
    tau_l: float = 200.0
    tau_r: float = 365.0
    tau_sw: float = 400.0

    @staticmethod
    def r_m_sw_func(_t: float) -> float:
        return 0.01

    @staticmethod
    def r_m_r_func(_t: float) -> float:
        return 0.008


def test_missing_thorp_import_falls_back_to_port(monkeypatch: pytest.MonkeyPatch) -> None:
    import stomatal_optimiaztion.domains.tomato.tomics.alloc.components.partitioning.thorp_opt as thorp_opt

    monkeypatch.setattr(thorp_opt, "_import_thorp_allocation", lambda: None)

    alloc = thorp_allocation_fractions(
        **_base_kwargs(),
        thorp_params=_DummyThorpParams(),
        prefer_thorp=True,
        allow_port_fallback=True,
    )
    assert alloc.backend == "ported"


def test_objective_params_from_thorp_extracts_required_fields() -> None:
    params = objective_params_from_thorp(_DummyThorpParams())
    assert params.sla == 0.08
    assert params.tau_l == 200.0
    assert params.tau_r == 365.0
    assert params.tau_sw == 400.0


@pytest.mark.parametrize("scheme", ["4pool", "3pool"])
@pytest.mark.parametrize("policy", [SinkBasedTomatoPolicy(), ThorpVegetativePolicy()])
def test_partition_policy_invariants(policy: PartitionPolicy, scheme: str) -> None:
    fracs = policy.compute(
        env=_env(),
        state=_DummyState(co2_flux_g_m2_s=0.02),
        sinks={"S_fr_g_d": 12.0, "S_veg_g_d": 4.0},
        scheme=scheme,
        params=None,
    )

    values = list(fracs.values.values())
    assert values
    assert all(math.isfinite(v) for v in values)
    assert all(0.0 <= v <= 1.0 for v in values)
    assert sum(values) == pytest.approx(1.0, abs=1e-9)


def test_fruit_fraction_is_zero_when_fruit_sink_is_zero() -> None:
    env = _env()
    state = _DummyState(co2_flux_g_m2_s=0.02)
    sinks = {"S_fr_g_d": 0.0, "S_veg_g_d": 10.0}

    out_sink = SinkBasedTomatoPolicy().compute(
        env=env,
        state=state,
        sinks=sinks,
        scheme="4pool",
        params=None,
    )
    assert out_sink.values[Organ.FRUIT] == pytest.approx(0.0, abs=1e-15)

    out_thorp = ThorpVegetativePolicy().compute(
        env=env,
        state=state,
        sinks=sinks,
        scheme="4pool",
        params=None,
    )
    assert out_thorp.values[Organ.FRUIT] == pytest.approx(0.0, abs=1e-15)


def test_thorp_fruit_veg_policy_preserves_fraction_sum() -> None:
    fracs = ThorpFruitVegPolicy(w_fruit=0.4).compute(
        env=_env(),
        state=_DummyState(),
        sinks={"S_fr_g_d": 6.0, "S_veg_g_d": 4.0},
        scheme="4pool",
        params=None,
    )

    assert sum(fracs.values.values()) == pytest.approx(1.0, abs=1e-9)
    assert fracs.values[Organ.FRUIT] > 0.0


def test_tomato_model_accepts_thorp_partition_policy() -> None:
    model = TomatoModel(partition_policy="thorp_veg")
    model.update_inputs_from_row(
        {
            "T_air_C": 25.0,
            "PAR_umol": 500.0,
            "CO2_ppm": 420.0,
            "RH_percent": 60.0,
            "wind_speed_ms": 1.0,
            "n_fruits_per_truss": 4.0,
        }
    )

    current_time = datetime(2026, 1, 1, 12, 0, 0)
    model.run_timestep_calculations(3600.0, current_time)

    assert model.partition_policy.name == "thorp_veg"
    assert math.isfinite(model.part_leaf)
    assert math.isfinite(model.part_stem)
    assert math.isfinite(model.part_root)
    assert model.part_leaf + model.part_stem + model.part_root + model.part_fruit == pytest.approx(
        1.0, abs=1e-9
    )
