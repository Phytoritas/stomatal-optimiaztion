#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from stomatal_optimiaztion.domains.load_cell import (  # noqa: E402
    CANONICAL_COLUMNS,
    merge_duplicate_timestamps,
    read_almemo_raw_csv,
    resample_and_interpolate_1s,
    standardize_almemo_columns,
)

DATE_RE = r"^\d{4}-\d{2}-\d{2}$"
LC_COLS = [f"loadcell_{idx}_kg" for idx in range(1, 7)]


@dataclass(frozen=True)
class PreprocessConfig:
    repo_root: Path
    raw_dir: Path
    raw_pattern: str
    canonical_dir: Path
    transpiration_1m_dir: Path
    marker_dir: Path
    viewer_dir: Path | None
    plants_per_loadcell: int = 3
    encoding: str = "latin1"
    overwrite: bool = False
    max_files: int | None = None

    def __post_init__(self) -> None:
        repo_root = Path(self.repo_root).resolve()
        object.__setattr__(self, "repo_root", repo_root)
        for field_name in (
            "raw_dir",
            "canonical_dir",
            "transpiration_1m_dir",
            "marker_dir",
        ):
            path = Path(getattr(self, field_name))
            object.__setattr__(self, field_name, path if path.is_absolute() else repo_root / path)
        if self.viewer_dir is not None:
            viewer_dir = Path(self.viewer_dir)
            object.__setattr__(
                self,
                "viewer_dir",
                viewer_dir if viewer_dir.is_absolute() else repo_root / viewer_dir,
            )


@dataclass(frozen=True)
class PreprocessResult:
    raw_total: int
    raw_skipped: int
    raw_processed: int
    raw_failed: int
    updated_dates: list[str]


def _now_utc_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _sha1_12(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]


def _safe_relpath(repo_root: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(repo_root.resolve()).as_posix())
    except Exception:
        return str(path.resolve().as_posix())


def _load_done_markers(marker_dir: Path) -> dict[str, set[tuple[int, int]]]:
    markers: dict[str, set[tuple[int, int]]] = {}
    if not marker_dir.exists():
        return markers

    for path in marker_dir.glob("*.json"):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if str(payload.get("status", "")).strip() != "done":
            continue

        input_path = str(payload.get("input", "")).strip()
        source = payload.get("source", {}) or {}
        if not input_path:
            continue
        try:
            size = int(source.get("size"))
            mtime_ns = int(source.get("mtime_ns"))
        except Exception:
            continue
        markers.setdefault(input_path, set()).add((size, mtime_ns))

    return markers


def _write_marker(
    *,
    marker_dir: Path,
    input_rel: str,
    size: int,
    mtime_ns: int,
    status: str,
    run: dict[str, Any],
    result: dict[str, Any],
) -> Path:
    marker_dir.mkdir(parents=True, exist_ok=True)
    tag = _sha1_12(f"{input_rel}|{size}|{mtime_ns}|{run.get('version', 'v1')}")
    out_path = marker_dir / f"{Path(input_rel).stem}__{tag}.json"
    payload = {
        "status": status,
        "input": input_rel,
        "source": {"size": int(size), "mtime_ns": int(mtime_ns)},
        "run": run,
        "result": result,
        "created_at_utc": _now_utc_iso(),
    }
    out_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return out_path


def _upsert_canonical_day(
    *,
    date: str,
    new_day_df_1s: pd.DataFrame,
    canonical_dir: Path,
    overwrite: bool,
    log: Callable[[str], None],
) -> pd.DataFrame:
    if not pd.Series([date]).str.match(DATE_RE).item():
        raise ValueError(f"Invalid date: {date}")

    canonical_dir.mkdir(parents=True, exist_ok=True)
    out_path = canonical_dir / f"{date}_canonical_1s.parquet"

    new_df = new_day_df_1s.copy()
    new_df.index = pd.DatetimeIndex(new_df.index, name="timestamp")
    new_df = new_df[CANONICAL_COLUMNS].astype("float64")

    if out_path.exists() and not overwrite:
        try:
            old = pd.read_parquet(out_path)
            if not old.empty and "timestamp" in old.columns:
                old = old.copy()
                old["timestamp"] = pd.to_datetime(old["timestamp"])
                old = old.set_index("timestamp", drop=True)
                for column in CANONICAL_COLUMNS:
                    if column not in old.columns:
                        old[column] = np.nan
                old = old[CANONICAL_COLUMNS].astype("float64")
                combined = pd.concat([old, new_df], axis=0)
                combined = combined[~combined.index.duplicated(keep="last")].sort_index()
            else:
                combined = new_df
        except Exception as exc:
            log(f"[warn] failed to read existing canonical for merge ({out_path.name}): {exc}")
            combined = new_df
    else:
        combined = new_df

    if combined.empty:
        raise ValueError(f"Empty combined canonical for {date}")

    full_index = pd.date_range(
        start=combined.index.min(),
        end=combined.index.max(),
        freq="1s",
        name="timestamp",
    )
    combined = combined.reindex(full_index).interpolate(method="time", limit_direction="both")
    combined.reset_index().to_parquet(
        out_path,
        index=False,
        engine="pyarrow",
        compression="snappy",
    )
    log(f"[ok] wrote canonical: {out_path}")
    return combined


