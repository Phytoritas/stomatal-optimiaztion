#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import sys
import threading
import time
from collections.abc import Sequence
from datetime import datetime, timezone
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from socketserver import ThreadingMixIn
from typing import Any
from urllib.parse import urlparse

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"
for path in (SRC_DIR, SCRIPTS_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import preprocess_incremental as pp  # noqa: E402

DATE_RE = r"^\d{4}-\d{2}-\d{2}$"
LC_COLS = [f"loadcell_{idx}_kg" for idx in range(1, 7)]


def _safe_path_under(root: Path, user_path: str) -> Path:
    path = Path(user_path).expanduser()
    path = (root / path).resolve() if not path.is_absolute() else path.resolve()
    root_resolved = root.resolve()
    if path == root_resolved:
        return path
    if root_resolved not in path.parents:
        raise ValueError(f"final_dir must be under repo root: {root_resolved}")
    return path


def _rolling_slope_trailing(values: np.ndarray, window: int) -> np.ndarray:
    size = int(len(values))
    out = np.full(size, np.nan, dtype=np.float64)
    window_size = int(window)
    if window_size < 2 or size < window_size:
        return out

    idx = np.arange(size, dtype=np.float64)
    cumsum_y = np.cumsum(values, dtype=np.float64)
    cumsum_xy = np.cumsum(idx * values, dtype=np.float64)

    sum_x = (window_size * (window_size - 1)) / 2.0
    var_x = (window_size * (window_size * window_size - 1)) / 12.0
    if var_x <= 0:
        return out

    for end_idx in range(window_size - 1, size):
        start_idx = end_idx - window_size + 1
        sum_y = float(cumsum_y[end_idx] - (cumsum_y[start_idx - 1] if start_idx > 0 else 0.0))
        sum_xy = float(
            cumsum_xy[end_idx] - (cumsum_xy[start_idx - 1] if start_idx > 0 else 0.0)
        )
        shifted_sum_xy = sum_xy - float(start_idx) * sum_y
        numerator = shifted_sum_xy - (sum_x * sum_y) / float(window_size)
        out[end_idx] = numerator / var_x

    return out


def _compute_transpiration(
    *,
    canonical_path: Path,
    transpiration_1m_dir: Path,
    date: str,
    method: str,
    resolution: str,
    plants_per_loadcell: int,
    ma_window_sec: int,
    reg_window_sec: int,
    cap_g_min_per_plant: float | None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    if plants_per_loadcell < 1:
        raise ValueError("plants_per_loadcell must be >= 1")
    if cap_g_min_per_plant is not None and (
        not math.isfinite(cap_g_min_per_plant) or cap_g_min_per_plant <= 0
    ):
        raise ValueError("cap_g_min_per_plant must be a finite value > 0")

    df = pd.read_parquet(canonical_path, columns=["timestamp", *LC_COLS])
    if df.empty:
        raise ValueError(f"Empty canonical file: {canonical_path}")
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").set_index("timestamp", drop=True)
    weights_g = df[LC_COLS].astype("float64") * 1000.0

    meta = {
        "date": date,
        "method": method,
        "resolution": resolution,
        "plants_per_loadcell": int(plants_per_loadcell),
        "ma_window_sec": int(ma_window_sec),
        "reg_window_sec": int(reg_window_sec),
        "cap_g_min_per_plant": cap_g_min_per_plant,
        "source_canonical": str(canonical_path),
        "source_transpiration_1m": None,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
    }

    def apply_cap(frame: pd.DataFrame) -> pd.DataFrame:
        if cap_g_min_per_plant is None:
            return frame
        return frame.clip(upper=float(cap_g_min_per_plant))

    if method == "diff60_1m":
        if resolution != "1m":
            raise ValueError("diff60_1m method only supports resolution=1m")
        pattern = f"{date}__transpiration_1m__diff60__g_min_per_plant__p{plants_per_loadcell}*.parquet"
        matches = sorted(transpiration_1m_dir.glob(pattern)) if transpiration_1m_dir.exists() else []
        if matches:
            meta["source_transpiration_1m"] = str(matches[0])
            tdf = pd.read_parquet(matches[0])
            columns = [f"loadcell_{idx}_transpiration_g_min_per_plant" for idx in range(1, 7)]
            missing = [column for column in columns if column not in tdf.columns]
            if missing:
                raise KeyError(f"Missing columns in {matches[0]}: {missing}")
            tdf["timestamp"] = pd.to_datetime(tdf["timestamp"])
            transpiration = tdf.sort_values("timestamp").set_index("timestamp", drop=True)[columns]
            transpiration = transpiration.astype("float64")
            transpiration.columns = LC_COLS
        else:
            delta_g = weights_g.resample("1min", label="right", closed="right").last().diff()
            transpiration = (-delta_g).clip(lower=0.0).fillna(0.0) / float(plants_per_loadcell)
        transpiration = apply_cap(transpiration)
    elif method in {"diff_1s", "ma_diff_1s", "reg_1s"}:
        if method == "diff_1s":
            base = weights_g
            delta_g = base.diff()
            transpiration = (-delta_g).clip(lower=0.0).fillna(0.0) / float(plants_per_loadcell)
            transpiration = apply_cap(transpiration * 60.0)
        elif method == "ma_diff_1s":
            base = weights_g.rolling(window=max(1, int(ma_window_sec)), min_periods=1).mean()
            delta_g = base.diff()
            transpiration = (-delta_g).clip(lower=0.0).fillna(0.0) / float(plants_per_loadcell)
            transpiration = apply_cap(transpiration * 60.0)
        else:
            slopes = {
                column: _rolling_slope_trailing(
                    weights_g[column].to_numpy(dtype=np.float64),
                    max(2, int(reg_window_sec)),
                )
                for column in LC_COLS
            }
            transpiration = pd.DataFrame(slopes, index=weights_g.index)
            transpiration = (
                (-transpiration).clip(lower=0.0).fillna(0.0) / float(plants_per_loadcell)
            ) * 60.0
            transpiration = apply_cap(transpiration)

        if resolution == "1m":
            transpiration = transpiration.resample("1min", label="right", closed="right").mean()
        elif resolution != "1s":
            raise ValueError("resolution must be '1s' or '1m'")
    else:
        raise ValueError(f"Unknown method: {method}")

    out = pd.DataFrame(index=transpiration.index)
    for idx in range(1, 7):
        out[f"loadcell_{idx}_transpiration_g_min_per_plant"] = transpiration[f"loadcell_{idx}_kg"]
    transpiration_total = transpiration * float(plants_per_loadcell)
    out["total_transpiration_g_min"] = transpiration_total.sum(axis=1)
    out["avg_transpiration_g_min_per_plant"] = (
        out["total_transpiration_g_min"] / float(plants_per_loadcell * 6)
    )
    return out.reset_index(), meta


class _ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


def _utc_iso_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _init_preprocess_state() -> dict[str, Any]:
    return {
        "running": False,
        "cancel_requested": False,
        "phase": "idle",
        "message": "",
        "started_at_utc": None,
        "ended_at_utc": None,
        "updated_at_utc": None,
        "log_tail": [],
        "result": None,
        "error": None,
    }


def _append_log(preprocess_state: dict[str, Any], message: str, *, max_lines: int = 240) -> None:
    line = f"{_utc_iso_now()} {message}"
    preprocess_state["message"] = message
    preprocess_state["updated_at_utc"] = _utc_iso_now()
    tail = preprocess_state.get("log_tail", [])
    if not isinstance(tail, list):
        tail = []
    tail.append(line)
    preprocess_state["log_tail"] = tail[-max_lines:]


def _start_preprocess_job(server_state: dict[str, Any], request_payload: dict[str, Any]) -> dict[str, Any]:
    lock: threading.Lock = server_state["preprocess_lock"]
    with lock:
        state = server_state["preprocess_state"]
        if state.get("running"):
            return {"ok": True, "started": False, "running": True, "message": "already running"}
        server_state["preprocess_state"] = _init_preprocess_state()
        state = server_state["preprocess_state"]
        state["running"] = True
        state["phase"] = "starting"
        state["started_at_utc"] = _utc_iso_now()
        state["updated_at_utc"] = state["started_at_utc"]
        _append_log(state, "[info] preprocess job started")

    cfg = pp.PreprocessConfig(
        repo_root=server_state["repo_root"],
        raw_dir=_safe_path_under(
            server_state["repo_root"],
            str(request_payload.get("raw_dir", "data/raw")).strip() or "data/raw",
        ),
        raw_pattern=str(request_payload.get("pattern", "ALMEMO500~*.csv")).strip() or "ALMEMO500~*.csv",
        canonical_dir=Path(server_state["canonical_dir"]),
        transpiration_1m_dir=Path(server_state["transpiration_1m_dir"]),
        marker_dir=Path(server_state["marker_dir"]),
        viewer_dir=Path(server_state["viewer_dir"]),
        plants_per_loadcell=int(request_payload.get("plants_per_loadcell", request_payload.get("plants", 3)) or 3),
        overwrite=False,
        max_files=(
            None
            if request_payload.get("max_files", None) is None
            else int(request_payload["max_files"])
        ),
    )

    def should_cancel() -> bool:
        with lock:
            return bool(server_state["preprocess_state"].get("cancel_requested", False))

    def log(message: str) -> None:
        with lock:
            _append_log(server_state["preprocess_state"], message)

    def worker() -> None:
        try:
            with lock:
                server_state["preprocess_state"]["phase"] = "running"
            result = pp.run_incremental_preprocess(cfg, log=log, should_cancel=should_cancel)
            with lock:
                state = server_state["preprocess_state"]
                state["phase"] = "done"
                state["running"] = False
                state["ended_at_utc"] = _utc_iso_now()
                state["result"] = {
                    "raw_total": result.raw_total,
                    "raw_skipped": result.raw_skipped,
                    "raw_processed": result.raw_processed,
                    "raw_failed": result.raw_failed,
                    "updated_dates": result.updated_dates,
                }
        except Exception as exc:
            with lock:
                state = server_state["preprocess_state"]
                state["phase"] = "error"
                state["running"] = False
                state["ended_at_utc"] = _utc_iso_now()
                state["error"] = str(exc)
                _append_log(state, f"[error] {exc}")

    thread = threading.Thread(target=worker, name="preprocess-job", daemon=True)
    with lock:
        server_state["preprocess_thread"] = thread
    thread.start()
    return {"ok": True, "started": True, "running": True}


def _make_handler(*, directory: Path, server_state: dict[str, Any]):
    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(directory), **kwargs)

        def _send_json(self, payload_obj: Any, status: int = 200) -> None:
            payload = json.dumps(payload_obj, ensure_ascii=True).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def _read_json(self) -> dict[str, Any]:
            length = int(self.headers.get("Content-Length", "0") or "0")
            raw = self.rfile.read(length) if length > 0 else b"{}"
            try:
                return json.loads(raw.decode("utf-8"))
            except Exception as exc:
                raise ValueError(f"Invalid JSON: {exc}") from exc

        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path == "/api/health":
                self._send_json(
                    {
                        "ok": True,
                        "viewer_dir": str(directory),
                        "canonical_dir": str(server_state["canonical_dir"]),
                        "transpiration_1m_dir": str(server_state["transpiration_1m_dir"]),
                        "final_dir": str(server_state["final_dir"]),
                        "marker_dir": str(server_state["marker_dir"]),
                    }
                )
                return
            if parsed.path == "/api/preprocess/status":
                with server_state["preprocess_lock"]:
                    state = dict(server_state["preprocess_state"])
                self._send_json({"ok": True, "state": state})
                return
            super().do_GET()

        def do_POST(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            try:
                request_payload = self._read_json()
                if parsed.path == "/api/preprocess":
                    self._send_json(_start_preprocess_job(server_state, request_payload))
                    return
                if parsed.path == "/api/preprocess/cancel":
                    with server_state["preprocess_lock"]:
                        server_state["preprocess_state"]["cancel_requested"] = True
                        _append_log(server_state["preprocess_state"], "[warn] cancel requested")
                    self._send_json({"ok": True})
                    return
                if parsed.path != "/api/export":
                    self.send_error(404)
                    return

                date = str(request_payload.get("date", "")).strip()
                if not pd.Series([date]).str.match(DATE_RE).item():
                    raise ValueError("date must be YYYY-MM-DD")

                final_dir = _safe_path_under(
                    server_state["repo_root"],
                    str(request_payload.get("final_dir", str(server_state["final_dir"]))).strip()
                    or str(server_state["final_dir"]),
                )
                canonical_path = Path(server_state["canonical_dir"]) / f"{date}_canonical_1s.parquet"
                if not canonical_path.exists():
                    raise FileNotFoundError(f"canonical file not found: {canonical_path}")

                method = str(request_payload.get("method", "")).strip()
                resolution = str(request_payload.get("resolution", "")).strip()
                out_df, meta = _compute_transpiration(
                    canonical_path=canonical_path,
                    transpiration_1m_dir=Path(server_state["transpiration_1m_dir"]),
                    date=date,
                    method=method,
                    resolution=resolution,
                    plants_per_loadcell=int(request_payload.get("plants_per_loadcell", 3)),
                    ma_window_sec=int(request_payload.get("ma_window_sec", 60)),
                    reg_window_sec=int(request_payload.get("reg_window_sec", 300)),
                    cap_g_min_per_plant=(
                        None
                        if request_payload.get("cap_g_min_per_plant", None) is None
                        else float(request_payload["cap_g_min_per_plant"])
                    ),
                )

                out_dir = final_dir / date
                out_dir.mkdir(parents=True, exist_ok=True)
                out_path = out_dir / f"transpiration_{resolution}__{method}.parquet"
                meta_path = out_dir / f"transpiration_{resolution}__{method}__meta.json"
                out_df.to_parquet(out_path, index=False, engine="pyarrow", compression="snappy")
                meta_path.write_text(
                    json.dumps(meta, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                self._send_json({"ok": True, "path": str(out_path), "rows": int(len(out_df))})
            except Exception as exc:
                self._send_json({"ok": False, "error": str(exc)}, status=400)

    return Handler


def create_server(
    *,
    bind: str,
    port: int,
    viewer_dir: Path,
    canonical_dir: Path,
    transpiration_1m_dir: Path,
    final_dir: Path,
    marker_dir: Path,
    repo_root: Path = PROJECT_ROOT,
) -> _ThreadingHTTPServer:
    server_state = {
        "repo_root": Path(repo_root).resolve(),
        "viewer_dir": Path(viewer_dir).resolve(),
        "canonical_dir": Path(canonical_dir).resolve(),
        "transpiration_1m_dir": Path(transpiration_1m_dir).resolve(),
        "final_dir": Path(final_dir).resolve(),
        "marker_dir": Path(marker_dir).resolve(),
        "preprocess_lock": threading.Lock(),
        "preprocess_state": _init_preprocess_state(),
        "preprocess_thread": None,
    }
    handler_cls = _make_handler(directory=Path(viewer_dir).resolve(), server_state=server_state)
    server = _ThreadingHTTPServer((str(bind), int(port)), handler_cls)
    setattr(server, "preprocess_compare_state", server_state)
    return server


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Serve preprocess-compare viewer with export API.")
    parser.add_argument(
        "--viewer-dir",
        type=Path,
        default=Path("artifacts/preprocess_compare"),
        help="Directory with index.html/app.js/style.css/data/*.json.",
    )
    parser.add_argument(
        "--canonical-dir",
        type=Path,
        default=Path("data/processed/canonical_1s"),
        help="Directory with YYYY-MM-DD_canonical_1s.parquet files.",
    )
    parser.add_argument(
        "--transpiration-1m-dir",
        type=Path,
        default=Path("data/processed/transpiration_1m"),
        help="Directory with transpiration 1m parquet outputs.",
    )
    parser.add_argument(
        "--final-dir",
        type=Path,
        default=Path("data/final"),
        help="Base directory for saved final outputs.",
    )
    parser.add_argument(
        "--marker-dir",
        type=Path,
        default=Path("data/processed/_batch_markers"),
        help="Directory for per-raw-file processing markers.",
    )
    parser.add_argument("--bind", type=str, default="127.0.0.1", help="Bind address.")
    parser.add_argument("--port", type=int, default=8000, help="Port.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    viewer_dir = Path(args.viewer_dir)
    canonical_dir = Path(args.canonical_dir)
    if not (viewer_dir / "index.html").exists():
        raise FileNotFoundError(f"viewer-dir missing index.html: {viewer_dir}")
    if not canonical_dir.exists():
        raise FileNotFoundError(f"canonical-dir not found: {canonical_dir}")

    server = create_server(
        bind=args.bind,
        port=args.port,
        viewer_dir=viewer_dir,
        canonical_dir=canonical_dir,
        transpiration_1m_dir=Path(args.transpiration_1m_dir),
        final_dir=Path(args.final_dir),
        marker_dir=Path(args.marker_dir),
        repo_root=PROJECT_ROOT,
    )
    host, port = server.server_address
    state = getattr(server, "preprocess_compare_state")
    print(f"[ok] serving viewer: {viewer_dir}  (bind={host} port={port})")
    print(f"[ok] export base dir: {state['final_dir']}")
    print("open: http://<host>:<port>/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"[error] {exc}", file=sys.stderr)
        raise
