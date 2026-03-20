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
    config_path = repo_root / "configs" / "exp" / "tomics_partition_compare.yaml"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(
        "\n".join(
            [
                "exp:",
                "  name: compare_test",
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
                "",
            ]
        ),
        encoding="utf-8",
    )
    return config_path


def _script_path() -> Path:
    return Path(__file__).resolve().parents[1] / "scripts" / "run_tomics_partition_compare.py"


def test_compare_runner_writes_expected_artifacts(tmp_path: Path) -> None:
    repo_root = _make_repo_root(tmp_path)
    forcing_path = repo_root / "data" / "forcing.csv"
    forcing_path.parent.mkdir(parents=True)
    _write_forcing_csv(forcing_path)
    config_path = _write_config(repo_root)
    output_root = tmp_path / "compare-output"

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
    experiment_dir = Path(summary["output_root"])
    assert experiment_dir.exists()

    for policy_name in ("legacy", "thorp_fruit_veg", "tomics"):
        policy_dir = experiment_dir / policy_name
        assert (policy_dir / "df.csv").exists()
        assert (policy_dir / "meta.json").exists()

    summary_csv = experiment_dir / "summary.csv"
    comparison_plot = experiment_dir / "comparison_plot.png"
    assert summary_csv.exists()
    assert comparison_plot.exists()
    assert not (experiment_dir / "comparison_plot.pdf").exists()
    assert (experiment_dir / "comparison_plot_data.csv").exists()
    assert (experiment_dir / "comparison_plot_spec.yaml").exists()
    assert (experiment_dir / "comparison_plot_resolved_spec.yaml").exists()
    assert (experiment_dir / "comparison_plot_tokens.yaml").exists()
    assert (experiment_dir / "comparison_plot_metadata.json").exists()
    assert Path(summary["comparison_plot_metadata"]).exists()

    summary_df = pd.read_csv(summary_csv)
    assert set(summary_df["policy"]) == {"legacy", "thorp_fruit_veg", "tomics"}
    assert {
        "mean_alloc_frac_fruit",
        "mean_alloc_frac_leaf",
        "mean_alloc_frac_stem",
        "mean_alloc_frac_root",
        "final_lai",
        "final_total_dry_weight_g_m2",
        "mean_theta_substrate",
        "mean_water_supply_stress",
    }.issubset(summary_df.columns)
