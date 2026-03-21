from __future__ import annotations

from pathlib import Path

from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.artifact_sync import (
    CanonicalWinnerIds,
    docs_reference_winners,
)


def test_docs_artifact_sync_detects_required_winner_mentions(tmp_path: Path) -> None:
    docs_path = tmp_path / "summary.md"
    docs_path.write_text(
        "Current: `kuijpers_hybrid_candidate__wet_root_cap_0p08`\nPromoted: `constrained_full_plus_feedback__buffer_capacity_g_m2_12p0`\n",
        encoding="utf-8",
    )
    winners = CanonicalWinnerIds(
        current_selected_architecture_id="kuijpers_hybrid_candidate__wet_root_cap_0p08",
        promoted_selected_architecture_id="constrained_full_plus_feedback__buffer_capacity_g_m2_12p0",
    )
    assert docs_reference_winners(docs_paths=[docs_path], winners=winners)


def test_repo_docs_reference_current_public_canonical_winners() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    docs_paths = [
        repo_root / "docs" / "architecture" / "tomics-current-vs-promoted-factorial-knu.md",
        repo_root / "docs" / "architecture" / "review" / "tomics-knu-actual-data-validation.md",
        repo_root / "docs" / "architecture" / "review" / "tomics-promoted-allocator-design.md",
    ]
    winners = CanonicalWinnerIds(
        current_selected_architecture_id="kuijpers_hybrid_candidate",
        promoted_selected_architecture_id="constrained_full_plus_feedback__buffer_capacity_g_m2_12p0",
    )
    assert docs_reference_winners(docs_paths=docs_paths, winners=winners)
