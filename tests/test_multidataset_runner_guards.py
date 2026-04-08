from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd
import yaml


def _load_script_module(module_name: str, relative_script_path: str):
    repo_root = Path(__file__).resolve().parents[1]
    script_path = repo_root / relative_script_path
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load script module from {script_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_multidataset_factorial_runner_requires_explicit_root_for_non_knu_runnable_dataset(tmp_path: Path) -> None:
    module = _load_script_module(
        "run_tomics_multidataset_harvest_factorial_module",
        "scripts/run_tomics_multidataset_harvest_factorial.py",
    )
    forcing_path = tmp_path / "forcing.csv"
    harvest_path = tmp_path / "harvest.csv"
    output_root = tmp_path / "out"
    forcing_path.write_text("datetime,T_air_C\n2025-01-01,24\n", encoding="utf-8")
    harvest_path.write_text("date,measured\n2025-01-01,1.0\n", encoding="utf-8")
    config = {
        "validation": {
            "datasets": {
                "items": [
                    {
                        "dataset_id": "public_demo",
                        "dataset_kind": "fixture",
                        "display_name": "Public Demo",
                        "dataset_family": "public_rda",
                        "observation_family": "yield",
                        "capability": "measured_harvest",
                        "ingestion_status": "runnable",
                        "forcing_path": str(forcing_path),
                        "observed_harvest_path": str(harvest_path),
                        "validation_start": "2025-01-01",
                        "validation_end": "2025-01-31",
                        "basis": {"reporting_basis": "floor_area_g_m2", "plants_per_m2": 1.7},
                        "observation": {"date_column": "date", "measured_cumulative_column": "measured"},
                        "sanitized_fixture": {
                            "forcing_fixture_path": str(forcing_path),
                            "observed_harvest_fixture_path": str(harvest_path),
                        },
                    }
                ]
            },
            "multidataset_factorial": {
                "output_root": str(output_root),
                "dataset_factorial_roots": {},
            },
        }
    }
    config_path = tmp_path / "factorial.yaml"
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

    result = module.run_multidataset_harvest_factorial(config, repo_root=tmp_path, config_path=config_path)

    assert result["scorecard_rows"] == 0
    skip_df = pd.read_csv(output_root / "dataset_skip_report.csv")
    assert skip_df.loc[0, "dataset_id"] == "public_demo"
    assert skip_df.loc[0, "skip_reason"] == "missing_dataset_factorial_root"


def test_multidataset_promotion_gate_fails_when_required_upstream_artifacts_are_missing(tmp_path: Path) -> None:
    module = _load_script_module(
        "run_tomics_multidataset_harvest_promotion_gate_module",
        "scripts/run_tomics_multidataset_harvest_promotion_gate.py",
    )
    config = {
        "validation": {
            "multidataset_promotion_gate": {
                "scorecard_root": str(tmp_path / "missing"),
                "output_root": str(tmp_path / "out"),
            }
        }
    }

    try:
        module.run_multidataset_harvest_promotion_gate(
            config,
            repo_root=tmp_path,
            config_path=tmp_path / "gate.yaml",
        )
    except FileNotFoundError as exc:
        assert "cross_dataset_scorecard.csv" in str(exc)
    else:
        raise AssertionError("Expected promotion gate to fail when upstream scorecard artifacts are missing.")
