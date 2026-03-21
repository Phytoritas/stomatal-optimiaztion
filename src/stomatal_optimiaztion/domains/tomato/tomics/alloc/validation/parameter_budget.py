from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.alloc.core import load_config
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.artifact_sync import (
    CanonicalWinnerIds,
    load_canonical_winner_ids,
)


@dataclass(frozen=True, slots=True)
class SplitWindow:
    split_id: str
    split_kind: str
    calibration_start: pd.Timestamp
    calibration_end: pd.Timestamp
    holdout_start: pd.Timestamp
    holdout_end: pd.Timestamp


@dataclass(frozen=True, slots=True)
class CalibrationCandidate:
    candidate_label: str
    architecture_id: str
    candidate_role: str
    calibratable: bool
    row: dict[str, object]


@dataclass(frozen=True, slots=True)
class CalibrationBudget:
    candidate_label: str
    candidate_architecture_id: str
    shared_parameters: list[str]
    architecture_specific_parameters: list[str]
    hidden_state_parameters: list[str]
    effective_free_parameter_count: int
    notes: list[str]

    @property
    def free_parameters(self) -> list[str]:
        return list(self.shared_parameters)

    @property
    def max_free_parameter_count(self) -> int:
        return int(self.effective_free_parameter_count)

    @property
    def hidden_state_mode_budget(self) -> int:
        return 3

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_label": self.candidate_label,
            "candidate_architecture_id": self.candidate_architecture_id,
            "shared_parameters": list(self.shared_parameters),
            "architecture_specific_parameters": list(self.architecture_specific_parameters),
            "hidden_state_parameters": list(self.hidden_state_parameters),
            "effective_free_parameter_count": self.effective_free_parameter_count,
            "free_parameters": list(self.shared_parameters),
            "max_free_parameter_count": self.max_free_parameter_count,
            "hidden_state_mode_budget": self.hidden_state_mode_budget,
            "notes": list(self.notes),
        }


def _as_dict(raw: object) -> dict[str, Any]:
    if isinstance(raw, dict):
        return {str(key): value for key, value in raw.items()}
    return {}


def _resolve_config_path(raw: str | Path, *, repo_root: Path, config_path: Path) -> Path:
    candidate = Path(raw)
    if candidate.is_absolute():
        return candidate
    probes = [
        (config_path.parent / candidate).resolve(),
        (repo_root / candidate).resolve(),
    ]
    for probe in probes:
        if probe.exists():
            return probe
    return probes[0]


def _load_selected_payload(output_root: Path) -> dict[str, Any]:
    return json.loads((output_root / "selected_architecture.json").read_text(encoding="utf-8"))


def _base_tomics_params(config: dict[str, Any]) -> dict[str, object]:
    pipeline_cfg = _as_dict(config.get("pipeline"))
    params = _as_dict(pipeline_cfg.get("partition_policy_params"))
    tomics = _as_dict(pipeline_cfg.get("tomics"))
    if tomics:
        params = {**params, **tomics}
    return params


def _shipped_tomics_row(base_config: dict[str, Any]) -> dict[str, object]:
    params = _base_tomics_params(base_config)
    return {
        "architecture_id": "shipped_tomics_control",
        "partition_policy": "tomics",
        "policy_family": "incumbent",
        "allocation_scheme": str(_as_dict(base_config.get("pipeline")).get("allocation_scheme", "4pool")),
        "fruit_load_multiplier": 1.0,
        "wet_root_cap": float(params.get("wet_root_cap", 0.10)),
        "dry_root_cap": float(params.get("dry_root_cap", 0.18)),
        "lai_target_center": float(params.get("lai_target_center", 2.75)),
        "leaf_fraction_of_shoot_base": float(params.get("leaf_fraction_of_shoot_base", 0.70)),
        "thorp_root_blend": float(params.get("thorp_root_blend", 1.0)),
    }


