from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class CanonicalWinnerIds:
    current_selected_architecture_id: str
    promoted_selected_architecture_id: str


def load_canonical_winner_ids(*, current_output_root: Path, promoted_output_root: Path) -> CanonicalWinnerIds:
    current_payload = json.loads((current_output_root / "selected_architecture.json").read_text(encoding="utf-8"))
    promoted_payload = json.loads((promoted_output_root / "selected_architecture.json").read_text(encoding="utf-8"))
    return CanonicalWinnerIds(
        current_selected_architecture_id=str(current_payload["selected_architecture_id"]),
        promoted_selected_architecture_id=str(promoted_payload["selected_architecture_id"]),
    )


def write_canonical_winner_manifest(
    *,
    output_root: Path,
    winners: CanonicalWinnerIds,
) -> Path:
    output_root.mkdir(parents=True, exist_ok=True)
    path = output_root / "canonical_winners.json"
    path.write_text(
        json.dumps(
            {
                "current_selected_architecture_id": winners.current_selected_architecture_id,
                "promoted_selected_architecture_id": winners.promoted_selected_architecture_id,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return path


def extract_winner_mentions(text: str) -> set[str]:
    return set(re.findall(r"`([^`]+)`", text))


def docs_reference_winners(*, docs_paths: list[Path], winners: CanonicalWinnerIds) -> bool:
    expected = {
        winners.current_selected_architecture_id,
        winners.promoted_selected_architecture_id,
    }
    found: set[str] = set()
    for path in docs_paths:
        if not path.exists():
            continue
        found.update(extract_winner_mentions(path.read_text(encoding="utf-8")))
    return expected.issubset(found)


__all__ = [
    "CanonicalWinnerIds",
    "docs_reference_winners",
    "extract_winner_mentions",
    "load_canonical_winner_ids",
    "write_canonical_winner_manifest",
]
