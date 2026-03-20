from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pandas as pd


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
                "2026-01-01T06:00:00",
                "2026-01-01T12:00:00",
            ],
            "T_air_C": [21.0, 23.0, 25.0],
            "PAR_umol": [120.0, 320.0, 520.0],
            "CO2_ppm": [410.0, 420.0, 430.0],
            "RH_percent": [75.0, 65.0, 58.0],
            "wind_speed_ms": [0.6, 0.9, 1.1],
            "n_fruits_per_truss": [4, 4, 5],
        }
    ).to_csv(path, index=False)


def _write_config(repo_root: Path) -> Path:
    config_path = repo_root / "configs" / "exp" / "tomics_factorial.yaml"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(
        "\n".join(
            [
                "exp:",
                "  name: factorial_test",
                "pipeline:",
                "  model: tomato_legacy",
                "  partition_policy: tomics",
                "  allocation_scheme: 4pool",
                "  theta_substrate: 0.33",
                "  fixed_lai: 2.3",
                "  tomics:",
                "    wet_root_cap: 0.10",
                "    dry_root_cap: 0.18",
                "    lai_target_center: 2.75",
                "forcing:",
                "  csv_path: ../../data/forcing.csv",
                "  default_dt_s: 21600",
                "  max_steps: 3",
                "screen:",
                "  partition_policies: [legacy, tomics]",
                "  theta_substrate: [0.20, 0.33]",
                "  wet_root_cap: [0.08]",
                "  dry_root_cap: [0.15]",
                "  lai_target_center: [2.5, 3.0]",
                "  collapse_non_tomics_tomics_factors: true",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return config_path


def _script_path() -> Path:
    return Path(__file__).resolve().parents[1] / "scripts" / "run_tomics_factorial.py"


def test_factorial_runner_writes_design_and_summary_artifacts(tmp_path: Path) -> None:
    repo_root = _make_repo_root(tmp_path)
    forcing_path = repo_root / "data" / "forcing.csv"
    forcing_path.parent.mkdir(parents=True)
    _write_forcing_csv(forcing_path)
    config_path = _write_config(repo_root)
    output_root = tmp_path / "factorial-output"

    result = subprocess.run(
        [
            sys.executable,
            str(_script_path()),
            "--config",
            str(config_path),
            "--output-root",
            str(output_root),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    summary = json.loads(result.stdout.strip())
    design_table = Path(summary["design_table_csv"])
    run_metrics = Path(summary["run_metrics_csv"])
    summary_plot = Path(summary["summary_plot"])

    assert design_table.exists()
    assert run_metrics.exists()
    assert summary_plot.exists()
    assert (Path(summary["output_root"]) / "meta.json").exists()

    design_df = pd.read_csv(design_table)
    metrics_df = pd.read_csv(run_metrics)
    assert {
        "partition_policy",
        "theta_substrate",
        "wet_root_cap",
        "dry_root_cap",
        "lai_target_center",
    }.issubset(design_df.columns)
    assert {
        "run_key",
        "final_lai",
        "final_total_dry_weight_g_m2",
        "mean_alloc_frac_root",
    }.issubset(metrics_df.columns)
    assert set(metrics_df["partition_policy"]) == {"legacy", "tomics"}
