from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.parameter_budget import (
    CalibrationCandidate,
)


@dataclass(frozen=True, slots=True)
class AllocationLaneSpec:
    lane_id: str
    partition_policy: str
    candidate_label: str
    promotion_eligible: bool
    reference_only: bool
    diagnostic_only: bool
    architecture_id_override: str | None = None
    policy_family_override: str | None = None


@dataclass(frozen=True, slots=True)
class ResolvedAllocationLane:
    lane_id: str
    partition_policy: str
    candidate_label: str
    promotion_eligible: bool
    reference_only: bool
    diagnostic_only: bool
    architecture_id: str
    candidate_row: dict[str, object]


def default_allocation_lane_specs() -> tuple[AllocationLaneSpec, ...]:
    return (
        AllocationLaneSpec(
            lane_id="legacy_sink_baseline",
            partition_policy="legacy",
            candidate_label="shipped_tomics",
            promotion_eligible=False,
            reference_only=True,
            diagnostic_only=True,
            architecture_id_override="legacy_control",
            policy_family_override="legacy_baseline",
        ),
        AllocationLaneSpec(
            lane_id="incumbent_current",
            partition_policy="tomics",
            candidate_label="shipped_tomics",
            promotion_eligible=True,
            reference_only=False,
            diagnostic_only=False,
        ),
        AllocationLaneSpec(
            lane_id="research_current",
            partition_policy="tomics_alloc_research",
            candidate_label="current_selected",
            promotion_eligible=True,
            reference_only=False,
            diagnostic_only=False,
        ),
        AllocationLaneSpec(
            lane_id="research_promoted",
            partition_policy="tomics_promoted_research",
            candidate_label="promoted_selected",
            promotion_eligible=True,
            reference_only=False,
            diagnostic_only=False,
        ),
        AllocationLaneSpec(
            lane_id="raw_reference_thorp",
            partition_policy="thorp_fruit_veg",
            candidate_label="shipped_tomics",
            promotion_eligible=False,
            reference_only=True,
            diagnostic_only=True,
            architecture_id_override="raw_thorp_like_control",
            policy_family_override="raw_reference_thorp",
        ),
    )


def resolve_allocation_lanes(
    candidates: Iterable[CalibrationCandidate],
    *,
    lane_ids: Iterable[str] | None = None,
) -> list[ResolvedAllocationLane]:
    candidate_map = {candidate.candidate_label: candidate for candidate in candidates}
    requested = set(str(value) for value in lane_ids) if lane_ids is not None else None
    resolved: list[ResolvedAllocationLane] = []
    for spec in default_allocation_lane_specs():
        if requested is not None and spec.lane_id not in requested:
            continue
        candidate = candidate_map[spec.candidate_label]
        candidate_row = dict(candidate.row)
        candidate_row["partition_policy"] = spec.partition_policy
        candidate_row["architecture_id"] = spec.architecture_id_override or str(
            candidate_row.get("architecture_id", candidate.architecture_id)
        )
        if spec.policy_family_override is not None:
            candidate_row["policy_family"] = spec.policy_family_override
        resolved.append(
            ResolvedAllocationLane(
                lane_id=spec.lane_id,
                partition_policy=spec.partition_policy,
                candidate_label=spec.candidate_label,
                promotion_eligible=spec.promotion_eligible,
                reference_only=spec.reference_only,
                diagnostic_only=spec.diagnostic_only,
                architecture_id=str(candidate_row["architecture_id"]),
                candidate_row=candidate_row,
            )
        )
    return resolved


__all__ = [
    "AllocationLaneSpec",
    "ResolvedAllocationLane",
    "default_allocation_lane_specs",
    "resolve_allocation_lanes",
]
