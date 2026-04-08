from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.datasets.contracts import (
    DatasetCapability,
    DatasetIngestionStatus,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.datasets.metadata import (
    build_dataset_review_template,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.datasets.traitenv_loader import (
    build_traitenv_candidate_registry,
    load_traitenv_inventory,
)


def _write_traitenv_fixture(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [
            {
                "source_group": "school_traits",
                "source_kind": "school",
                "dataset_family": "school_trait_bundle",
                "observation_family": "yield",
                "relative_path": "school/yield.xlsx",
            },
            {
                "source_group": "public_data",
                "source_kind": "public",
                "dataset_family": "public_bigdata_platform",
                "observation_family": "yield_environment",
                "relative_path": "public/yield_env.csv",
            },
            {
                "source_group": "school_environment",
                "source_kind": "school",
                "dataset_family": "school_greenhouse_environment",
                "observation_family": "environment",
                "relative_path": "school/env.csv",
            },
        ]
    ).to_csv(root / "source_inventory.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(
        [
            {"source_group": "school_traits", "dataset_family": "school_trait_bundle", "observation_family": "yield", "n_files": 1},
            {"source_group": "public_data", "dataset_family": "public_bigdata_platform", "observation_family": "yield_environment", "n_files": 1},
            {"source_group": "school_environment", "dataset_family": "school_greenhouse_environment", "observation_family": "environment", "n_files": 1},
        ]
    ).to_csv(root / "source_summary.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(
        [
            {"standard_name": "observation_date", "domain": "identifier", "unit_std": "date", "grain_hint": "all", "raw_aliases": "DATE", "notes": ""},
            {"standard_name": "total_yield_weight_g", "domain": "yield", "unit_std": "g", "grain_hint": "line_or_truss_day", "raw_aliases": "fruit_weight_g + fallen_fruit_weight_g", "notes": ""},
        ]
    ).to_csv(root / "variable_dictionary.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(
        [
            {"rule_id": "school_total_yield_weight", "scope": "school_yield", "target_field": "total_yield_weight_g", "priority": 1, "expression": "fruit_weight_g + fallen_fruit_weight_g", "notes": ""},
        ]
    ).to_csv(root / "comparison_rules.csv", index=False, encoding="utf-8-sig")
    (root / "integration_contract.json").write_text(
        json.dumps({"fact_tables": [{"name": "comparison_daily"}]}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (root / "run_manifest.json").write_text(
        json.dumps({"n_files": 3, "n_dataset_families": 3}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    pd.DataFrame(
        [{"slice_type": "season_domain", "slice_key": "2025__yield", "season_key": "2025", "domain_key": "yield", "path": "workbooks/2025/yield.xlsx", "observation_rows": 10, "measurement_rows": 10, "comparison_rows": 10}]
    ).to_csv(root / "workbook_index.csv", index=False, encoding="utf-8-sig")
    (root / "traitenv_design_workbook.xlsx").write_bytes(b"placeholder-workbook")
    pd.DataFrame(
        [
            {"comparison_date": "2025-01-01", "dataset_family": "school_trait_bundle", "observation_family": "yield", "season_label": "2025", "treatment": "Control", "comparison_entity": "A", "standard_name": "total_yield_weight_g", "aggregation_stat": "sum", "n_values": 1, "value_mean": 10.0, "value_min": 10.0, "value_max": 10.0, "value_sum": 10.0},
            {"comparison_date": "2025-01-02", "dataset_family": "public_bigdata_platform", "observation_family": "yield_environment", "season_label": "2025", "treatment": "", "comparison_entity": "site-1", "standard_name": "fruit_weight_g", "aggregation_stat": "mean", "n_values": 1, "value_mean": 5.0, "value_min": 5.0, "value_max": 5.0, "value_sum": 5.0},
        ]
    ).to_csv(root / "comparison_daily.csv", index=False, encoding="utf-8-sig")


def test_traitenv_loader_classifies_candidates_conservatively(tmp_path: Path) -> None:
    traitenv_root = tmp_path / "traitenv"
    _write_traitenv_fixture(traitenv_root)

    inventory = load_traitenv_inventory(traitenv_root)
    registry = build_traitenv_candidate_registry(inventory)

    measured = registry.require("school_trait_bundle__yield")
    proxy = registry.require("public_bigdata_platform__yield_environment")
    context = registry.require("school_greenhouse_environment__environment")

    assert measured.capability is DatasetCapability.MEASURED_HARVEST
    assert measured.ingestion_status is DatasetIngestionStatus.DRAFT_NEEDS_RAW_FIXTURE
    assert measured.observation.date_column is None
    assert measured.observation.daily_increment_column is None
    assert measured.notes["candidate_date_key"] == "observation_date"
    assert measured.notes["candidate_harvest_column"] == "total_yield_weight_g"
    assert "missing_date_column" in measured.blocker_codes
    assert "missing_measured_cumulative_column" in measured.blocker_codes
    assert measured.notes["candidate_harvest_includes_fallen_fruit"] is True
    assert proxy.capability is DatasetCapability.HARVEST_PROXY
    assert proxy.observation.measured_cumulative_column is None
    assert proxy.observation.daily_increment_column is None
    assert proxy.notes["candidate_harvest_column"] is None
    assert proxy.notes["candidate_harvest_requires_cumulative_construction"] is False
    assert context.capability is DatasetCapability.CONTEXT_ONLY
    assert registry.default_dataset_ids == ()


def test_traitenv_review_template_exposes_missing_measured_harvest_fields(tmp_path: Path) -> None:
    traitenv_root = tmp_path / "traitenv"
    _write_traitenv_fixture(traitenv_root)

    registry = build_traitenv_candidate_registry(traitenv_root)
    measured = registry.require("school_trait_bundle__yield")
    template = build_dataset_review_template(measured)

    assert template["dataset_id"] == "school_trait_bundle__yield"
    assert "missing_measured_cumulative_column" in template["blocker_codes"]
    assert template["candidate_schema_hints"]["candidate_harvest_column"] == "total_yield_weight_g"
    assert template["candidate_schema_hints"]["candidate_date_key"] == "observation_date"
    assert template["review_updates"]["observation"]["date_column"] is None
    assert template["review_updates"]["observation"]["measured_cumulative_column"] is None
    assert template["promotion_ready_checklist"]["sanitized_fixture_pair"] is False


def test_import_traitenv_dataset_candidates_script_smoke(tmp_path: Path) -> None:
    traitenv_root = tmp_path / "traitenv"
    output_root = tmp_path / "out"
    reviewed_dir = tmp_path / "reviewed"
    _write_traitenv_fixture(traitenv_root)

    result = subprocess.run(
            [
                sys.executable,
                "scripts/import_traitenv_dataset_candidates.py",
                "--traitenv-root",
                str(traitenv_root),
                "--output-root",
                str(output_root),
                "--reviewed-manifest-dir",
                str(reviewed_dir),
            ],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert (output_root / "dataset_capability_table.csv").exists()
    assert (output_root / "dataset_blockers.csv").exists()
    assert (output_root / "dataset_blocker_report.md").exists()
    assert (output_root / "dataset_registry_snapshot.json").exists()
    assert (reviewed_dir / "traitenv_candidate_registry.json").exists()
    assert (reviewed_dir / "review_template_index.json").exists()
    assert (reviewed_dir / "review_templates" / "school_trait_bundle__yield.review.json").exists()
