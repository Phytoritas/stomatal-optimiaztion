from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

SEASON_ID = "2025_2C"
LATENT_ALLOCATION_PIPELINE_VERSION = "tomics-haf-2025-2c-latent-allocation-v1"

PRIOR_FAMILIES: tuple[str, ...] = (
    "legacy_tomato_prior",
    "thorp_bounded_prior",
    "tomato_constrained_thorp_prior",
)

ORGAN_NAMES: tuple[str, ...] = ("fruit", "leaf", "stem", "root")

DIRECT_VALIDATION_STATEMENT = (
    "Latent allocation is not direct allocation validation because direct organ "
    "partition observations are unavailable."
)

OUTPUT_FILENAMES = {
    "inputs": "latent_allocation_inference_inputs.csv",
    "priors": "latent_allocation_priors.csv",
    "posteriors": "latent_allocation_posteriors.csv",
    "diagnostics": "latent_allocation_diagnostics.csv",
    "identifiability": "latent_allocation_identifiability.csv",
    "guardrails": "latent_allocation_guardrails.csv",
    "summary": "latent_allocation_summary.md",
    "metadata": "latent_allocation_metadata.json",
}


@dataclass(frozen=True, slots=True)
class AllocationBounds:
    fruit_floor: float
    leaf_floor: float
    stem_floor: float
    root_floor: float
    fruit_cap: float
    leaf_cap: float
    stem_cap: float
    root_cap: float
    wet_root_cap: float


def as_dict(raw: object) -> dict[str, Any]:
    if isinstance(raw, Mapping):
        return {str(key): value for key, value in raw.items()}
    return {}


def resolve_repo_path(repo_root: Path, value: str | Path) -> Path:
    candidate = Path(value)
    if candidate.is_absolute():
        return candidate
    return (repo_root / candidate).resolve()


def nested_float(mapping: Mapping[str, Any], section: str, key: str, default: float) -> float:
    value = as_dict(mapping.get(section)).get(key, default)
    try:
        result = float(value)
    except (TypeError, ValueError):
        return float(default)
    return result


def allocation_bounds(config: Mapping[str, Any]) -> AllocationBounds:
    latent = as_dict(config.get("latent_allocation"))
    floors = as_dict(latent.get("biological_floors"))
    caps = as_dict(latent.get("biological_caps"))
    return AllocationBounds(
        fruit_floor=float(floors.get("fruit", 0.05)),
        leaf_floor=float(floors.get("leaf", 0.12)),
        stem_floor=float(floors.get("stem", 0.08)),
        root_floor=float(floors.get("root", 0.02)),
        fruit_cap=float(caps.get("fruit", 0.85)),
        leaf_cap=float(caps.get("leaf", 0.55)),
        stem_cap=float(caps.get("stem", 0.45)),
        root_cap=float(caps.get("root", 0.25)),
        wet_root_cap=float(caps.get("wet_root", 0.12)),
    )


__all__ = [
    "AllocationBounds",
    "DIRECT_VALIDATION_STATEMENT",
    "LATENT_ALLOCATION_PIPELINE_VERSION",
    "ORGAN_NAMES",
    "OUTPUT_FILENAMES",
    "PRIOR_FAMILIES",
    "SEASON_ID",
    "allocation_bounds",
    "as_dict",
    "nested_float",
    "resolve_repo_path",
]
