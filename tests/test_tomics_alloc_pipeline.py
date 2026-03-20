from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from stomatal_optimiaztion.domains.tomato.tomics.alloc.pipelines import (
    config_payload_for_exp_key,
    resolve_forcing_path,
    resolve_repo_root,
    run_tomato_legacy_pipeline,
    summarize_tomato_legacy_metrics,
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


def test_resolve_repo_root_prefers_configured_path_relative_to_config_path(
    tmp_path: Path,
) -> None:
    repo_root = _make_repo_root(tmp_path)
    config_path = repo_root / "configs" / "exp" / "tomato_legacy.yaml"
    config_path.parent.mkdir(parents=True)
    config_path.write_text("pipeline: {}\n", encoding="utf-8")

    resolved = resolve_repo_root(
        {"paths": {"repo_root": "../.."}},
        config_path=config_path,
    )

    assert resolved == repo_root.resolve()


def test_resolve_repo_root_infers_from_config_path_markers(tmp_path: Path) -> None:
    repo_root = _make_repo_root(tmp_path)
    config_path = repo_root / "configs" / "exp" / "tomato_legacy.yaml"
    config_path.parent.mkdir(parents=True)
    config_path.write_text("pipeline: {}\n", encoding="utf-8")

    resolved = resolve_repo_root({}, config_path=config_path)

    assert resolved == repo_root.resolve()


def test_resolve_forcing_path_uses_repo_root_and_config_path(tmp_path: Path) -> None:
    repo_root = _make_repo_root(tmp_path)
    forcing_path = repo_root / "data" / "forcing.csv"
    forcing_path.parent.mkdir(parents=True)
    _write_forcing_csv(forcing_path)
    config_path = repo_root / "configs" / "exp" / "tomato_legacy.yaml"
    config_path.parent.mkdir(parents=True)
    config_path.write_text("forcing: {}\n", encoding="utf-8")

    resolved = resolve_forcing_path(
        {"forcing": {"csv_path": "../../data/forcing.csv"}},
        repo_root=repo_root,
        config_path=config_path,
    )

    assert resolved == forcing_path.resolve()


def test_config_payload_for_exp_key_keeps_only_expected_sections() -> None:
    payload = config_payload_for_exp_key(
        {
            "exp": {"name": "demo"},
            "pipeline": {"model": "tomato_legacy"},
            "forcing": {"max_steps": 2},
            "paths": {"repo_root": "ignored"},
        }
    )

    assert payload == {
        "exp": {"name": "demo"},
        "pipeline": {"model": "tomato_legacy"},
        "forcing": {"max_steps": 2},
    }


def test_run_tomato_legacy_pipeline_runs_with_relative_paths(tmp_path: Path) -> None:
    repo_root = _make_repo_root(tmp_path)
    forcing_path = repo_root / "data" / "forcing.csv"
    forcing_path.parent.mkdir(parents=True)
    _write_forcing_csv(forcing_path)
    config_path = repo_root / "configs" / "exp" / "tomato_legacy.yaml"
    config_path.parent.mkdir(parents=True)
    config_path.write_text("exp: {}\n", encoding="utf-8")

    config = {
        "exp": {"name": "tomato_legacy"},
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

    out = run_tomato_legacy_pipeline(config, config_path=config_path)

    expected_columns = {
        "datetime",
        "theta_substrate",
        "water_supply_stress",
        "e",
        "g_w",
        "a_n",
        "r_d",
        "LAI",
        "total_dry_weight_g_m2",
        "transpiration_rate_g_s_m2",
    }
    assert expected_columns.issubset(out.columns)
    assert len(out) == 2
    assert out["LAI"].tolist() == pytest.approx([2.1, 2.1])

    numeric = out[list(expected_columns - {"datetime"})].to_numpy(dtype=float)
    assert np.isfinite(numeric).all()


def test_run_tomato_legacy_pipeline_rejects_unsupported_model(tmp_path: Path) -> None:
    repo_root = _make_repo_root(tmp_path)
    forcing_path = repo_root / "data" / "forcing.csv"
    forcing_path.parent.mkdir(parents=True)
    _write_forcing_csv(forcing_path)

    with pytest.raises(ValueError, match="Unsupported pipeline.model"):
        run_tomato_legacy_pipeline(
            {
                "pipeline": {"model": "other"},
                "forcing": {"csv_path": str(forcing_path)},
            },
            repo_root=repo_root,
        )


def test_summarize_tomato_legacy_metrics_reports_rows_and_final_fields(tmp_path: Path) -> None:
    repo_root = _make_repo_root(tmp_path)
    forcing_path = repo_root / "data" / "forcing.csv"
    forcing_path.parent.mkdir(parents=True)
    _write_forcing_csv(forcing_path)

    out = run_tomato_legacy_pipeline(
        {
            "pipeline": {
                "model": "tomato_legacy",
                "fixed_lai": 2.0,
                "theta_substrate": 0.33,
            },
            "forcing": {
                "csv_path": str(forcing_path),
                "max_steps": 3,
                "default_dt_s": 3600.0,
            },
        },
        repo_root=repo_root,
    )

    metrics = summarize_tomato_legacy_metrics(out)

    assert metrics["rows"] == 3
    assert metrics["mean_theta_substrate"] == pytest.approx(0.33)
    assert float(metrics["final_lai"]) == pytest.approx(2.0)
    assert float(metrics["final_total_dry_weight_g_m2"]) >= 0.0


def test_summarize_tomato_legacy_metrics_handles_empty_dataframe() -> None:
    metrics = summarize_tomato_legacy_metrics(pd.DataFrame())

    assert metrics == {"rows": 0}
