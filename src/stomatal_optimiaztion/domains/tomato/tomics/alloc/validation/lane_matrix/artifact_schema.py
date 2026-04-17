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

    def scenario_root(self, scenario_id: str) -> Path:
        return self.scenarios_root / scenario_id


__all__ = ["ARTIFACT_FILENAMES", "LaneMatrixArtifactPaths"]
