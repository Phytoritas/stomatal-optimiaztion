from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from stomatal_optimiaztion.domains.tomato.tomics.alloc.core import load_config
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.parameter_budget import (
    CalibrationCandidate,
    SplitWindow,
    build_split_windows,
    load_fairness_candidates,
)


@dataclass(frozen=True, slots=True)
class HarvestDesignRow:
    stage: str
    allocator_family: str
    candidate_label: str
    architecture_id: str
    fruit_harvest_family: str
    leaf_harvest_family: str
    fdmc_mode: str
    harvest_delay_days: float
    harvest_readiness_threshold: float
    fruit_params: dict[str, object]
    leaf_params: dict[str, object]
    candidate_row: dict[str, object]

    @property
    def candidate_key(self) -> str:
        return "|".join(
            [
                self.candidate_label,
                self.fruit_harvest_family,
                self.leaf_harvest_family,
                self.fdmc_mode,
                f"{self.harvest_delay_days:g}",
                f"{self.harvest_readiness_threshold:g}",
            ]
        )


def _as_dict(raw: object) -> dict[str, Any]:
    if isinstance(raw, dict):
        return {str(key): value for key, value in raw.items()}
    return {}


def load_harvest_candidates(
    *,
    config: dict[str, Any],
    repo_root: Path,
    config_path: Path,
) -> tuple[list[CalibrationCandidate], dict[str, Any]]:
    _, candidates, reference_meta = load_fairness_candidates(
        fairness_config=config,
        repo_root=repo_root,
        config_path=config_path,
    )
    return candidates, reference_meta


def load_harvest_base_config(reference_meta: dict[str, Any]) -> dict[str, Any]:
    base_config = reference_meta.get("base_config")
    if isinstance(base_config, dict):
        return dict(base_config)
    return load_config(Path(str(reference_meta["base_config_path"])))


def build_harvest_budget_manifest(
    *,
    candidates: list[HarvestDesignRow],
    splits: list[SplitWindow],
) -> dict[str, Any]:
    candidate_keys = {candidate.candidate_key: candidate for candidate in candidates}
    return {
        "shared_free_parameters": [
            "fruit_load_multiplier",
            "lai_target_center",
            "harvest_delay_days",
            "harvest_readiness_threshold",
        ],
        "harvest_family_specific_parameters": {
            key: {
                "fruit_params": dict(candidate.fruit_params),
                "leaf_params": dict(candidate.leaf_params),
            }
            for key, candidate in candidate_keys.items()
        },
        "effective_free_parameter_count": {key: 4 for key in candidate_keys},
        "hidden_state_parameters": [
            "reconstruction_mode",
            "initial_state_overrides.W_lv",
            "initial_state_overrides.W_st",
            "initial_state_overrides.W_rt",
            "initial_state_overrides.W_fr",
            "initial_state_overrides.W_fr_harvested",
            "initial_state_overrides.truss_cohorts",
            "initial_state_overrides.reserve_ch2o_g",
            "initial_state_overrides.buffer_pool_g",
        ],
        "splits": [
            {
                "split_id": split.split_id,
                "split_kind": split.split_kind,
                "calibration_start": split.calibration_start.date().isoformat(),
                "calibration_end": split.calibration_end.date().isoformat(),
                "holdout_start": split.holdout_start.date().isoformat(),
                "holdout_end": split.holdout_end.date().isoformat(),
            }
            for split in splits
        ],
        "notes": [
            "Harvest-aware parity ties calibration freedom across shipped/current/promoted candidates.",
            "Family-specific knobs are shortlisted first, then frozen during promotion-gate calibration unless explicitly budgeted.",
        ],
    }


__all__ = [
    "HarvestDesignRow",
    "build_harvest_budget_manifest",
    "build_split_windows",
    "load_harvest_base_config",
    "load_harvest_candidates",
]
