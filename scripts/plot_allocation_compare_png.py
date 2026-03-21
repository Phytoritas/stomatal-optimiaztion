#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from stomatal_optimiaztion.domains.tomato.tomics.plotting import (  # noqa: E402
    render_allocation_compare_bundle,
)


ALLOC_COLS: tuple[str, ...] = (
    "alloc_frac_fruit",
    "alloc_frac_leaf",
    "alloc_frac_stem",
    "alloc_frac_root",
)
DEFAULT_ALLOCATION_COMPARE_SPEC_PATH = PROJECT_ROOT / "configs" / "plotkit" / "tomics" / "allocation_compare.yaml"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compare allocation fractions between two simulation CSV outputs.")
    parser.add_argument(
        "--baseline",
        default="out/tomics/analysis/partition-compare/example/legacy/df.csv",
        help="Baseline (legacy) simulation CSV.",
    )
    parser.add_argument(
        "--candidate",
        default="out/tomics/analysis/partition-compare/example/tomics/df.csv",
        help="Candidate simulation CSV to compare against baseline.",
    )
    parser.add_argument(
        "--baseline-label",
        default="legacy (sink_based)",
        help="Legend label for baseline.",
    )
    parser.add_argument(
        "--candidate-label",
        default="TOMICS hybrid (tomics, 4pool)",
        help="Legend label for candidate.",
    )
    parser.add_argument(
        "--output",
        default="out/tomics/analysis/partition-compare/example/comparison_plot.png",
        help="Output PNG path.",
    )
    parser.add_argument(
        "--every",
        type=int,
        default=60,
        help="Row stride for plotting (e.g., 60 plots every 60th row).",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=170,
        help="PNG DPI.",
    )
    parser.add_argument(
        "--spec",
        default=str(DEFAULT_ALLOCATION_COMPARE_SPEC_PATH),
        help="Plotkit spec path for the allocation-comparison figure.",
    )
    return parser


def _read_alloc_csv(path: Path, *, suffix: str) -> pd.DataFrame:
    cols = ["datetime", *ALLOC_COLS]
    df = pd.read_csv(path, usecols=cols, parse_dates=["datetime"])
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise KeyError(f"Missing required columns in {path}: {missing}")

    rename_map = {col: f"{col}{suffix}" for col in ALLOC_COLS}
    return df.rename(columns=rename_map).sort_values("datetime").reset_index(drop=True)


def _plot(
    merged: pd.DataFrame,
    *,
    baseline_label: str,
    candidate_label: str,
    out_path: Path,
    dpi: int,
    spec_path: Path,
) -> None:
    render_allocation_compare_bundle(
        merged=merged,
        baseline_label=baseline_label,
        candidate_label=candidate_label,
        out_path=out_path,
        spec_path=spec_path,
    )


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    baseline_path = Path(args.baseline).resolve()
    candidate_path = Path(args.candidate).resolve()
    if not baseline_path.exists():
        raise FileNotFoundError(f"Baseline CSV not found: {baseline_path}")
    if not candidate_path.exists():
        raise FileNotFoundError(f"Candidate CSV not found: {candidate_path}")

    baseline = _read_alloc_csv(baseline_path, suffix="__baseline")
    candidate = _read_alloc_csv(candidate_path, suffix="__candidate")

    merged = pd.merge(baseline, candidate, on="datetime", how="inner")
    if merged.empty:
        raise ValueError("No overlapping datetime rows between baseline and candidate.")

    every = max(int(args.every), 1)
    merged_plot = merged.iloc[::every].copy()

    out_path = Path(args.output).resolve()
    _plot(
        merged_plot,
        baseline_label=str(args.baseline_label),
        candidate_label=str(args.candidate_label),
        out_path=out_path,
        dpi=int(args.dpi),
        spec_path=Path(args.spec).resolve(),
    )
    print(out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
