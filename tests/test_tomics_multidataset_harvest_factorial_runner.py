from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pandas as pd


def _script_path() -> Path:
    return Path(__file__).resolve().parents[1] / "scripts" / "run_tomics_multidataset_harvest_factorial.py"


def _load_script_module():
    spec = importlib.util.spec_from_file_location(
        "tomics_multidataset_harvest_factorial_runner_script",
        _script_path(),
    )
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write_dataset_files(tmp_path: Path, dataset_id: str) -> dict[str, object]:
    forcing_path = tmp_path / f"{dataset_id}_forcing.csv"
    harvest_path = tmp_path / f"{dataset_id}_harvest.csv"
    forcing_path.write_text("datetime,T_air_C\n2025-01-01,24\n", encoding="utf-8")
    harvest_path.write_text("date,measured\n2025-01-01,1.0\n", encoding="utf-8")
    return {
        "dataset_id": dataset_id,
        "dataset_kind": "fixture",
        "display_name": dataset_id,
        "dataset_family": "fixture_family",
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


def _write_factorial_outputs(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [
            {
                "fruit_harvest_family": "dekoning_fds",
                "leaf_harvest_family": "vegetative_unit_pruning",
                "fdmc_mode": "dekoning_fds",
                "mean_score": -8.0,
                "mean_rmse_cumulative_offset": 4.0,
                "mean_rmse_daily_increment": 1.5,
                "max_harvest_mass_balance_error": 0.0,
                "max_canopy_collapse_days": 2.0,
                "mean_native_family_state_fraction": 0.8,
                "mean_proxy_family_state_fraction": 0.2,
                "mean_shared_tdvs_proxy_fraction": 0.1,
                "family_state_mode_distribution": json.dumps({"native_payload": 0.8}, sort_keys=True),
                "proxy_mode_used_distribution": json.dumps({"false": 0.8, "true": 0.2}, sort_keys=True),
            }
        ]
    ).to_csv(root / "candidate_ranking.csv", index=False)
    (root / "selected_harvest_family.json").write_text(
        json.dumps(
            {
                "selected_fruit_harvest_family": "dekoning_fds",
                "selected_leaf_harvest_family": "vegetative_unit_pruning",
                "selected_fdmc_mode": "dekoning_fds",
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )


def test_multidataset_factorial_runner_does_not_reuse_knu_root_for_unmapped_dataset(tmp_path: Path) -> None:
    module = _load_script_module()
    knu_factorial_root = tmp_path / "out" / "tomics_knu_harvest_family_factorial"
    _write_factorial_outputs(knu_factorial_root)

    config = {
        "validation": {
            "datasets": {
                "default_dataset_ids": ["knu_actual"],
                "items": [
                    _write_dataset_files(tmp_path, "knu_actual"),
                    _write_dataset_files(tmp_path, "school_demo"),
                ],
            },
            "multidataset_factorial": {
                "output_root": str(tmp_path / "multidataset-output"),
                "dataset_factorial_roots": {
                    "knu_actual": str(knu_factorial_root),
                },
            },
        }
    }
    config_path = tmp_path / "tomics_multidataset.yaml"
    config_path.write_text("validation: {}\n", encoding="utf-8")

    result = module.run_multidataset_harvest_factorial(
        config,
        repo_root=tmp_path,
        config_path=config_path,
    )
    output_root = Path(result["output_root"])
    selected_payload = json.loads((output_root / "per_dataset_selected_families.json").read_text(encoding="utf-8"))
    skipped_df = pd.read_csv(output_root / "dataset_skip_report.csv")
    scorecard_df = pd.read_csv(output_root / "cross_dataset_scorecard.csv")

    assert result["runnable_measured_dataset_count"] == 2
    assert [row["dataset_id"] for row in selected_payload["datasets"]] == ["knu_actual"]
    assert set(scorecard_df["dataset_ids"]) == {json.dumps(["knu_actual"])}
    school_skip = skipped_df.loc[skipped_df["dataset_id"].eq("school_demo")]
    assert not school_skip.empty
    assert school_skip.iloc[0]["skip_reason"] == "missing_dataset_factorial_root"
