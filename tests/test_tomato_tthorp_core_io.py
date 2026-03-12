from __future__ import annotations

import json
from pathlib import Path

import pytest

from stomatal_optimiaztion.domains.tomato.tthorp.core import (
    deep_merge,
    ensure_dir,
    load_config,
    read_yaml,
    write_json,
)


def test_ensure_dir_creates_nested_directory(tmp_path: Path) -> None:
    out_dir = ensure_dir(tmp_path / "artifacts" / "tomato" / "run")

    assert out_dir.exists()
    assert out_dir.is_dir()


def test_write_json_creates_parent_and_writes_sorted_payload(tmp_path: Path) -> None:
    out_path = write_json(
        tmp_path / "out" / "meta.json",
        {"z_key": 1, "a_key": {"nested": True}},
    )

    text = out_path.read_text(encoding="utf-8")
    assert text.endswith("\n")
    assert '"a_key"' in text.splitlines()[1]
    assert json.loads(text) == {"a_key": {"nested": True}, "z_key": 1}


def test_read_yaml_returns_mapping(tmp_path: Path) -> None:
    yaml_path = tmp_path / "config.yaml"
    yaml_path.write_text(
        "exp:\n  name: tomato_dayrun\nforcing:\n  max_steps: 12\n",
        encoding="utf-8",
    )

    parsed = read_yaml(yaml_path)

    assert parsed == {"exp": {"name": "tomato_dayrun"}, "forcing": {"max_steps": 12}}


def test_read_yaml_rejects_non_mapping(tmp_path: Path) -> None:
    yaml_path = tmp_path / "invalid.yaml"
    yaml_path.write_text("- tomato\n- cucumber\n", encoding="utf-8")

    with pytest.raises(TypeError, match="Config must parse to a mapping"):
        read_yaml(yaml_path)


def test_deep_merge_recursively_overrides_without_mutating_inputs() -> None:
    base = {
        "exp": {"name": "base", "tags": ["legacy"]},
        "forcing": {"max_steps": 10, "default_dt_s": 3600.0},
    }
    override = {
        "exp": {"name": "override"},
        "forcing": {"max_steps": 20},
        "pipeline": {"model": "tomato_legacy"},
    }

    merged = deep_merge(base, override)

    assert merged == {
        "exp": {"name": "override", "tags": ["legacy"]},
        "forcing": {"max_steps": 20, "default_dt_s": 3600.0},
        "pipeline": {"model": "tomato_legacy"},
    }
    assert base["exp"]["name"] == "base"
    assert "pipeline" not in base


def test_load_config_merges_recursive_extends_chain(tmp_path: Path) -> None:
    base_path = tmp_path / "configs" / "base.yaml"
    child_path = tmp_path / "configs" / "child.yaml"
    grandchild_path = tmp_path / "configs" / "exp" / "tomato_dayrun.yaml"
    base_path.parent.mkdir(parents=True)
    grandchild_path.parent.mkdir(parents=True)

    base_path.write_text(
        "\n".join(
            [
                "exp:",
                "  name: base",
                "pipeline:",
                "  model: tomato_legacy",
                "  fixed_lai: 2.0",
                "forcing:",
                "  csv_path: data/base.csv",
                "  max_steps: 8",
                "",
            ]
        ),
        encoding="utf-8",
    )
    child_path.write_text(
        "\n".join(
            [
                "extends: base.yaml",
                "pipeline:",
                "  fixed_lai: 2.5",
                "forcing:",
                "  default_dt_s: 3600.0",
                "",
            ]
        ),
        encoding="utf-8",
    )
    grandchild_path.write_text(
        "\n".join(
            [
                "extends: ../child.yaml",
                "exp:",
                "  name: tomato_dayrun",
                "forcing:",
                "  max_steps: 12",
                "",
            ]
        ),
        encoding="utf-8",
    )

    config = load_config(grandchild_path)

    assert config == {
        "exp": {"name": "tomato_dayrun"},
        "pipeline": {"model": "tomato_legacy", "fixed_lai": 2.5},
        "forcing": {
            "csv_path": "data/base.csv",
            "max_steps": 12,
            "default_dt_s": 3600.0,
        },
    }
    assert "extends" not in config
