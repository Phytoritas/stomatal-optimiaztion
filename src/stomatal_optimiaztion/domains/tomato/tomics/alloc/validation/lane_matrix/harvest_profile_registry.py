from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def _as_dict(raw: object) -> dict[str, Any]:
    if isinstance(raw, dict):
        return {str(key): value for key, value in raw.items()}
    return {}


@dataclass(frozen=True, slots=True)
class HarvestProfileSpec:
    harvest_profile_id: str
    fruit_harvest_family: str
    leaf_harvest_family: str
    fdmc_mode: str
    harvest_delay_days: float
    harvest_readiness_threshold: float
    fruit_params: dict[str, object]
    leaf_params: dict[str, object]
    promotion_eligible: bool
    diagnostic_only: bool
    selected_family_label: str
    selected_family_is_native: bool
    selected_family_is_proxy: bool


def _selected_payload_path(*, repo_root: Path, selected_payload_path: str | Path | None = None) -> Path:
    if selected_payload_path is not None:
        candidate = Path(selected_payload_path)
        if candidate.is_absolute():
            return candidate
        return (repo_root / candidate).resolve()
    return (repo_root / "out" / "tomics_knu_harvest_family_factorial" / "selected_harvest_family.json").resolve()


def resolve_harvest_profiles(
    *,
    repo_root: Path,
    requested_ids: list[str] | None = None,
    selected_payload_path: str | Path | None = None,
) -> list[HarvestProfileSpec]:
    requested = set(requested_ids) if requested_ids else None
    profiles: list[HarvestProfileSpec] = [
        HarvestProfileSpec(
            harvest_profile_id="incumbent_harvest_profile",
            fruit_harvest_family="tomsim_truss",
            leaf_harvest_family="linked_truss_stage",
            fdmc_mode="constant_observed_mean",
            harvest_delay_days=0.0,
            harvest_readiness_threshold=1.0,
            fruit_params={"tdvs_harvest_threshold": 1.0},
            leaf_params={"linked_leaf_stage": 0.9},
            promotion_eligible=True,
            diagnostic_only=False,
            selected_family_label="shipped_incumbent",
            selected_family_is_native=True,
            selected_family_is_proxy=False,
        ),
        HarvestProfileSpec(
            harvest_profile_id="diagnostic_factorial_harvest_profile",
            fruit_harvest_family="tomgro_ageclass",
            leaf_harvest_family="vegetative_unit_pruning",
            fdmc_mode="constant_observed_mean",
            harvest_delay_days=0.0,
            harvest_readiness_threshold=20.0,
            fruit_params={"mature_class_index": 20},
            leaf_params={"colour_threshold": 0.9},
            promotion_eligible=False,
            diagnostic_only=True,
            selected_family_label="diagnostic_factorial",
            selected_family_is_native=False,
            selected_family_is_proxy=True,
        ),
    ]
    selected_path = _selected_payload_path(
        repo_root=repo_root,
        selected_payload_path=selected_payload_path,
    )
    if requested is None or "locked_research_selected_harvest_profile" in requested:
        if not selected_path.exists():
            raise FileNotFoundError(
                "locked_research_selected_harvest_profile requires out/tomics_knu_harvest_family_factorial/selected_harvest_family.json"
            )
        payload = json.loads(selected_path.read_text(encoding="utf-8"))
        profiles.append(
            HarvestProfileSpec(
                harvest_profile_id="locked_research_selected_harvest_profile",
                fruit_harvest_family=str(payload["selected_fruit_harvest_family"]),
                leaf_harvest_family=str(payload["selected_leaf_harvest_family"]),
                fdmc_mode=str(payload["selected_fdmc_mode"]),
                harvest_delay_days=float(payload.get("harvest_delay_days", 0.0)),
                harvest_readiness_threshold=float(payload.get("harvest_readiness_threshold", 1.0)),
                fruit_params=_as_dict(payload.get("fruit_params")),
                leaf_params=_as_dict(payload.get("leaf_params")),
                promotion_eligible=True,
                diagnostic_only=False,
                selected_family_label=str(payload.get("selected_harvest_family_id", "locked_research_selected")),
                selected_family_is_native=float(payload.get("winner_native_state_fraction", 0.0)) >= 0.5,
                selected_family_is_proxy=float(payload.get("winner_proxy_state_fraction", 0.0)) > 0.0,
            )
        )
    if requested is None:
        return profiles
    return [profile for profile in profiles if profile.harvest_profile_id in requested]


__all__ = ["HarvestProfileSpec", "resolve_harvest_profiles"]
