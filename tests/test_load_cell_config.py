from __future__ import annotations

from pathlib import Path

import pytest

from stomatal_optimiaztion.domains import load_cell
from stomatal_optimiaztion.domains.load_cell import PipelineConfig, load_config


def test_load_cell_import_surface_exposes_config_helpers() -> None:
    assert load_cell.PipelineConfig is PipelineConfig
    assert load_cell.load_config is load_config


def test_pipeline_config_to_dict_serializes_paths() -> None:
    config = PipelineConfig(
        input_path=Path("input.csv"),
        output_path=Path("out.csv"),
    )

    data = config.to_dict()

    assert data["input_path"] == "input.csv"
    assert data["output_path"] == "out.csv"
    assert data["smooth_method"] == "savgol"


def test_load_config_without_path_returns_defaults() -> None:
    config = load_config()

    assert config.input_path is None
    assert config.output_path is None
    assert config.timestamp_column == "timestamp"
    assert config.water_balance_scale_max == 3.0


def test_load_config_reads_yaml_and_coerces_paths(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "\n".join(
            [
                "input_path: data/raw.csv",
                "output_path: artifacts/out.csv",
                "smooth_window_sec: 61",
                "use_hysteresis_labels: true",
            ]
        ),
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config.input_path == Path("data/raw.csv")
    assert config.output_path == Path("artifacts/out.csv")
    assert config.smooth_window_sec == 61
    assert config.use_hysteresis_labels is True


def test_load_config_overrides_take_precedence(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text("smooth_window_sec: 61\noutput_path: artifacts/out.csv\n", encoding="utf-8")

    config = load_config(
        config_path,
        overrides={
            "smooth_window_sec": 15,
            "output_path": "",
        },
    )

    assert config.smooth_window_sec == 15
    assert config.output_path is None


def test_load_config_raises_for_missing_file(tmp_path: Path) -> None:
    missing_path = tmp_path / "missing.yaml"

    with pytest.raises(FileNotFoundError):
        load_config(missing_path)


def test_load_config_requires_mapping_root(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text("- bad\n- config\n", encoding="utf-8")

    with pytest.raises(ValueError, match="mapping"):
        load_config(config_path)
