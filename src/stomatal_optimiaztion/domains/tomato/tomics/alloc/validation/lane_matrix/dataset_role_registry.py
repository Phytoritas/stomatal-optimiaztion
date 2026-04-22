from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.datasets.contracts import (
    DatasetCapability,
    DatasetMetadataContract,
    is_measured_harvest_runnable,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.datasets.registry import (
    DatasetRegistry,
)


@dataclass(frozen=True, slots=True)
class DatasetRoleSpec:
    dataset_role: str
    promotion_denominator_eligible: bool
    scorecard_included: bool


@dataclass(frozen=True, slots=True)
class ResolvedDatasetRole:
    dataset_id: str
    dataset_kind: str
    display_name: str
    dataset_role: str
    promotion_denominator_eligible: bool
    scorecard_included: bool
    has_measured_harvest_contract: bool
    reporting_basis: str
    plants_per_m2: float
    dataset: DatasetMetadataContract


ROLE_SPECS = {
    "measured_harvest": DatasetRoleSpec(
        dataset_role="measured_harvest",
        promotion_denominator_eligible=True,
        scorecard_included=True,
    ),
    "trait_plus_env_no_harvest": DatasetRoleSpec(
        dataset_role="trait_plus_env_no_harvest",
        promotion_denominator_eligible=False,
        scorecard_included=True,
    ),
    "env_only": DatasetRoleSpec(
        dataset_role="env_only",
        promotion_denominator_eligible=False,
        scorecard_included=True,
    ),
    "metadata_only": DatasetRoleSpec(
        dataset_role="metadata_only",
        promotion_denominator_eligible=False,
        scorecard_included=False,
    ),
    "yield_environment_only": DatasetRoleSpec(
        dataset_role="yield_environment_only",
        promotion_denominator_eligible=False,
        scorecard_included=True,
    ),
}


def _family_text(dataset: DatasetMetadataContract) -> str:
    fragments = [
        dataset.dataset_kind,
        str(dataset.notes.get("dataset_family", "")),
        str(dataset.notes.get("source_family", "")),
        str(dataset.notes.get("observation_family", "")),
        str(dataset.notes.get("dataset_role_hint", "")),
        str(dataset.notes.get("dataset_role", "")),
    ]
    return " ".join(fragment.lower() for fragment in fragments if fragment).strip()


def _explicit_role_hint(dataset: DatasetMetadataContract) -> str | None:
    for key in ("dataset_role", "dataset_role_hint"):
        raw = str(dataset.notes.get(key, "")).strip().lower()
        if raw in ROLE_SPECS:
            return raw
    return None


def measured_harvest_contract_satisfied(dataset: DatasetMetadataContract) -> bool:
    return is_measured_harvest_runnable(dataset)


def infer_dataset_role(dataset: DatasetMetadataContract) -> str:
    explicit = _explicit_role_hint(dataset)
    if explicit is not None:
        if explicit == "measured_harvest" and not measured_harvest_contract_satisfied(dataset):
            raise ValueError(f"Dataset {dataset.dataset_id!r} was marked measured_harvest without a valid contract.")
        return explicit
    family_text = _family_text(dataset)
    if "yield_environment" in family_text:
        return "yield_environment_only"
    if "trait" in family_text and "env" in family_text:
        return "trait_plus_env_no_harvest"
    if "traitenv" in family_text or "trait_plus_env" in family_text:
        return "trait_plus_env_no_harvest"
    if dataset.capability is DatasetCapability.HARVEST_PROXY:
        return "yield_environment_only"
    if dataset.capability is DatasetCapability.MEASURED_HARVEST and measured_harvest_contract_satisfied(dataset):
        return "measured_harvest"
    has_measured_contract = measured_harvest_contract_satisfied(dataset)
    if "metadata" in family_text:
        return "metadata_only"
    if has_measured_contract and any(
        token in family_text
        for token in (
            "measured_harvest",
            "actual_harvest",
            "observed_harvest",
            "knu_actual",
            "knu_measured_harvest",
        )
    ):
        return "measured_harvest"
    if "env_only" in family_text or family_text.endswith(" env"):
        return "env_only"
    if "environment" in family_text or "greenhouse_environment" in family_text:
        return "env_only"
    return "metadata_only"


def resolve_dataset_roles(
    registry: DatasetRegistry,
    *,
    dataset_ids: Iterable[str] | None = None,
) -> list[ResolvedDatasetRole]:
    if dataset_ids is None:
        requested = None
    else:
        requested = {str(value) for value in dataset_ids}
        available_ids = {dataset.dataset_id for dataset in registry.datasets}
        unknown_ids = sorted(requested.difference(available_ids))
        if unknown_ids:
            raise ValueError(f"Unknown dataset ids requested: {', '.join(unknown_ids)}")
    resolved: list[ResolvedDatasetRole] = []
    for dataset in registry.datasets:
        if requested is not None and dataset.dataset_id not in requested:
            continue
        dataset_role = infer_dataset_role(dataset)
        spec = ROLE_SPECS[dataset_role]
        resolved.append(
            ResolvedDatasetRole(
                dataset_id=dataset.dataset_id,
                dataset_kind=dataset.dataset_kind,
                display_name=dataset.display_name,
                dataset_role=dataset_role,
                promotion_denominator_eligible=spec.promotion_denominator_eligible,
                scorecard_included=spec.scorecard_included,
                has_measured_harvest_contract=measured_harvest_contract_satisfied(dataset),
                reporting_basis=dataset.basis.reporting_basis,
                plants_per_m2=float(dataset.basis.plants_per_m2 or 0.0),
                dataset=dataset,
            )
        )
    return resolved


__all__ = [
    "DatasetRoleSpec",
    "ResolvedDatasetRole",
    "ROLE_SPECS",
    "infer_dataset_role",
    "measured_harvest_contract_satisfied",
    "resolve_dataset_roles",
]
