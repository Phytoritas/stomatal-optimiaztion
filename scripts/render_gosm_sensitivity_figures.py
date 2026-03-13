from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from stomatal_optimiaztion.domains.gosm.examples import (  # noqa: E402
    DEFAULT_COMPARE_TRUE_IMAG_SPEC_PATH,
    DEFAULT_LEGACY_GOSM_EXAMPLE_DIR,
    DEFAULT_SENSITIVITY_ALL_SPEC_PATH,
    DEFAULT_SENSITIVITY_OUTPUT_DIR,
    DEFAULT_SENSITIVITY_SOME_SPEC_PATH,
    render_sensitivity_figure_suite,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Render the root GOSM sensitivity/manuscript figure bundles.")
    parser.add_argument(
        "--legacy-example-dir",
        type=Path,
        default=DEFAULT_LEGACY_GOSM_EXAMPLE_DIR,
        help="Legacy GOSM example directory containing the sensitivity .mat files.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_SENSITIVITY_OUTPUT_DIR,
        help="Directory where the rendered figure bundles will be written.",
    )
    parser.add_argument(
        "--compare-spec",
        type=Path,
        default=DEFAULT_COMPARE_TRUE_IMAG_SPEC_PATH,
        help="Spec path for the true-vs-imag comparison figure.",
    )
    parser.add_argument(
        "--sensitivity-all-spec",
        type=Path,
        default=DEFAULT_SENSITIVITY_ALL_SPEC_PATH,
        help="Spec path for the full sensitivity figure.",
    )
    parser.add_argument(
        "--sensitivity-some-spec",
        type=Path,
        default=DEFAULT_SENSITIVITY_SOME_SPEC_PATH,
        help="Spec path for the steady-state versus AOH figure.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    artifacts = render_sensitivity_figure_suite(
        legacy_example_dir=args.legacy_example_dir,
        output_dir=args.output_dir,
        compare_spec_path=args.compare_spec,
        sensitivity_all_spec_path=args.sensitivity_all_spec,
        sensitivity_some_spec_path=args.sensitivity_some_spec,
    )
    print(json.dumps(artifacts.to_summary(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