def _write_transpiration_1m_diff60(
    *,
    date: str,
    canonical_1s: pd.DataFrame,
    transpiration_1m_dir: Path,
    plants_per_loadcell: int,
    log: Callable[[str], None],
) -> Path:
    if plants_per_loadcell < 1:
        raise ValueError("plants_per_loadcell must be >= 1")

    transpiration_1m_dir.mkdir(parents=True, exist_ok=True)
    out_path = (
        transpiration_1m_dir
        / f"{date}__transpiration_1m__diff60__g_min_per_plant__p{int(plants_per_loadcell)}.parquet"
    )

    df = canonical_1s.copy()
    for column in LC_COLS:
        if column not in df.columns:
            df[column] = np.nan
    df = df[LC_COLS].astype("float64")

    weights_1m = df.resample("1min", label="right", closed="right").last()
    delta_kg = weights_1m.diff()
    transp_g_min_per_plant = (
        (-delta_kg).clip(lower=0.0).fillna(0.0) * 1000.0 / float(plants_per_loadcell)
    )

    out = pd.DataFrame(index=transp_g_min_per_plant.index)
    for idx in range(1, 7):
        out[f"loadcell_{idx}_transpiration_g_min_per_plant"] = transp_g_min_per_plant[
            f"loadcell_{idx}_kg"
        ]
    transp_g_min_total = transp_g_min_per_plant * float(plants_per_loadcell)
    out["total_transpiration_g_min"] = transp_g_min_total.sum(axis=1)
    out["avg_transpiration_g_min_per_plant"] = (
        out["total_transpiration_g_min"] / float(plants_per_loadcell * 6)
    )
    out.reset_index().to_parquet(
        out_path,
        index=False,
        engine="pyarrow",
        compression="snappy",
    )
    log(f"[ok] wrote transpiration_1m: {out_path}")
    return out_path


def _viewer_write_day_json(
    *,
    viewer_data_dir: Path,
    date: str,
    canonical_path: Path,
    transpiration_1m_path: Path | None,
    plants_per_loadcell: int,
    log: Callable[[str], None],
) -> None:
    df = pd.read_parquet(canonical_path, columns=["timestamp", *LC_COLS])
    if df.empty:
        raise ValueError(f"Empty canonical file: {canonical_path}")

    t0_iso = pd.Timestamp(df["timestamp"].iloc[0]).to_pydatetime().strftime("%Y-%m-%dT%H:%M:%S")
    weights_dg = np.rint(
        np.nan_to_num(df[LC_COLS].to_numpy(dtype=np.float64), nan=0.0) * 10000.0
    ).astype(np.int32)
    payload: dict[str, Any] = {
        "date": date,
        "plants_per_loadcell": int(plants_per_loadcell),
        "t0_1s": t0_iso,
        "n_1s": int(len(df)),
        "weights_dg": [weights_dg[:, idx].tolist() for idx in range(6)],
        "transp1m_mg_min_per_plant": None,
    }

    if transpiration_1m_path is not None and transpiration_1m_path.exists():
        tdf = pd.read_parquet(transpiration_1m_path)
        if not tdf.empty:
            columns = [f"loadcell_{idx}_transpiration_g_min_per_plant" for idx in range(1, 7)]
            missing = [column for column in columns if column not in tdf.columns]
            if missing:
                raise KeyError(f"Missing columns in {transpiration_1m_path}: {missing}")
            transp_mg = np.rint(
                np.nan_to_num(tdf[columns].to_numpy(dtype=np.float64), nan=0.0) * 1000.0
            ).astype(np.int32)
            payload["transp1m_mg_min_per_plant"] = {
                "t0_1m": pd.Timestamp(tdf["timestamp"].iloc[0])
                .to_pydatetime()
                .strftime("%Y-%m-%dT%H:%M:%S"),
                "n": int(len(tdf)),
                "dt_sec": 60,
                "values": [transp_mg[:, idx].tolist() for idx in range(6)],
            }

    out_path = viewer_data_dir / f"{date}.json"
    out_path.write_text(
        json.dumps(payload, ensure_ascii=True, separators=(",", ":")),
        encoding="utf-8",
    )
    log(f"[ok] wrote viewer day json: {out_path}")


