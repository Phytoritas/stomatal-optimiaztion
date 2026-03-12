from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime

import pytest

from stomatal_optimiaztion.domains.tomato.tthorp.components.partitioning import (
    AllocationFractions,
    Organ,
    PartitionPolicy,
    SinkBasedTomatoPolicy,
    build_partition_policy,
    coerce_partition_policy,
)
from stomatal_optimiaztion.domains.tomato.tthorp.contracts import EnvStep
from stomatal_optimiaztion.domains.tomato.tthorp.models.tomato_legacy import TomatoModel


@dataclass(frozen=True, slots=True)
class _DummyState:
    root_frac_of_total_veg: float = 0.15 / 1.15


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

    with pytest.raises(NotImplementedError, match="not migrated yet"):
        build_partition_policy("thorp_veg")


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
