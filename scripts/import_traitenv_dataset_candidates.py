from __future__ import annotations

import argparse
from pathlib import Path

from stomatal_optimiaztion.domains.tomato.tomics.alloc.core import ensure_dir, write_json
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.datasets.contracts import DatasetCapability
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.datasets.metadata import (
    build_dataset_blocker_report,
    build_dataset_inventory_summary,
    build_dataset_review_template,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.datasets.traitenv_loader import (
    build_traitenv_candidate_registry,
    load_traitenv_inventory,
)


def run_import_traitenv_dataset_candidates(
    *,
    traitenv_path: str | Path,
    output_root: str | Path,
    reviewed_manifest_dir: str | Path | None = None,
) -> dict[str, object]:
    inventory = load_traitenv_inventory(traitenv_path)
    registry = build_traitenv_candidate_registry(traitenv_path)
    output_dir = ensure_dir(Path(output_root).resolve())

    capability_df = registry.to_frame()
    blocker_df = registry.blocker_frame()
    snapshot_payload = registry.to_payload()
    inventory_summary = {
        **build_dataset_inventory_summary(list(registry.datasets)),
        "traitenv_bundle_path": str(inventory.bundle_path),
        "traitenv_bundle_kind": inventory.bundle_kind,
        "design_workbook_present": inventory.design_workbook_present,
        "run_manifest": inventory.run_manifest,
    }

    capability_df.to_csv(output_dir / "dataset_capability_table.csv", index=False)
    blocker_df.to_csv(output_dir / "dataset_blockers.csv", index=False)
    write_json(output_dir / "dataset_registry_snapshot.json", snapshot_payload)
    write_json(output_dir / "traitenv_inventory_summary.json", inventory_summary)
    (output_dir / "dataset_blocker_report.md").write_text(
        build_dataset_blocker_report(list(registry.datasets)),
        encoding="utf-8",
    )

    if reviewed_manifest_dir is not None:
        reviewed_dir = ensure_dir(Path(reviewed_manifest_dir).resolve())
        write_json(reviewed_dir / "traitenv_candidate_registry.json", snapshot_payload)
        review_template_dir = ensure_dir(reviewed_dir / "review_templates")
        review_template_index: list[dict[str, str]] = []
        for dataset in registry.datasets:
            if dataset.capability is DatasetCapability.CONTEXT_ONLY or dataset.is_runnable_measured_harvest:
                continue
            template_filename = f"{dataset.dataset_id}.review.json"
            write_json(
                review_template_dir / template_filename,
                build_dataset_review_template(dataset),
            )
            review_template_index.append(
                {
                    "dataset_id": dataset.dataset_id,
                    "capability": dataset.capability.value,
                    "ingestion_status": dataset.ingestion_status.value,
                    "path": f"review_templates/{template_filename}",
                }
            )
        write_json(reviewed_dir / "review_template_index.json", {"templates": review_template_index})

    preview_columns = [
        "dataset_id",
        "dataset_family",
        "observation_family",
        "capability",
        "ingestion_status",
        "is_runnable_measured_harvest",
        "blocker_codes",
    ]
    preview_df = capability_df.loc[:, [column for column in preview_columns if column in capability_df.columns]]
    if not preview_df.empty:
        print(preview_df.to_string(index=False))
    else:
        print("No traitenv dataset candidates were derived.")

    return {
        "output_root": str(output_dir),
        "candidate_dataset_count": len(registry.datasets),
        "runnable_measured_dataset_count": len(registry.runnable_measured_harvest_datasets()),
        "review_template_count": (
            0
            if reviewed_manifest_dir is None
            else sum(
                1
                for dataset in registry.datasets
                if dataset.capability is not DatasetCapability.CONTEXT_ONLY and not dataset.is_runnable_measured_harvest
            )
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import conservative TOMICS multi-dataset candidates from a traitenv inventory bundle."
    )
    parser.add_argument(
        "--traitenv-path",
        "--traitenv-root",
        dest="traitenv_path",
        required=True,
        help="Path to the traitenv inventory directory or traitenv.zip bundle.",
    )
    parser.add_argument(
        "--output-root",
        default="out/tomics/validation/multidataset",
        help="Directory for candidate capability/blocker artifacts.",
    )
    parser.add_argument(
        "--reviewed-manifest-dir",
        default=None,
        help="Optional directory where a reviewable candidate registry snapshot JSON will be written.",
    )
    args = parser.parse_args()

    result = run_import_traitenv_dataset_candidates(
        traitenv_path=args.traitenv_path,
        output_root=args.output_root,
        reviewed_manifest_dir=args.reviewed_manifest_dir,
    )
    print(result["output_root"])


if __name__ == "__main__":
    main()
