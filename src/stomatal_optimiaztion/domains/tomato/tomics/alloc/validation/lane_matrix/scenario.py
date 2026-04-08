from __future__ import annotations

from dataclasses import dataclass
from itertools import product

from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.lane_matrix.allocation_lane_registry import (
    ResolvedAllocationLane,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.lane_matrix.dataset_role_registry import (
    ResolvedDatasetRole,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.lane_matrix.harvest_profile_registry import (
    HarvestProfileSpec,
)


@dataclass(frozen=True, slots=True)
class ComparisonScenario:
    allocation_lane: ResolvedAllocationLane
    harvest_profile: HarvestProfileSpec
    dataset_role_assignment: ResolvedDatasetRole

    @property
    def scenario_id(self) -> str:
        return "__".join(
            [
                self.allocation_lane.lane_id,
                self.harvest_profile.harvest_profile_id,
                self.dataset_role_assignment.dataset_id,
            ]
        )

    @property
    def promotion_surface_eligible(self) -> bool:
        return bool(
            self.allocation_lane.promotion_eligible
            and not self.allocation_lane.reference_only
            and self.harvest_profile.promotion_eligible
            and not self.harvest_profile.diagnostic_only
            and self.dataset_role_assignment.promotion_denominator_eligible
        )


def compose_scenarios(
    allocation_lanes: list[ResolvedAllocationLane],
    harvest_profiles: list[HarvestProfileSpec],
    dataset_roles: list[ResolvedDatasetRole],
) -> list[ComparisonScenario]:
    return [
        ComparisonScenario(
            allocation_lane=allocation_lane,
            harvest_profile=harvest_profile,
            dataset_role_assignment=dataset_role,
        )
        for allocation_lane, harvest_profile, dataset_role in product(
            allocation_lanes,
            harvest_profiles,
            dataset_roles,
        )
    ]


__all__ = ["ComparisonScenario", "compose_scenarios"]