def build_split_windows(observed_df: pd.DataFrame) -> list[SplitWindow]:
    dates = pd.to_datetime(observed_df["date"], errors="coerce").dropna().dt.normalize().drop_duplicates().sort_values()
    if dates.shape[0] < 12:
        raise ValueError("KNU validation requires at least 12 daily observations to build blocked and rolling splits.")
    date_list = list(dates)
    blocked_primary = SplitWindow(
        split_id="blocked_primary",
        split_kind="blocked_holdout",
        calibration_start=date_list[0],
        calibration_end=date_list[min(11, len(date_list) - 2)],
        holdout_start=date_list[min(12, len(date_list) - 1)],
        holdout_end=date_list[-1],
    )
    rolling_origin_mid = SplitWindow(
        split_id="rolling_origin_mid",
        split_kind="rolling_origin",
        calibration_start=date_list[0],
        calibration_end=date_list[min(8, len(date_list) - 4)],
        holdout_start=date_list[min(9, len(date_list) - 3)],
        holdout_end=date_list[min(16, len(date_list) - 1)],
    )
    alternate_holdout = SplitWindow(
        split_id="alternate_holdout_late",
        split_kind="alternate_holdout",
        calibration_start=date_list[0],
        calibration_end=date_list[min(9, len(date_list) - 2)],
        holdout_start=date_list[min(10, len(date_list) - 1)],
        holdout_end=date_list[-1],
    )
    return [blocked_primary, rolling_origin_mid, alternate_holdout]


def load_fairness_candidates(
    *,
    fairness_config: dict[str, Any],
    repo_root: Path,
    config_path: Path,
) -> tuple[CanonicalWinnerIds, list[CalibrationCandidate], dict[str, Any]]:
    reference_cfg = _as_dict(fairness_config.get("reference"))
    current_vs_promoted_path = _resolve_config_path(
        reference_cfg.get("current_vs_promoted_config", "configs/exp/tomics_current_vs_promoted_factorial_knu.yaml"),
        repo_root=repo_root,
        config_path=config_path,
    )
    current_vs_promoted_cfg = load_config(current_vs_promoted_path)
    output_paths = _as_dict(current_vs_promoted_cfg.get("paths"))
    current_output_root = _resolve_config_path(
        reference_cfg.get("current_output_root", output_paths.get("current_output_root", "out/tomics_current_factorial_knu")),
        repo_root=repo_root,
        config_path=current_vs_promoted_path,
    )
    promoted_output_root = _resolve_config_path(
        reference_cfg.get("promoted_output_root", output_paths.get("promoted_output_root", "out/tomics_promoted_factorial_knu")),
        repo_root=repo_root,
        config_path=current_vs_promoted_path,
    )
    winners = load_canonical_winner_ids(
        current_output_root=current_output_root,
        promoted_output_root=promoted_output_root,
    )
    current_payload = _load_selected_payload(current_output_root)
    promoted_payload = _load_selected_payload(promoted_output_root)

    base_config_path = _resolve_config_path(
        _as_dict(current_vs_promoted_cfg.get("current")).get("base_config", "configs/exp/tomics_allocation_factorial.yaml"),
        repo_root=repo_root,
        config_path=current_vs_promoted_path,
    )
    base_config = load_config(base_config_path)
    candidates = [
        CalibrationCandidate(
            candidate_label="workbook_estimated",
            architecture_id="workbook_estimated_baseline",
            candidate_role="comparator",
            calibratable=False,
            row={
                "architecture_id": "workbook_estimated_baseline",
                "partition_policy": "workbook_estimated_baseline",
                "policy_family": "comparator",
                "allocation_scheme": "4pool",
            },
        ),
        CalibrationCandidate(
            candidate_label="shipped_tomics",
            architecture_id="shipped_tomics_control",
            candidate_role="incumbent",
            calibratable=True,
            row=_shipped_tomics_row(base_config),
        ),
        CalibrationCandidate(
            candidate_label="current_selected",
            architecture_id=str(current_payload["selected_architecture_id"]),
            candidate_role="research_current",
            calibratable=True,
            row={**_as_dict(current_payload.get("selected_architecture")), "policy_family": "current_selected"},
        ),
        CalibrationCandidate(
            candidate_label="promoted_selected",
            architecture_id=str(promoted_payload["selected_architecture_id"]),
            candidate_role="research_promoted",
            calibratable=True,
            row={**_as_dict(promoted_payload.get("selected_architecture")), "policy_family": "promoted_selected"},
        ),
    ]
    reference_meta = {
        "current_vs_promoted_config_path": str(current_vs_promoted_path),
        "current_output_root": str(current_output_root),
        "promoted_output_root": str(promoted_output_root),
        "base_config_path": str(base_config_path),
        "base_config": base_config,
    }
    return winners, candidates, reference_meta


