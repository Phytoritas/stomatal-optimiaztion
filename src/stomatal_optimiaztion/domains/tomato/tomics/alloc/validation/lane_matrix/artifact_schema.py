from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


ARTIFACT_FILENAMES = {
    "matrix_spec": "matrix_spec.json",
    "resolved_matrix_spec": "resolved_matrix_spec.json",
    "scenario_index": "scenario_index.csv",
    "lane_scorecard": "lane_scorecard.csv",
    "lane_gate_decision": "lane_gate_decision.json",
    "diagnostic_surface": "diagnostic_surface.csv",
    "promotion_surface": "promotion_surface.csv",
    "dataset_role_summary": "dataset_role_summary.csv",
    "architecture_matrix": "architecture_matrix.csv",
    "per_dataset_metric_summary": "per_dataset_metric_summary.csv",
    "dataset_role_matrix": "dataset_role_matrix.csv",
    "primary_measured_score": "primary_measured_score.json",
    "review_only_public_score": "review_only_public_score.json",
    "all_runnable_smoke_score": "all_runnable_smoke_score.json",
    "promotion_gate_decision": "promotion_gate_decision.json",
    "readme": "README.md",
}


@dataclass(frozen=True, slots=True)
class LaneMatrixArtifactPaths:
    root: Path

    @property
    def scenarios_root(self) -> Path:
        return self.root / "scenarios"

    @property
    def matrix_spec_path(self) -> Path:
        return self.root / ARTIFACT_FILENAMES["matrix_spec"]

    @property
    def resolved_matrix_spec_path(self) -> Path:
        return self.root / ARTIFACT_FILENAMES["resolved_matrix_spec"]

    @property
    def scenario_index_path(self) -> Path:
        return self.root / ARTIFACT_FILENAMES["scenario_index"]

    @property
    def lane_scorecard_path(self) -> Path:
        return self.root / ARTIFACT_FILENAMES["lane_scorecard"]

    @property
    def lane_gate_decision_path(self) -> Path:
        return self.root / ARTIFACT_FILENAMES["lane_gate_decision"]

    @property
    def diagnostic_surface_path(self) -> Path:
        return self.root / ARTIFACT_FILENAMES["diagnostic_surface"]

    @property
    def promotion_surface_path(self) -> Path:
        return self.root / ARTIFACT_FILENAMES["promotion_surface"]

    @property
    def dataset_role_summary_path(self) -> Path:
        return self.root / ARTIFACT_FILENAMES["dataset_role_summary"]

    @property
    def architecture_matrix_path(self) -> Path:
        return self.root / ARTIFACT_FILENAMES["architecture_matrix"]

    @property
    def per_dataset_metric_summary_path(self) -> Path:
        return self.root / ARTIFACT_FILENAMES["per_dataset_metric_summary"]

    @property
    def dataset_role_matrix_path(self) -> Path:
        return self.root / ARTIFACT_FILENAMES["dataset_role_matrix"]

    @property
    def primary_measured_score_path(self) -> Path:
        return self.root / ARTIFACT_FILENAMES["primary_measured_score"]

    @property
    def review_only_public_score_path(self) -> Path:
        return self.root / ARTIFACT_FILENAMES["review_only_public_score"]

    @property
    def all_runnable_smoke_score_path(self) -> Path:
        return self.root / ARTIFACT_FILENAMES["all_runnable_smoke_score"]

    @property
    def promotion_gate_decision_path(self) -> Path:
        return self.root / ARTIFACT_FILENAMES["promotion_gate_decision"]

    @property
    def readme_path(self) -> Path:
        return self.root / ARTIFACT_FILENAMES["readme"]

    def scenario_root(self, scenario_id: str) -> Path:
        return self.scenarios_root / scenario_id


__all__ = ["ARTIFACT_FILENAMES", "LaneMatrixArtifactPaths"]
