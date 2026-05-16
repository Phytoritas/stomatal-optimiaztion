from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.alloc.core import ensure_dir, write_json


def as_dict(raw: object) -> dict[str, Any]:
    if isinstance(raw, Mapping):
        return {str(key): value for key, value in raw.items()}
    return {}


def resolve_artifact_path(
    raw: str | Path,
    *,
    repo_root: Path,
    config_path: Path | None = None,
    prefer_repo_root: bool = False,
) -> Path:
    candidate = Path(raw)
    if candidate.is_absolute():
        return candidate
    probes: list[Path] = []
    repo_probe = (repo_root / candidate).resolve()
    if prefer_repo_root:
        return repo_probe
    config_probe = (config_path.parent / candidate).resolve() if config_path is not None else None
    if config_probe is not None:
        probes.append(config_probe)
    probes.append(repo_probe)
    probes.append((Path.cwd() / candidate).resolve())
    for probe in probes:
        if probe.exists():
            return probe
    return probes[0]


def read_json(path: Path, *, artifact_label: str) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Required HAF gate artifact is missing: {artifact_label} at {path}")
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, Mapping):
        raise TypeError(f"Required HAF gate artifact must be a mapping: {artifact_label} at {path}")
    return {str(key): value for key, value in raw.items()}


def read_required_csv(path: Path, *, artifact_label: str) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Required HAF gate artifact is missing: {artifact_label} at {path}")
    try:
        frame = pd.read_csv(path)
    except pd.errors.EmptyDataError:
        raise ValueError(f"Required HAF gate artifact is empty: {artifact_label} at {path}") from None
    if frame.empty:
        raise ValueError(f"Required HAF gate artifact has no rows: {artifact_label} at {path}")
    return frame


def bool_value(value: object, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        if pd.isna(value):
            return default
        return bool(value)
    normalized = str(value).strip().casefold()
    if normalized in {"true", "1", "yes", "y"}:
        return True
    if normalized in {"false", "0", "no", "n", ""}:
        return False
    return default


def float_value(value: object, default: float = 0.0) -> float:
    numeric = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(numeric):
        return default
    return float(numeric)


def int_value(value: object, default: int = 0) -> int:
    numeric = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(numeric):
        return default
    return int(numeric)


def json_cell(value: object) -> object:
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True)
    if value is None:
        return ""
    return value


def write_key_value_csv(path: Path, payload: Mapping[str, Any]) -> Path:
    rows = [{"field": key, "value": json_cell(value)} for key, value in payload.items()]
    ensure_dir(path.parent)
    pd.DataFrame(rows).to_csv(path, index=False)
    return path


def write_markdown_table(path: Path, frame: pd.DataFrame, *, title: str, intro_lines: list[str] | None = None) -> Path:
    lines = [f"# {title}", ""]
    lines.extend(intro_lines or [])
    if intro_lines:
        lines.append("")
    if frame.empty:
        lines.extend(["No rows.", ""])
    else:
        columns = [str(column) for column in frame.columns]
        lines.append("| " + " | ".join(columns) + " |")
        lines.append("| " + " | ".join(["---"] * len(columns)) + " |")
        for _, row in frame.iterrows():
            values = [str(row.get(column, "")).replace("\n", " ") for column in columns]
            lines.append("| " + " | ".join(values) + " |")
        lines.append("")
    ensure_dir(path.parent)
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def duplicate_casefold_keys(raw_text: str) -> list[str]:
    duplicates: list[str] = []

    def hook(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        seen: set[str] = set()
        for key, _value in pairs:
            normalized = str(key).casefold()
            if normalized in seen and normalized not in duplicates:
                duplicates.append(normalized)
            seen.add(normalized)
        return dict(pairs)

    json.loads(raw_text, object_pairs_hook=hook)
    return duplicates


def check_row(
    check_id: str,
    passed: bool,
    *,
    hard_blocker: bool = True,
    evidence_value: object = "",
    blocker_code: str | None = None,
    notes: str = "",
) -> dict[str, object]:
    return {
        "check_id": check_id,
        "status": "pass" if passed else "fail",
        "hard_blocker": bool(hard_blocker),
        "blocker_code": "" if passed else (blocker_code or check_id),
        "evidence_value": json_cell(evidence_value),
        "notes": notes,
    }


def write_json_and_csv_pair(
    *,
    json_path: Path,
    csv_path: Path,
    payload: Mapping[str, Any],
) -> None:
    write_json(json_path, dict(payload))
    write_key_value_csv(csv_path, payload)


__all__ = [
    "as_dict",
    "bool_value",
    "check_row",
    "duplicate_casefold_keys",
    "float_value",
    "int_value",
    "json_cell",
    "read_json",
    "read_required_csv",
    "resolve_artifact_path",
    "write_json_and_csv_pair",
    "write_key_value_csv",
    "write_markdown_table",
]
