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
    DEFAULT_CONTROL_FIGURE_OUTPUT_DIR,
    DEFAULT_CONTROL_FIGURE_SPEC_PATH,
    render_control_example_figure_bundle,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Render the root GOSM control example figure bundle.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_CONTROL_FIGURE_OUTPUT_DIR,
        help="Directory where the rendered figure bundle will be written.",
    )
    parser.add_argument(
        "--spec",
        type=Path,
        default=DEFAULT_CONTROL_FIGURE_SPEC_PATH,
        help="Plotkit-style YAML spec path.",
    )
    parser.add_argument(
        "--legacy-mat-path",
        type=Path,
        default=None,
        help="Optional legacy MATLAB control payload path for numeric parity comparison.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    artifacts = render_control_example_figure_bundle(
        output_dir=args.output_dir,
        spec_path=args.spec,
        legacy_mat_path=args.legacy_mat_path,
    )
    print(json.dumps(artifacts.to_summary(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
