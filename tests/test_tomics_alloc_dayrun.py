from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.alloc.core import build_exp_key, load_config
from stomatal_optimiaztion.domains.tomato.tomics.alloc.pipelines import (
    config_payload_for_exp_key,
    run_tomato_dayrun,
    run_tomato_dayrun_from_config,
)


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


def _base_config() -> dict[str, object]:
    return {
        "exp": {"name": "tomato_dayrun"},
        "pipeline": {
            "model": "tomato_legacy",
            "fixed_lai": 2.1,
            "theta_substrate": 0.33,
            "partition_policy": "thorp_veg",
            "allocation_scheme": "4pool",
        },
        "forcing": {
            "csv_path": "../../data/forcing.csv",
            "max_steps": 2,
            "default_dt_s": 3600.0,
        },
    }


def test_run_tomato_dayrun_writes_relative_output_artifacts(tmp_path: Path) -> None:
    repo_root = _make_repo_root(tmp_path)
    forcing_path = repo_root / "data" / "forcing.csv"
    forcing_path.parent.mkdir(parents=True)
    _write_forcing_csv(forcing_path)
    config_path = repo_root / "configs" / "exp" / "tomato_dayrun.yaml"
    config_path.parent.mkdir(parents=True)
    config_path.write_text("exp: {}\n", encoding="utf-8")

    config = _base_config()
    artifacts = run_tomato_dayrun(
        config,
        output_dir="artifacts/runs/demo",
        repo_root=repo_root,
        config_path=config_path,
    )

    assert artifacts.output_dir == (repo_root / "artifacts" / "runs" / "demo").resolve()
    assert artifacts.df_csv == artifacts.output_dir / "df.csv"
    assert artifacts.meta_json == artifacts.output_dir / "meta.json"
    assert artifacts.df_csv.exists()
    assert artifacts.meta_json.exists()

    df = pd.read_csv(artifacts.df_csv)
    with artifacts.meta_json.open("r", encoding="utf-8") as handle:
        meta = json.load(handle)

    assert len(df) == 2
    assert meta["exp_name"] == "tomato_dayrun"
    assert meta["model"] == "tomato_legacy"
    assert meta["rows"] == 2
    assert meta["schedule"] == {"max_steps": 2, "default_dt_s": 3600.0}
    assert meta["exp_key"] == build_exp_key(
        config_payload_for_exp_key(config),
        prefix="tomato_dayrun",
    )
    assert "metrics" in meta
    assert "created_at" not in meta


def test_run_tomato_dayrun_from_config_loads_extends_and_infers_repo_root(
    tmp_path: Path,
) -> None:
    repo_root = _make_repo_root(tmp_path)
    forcing_path = repo_root / "data" / "forcing.csv"
    forcing_path.parent.mkdir(parents=True)
    _write_forcing_csv(forcing_path)

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
                "forcing:",
                "  csv_path: ../../data/forcing.csv",
                "  default_dt_s: 3600.0",
                "",
            ]
        ),
        encoding="utf-8",
    )
    config_path = exp_dir / "tomato_dayrun.yaml"
    config_path.write_text(
        "\n".join(
            [
                "extends: ../base.yaml",
                "pipeline:",
                "  partition_policy: thorp_veg",
                "  allocation_scheme: 4pool",
                "forcing:",
                "  max_steps: 3",
                "",
            ]
        ),
        encoding="utf-8",
    )

    artifacts = run_tomato_dayrun_from_config(
        config_path,
        output_dir="artifacts/runs/from-config",
    )

    with artifacts.meta_json.open("r", encoding="utf-8") as handle:
        meta = json.load(handle)

    config = load_config(config_path)
    assert artifacts.output_dir == (repo_root / "artifacts" / "runs" / "from-config").resolve()
    assert meta["rows"] == 3
    assert meta["schedule"] == {"max_steps": 3, "default_dt_s": 3600.0}
    assert meta["exp_key"] == build_exp_key(
        config_payload_for_exp_key(config),
        prefix="tomato_dayrun",
    )


def test_run_tomato_dayrun_supports_absolute_output_dir(tmp_path: Path) -> None:
    repo_root = _make_repo_root(tmp_path)
    forcing_path = repo_root / "data" / "forcing.csv"
    forcing_path.parent.mkdir(parents=True)
    _write_forcing_csv(forcing_path)
    config = _base_config()
    config["forcing"] = {
        **dict(config["forcing"]),  # type: ignore[arg-type]
        "csv_path": str(forcing_path),
    }

    artifacts = run_tomato_dayrun(
        config,
        output_dir=tmp_path / "absolute-output",
        repo_root=repo_root,
    )

    assert artifacts.output_dir == (tmp_path / "absolute-output").resolve()
    assert artifacts.df_csv.exists()
    assert artifacts.meta_json.exists()
