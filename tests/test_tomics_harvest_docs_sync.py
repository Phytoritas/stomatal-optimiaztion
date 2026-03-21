from __future__ import annotations

import json
from pathlib import Path

import pytest


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_harvest_manifest_code_paths_exist() -> None:
    repo_root = _repo_root()
    required_paths = [
        repo_root / "src/stomatal_optimiaztion/domains/tomato/tomics/alloc/components/harvest/fruit_harvest_tomsim.py",
        repo_root / "src/stomatal_optimiaztion/domains/tomato/tomics/alloc/components/harvest/fruit_harvest_tomgro.py",
        repo_root / "src/stomatal_optimiaztion/domains/tomato/tomics/alloc/components/harvest/fruit_harvest_dekoning.py",
        repo_root / "src/stomatal_optimiaztion/domains/tomato/tomics/alloc/components/harvest/fruit_harvest_vanthoor.py",
        repo_root / "src/stomatal_optimiaztion/domains/tomato/tomics/alloc/components/harvest/leaf_harvest.py",
        repo_root / "src/stomatal_optimiaztion/domains/tomato/tomics/alloc/components/harvest/contracts.py",
    ]
    assert all(path.exists() for path in required_paths)


def test_harvest_docs_reference_current_selected_family_when_artifacts_exist() -> None:
    repo_root = _repo_root()
    selected_path = repo_root / "out/tomics_knu_harvest_family_factorial/selected_harvest_family.json"
    winners_path = repo_root / "out/tomics_knu_harvest_family_factorial/canonical_harvest_winners.json"
    if not selected_path.exists() or not winners_path.exists():
        pytest.skip("Harvest factorial artifacts are not present; run the harvest factorial before docs/artifact sync validation.")

    selected = json.loads(selected_path.read_text(encoding="utf-8"))
    winners = json.loads(winners_path.read_text(encoding="utf-8"))
    docs_text = "\n".join(
        (
            (repo_root / "docs/architecture/tomics-harvest-architecture-pipeline.md").read_text(encoding="utf-8"),
            (repo_root / "docs/architecture/review/tomics-harvest-family-review.md").read_text(encoding="utf-8"),
            (repo_root / "docs/architecture/review/tomics-knu-harvest-aware-promotion-gate.md").read_text(encoding="utf-8"),
        )
    )

    assert selected["selected_fruit_harvest_family"] == winners["selected_research_family"]["selected_fruit_harvest_family"]
    assert selected["selected_leaf_harvest_family"] == winners["selected_research_family"]["selected_leaf_harvest_family"]
    assert selected["selected_fruit_harvest_family"] in docs_text
    assert selected["selected_leaf_harvest_family"] in docs_text
    assert "Keep shipped TOMICS + incumbent TOMSIM harvest as the incumbent baseline." in docs_text
