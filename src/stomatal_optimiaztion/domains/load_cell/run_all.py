"""End-to-end runner for load-cell preprocessing plus workflow or sweep."""

from __future__ import annotations

import argparse
import logging
from collections.abc import Callable, Sequence
from pathlib import Path

from . import sweep
from . import workflow

PreprocessRawFolderFn = Callable[..., object]


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser for the end-to-end runner."""

    parser = argparse.ArgumentParser(
        description="End-to-end: raw ALMEMO -> daily CSVs -> workflow/sweep results.",
    )
    parser.add_argument(
        "--raw-input-dir",
        type=Path,
        default=Path("data/raw"),
        help="Directory containing raw ALMEMO500~*.csv files.",
    )
    parser.add_argument(
        "--pattern",
        type=str,
        default="ALMEMO500~*.csv",
        help="Glob pattern for raw input files.",
    )
    parser.add_argument(
        "--encoding",
        type=str,
        default="latin1",
        help="Encoding for raw ALMEMO files (latin1 is safest).",
    )
    parser.add_argument(
        "--max-files",
        type=int,
        default=None,
        help="Optional cap on number of raw files to preprocess (for testing).",
    )
    parser.add_argument(
        "--skip-preprocess",
        action="store_true",
        help="Skip raw->daily preprocessing step (assume daily CSVs already exist).",
    )
    parser.add_argument(
        "--overwrite-preprocess",
        action="store_true",
        help="Overwrite existing daily CSVs during preprocessing.",
    )
    parser.add_argument(
        "--daily-raw-dir",
        type=Path,
        default=Path("data/preprocessed_csv"),
        help="Output dir for per-day raw CSVs (no 1s interpolation).",
    )
    parser.add_argument(
        "--daily-interpolated-dir",
        type=Path,
        default=Path("data/preprocessed_csv_interpolated"),
        help="Output dir for per-day interpolated CSVs (1s interpolation).",
    )
    parser.add_argument(
        "--out-root",
        type=Path,
        default=Path("runs"),
        help="Output root directory for final results (workflow/sweep).",
    )
    parser.add_argument(
        "--variants",
        choices=["interpolated", "raw", "both"],
        default="both",
        help="Which datasets to process in the workflow stage.",
    )
    parser.add_argument(
        "--loadcells",
        type=int,
        nargs="+",
        default=[1, 2, 3, 4, 5, 6],
        help="Loadcell ids to process.",
    )
    parser.add_argument(
        "--dates",
        nargs="*",
        help="Optional list of daily filenames (YYYY-MM-DD.csv). If omitted, process all matched days.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        action="append",
        default=[],
        help="Config YAML for workflow (repeatable). Default: ./config.yaml",
    )
    parser.add_argument(
        "--excel",
        action="store_true",
        help="Also write Excel outputs (multi-sheet) for each result.",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="WARNING",
        help="Logging level (DEBUG, INFO, WARNING, ...).",
    )
    parser.add_argument(
        "--base-config",
        type=Path,
        default=Path("config.yaml"),
        help="Base config used when running sweep (and default config for workflow).",
    )
    parser.add_argument(
        "--grid",
        action="append",
        default=[],
        help="Grid spec KEY=V1,V2,... (repeatable). If provided, runs sweep instead of workflow.",
    )
    return parser


def _resolve_preprocess_raw_folder(
    preprocess_raw_folder: PreprocessRawFolderFn | None = None,
) -> PreprocessRawFolderFn:
    if preprocess_raw_folder is not None:
        return preprocess_raw_folder

    try:
        from stomatal_optimiaztion.domains.load_cell.almemo_preprocess import (  # type: ignore[attr-defined]
            preprocess_raw_folder as resolved_preprocess_raw_folder,
        )
    except ImportError as exc:
        raise RuntimeError(
            "load-cell raw preprocessing is not available yet. "
            "Pass skip_preprocess=True or inject preprocess_raw_folder."
        ) from exc

    return resolved_preprocess_raw_folder


def run_all(
    *,
    raw_input_dir: Path,
    pattern: str = "ALMEMO500~*.csv",
    encoding: str = "latin1",
    max_files: int | None = None,
    skip_preprocess: bool = False,
    overwrite_preprocess: bool = False,
    daily_raw_dir: Path = Path("data/preprocessed_csv"),
    daily_interpolated_dir: Path = Path("data/preprocessed_csv_interpolated"),
    out_root: Path = Path("runs"),
    variants: str = "both",
    loadcells: Sequence[int] = (1, 2, 3, 4, 5, 6),
    dates: list[str] | None = None,
    config_paths: Sequence[Path] | None = None,
    include_excel: bool = False,
    log_level: str = "WARNING",
    base_config: Path = Path("config.yaml"),
    grid_args: Sequence[str] | None = None,
    preprocess_raw_folder: PreprocessRawFolderFn | None = None,
) -> None:
    """Run raw preprocessing plus workflow or sweep from one entrypoint."""

    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.WARNING),
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    grid_args_list = list(grid_args or [])

    if not skip_preprocess:
        preprocess = _resolve_preprocess_raw_folder(preprocess_raw_folder)
        preprocess(
            raw_input_dir,
            daily_raw_dir,
            pattern=pattern,
            max_files=max_files,
            overwrite=overwrite_preprocess,
            encoding=encoding,
            interpolate_1s=False,
        )
        preprocess(
            raw_input_dir,
            daily_interpolated_dir,
            pattern=pattern,
            max_files=max_files,
            overwrite=overwrite_preprocess,
            encoding=encoding,
            interpolate_1s=True,
        )

    if grid_args_list:
        sweep.run_sweep(
            out_root=out_root,
            interpolated_dir=daily_interpolated_dir,
            raw_dir=daily_raw_dir,
            base_config_path=base_config,
            grid_args=grid_args_list,
            variants=variants,
            loadcells=list(loadcells),
            dates=list(dates) if dates else None,
            include_excel=bool(include_excel),
            log_level=log_level,
        )
        return

    resolved_config_paths = list(config_paths) if config_paths else [base_config]
    workflow.run_workflow(
        interpolated_dir=daily_interpolated_dir,
        raw_dir=daily_raw_dir,
        out_root=out_root,
        config_paths=resolved_config_paths,
        variants=variants,
        loadcells=list(loadcells),
        dates=list(dates) if dates else None,
        include_excel=include_excel,
        log_level=log_level,
    )


def main(
    argv: Sequence[str] | None = None,
    *,
    preprocess_raw_folder: PreprocessRawFolderFn | None = None,
) -> int:
    """Entry point for command-line execution."""

    args = build_parser().parse_args(list(argv) if argv is not None else None)
    run_all(
        raw_input_dir=args.raw_input_dir,
        pattern=args.pattern,
        encoding=args.encoding,
        max_files=args.max_files,
        skip_preprocess=args.skip_preprocess,
        overwrite_preprocess=args.overwrite_preprocess,
        daily_raw_dir=args.daily_raw_dir,
        daily_interpolated_dir=args.daily_interpolated_dir,
        out_root=args.out_root,
        variants=args.variants,
        loadcells=args.loadcells,
        dates=list(args.dates) if args.dates else None,
        config_paths=args.config if args.config else [args.base_config],
        include_excel=args.excel,
        log_level=args.log_level,
        base_config=args.base_config,
        grid_args=args.grid,
        preprocess_raw_folder=preprocess_raw_folder,
    )
    return 0
