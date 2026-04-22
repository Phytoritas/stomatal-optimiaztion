from __future__ import annotations

import argparse
import json
from pathlib import Path

from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.traitenv_school_validation import (
    build_school_traitenv_validation_bundle,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Prepare a private-reviewed school traitenv validation bundle.",
    )
    parser.add_argument(
        "--traitenv-root",
        type=Path,
        default=Path("out/private-data/traitenv"),
        help="Cloned traitenv root that contains the school partition tables.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("out/private-data/tomics_school_traitenv_validation"),
        help="Local output root for generated private forcing/harvest/config artifacts.",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Repository root. Defaults to the current repo.",
    )
    parser.add_argument(
        "--raw-repo-root",
        type=Path,
        default=None,
        help="Optional raw tomato repo root used for workbook fallback metadata recovery.",
    )
    parser.add_argument("--season", default="2024", help="Season label selector.")
    parser.add_argument("--treatment", default="Control", help="Treatment selector.")
    parser.add_argument(
        "--dry-matter-ratio",
        type=float,
        default=0.065,
        help="Literature dry-matter ratio applied to fresh harvest totals.",
    )
    parser.add_argument(
        "--par-umol-per-w-m2",
        type=float,
        default=2.3,
        help="PAR conversion factor for the greenhouse forcing bundle.",
    )
    parser.add_argument(
        "--approve-runnable-contract",
        action="store_true",
        help="Clear the review-only blocker inside the generated private overlay only.",
    )
    parser.add_argument(
        "--current-vs-promoted-base-config",
        type=Path,
        default=Path("configs/exp/tomics_current_vs_promoted_factorial_knu.yaml"),
        help="Base config used to generate the school current-vs-promoted config.",
    )
    parser.add_argument(
        "--harvest-factorial-base-config",
        type=Path,
        default=Path("configs/exp/tomics_knu_harvest_family_factorial.yaml"),
        help="Base config used to generate the school harvest-family config.",
    )
    parser.add_argument(
        "--multidataset-base-config",
        type=Path,
        default=Path("configs/exp/tomics_multidataset_harvest_factorial.yaml"),
        help="Base config used to generate the multidataset factorial config.",
    )
    parser.add_argument(
        "--promotion-gate-base-config",
        type=Path,
        default=Path("configs/exp/tomics_multidataset_harvest_promotion_gate.yaml"),
        help="Base config used to generate the multidataset promotion gate config.",
    )
    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    bundle = build_school_traitenv_validation_bundle(
        traitenv_root=args.traitenv_root,
        output_root=args.output_root,
        repo_root=args.repo_root,
        raw_repo_root=args.raw_repo_root,
        season=args.season,
        treatment=args.treatment,
        dry_matter_ratio=args.dry_matter_ratio,
        par_umol_per_w_m2=args.par_umol_per_w_m2,
        approve_runnable_contract=args.approve_runnable_contract,
        current_vs_promoted_base_config=args.current_vs_promoted_base_config,
        harvest_factorial_base_config=args.harvest_factorial_base_config,
        multidataset_base_config=args.multidataset_base_config,
        promotion_gate_base_config=args.promotion_gate_base_config,
    )
    summary = {
        "forcing_csv_path": str(bundle.forcing_csv_path),
        "yield_csv_path": str(bundle.yield_csv_path),
        "manifest_path": str(bundle.manifest_path),
        "season": bundle.season,
        "treatment": bundle.treatment,
        "validation_start": bundle.validation_start,
        "validation_end": bundle.validation_end,
        "generated_config_paths": {key: str(value) for key, value in bundle.generated_config_paths.items()},
        "approve_runnable_contract": bundle.approve_runnable_contract,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
