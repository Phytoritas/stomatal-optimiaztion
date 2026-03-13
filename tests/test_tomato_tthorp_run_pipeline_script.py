from __future__ import annotations

import json
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


def _write_forcing_csv(path: Path) -> None:
    pd.DataFrame(
        {
            "datetime": [
                "2026-01-01T00:00:00",
                "2026-01-01T01:00:00",
                "2026-01-01T02:00:00",
            ],
            "T_air_C": [21.0, 22.0, 23.0],
            "PAR_umol": [150.0, 250.0, 350.0],
            "CO2_ppm": [410.0, 420.0, 430.0],
            "RH_percent": [70.0, 65.0, 60.0],
            "wind_speed_ms": [0.8, 1.0, 1.2],
        }
    ).to_csv(path, index=False)


def _write_config(repo_root: Path, *, include_output_dir: bool) -> Path:
    configs_dir = repo_root / "configs"
    exp_dir = configs_dir / "exp"
    exp_dir.mkdir(parents=True)
    (configs_dir / "base.yaml").write_text(
        "\n".join(
            [
                "exp:",
                "  name: tomato_dayrun",
                "pipeline:",
                "  model: tomato_legacy",
                "  fixed_lai: 2.0",
                "  theta_substrate: 0.33",
                "  partition_policy: thorp_veg",
                "  allocation_scheme: 4pool",
                "forcing:",
                "  csv_path: ../../data/forcing.csv",
                "  default_dt_s: 3600.0",
                "",
            ]
        ),
        encoding="utf-8",
    )
    lines = [
        "extends: ../base.yaml",
        "forcing:",
        "  max_steps: 3",
    ]
    if include_output_dir:
        lines.extend(
            [
                "paths:",
                "  output_dir: artifacts/custom-runs",
            ]
        )
    lines.append("")
    config_path = exp_dir / "tomato_dayrun.yaml"
    config_path.write_text("\n".join(lines), encoding="utf-8")
    return config_path


def _script_path() -> Path:
    return Path(__file__).resolve().parents[1] / "scripts" / "run_pipeline.py"


def test_run_pipeline_script_writes_summary_and_artifacts(tmp_path: Path) -> None:
    repo_root = _make_repo_root(tmp_path)
    forcing_path = repo_root / "data" / "forcing.csv"
    forcing_path.parent.mkdir(parents=True)
    _write_forcing_csv(forcing_path)
    config_path = _write_config(repo_root, include_output_dir=False)
    output_dir = tmp_path / "override-output"

    result = subprocess.run(
        [
            sys.executable,
            str(_script_path()),
            "--config",
            str(config_path),
            "--output-dir",
            str(output_dir),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    summary = json.loads(result.stdout.strip())
    config = load_config(config_path)
    expected_exp_key = build_exp_key(
        config_payload_for_exp_key(config),
        prefix="tomato_dayrun",
    )
    output_csv = output_dir / f"{expected_exp_key}.csv"
    metrics_json = output_dir / f"{expected_exp_key}.metrics.json"
    assert summary == {
        "exp_key": expected_exp_key,
        "metrics_json": str(metrics_json),
        "output_csv": str(output_csv),
        "rows": 3,
    }
    assert output_csv.exists()
    assert metrics_json.exists()

    with metrics_json.open("r", encoding="utf-8") as handle:
        metrics = json.load(handle)

    assert metrics["rows"] == 3
    assert "sum_a_n" in metrics


def test_run_pipeline_script_respects_exp_key_override_and_config_output_dir(
    tmp_path: Path,
) -> None:
    repo_root = _make_repo_root(tmp_path)
    forcing_path = repo_root / "data" / "forcing.csv"
    forcing_path.parent.mkdir(parents=True)
    _write_forcing_csv(forcing_path)
    config_path = _write_config(repo_root, include_output_dir=True)

    result = subprocess.run(
        [
            sys.executable,
            str(_script_path()),
            "--config",
            str(config_path),
            "--exp-key",
            "manual-key",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    summary = json.loads(result.stdout.strip())
    output_dir = (repo_root / "artifacts" / "custom-runs").resolve()
    output_csv = output_dir / "manual-key.csv"
    metrics_json = output_dir / "manual-key.metrics.json"
    assert summary == {
        "exp_key": "manual-key",
        "metrics_json": str(metrics_json),
        "output_csv": str(output_csv),
        "rows": 3,
    }
    assert output_csv.exists()
    assert metrics_json.exists()
