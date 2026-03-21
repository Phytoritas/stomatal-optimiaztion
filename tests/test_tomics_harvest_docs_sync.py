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


def test_harvest_docs_publish_required_roots_and_conclusion() -> None:
    repo_root = _repo_root()
    docs_text = "\n".join(
        (
            (repo_root / "README.md").read_text(encoding="utf-8"),
            (repo_root / "Phytoritas.md").read_text(encoding="utf-8"),
            (repo_root / "docs/architecture/Phytoritas.md").read_text(encoding="utf-8"),
            (repo_root / "docs/architecture/tomics-harvest-architecture-pipeline.md").read_text(encoding="utf-8"),
            (repo_root / "docs/architecture/review/tomics-harvest-family-review.md").read_text(encoding="utf-8"),
            (repo_root / "docs/architecture/review/tomics-knu-harvest-aware-promotion-gate.md").read_text(
                encoding="utf-8"
            ),
        )
    )

    required_snippets = [
        "Issue `#243` / module `119`",
        "out/tomics_knu_harvest_family_factorial/",
        "out/tomics_knu_harvest_promotion_gate/",
        "vanthoor_boxcar",
        "max_lai_pruning_flow",
        "source-grounded proxy adapter",
        "Keep shipped TOMICS + incumbent TOMSIM harvest as the incumbent baseline.",
    ]
    assert all(snippet in docs_text for snippet in required_snippets)


def test_harvest_review_docs_record_evidence_handles() -> None:
    repo_root = _repo_root()
    source_papers_root = repo_root / "docs/references/source_papers"
    expected_repo_local_sources = [
        "Heuvelink - 1996 - Tomato growth and yield  quantitative analysis and synthesis.pdf",
        "J. W. Jones et al. - 1991 - A DYNAMIC TOMATO GROWTH AND YIELD MODEL (TOMGRO).pdf",
        "De Koning - 1994 - Development and dry matter distribution in glasshouse tomato  a quantitative approach.pdf",
        "Kuijpers et al. - 2019 - Model selection with a common structure Tomato crop growth models.pdf",
        "Vanthoor et al. - 2011 - A methodology for model-based greenhouse design Part 2, description and validation of a tomato yiel.pdf",
        "Vanthoor et al. - 2011 - A methodology for model-based greenhouse design Part 2, description and validation of a tomato yiel 1.pdf",
    ]
    assert all((source_papers_root / name).exists() for name in expected_repo_local_sources)

    review_text = (repo_root / "docs/architecture/review/tomics-harvest-family-review.md").read_text(encoding="utf-8")
    equation_manifest_text = (
        repo_root / "docs/architecture/review/tomics-harvest-equation-manifest.md"
    ).read_text(encoding="utf-8")
    source_manifest_text = (repo_root / "docs/architecture/review/source_manifest.csv").read_text(encoding="utf-8")

    required_handles = [
        "HHD63E6H",
        "JZMAF7MV",
        "RT8W6KUD",
        "VYCHQ7HV",
        "SIZ3ZU3W",
        "CKLNUS4Q",
        "GRN6KBKD",
    ]
    assert all(handle in review_text for handle in required_handles)
    assert "SIZ3ZU3W" in equation_manifest_text
    assert "CKLNUS4Q" in equation_manifest_text
    assert "Zotero attachment CKLNUS4Q (repo-local appendix filename not present)" in source_manifest_text
    assert "zotero_attachment_full_text" in source_manifest_text


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
            (repo_root / "README.md").read_text(encoding="utf-8"),
            (repo_root / "Phytoritas.md").read_text(encoding="utf-8"),
            (repo_root / "docs/architecture/Phytoritas.md").read_text(encoding="utf-8"),
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
