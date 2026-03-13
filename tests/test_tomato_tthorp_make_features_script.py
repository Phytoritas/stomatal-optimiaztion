from __future__ import annotations

from pathlib import Path
import subprocess
import sys

import pandas as pd

from stomatal_optimiaztion.domains.tomato.tthorp.core import build_exp_key, load_config
from stomatal_optimiaztion.domains.tomato.tthorp.pipelines import config_payload_for_exp_key


def _make_repo_root(tmp_path: Path) -> Path:
    repo_root = tmp_path / "repo"
    (repo_root / "src" / "stomatal_optimiaztion").mkdir(parents=True)
    (repo_root / "pyproject.toml").write_text("[tool.poetry]\nname = 'demo'\n", encoding="utf-8")
    return repo_root


def _script_path() -> Path:
    return Path(__file__).resolve().parents[1] / "scripts" / "make_features.py"


def _write_config(repo_root: Path, *, include_features_dir: bool) -> Path:
    configs_dir = repo_root / "configs"
    exp_dir = configs_dir / "exp"
    exp_dir.mkdir(parents=True)
    (configs_dir / "base.yaml").write_text(
        "\n".join(
            [
                "exp:",
                "  name: tomato_dayrun",
                "forcing:",
                "  csv_path: ../../data/forcing.csv",
                "  default_co2_ppm: 430.0",
                "  default_n_fruits_per_truss: 5",
                "",
            ]
        ),
        encoding="utf-8",
    )
    lines = [
        "extends: ../base.yaml",
        "forcing:",
        "  max_steps: 2",
    ]
    if include_features_dir:
        lines.extend(
            [
                "paths:",
                "  features_dir: artifacts/features-alt",
            ]
        )
    lines.append("")
    config_path = exp_dir / "tomato_dayrun.yaml"
    config_path.write_text("\n".join(lines), encoding="utf-8")
    return config_path


def test_make_features_script_builds_feature_csv_with_override_output(tmp_path: Path) -> None:
    repo_root = _make_repo_root(tmp_path)
    forcing_path = repo_root / "data" / "forcing.csv"
    forcing_path.parent.mkdir(parents=True)
    pd.DataFrame(
        {
            "datetime": ["2026-01-01T00:00:00", "2026-01-01T01:00:00", "2026-01-01T02:00:00"],
            "SW_in_Wm2": [100.0, 200.0, 300.0],
            "T_air_C": [21.0, 22.0, 23.0],
            "RH_percent": [70.0, 65.0, 60.0],
            "wind_speed_ms": [0.8, 1.0, 1.2],
        }
    ).to_csv(forcing_path, index=False)
    config_path = _write_config(repo_root, include_features_dir=False)
    output_path = tmp_path / "features.csv"

    result = subprocess.run(
        [
            sys.executable,
            str(_script_path()),
            "--config",
            str(config_path),
            "--output",
            str(output_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert Path(result.stdout.strip()) == output_path.resolve()
    df = pd.read_csv(output_path)
    assert len(df) == 2
    assert df["PAR_umol"].tolist() == [460.0, 920.0]
    assert df["CO2_ppm"].tolist() == [430.0, 430.0]
    assert df["n_fruits_per_truss"].tolist() == [5, 5]


def test_make_features_script_uses_default_features_dir_and_existing_columns(
    tmp_path: Path,
) -> None:
    repo_root = _make_repo_root(tmp_path)
    forcing_path = repo_root / "data" / "forcing.csv"
    forcing_path.parent.mkdir(parents=True)
    pd.DataFrame(
        {
            "datetime": ["2026-01-01T00:00:00", "2026-01-01T01:00:00", "2026-01-01T02:00:00"],
            "r_incom": [50.0, 75.0, 100.0],
            "PAR_umol": [10.0, 20.0, 30.0],
            "CO2_ppm": [400.0, 405.0, 410.0],
            "n_fruits_per_truss": [3, 4, 5],
            "T_air_C": [20.0, 21.0, 22.0],
            "RH_percent": [60.0, 62.0, 64.0],
            "wind_speed_ms": [1.0, 1.1, 1.2],
        }
    ).to_csv(forcing_path, index=False)
    config_path = _write_config(repo_root, include_features_dir=True)
    config = load_config(config_path)
    exp_key = build_exp_key(config_payload_for_exp_key(config), prefix="tomato_dayrun")
    expected_output = (repo_root / "artifacts" / "features-alt" / f"{exp_key}.features.csv").resolve()

    result = subprocess.run(
        [
            sys.executable,
            str(_script_path()),
            "--config",
            str(config_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert Path(result.stdout.strip()) == expected_output
    df = pd.read_csv(expected_output)
    assert len(df) == 2
    assert df["PAR_umol"].tolist() == [10.0, 20.0]
    assert df["CO2_ppm"].tolist() == [400.0, 405.0]
    assert df["n_fruits_per_truss"].tolist() == [3, 4]