def build_calibration_budget_manifest(
    *,
    winners: CanonicalWinnerIds,
    candidates: list[CalibrationCandidate],
    splits: list[SplitWindow],
) -> dict[str, Any]:
    free_parameter_levels = {
        "theta_proxy_scenario": ["dry", "moderate", "wet"],
        "reconstruction_mode": ["minimal_scalar_init", "cohort_aware_init", "buffer_aware_init"],
        "init_lai_scale": [0.9, 1.0, 1.1],
        "init_fruit_scale": [0.8, 1.0, 1.2],
    }
    manifest = {
        "canonical_winners": {
            "current_selected_architecture_id": winners.current_selected_architecture_id,
            "promoted_selected_architecture_id": winners.promoted_selected_architecture_id,
        },
        "shared_free_parameters": free_parameter_levels,
        "nuisance_parameters": ["theta_proxy_scenario"],
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
        "effective_free_parameter_budget": {
            candidate.candidate_label: 2 if candidate.calibratable else 0 for candidate in candidates
        },
        "architecture_specific_parameters_frozen": {
            candidate.candidate_label: {
                key: value
                for key, value in candidate.row.items()
                if key
                not in {
                    "architecture_id",
                    "partition_policy",
                    "policy_family",
                    "allocation_scheme",
                    "fruit_load_multiplier",
                    "lai_target_center",
                }
            }
            for candidate in candidates
            if candidate.calibratable
        },
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
            "Workbook estimated remains a comparator only and is not a promotion candidate.",
            "Architecture-specific knobs are frozen to preserve calibration parity across shipped, current-selected, and promoted-selected candidates.",
            "Only shared root-zone and hidden-state uncertainty levers are calibrated across architectures.",
        ],
    }
    return manifest


def build_calibration_budget(
    *,
    candidate_label: str,
    candidate_row: dict[str, object],
) -> CalibrationBudget:
    architecture_specific = sorted(
        key
        for key in candidate_row
        if key
        not in {
            "architecture_id",
            "partition_policy",
            "policy_family",
            "allocation_scheme",
            "fruit_load_multiplier",
            "lai_target_center",
        }
    )
    free_parameter_count = 0 if candidate_label == "workbook_estimated" else 2
    return CalibrationBudget(
        candidate_label=candidate_label,
        candidate_architecture_id=str(candidate_row.get("architecture_id", candidate_label)),
        shared_parameters=["fruit_load_multiplier", "lai_target_center"],
        architecture_specific_parameters=architecture_specific,
        hidden_state_parameters=[
            "reconstruction_mode",
            "initial_state_overrides.W_lv",
            "initial_state_overrides.W_st",
            "initial_state_overrides.W_rt",
            "initial_state_overrides.W_fr",
            "initial_state_overrides.W_fr_harvested",
        ],
        effective_free_parameter_count=free_parameter_count,
        notes=[
            "Architecture-specific knobs stay fixed during parity calibration.",
            "Shared calibration budget is limited to fruit-load and canopy-target tuning on top of shared reconstruction.",
        ],
    )


__all__ = [
    "CalibrationCandidate",
    "CalibrationBudget",
    "SplitWindow",
    "build_calibration_budget",
    "build_calibration_budget_manifest",
    "build_split_windows",
    "load_fairness_candidates",
]
