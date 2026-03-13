from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from stomatal_optimiaztion.domains.gosm.examples import render_rerun_parity_suite as render_gosm_rerun_parity_suite  # noqa: E402
from stomatal_optimiaztion.domains.tdgm.examples import render_rerun_parity_suite as render_tdgm_rerun_parity_suite  # noqa: E402
from stomatal_optimiaztion.domains.thorp.examples import render_rerun_parity_bundle as render_thorp_rerun_parity_bundle  # noqa: E402

DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "out" / "rerun_parity"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Render Plotkit-style root rerun parity comparison figures for THORP, GOSM, and TDGM.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Root output directory for the comparison bundles.",
    )
    parser.add_argument(
        "--domains",
        nargs="*",
        default=["thorp", "gosm", "tdgm"],
        choices=("thorp", "gosm", "tdgm"),
        help="Subset of root domains to render.",
    )
    parser.add_argument(
        "--include-slow-gosm-imag",
        action="store_true",
        help="Include the slow GOSM imag conductance-loss rerun parity bundle.",
    )
    parser.add_argument(
        "--tdgm-case",
        action="append",
        default=None,
        help="Optional TDGM THORP-G case filename to render. May be passed multiple times.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    summary: dict[str, object] = {}
    if "thorp" in args.domains:
        summary["thorp"] = render_thorp_rerun_parity_bundle(
            output_dir=output_dir / "thorp" / "control_06rh",
        ).to_summary()
    if "gosm" in args.domains:
        summary["gosm"] = render_gosm_rerun_parity_suite(
            output_dir=output_dir / "gosm",
            include_slow_imag=args.include_slow_gosm_imag,
        ).to_summary()
    if "tdgm" in args.domains:
        summary["tdgm"] = render_tdgm_rerun_parity_suite(
            output_dir=output_dir / "tdgm",
            case_names=args.tdgm_case,
        ).to_summary()

    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
