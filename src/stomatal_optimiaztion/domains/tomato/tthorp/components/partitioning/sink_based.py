from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from stomatal_optimiaztion.domains.tomato.tthorp.components.partitioning.fractions import (
    AllocationFractions,
)
from stomatal_optimiaztion.domains.tomato.tthorp.components.partitioning.organ import Organ
from stomatal_optimiaztion.domains.tomato.tthorp.contracts import EnvStep


def _sink_fraction(*, numerator: float, denominator: float) -> float:
    if denominator > 1e-9:
        return numerator / denominator
    return 0.0


@dataclass(frozen=True, slots=True)
class SinkBasedTomatoPolicy:
    """Legacy tomato sink-based partitioning fractions."""

    name: str = "sink_based"
    leaf_fraction_of_shoot: float = 0.7
    stem_fraction_of_shoot: float = 0.3

    def compute(
        self,
        *,
        env: EnvStep,
        state: object,
        sinks: Mapping[str, float],
        scheme: str,
        params: Mapping[str, object] | None = None,
    ) -> AllocationFractions:
        del env
        del params

        s_fr_g_d = float(sinks.get("S_fr_g_d", 0.0))
        s_veg_g_d = float(sinks.get("S_veg_g_d", 0.0))

        s_fr_g_d = max(0.0, s_fr_g_d)
        s_veg_g_d = max(1e-9, s_veg_g_d)
        s_total_g_d = s_fr_g_d + s_veg_g_d
        f_fr_total = _sink_fraction(numerator=s_fr_g_d, denominator=s_total_g_d)
        f_veg_total = 1.0 - f_fr_total

        root_frac_of_total_veg = float(getattr(state, "root_frac_of_total_veg", 0.15 / 1.15))
        f_rt = f_veg_total * root_frac_of_total_veg
        f_shoot = f_veg_total - f_rt
        f_lv = f_shoot * self.leaf_fraction_of_shoot
        f_st = f_shoot * self.stem_fraction_of_shoot

        scheme_key = str(scheme).strip().lower()
        if scheme_key == "4pool":
            return AllocationFractions(
                values={
                    Organ.FRUIT: f_fr_total,
                    Organ.LEAF: f_lv,
                    Organ.STEM: f_st,
                    Organ.ROOT: f_rt,
                }
            )

        if scheme_key == "3pool":
            return AllocationFractions(
                values={
                    Organ.FRUIT: f_fr_total,
                    Organ.SHOOT: f_shoot,
                    Organ.ROOT: f_rt,
                }
            )

        raise ValueError(f"Unsupported partition scheme {scheme!r}; expected '4pool' or '3pool'.")
