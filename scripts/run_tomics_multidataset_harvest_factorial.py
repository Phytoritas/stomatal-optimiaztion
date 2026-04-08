from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from stomatal_optimiaztion.domains.tomato.tomics.alloc.core import ensure_dir, load_config, write_json
from stomatal_optimiaztion.domains.tomato.tomics.alloc.pipelines import resolve_repo_root
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.cross_dataset_scorecard import (
    build_cross_dataset_scorecard,
    load_dataset_factorial_outputs,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.datasets.metadata import (
    intake_priority_rows,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.datasets.registry import (
    load_dataset_registry,
)


def _as_dict(raw: object) -> dict[str, Any]:
    if isinstance(raw, dict):
        return {str(key): value for key, value in raw.items()}
    return {}


def _resolve_config_path(raw: str | Path, *, repo_root: Path, config_path: Path) -> Path:
    candidate = Path(raw)
    if candidate.is_absolute():
        return candidate
    config_probe = (config_path.parent / candidate).resolve()
    repo_probe = (repo_root / candidate).resolve()
    probes = [config_probe, repo_probe]
    for probe in probes:
        if probe.exists():
            return probe
    return repo_probe


def _resolve_artifact_path(raw: str | Path, *, repo_root: Path) -> Path:
    candidate = Path(raw)
    if candidate.is_absolute():
        return candidate
    return (repo_root / candidate).resolve()


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
            factorial_cfg.get("output_root", "out/tomics_multidataset_harvest_factorial"),
            repo_root=repo_root,
        )
    )
    dataset_roots = _as_dict(factorial_cfg.get("dataset_factorial_roots"))
    rankings = []
    selected_payloads = []
    for dataset in registry.datasets:
        factorial_root_raw = dataset_roots.get(dataset.dataset_id, "out/tomics_knu_harvest_family_factorial")
        ranking_df, selected_payload = load_dataset_factorial_outputs(
            dataset_id=dataset.dataset_id,
            factorial_root=_resolve_artifact_path(str(factorial_root_raw), repo_root=repo_root),
        )
        rankings.append(ranking_df)
        selected_payloads.append(selected_payload)
    scorecard_df = build_cross_dataset_scorecard(rankings, selected_payloads)
    registry_df = registry.to_frame()
    registry_df.to_csv(output_root / "dataset_registry.csv", index=False)
    scorecard_df.to_csv(output_root / "cross_dataset_scorecard.csv", index=False)
    write_json(output_root / "dataset_registry.json", registry.to_payload())
    write_json(output_root / "per_dataset_selected_families.json", {"datasets": selected_payloads})
    write_json(output_root / "intake_priority.json", {"datasets": intake_priority_rows(list(registry.datasets))})
    write_json(
        output_root / "dataset_metadata_summary.json",
        {
            "datasets": [
                {
                    "dataset_id": dataset.dataset_id,
                    "display_name": dataset.display_name,
                    "priority_tags": list(dataset.priority_tags),
                    "notes": dataset.notes,
                }
                for dataset in registry.datasets
            ]
        },
    )
    return {
        "output_root": str(output_root),
        "dataset_count": len(registry.datasets),
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
