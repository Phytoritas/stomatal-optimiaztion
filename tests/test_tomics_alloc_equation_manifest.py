from __future__ import annotations

from pathlib import Path

from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.partitioning.research_modes import (
    equation_traceability_rows,
    traceability_missing_paths,
)


def test_equation_traceability_rows_point_to_existing_code_paths() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    rows = equation_traceability_rows()

    assert rows
    assert not traceability_missing_paths(repo_root)


def test_tomics_allocation_review_manifests_exist() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    review_root = repo_root / "docs" / "architecture" / "review"

    assert (review_root / "tomics-allocation-primary-source-review.md").exists()
    assert (review_root / "tomics-allocation-equation-manifest.md").exists()
    assert (review_root / "tomics-allocation-gap-analysis.md").exists()
