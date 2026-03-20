#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


ALLOC_COLS: tuple[str, ...] = (
    "alloc_frac_fruit",
    "alloc_frac_leaf",
    "alloc_frac_stem",
    "alloc_frac_root",
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compare allocation fractions between two simulation CSV outputs.")
    parser.add_argument(
        "--baseline",
        default="out/tomics_partition_compare/example/legacy/df.csv",
        help="Baseline (legacy) simulation CSV.",
    )
    parser.add_argument(
        "--candidate",
        default="out/tomics_partition_compare/example/tomics/df.csv",
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
        default="out/tomics_partition_compare/example/comparison_plot.png",
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
) -> None:
    try:
        import matplotlib.dates as mdates
        import matplotlib.pyplot as plt
    except ModuleNotFoundError as exc:  # pragma: no cover
        raise ModuleNotFoundError(
            "Plotting requires matplotlib. Install with: python -m pip install matplotlib"
        ) from exc

    x = merged["datetime"]

    fig, axes = plt.subplots(nrows=4, ncols=1, sharex=True, figsize=(14, 10), constrained_layout=True)
    mapping = (
        ("fruit", "alloc_frac_fruit"),
        ("leaf", "alloc_frac_leaf"),
        ("stem", "alloc_frac_stem"),
        ("root", "alloc_frac_root"),
    )

    for ax, (name, col) in zip(axes, mapping, strict=True):
        base = pd.to_numeric(merged[f"{col}__baseline"], errors="coerce")
        cand = pd.to_numeric(merged[f"{col}__candidate"], errors="coerce")

        ax.plot(x, base, label=baseline_label, color="black", linewidth=0.9, alpha=0.85)
        ax.plot(x, cand, label=candidate_label, color="tab:blue", linewidth=0.9, alpha=0.85)
        ax.set_ylabel(f"{name} (-)")
        ax.set_ylim(-0.05, 1.05)
        ax.grid(True, alpha=0.25)
        if ax is axes[0]:
            ax.legend(loc="upper left", fontsize=9)

    locator = mdates.AutoDateLocator(minticks=4, maxticks=10)
    axes[-1].xaxis.set_major_locator(locator)
    axes[-1].xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))
    axes[-1].set_xlabel("datetime")

    axes[0].set_title("Allocation Fractions Comparison")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=int(dpi), bbox_inches="tight")
    plt.close(fig)


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
    )
    print(out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
