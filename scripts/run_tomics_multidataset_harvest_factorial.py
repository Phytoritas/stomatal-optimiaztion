from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.alloc.core import ensure_dir, load_config, write_json
from stomatal_optimiaztion.domains.tomato.tomics.alloc.pipelines import resolve_repo_root
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.cross_dataset_scorecard import (
    build_cross_dataset_inventory_scorecard,
    build_cross_dataset_scorecard,
    load_dataset_factorial_outputs,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.datasets.metadata import (
    build_dataset_blocker_report,
    intake_priority_rows,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.datasets.registry import (
    load_dataset_registry,
)


def _as_dict(raw: object) -> dict[str, Any]:
    if isinstance(raw, dict):
        return {str(key): value for key, value in raw.items()}
    return {}


def _resolve_artifact_path(raw: str | Path, *, repo_root: Path) -> Path:
    candidate = Path(raw)
    if candidate.is_absolute():
        return candidate
    return (repo_root / candidate).resolve()


def _factorial_root_for_dataset(
    *,
    dataset_id: str,
    dataset_roots: dict[str, Any],
    repo_root: Path,
) -> Path | None:
    if dataset_id in dataset_roots:
        return _resolve_artifact_path(str(dataset_roots[dataset_id]), repo_root=repo_root)
    if dataset_id == "knu_actual":
        return _resolve_artifact_path("out/tomics_knu_harvest_family_factorial", repo_root=repo_root)
    return None


def run_multidataset_harvest_factorial(
    config: dict[str, Any],
    *,
    repo_root: Path,
    config_path: Path,
) -> dict[str, object]:
    registry = load_dataset_registry(config, repo_root=repo_root, config_path=config_path)
    factorial_cfg = _as_dict(_as_dict(config.get("validation")).get("multidataset_factorial"))
    output_root = ensure_dir(
        _resolve_artifact_path(
            factorial_cfg.get("output_root", "out/tomics/validation/multidataset"),
            repo_root=repo_root,
        )
    )
    dataset_roots = _as_dict(factorial_cfg.get("dataset_factorial_roots"))
    rankings: list[pd.DataFrame] = []
    selected_payloads: list[dict[str, Any]] = []
    skipped_rows: list[dict[str, Any]] = []

    for dataset in registry.datasets:
        if not dataset.is_runnable_measured_harvest:
            skipped_rows.append(
                {
                    "dataset_id": dataset.dataset_id,
                    "capability": dataset.capability.value,
                    "ingestion_status": dataset.ingestion_status.value,
                    "skip_reason": "not_runnable_measured_harvest",
                    "blocker_codes": ",".join(dataset.blocker_codes),
                }
            )
            continue
        factorial_root = _factorial_root_for_dataset(
            dataset_id=dataset.dataset_id,
            dataset_roots=dataset_roots,
            repo_root=repo_root,
        )
        if factorial_root is None:
            skipped_rows.append(
                {
                    "dataset_id": dataset.dataset_id,
                    "capability": dataset.capability.value,
                    "ingestion_status": dataset.ingestion_status.value,
                    "skip_reason": "missing_dataset_factorial_root",
                    "blocker_codes": ",".join(dataset.blocker_codes),
                }
            )
            continue
        ranking_path = factorial_root / "candidate_ranking.csv"
        selected_path = factorial_root / "selected_harvest_family.json"
        if not ranking_path.exists() or not selected_path.exists():
            skipped_rows.append(
                {
                    "dataset_id": dataset.dataset_id,
                    "capability": dataset.capability.value,
                    "ingestion_status": dataset.ingestion_status.value,
                    "skip_reason": "missing_factorial_artifacts",
                    "blocker_codes": ",".join(dataset.blocker_codes),
                }
            )
            continue
        ranking_df, selected_payload = load_dataset_factorial_outputs(
            dataset_id=dataset.dataset_id,
            factorial_root=factorial_root,
        )
        rankings.append(ranking_df)
        selected_payloads.append(selected_payload)

    scorecard_df = build_cross_dataset_scorecard(rankings, selected_payloads, registry=registry)
    inventory_scorecard = build_cross_dataset_inventory_scorecard(
        registry,
        scorecard_df=scorecard_df,
        skipped_datasets=skipped_rows,
    )
    registry_df = registry.to_frame()
    blocker_df = registry.blocker_frame()
    skipped_df = pd.DataFrame.from_records(
        skipped_rows,
        columns=["dataset_id", "capability", "ingestion_status", "skip_reason", "blocker_codes"],
    )

    registry_df.to_csv(output_root / "dataset_capability_table.csv", index=False)
    blocker_df.to_csv(output_root / "dataset_blockers.csv", index=False)
    skipped_df.to_csv(output_root / "dataset_skip_report.csv", index=False)
    scorecard_df.to_csv(output_root / "cross_dataset_scorecard.csv", index=False)
    write_json(output_root / "dataset_registry_snapshot.json", registry.to_payload())
    write_json(output_root / "cross_dataset_scorecard.json", inventory_scorecard)
    write_json(output_root / "per_dataset_selected_families.json", {"datasets": selected_payloads})
    write_json(output_root / "intake_priority.json", {"datasets": intake_priority_rows(list(registry.datasets))})
    (output_root / "dataset_blocker_report.md").write_text(
        build_dataset_blocker_report(list(registry.datasets)),
        encoding="utf-8",
    )
    write_json(
        output_root / "dataset_metadata_summary.json",
        {
            "datasets": [
                {
                    "dataset_id": dataset.dataset_id,
                    "display_name": dataset.display_name,
                    "capability": dataset.capability.value,
                    "ingestion_status": dataset.ingestion_status.value,
                    "priority_tags": list(dataset.priority_tags),
                    "notes": dataset.notes,
                }
                for dataset in registry.datasets
            ]
        },
    )
    return {
        "output_root": str(output_root),
        "total_registry_datasets": len(registry.datasets),
        "runnable_measured_dataset_count": len(registry.runnable_measured_harvest_datasets()),
        "scorecard_rows": int(scorecard_df.shape[0]),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a TOMICS multi-dataset harvest scorecard scaffold.")
    parser.add_argument("--config", required=True, help="Path to multi-dataset harvest YAML config.")
    args = parser.parse_args()

    config_path = Path(args.config).resolve()
    config = load_config(config_path)
    repo_root = resolve_repo_root(config, config_path=config_path)
    result = run_multidataset_harvest_factorial(config, repo_root=repo_root, config_path=config_path)
    print(result["output_root"])


if __name__ == "__main__":
    main()
