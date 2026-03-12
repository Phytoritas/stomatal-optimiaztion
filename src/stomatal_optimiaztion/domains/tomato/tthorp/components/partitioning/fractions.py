from __future__ import annotations

import math
from dataclasses import dataclass

from stomatal_optimiaztion.domains.tomato.tthorp.components.partitioning.organ import (
    Organ,
)


@dataclass(frozen=True, slots=True)
class AllocationFractions:
    """Allocation fractions for the requested partition scheme."""

    values: dict[Organ, float]

    def __post_init__(self) -> None:
        normalized: dict[Organ, float] = {}
        for organ, raw in self.values.items():
            if not isinstance(organ, Organ):
                raise TypeError(
                    "AllocationFractions: keys must be Organ values, "
                    f"got {type(organ).__name__}."
                )
            normalized[organ] = float(raw)
        object.__setattr__(self, "values", normalized)
        self.validate()

    def validate(self, *, tol: float = 1e-9) -> None:
        if tol < 0.0:
            raise ValueError(f"AllocationFractions.validate: tol must be >= 0, got {tol!r}.")

        total = 0.0
        for organ, value in self.values.items():
            if not math.isfinite(value):
                raise ValueError(
                    f"AllocationFractions.validate: {organ.value} must be finite, got {value!r}."
                )
            if value < -tol or value > 1.0 + tol:
                raise ValueError(
                    f"AllocationFractions.validate: {organ.value} must be in [0, 1], got {value!r}."
                )
            total += value

        if abs(total - 1.0) > tol:
            raise ValueError(
                "AllocationFractions.validate: values must sum to 1.0 "
                f"(within {tol}), got {total!r}."
            )

    @classmethod
    def from_3pool_to_4pool(
        cls,
        fruit: float,
        shoot: float,
        root: float,
        *,
        leaf_stem_ratio: float = 0.7 / 0.3,
    ) -> "AllocationFractions":
        ratio = float(leaf_stem_ratio)
        if not math.isfinite(ratio) or ratio <= 0.0:
            raise ValueError(
                "AllocationFractions.from_3pool_to_4pool: leaf_stem_ratio must be finite and > 0, "
                f"got {leaf_stem_ratio!r}."
            )
        leaf_share = ratio / (1.0 + ratio)
        stem_share = 1.0 / (1.0 + ratio)
        return cls(
            values={
                Organ.FRUIT: float(fruit),
                Organ.LEAF: float(shoot) * leaf_share,
                Organ.STEM: float(shoot) * stem_share,
                Organ.ROOT: float(root),
            }
        )

    @classmethod
    def from_4pool_to_3pool(
        cls,
        fruit: float,
        leaf: float,
        stem: float,
        root: float,
    ) -> "AllocationFractions":
        shoot = float(leaf) + float(stem)
        return cls(
            values={
                Organ.FRUIT: float(fruit),
                Organ.SHOOT: shoot,
                Organ.ROOT: float(root),
            }
        )