def _viewer_refresh_dates_json(viewer_data_dir: Path) -> list[str]:
    dates = sorted(
        path.stem
        for path in viewer_data_dir.glob("*.json")
        if path.name != "dates.json" and pd.Series([path.stem]).str.match(DATE_RE).item()
    )
    (viewer_data_dir / "dates.json").write_text(
        json.dumps(dates, ensure_ascii=True),
        encoding="utf-8",
    )
    return dates


def run_incremental_preprocess(
    cfg: PreprocessConfig,
    *,
    log: Callable[[str], None],
    should_cancel: Callable[[], bool] | None = None,
) -> PreprocessResult:
    if cfg.plants_per_loadcell < 1:
        raise ValueError("plants_per_loadcell must be >= 1")

    if not cfg.raw_dir.exists():
        raise FileNotFoundError(f"raw_dir not found: {cfg.raw_dir}")

    done_markers = _load_done_markers(cfg.marker_dir)
    raw_files = sorted(cfg.raw_dir.glob(cfg.raw_pattern))
    if cfg.max_files is not None:
        raw_files = raw_files[: int(cfg.max_files)]

    updated_dates: set[str] = set()
    skipped = 0
    processed = 0
    failed = 0

    log(f"[info] raw scan: dir={cfg.raw_dir} pattern={cfg.raw_pattern} files={len(raw_files)}")

    for idx, path in enumerate(raw_files, start=1):
        if should_cancel and should_cancel():
            log("[warn] canceled by user.")
            break

        stat = path.stat()
        size = int(stat.st_size)
        mtime_ns = int(getattr(stat, "st_mtime_ns", int(stat.st_mtime * 1e9)))
        input_rel = _safe_relpath(cfg.repo_root, path)
        if input_rel in done_markers and (size, mtime_ns) in done_markers[input_rel]:
            skipped += 1
            continue

        log(f"[info] processing raw ({idx}/{len(raw_files)}): {input_rel}")
        run_payload = {
            "version": "incremental_v1",
            "encoding": cfg.encoding,
            "raw_pattern": cfg.raw_pattern,
            "split_by_date": True,
            "interpolate_1s": True,
            "plants_per_loadcell": int(cfg.plants_per_loadcell),
            "canonical_dir": _safe_relpath(cfg.repo_root, cfg.canonical_dir),
            "transpiration_1m_dir": _safe_relpath(cfg.repo_root, cfg.transpiration_1m_dir),
        }
        try:
            df_raw = read_almemo_raw_csv(path, encoding=cfg.encoding)
            if df_raw.empty:
                _write_marker(
                    marker_dir=cfg.marker_dir,
                    input_rel=input_rel,
                    size=size,
                    mtime_ns=mtime_ns,
                    status="done",
                    run=run_payload,
                    result={"note": "empty raw file"},
                )
                processed += 1
                continue

            df_std = merge_duplicate_timestamps(standardize_almemo_columns(df_raw))
            if df_std.empty:
                raise ValueError("standardized frame empty")

            for day_ts, group in df_std.groupby(df_std.index.normalize()):
                if should_cancel and should_cancel():
                    break
                date = pd.Timestamp(day_ts).date().isoformat()
                day_1s = resample_and_interpolate_1s(merge_duplicate_timestamps(group.sort_index()))
                canonical_1s = _upsert_canonical_day(
                    date=date,
                    new_day_df_1s=day_1s,
                    canonical_dir=cfg.canonical_dir,
                    overwrite=cfg.overwrite,
                    log=log,
                )
                _write_transpiration_1m_diff60(
                    date=date,
                    canonical_1s=canonical_1s,
                    transpiration_1m_dir=cfg.transpiration_1m_dir,
                    plants_per_loadcell=cfg.plants_per_loadcell,
                    log=log,
                )
                updated_dates.add(date)

            _write_marker(
                marker_dir=cfg.marker_dir,
                input_rel=input_rel,
                size=size,
                mtime_ns=mtime_ns,
                status="done",
                run=run_payload,
                result={"updated_dates": sorted(updated_dates)},
            )
            processed += 1
        except Exception as exc:
            failed += 1
            log(f"[error] failed processing {input_rel}: {exc}")
            _write_marker(
                marker_dir=cfg.marker_dir,
                input_rel=input_rel,
                size=size,
                mtime_ns=mtime_ns,
                status="error",
                run=run_payload,
                result={"error": str(exc)},
            )

    if cfg.viewer_dir is not None and updated_dates:
        viewer_data_dir = cfg.viewer_dir / "data"
        viewer_data_dir.mkdir(parents=True, exist_ok=True)
        log(f"[info] updating viewer cache for {len(updated_dates)} date(s) under: {viewer_data_dir}")
        for date in sorted(updated_dates):
            canonical_path = cfg.canonical_dir / f"{date}_canonical_1s.parquet"
            if not canonical_path.exists():
                log(f"[warn] missing canonical for viewer update: {canonical_path.name}")
                continue
            transpiration_path = (
                cfg.transpiration_1m_dir
                / f"{date}__transpiration_1m__diff60__g_min_per_plant__p{int(cfg.plants_per_loadcell)}.parquet"
            )
            _viewer_write_day_json(
                viewer_data_dir=viewer_data_dir,
                date=date,
                canonical_path=canonical_path,
                transpiration_1m_path=transpiration_path if transpiration_path.exists() else None,
                plants_per_loadcell=cfg.plants_per_loadcell,
                log=log,
            )
        dates = _viewer_refresh_dates_json(viewer_data_dir)
        log(f"[ok] viewer dates.json updated (dates={len(dates)})")

    result = PreprocessResult(
        raw_total=len(raw_files),
        raw_skipped=skipped,
        raw_processed=processed,
        raw_failed=failed,
        updated_dates=sorted(updated_dates),
    )
    log(
        f"[done] raw_total={result.raw_total} skipped={result.raw_skipped} "
        f"processed={result.raw_processed} failed={result.raw_failed} "
        f"updated_dates={len(result.updated_dates)}"
    )
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Incrementally preprocess ALMEMO raw CSV files into canonical parquet artifacts.",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=PROJECT_ROOT,
        help="Repository root used for relative path resolution.",
    )
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=Path("data/raw"),
        help="Directory containing raw ALMEMO500 exports.",
    )
    parser.add_argument(
        "--raw-pattern",
        type=str,
        default="ALMEMO500~*.csv",
        help="Glob for raw ALMEMO inputs.",
    )
    parser.add_argument(
        "--canonical-dir",
        type=Path,
        default=Path("data/processed/canonical_1s"),
        help="Directory for daily canonical 1-second parquet files.",
    )
    parser.add_argument(
        "--transpiration-1m-dir",
        type=Path,
        default=Path("data/processed/transpiration_1m"),
        help="Directory for daily transpiration 1-minute parquet files.",
    )
    parser.add_argument(
        "--marker-dir",
        type=Path,
        default=Path("data/processed/_batch_markers"),
        help="Directory for batch marker JSON files.",
    )
    parser.add_argument(
        "--viewer-dir",
        type=Path,
        default=Path("artifacts/preprocess_compare"),
        help="Viewer root whose data cache should be refreshed.",
    )
    parser.add_argument(
        "--no-viewer",
        dest="viewer_enabled",
        action="store_false",
        help="Disable viewer cache refresh after processing.",
    )
    parser.add_argument(
        "--plants-per-loadcell",
        type=int,
        default=3,
        help="Plant count used for transpiration-per-plant outputs.",
    )
    parser.add_argument(
        "--encoding",
        type=str,
        default="latin1",
        help="Encoding for raw ALMEMO CSV files.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite canonical parquet instead of upserting into existing files.",
    )
    parser.add_argument(
        "--max-files",
        type=int,
        default=None,
        help="Optional cap on raw files to process.",
    )
    parser.set_defaults(viewer_enabled=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    cfg = PreprocessConfig(
        repo_root=args.repo_root,
        raw_dir=args.raw_dir,
        raw_pattern=args.raw_pattern,
        canonical_dir=args.canonical_dir,
        transpiration_1m_dir=args.transpiration_1m_dir,
        marker_dir=args.marker_dir,
        viewer_dir=args.viewer_dir if args.viewer_enabled else None,
        plants_per_loadcell=args.plants_per_loadcell,
        encoding=args.encoding,
        overwrite=args.overwrite,
        max_files=args.max_files,
    )
    result = run_incremental_preprocess(cfg, log=lambda message: print(message, file=sys.stderr))
    print(json.dumps(asdict(result), ensure_ascii=True, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
