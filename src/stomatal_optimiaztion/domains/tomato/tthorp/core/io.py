from __future__ import annotations

from collections.abc import Mapping
import copy
import json
from pathlib import Path
from typing import Any

import yaml


def ensure_dir(path: str | Path) -> Path:
    out_dir = Path(path)
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def write_json(path: str | Path, payload: Mapping[str, Any]) -> Path:
    out_path = Path(path)
    ensure_dir(out_path.parent)
    with out_path.open("w", encoding="utf-8") as handle:
        json.dump(dict(payload), handle, indent=2, sort_keys=True)
        handle.write("\n")
    return out_path


def read_yaml(path: str | Path) -> dict[str, Any]:
    yaml_path = Path(path)
    with yaml_path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}
    if not isinstance(raw, Mapping):
        raise TypeError(f"Config must parse to a mapping, got {type(raw).__name__}.")
    return {str(key): value for key, value in raw.items()}


def deep_merge(base: Mapping[str, Any], override: Mapping[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = copy.deepcopy(dict(base))
    for key, value in override.items():
        if key in merged and isinstance(merged[key], Mapping) and isinstance(value, Mapping):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


def load_config(path: str | Path) -> dict[str, Any]:
    config_path = Path(path).resolve()
    config = read_yaml(config_path)
    parent = config.pop("extends", None)
    if parent is None:
        return config

    parent_path = config_path.parent / str(parent)
    base = load_config(parent_path)
    return deep_merge(base, config)


__all__ = [
    "deep_merge",
    "ensure_dir",
    "load_config",
    "read_yaml",
    "write_json",
]
