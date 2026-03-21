from __future__ import annotations

import json
from pathlib import Path

from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.artifact_sync import (
    load_canonical_winner_ids,
    write_canonical_winner_manifest,
)


def test_canonical_winner_manifest_round_trip(tmp_path: Path) -> None:
    current_root = tmp_path / "current"
    promoted_root = tmp_path / "promoted"
    current_root.mkdir()
    promoted_root.mkdir()
    (current_root / "selected_architecture.json").write_text(
        json.dumps({"selected_architecture_id": "current_winner"}),
        encoding="utf-8",
    )
    (promoted_root / "selected_architecture.json").write_text(
        json.dumps({"selected_architecture_id": "promoted_winner"}),
        encoding="utf-8",
    )
    winners = load_canonical_winner_ids(current_output_root=current_root, promoted_output_root=promoted_root)
    manifest_path = write_canonical_winner_manifest(output_root=tmp_path / "comparison", winners=winners)
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert payload["current_selected_architecture_id"] == "current_winner"
    assert payload["promoted_selected_architecture_id"] == "promoted_winner"
