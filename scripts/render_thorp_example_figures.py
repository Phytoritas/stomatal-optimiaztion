from __future__ import annotations

import argparse
import json
from pathlib import Path

from stomatal_optimiaztion.domains.thorp.examples import (
    DEFAULT_LEGACY_THORP_EXAMPLE_DIR,
    render_thorp_example_figure_suite,
)
from stomatal_optimiaztion.domains.thorp.examples.figure_workflows import (
    DEFAULT_ALLOCATION_FRACTION_SPEC_PATH,
    DEFAULT_ECO2_LIGHT_SPEC_PATH,
    DEFAULT_GROUNDWATER_SWEEP_SPEC_PATH,
    DEFAULT_MASS_FRACTION_SPEC_PATH,
    DEFAULT_STRUCTURAL_TRAIT_SPEC_PATH,
    DEFAULT_THORP_EXAMPLE_OUTPUT_DIR,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Render Plotkit-style root THORP example figure bundles.")
    parser.add_argument("--legacy-example-dir", type=Path, default=DEFAULT_LEGACY_THORP_EXAMPLE_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_THORP_EXAMPLE_OUTPUT_DIR)
    parser.add_argument("--mass-fraction-spec", type=Path, default=DEFAULT_MASS_FRACTION_SPEC_PATH)
    parser.add_argument("--allocation-fraction-spec", type=Path, default=DEFAULT_ALLOCATION_FRACTION_SPEC_PATH)
    parser.add_argument("--structural-trait-spec", type=Path, default=DEFAULT_STRUCTURAL_TRAIT_SPEC_PATH)
    parser.add_argument("--groundwater-sweep-spec", type=Path, default=DEFAULT_GROUNDWATER_SWEEP_SPEC_PATH)
    parser.add_argument("--eco2-light-spec", type=Path, default=DEFAULT_ECO2_LIGHT_SPEC_PATH)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    artifacts = render_thorp_example_figure_suite(
        legacy_example_dir=args.legacy_example_dir,
        output_dir=args.output_dir,
        mass_fraction_spec_path=args.mass_fraction_spec,
        allocation_fraction_spec_path=args.allocation_fraction_spec,
        structural_trait_spec_path=args.structural_trait_spec,
        groundwater_sweep_spec_path=args.groundwater_sweep_spec,
        eco2_light_spec_path=args.eco2_light_spec,
    )
    print(json.dumps(artifacts.to_summary(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
