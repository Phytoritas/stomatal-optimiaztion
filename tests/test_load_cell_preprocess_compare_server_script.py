from __future__ import annotations

import importlib.util
import json
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

import pandas as pd
import pytest


def _script_path() -> Path:
    return Path(__file__).resolve().parents[1] / "scripts" / "preprocess_compare_server.py"


def _load_script_module():
    spec = importlib.util.spec_from_file_location(
        "load_cell_preprocess_compare_server_script",
        _script_path(),
    )
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _canonical_frame(*, start: str = "2025-01-01 00:00:00", periods: int = 61) -> pd.DataFrame:
    index = pd.date_range(start, periods=periods, freq="1s", name="timestamp")
    data = {
        f"loadcell_{idx}_kg": [10.0 - (row / 60.0 if idx == 1 else 0.0) for row in range(periods)]
        for idx in range(1, 7)
    }
    return pd.DataFrame(data, index=index)


def _write_canonical_day(path: Path) -> None:
    _canonical_frame().reset_index().to_parquet(
        path,
        index=False,
        engine="pyarrow",
        compression="snappy",
    )


def _write_transpiration_day(path: Path, value: float = 7.5) -> None:
    pd.DataFrame(
        {
            "timestamp": pd.date_range("2025-01-01 00:01:00", periods=1, freq="1min"),
            **{
                f"loadcell_{idx}_transpiration_g_min_per_plant": [value + idx - 1]
                for idx in range(1, 7)
            },
        }
    ).to_parquet(path, index=False, engine="pyarrow", compression="snappy")


def _write_viewer_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    (path / "index.html").write_text("<!doctype html><title>viewer</title>", encoding="utf-8")


def _http_json(url: str, *, method: str = "GET", payload: dict[str, object] | None = None) -> dict[str, object]:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"} if data is not None else {},
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:  # pragma: no cover
        body = exc.read().decode("utf-8")
        raise AssertionError(f"HTTP {exc.code}: {body}") from exc


def _start_server(module, tmp_path: Path):
    viewer_dir = tmp_path / "viewer"
    canonical_dir = tmp_path / "data" / "processed" / "canonical_1s"
    transpiration_dir = tmp_path / "data" / "processed" / "transpiration_1m"
    marker_dir = tmp_path / "data" / "processed" / "_batch_markers"
    final_dir = tmp_path / "data" / "final"
    for directory in (canonical_dir, transpiration_dir, marker_dir, final_dir):
        directory.mkdir(parents=True, exist_ok=True)
    _write_viewer_dir(viewer_dir)
    _write_canonical_day(canonical_dir / "2025-01-01_canonical_1s.parquet")
    _write_transpiration_day(
        transpiration_dir / "2025-01-01__transpiration_1m__diff60__g_min_per_plant__p3.parquet"
    )
    server = module.create_server(
        bind="127.0.0.1",
        port=0,
        viewer_dir=viewer_dir,
        canonical_dir=canonical_dir,
        transpiration_1m_dir=transpiration_dir,
        final_dir=final_dir,
        marker_dir=marker_dir,
        repo_root=tmp_path,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://{server.server_address[0]}:{server.server_address[1]}"
    return server, thread, base_url, {
        "viewer_dir": viewer_dir,
        "canonical_dir": canonical_dir,
        "transpiration_dir": transpiration_dir,
        "final_dir": final_dir,
        "marker_dir": marker_dir,
    }


def test_safe_path_under_rejects_escape(tmp_path: Path) -> None:
    module = _load_script_module()

    assert module._safe_path_under(tmp_path, "data/final") == (tmp_path / "data" / "final").resolve()
    with pytest.raises(ValueError, match="final_dir must be under repo root"):
        module._safe_path_under(tmp_path, "..")


def test_build_parser_defaults_match_legacy_server_paths() -> None:
    module = _load_script_module()
    args = module.build_parser().parse_args([])

    assert args.viewer_dir == Path("artifacts/preprocess_compare")
    assert args.canonical_dir == Path("data/processed/canonical_1s")
    assert args.transpiration_1m_dir == Path("data/processed/transpiration_1m")
    assert args.final_dir == Path("data/final")
    assert args.marker_dir == Path("data/processed/_batch_markers")
    assert args.bind == "127.0.0.1"
    assert args.port == 8000


def test_compute_transpiration_prefers_existing_one_minute_artifact(tmp_path: Path) -> None:
    module = _load_script_module()
    canonical_path = tmp_path / "2025-01-01_canonical_1s.parquet"
    transpiration_dir = tmp_path / "transpiration_1m"
    transpiration_dir.mkdir()
    _write_canonical_day(canonical_path)
    transpiration_path = (
        transpiration_dir / "2025-01-01__transpiration_1m__diff60__g_min_per_plant__p3.parquet"
    )
    _write_transpiration_day(transpiration_path, value=8.5)

    out_df, meta = module._compute_transpiration(
        canonical_path=canonical_path,
        transpiration_1m_dir=transpiration_dir,
        date="2025-01-01",
        method="diff60_1m",
        resolution="1m",
        plants_per_loadcell=3,
        ma_window_sec=60,
        reg_window_sec=300,
        cap_g_min_per_plant=None,
    )

    assert meta["source_transpiration_1m"] == str(transpiration_path)
    assert float(out_df["loadcell_1_transpiration_g_min_per_plant"].iloc[0]) == pytest.approx(8.5)


def test_compute_transpiration_regression_supports_one_second_cap(tmp_path: Path) -> None:
    module = _load_script_module()
    canonical_path = tmp_path / "2025-01-01_canonical_1s.parquet"
    _write_canonical_day(canonical_path)

    out_df, meta = module._compute_transpiration(
        canonical_path=canonical_path,
        transpiration_1m_dir=tmp_path / "missing",
        date="2025-01-01",
        method="reg_1s",
        resolution="1s",
        plants_per_loadcell=3,
        ma_window_sec=60,
        reg_window_sec=5,
        cap_g_min_per_plant=5.0,
    )

    assert meta["method"] == "reg_1s"
    assert meta["resolution"] == "1s"
    assert len(out_df) == 61
    assert float(out_df["loadcell_1_transpiration_g_min_per_plant"].max()) <= 5.0


def test_server_health_and_export_api_write_final_outputs(tmp_path: Path) -> None:
    module = _load_script_module()
    server, thread, base_url, paths = _start_server(module, tmp_path)
    try:
        health = _http_json(f"{base_url}/api/health")
        export = _http_json(
            f"{base_url}/api/export",
            method="POST",
            payload={
                "date": "2025-01-01",
                "method": "diff60_1m",
                "resolution": "1m",
                "plants_per_loadcell": 3,
                "final_dir": "data/final",
            },
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    out_path = Path(str(export["path"]))
    meta_path = out_path.with_name(f"{out_path.stem}__meta.json")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    assert health["ok"] is True
    assert health["final_dir"] == str(paths["final_dir"].resolve())
    assert export["ok"] is True
    assert out_path.exists()
    assert meta["method"] == "diff60_1m"
    assert meta["resolution"] == "1m"
    assert meta["source_transpiration_1m"] == str(
        (
            paths["transpiration_dir"]
            / "2025-01-01__transpiration_1m__diff60__g_min_per_plant__p3.parquet"
        ).resolve()
    )


def test_server_preprocess_endpoints_track_status_and_cancel(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_script_module()
    server, thread, base_url, _ = _start_server(module, tmp_path)
    (tmp_path / "data" / "raw").mkdir(parents=True, exist_ok=True)

    def fake_run_incremental_preprocess(cfg, *, log, should_cancel=None):
        log(f"[info] fake preprocess {cfg.raw_pattern}")
        while should_cancel is not None and not should_cancel():
            time.sleep(0.02)
        log("[warn] fake cancel observed")
        return module.pp.PreprocessResult(
            raw_total=1,
            raw_skipped=0,
            raw_processed=1,
            raw_failed=0,
            updated_dates=["2025-01-01"],
        )

    monkeypatch.setattr(module.pp, "run_incremental_preprocess", fake_run_incremental_preprocess)

    try:
        started = _http_json(
            f"{base_url}/api/preprocess",
            method="POST",
            payload={"raw_dir": "data/raw", "pattern": "ALMEMO500~*.csv"},
        )
        already_running = _http_json(
            f"{base_url}/api/preprocess",
            method="POST",
            payload={"raw_dir": "data/raw"},
        )
        status = _http_json(f"{base_url}/api/preprocess/status")
        canceled = _http_json(f"{base_url}/api/preprocess/cancel", method="POST", payload={})

        deadline = time.time() + 3.0
        final_status = status
        while time.time() < deadline:
            final_status = _http_json(f"{base_url}/api/preprocess/status")
            if not final_status["state"]["running"]:
                break
            time.sleep(0.05)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert started["started"] is True
    assert already_running["started"] is False
    assert status["state"]["running"] is True
    assert canceled["ok"] is True
    assert final_status["state"]["phase"] == "done"
    assert final_status["state"]["result"]["updated_dates"] == ["2025-01-01"]
    log_tail = "\n".join(final_status["state"]["log_tail"])
    assert "cancel requested" in log_tail
    assert "fake cancel observed" in log_tail


def test_main_dispatches_cli_arguments(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    module = _load_script_module()
    viewer_dir = tmp_path / "viewer"
    canonical_dir = tmp_path / "canonical"
    transpiration_dir = tmp_path / "transpiration_1m"
    final_dir = tmp_path / "final"
    marker_dir = tmp_path / "markers"
    _write_viewer_dir(viewer_dir)
    canonical_dir.mkdir()
    captures: dict[str, object] = {}

    class FakeServer:
        server_address = ("127.0.0.1", 8123)

        def __init__(self) -> None:
            self.preprocess_compare_state = {"final_dir": final_dir.resolve()}

        def serve_forever(self) -> None:
            return None

        def server_close(self) -> None:
            return None

    def fake_create_server(**kwargs):
        captures.update(kwargs)
        return FakeServer()

    monkeypatch.setattr(module, "create_server", fake_create_server)

    result = module.main(
        [
            "--viewer-dir",
            str(viewer_dir),
            "--canonical-dir",
            str(canonical_dir),
            "--transpiration-1m-dir",
            str(transpiration_dir),
            "--final-dir",
            str(final_dir),
            "--marker-dir",
            str(marker_dir),
            "--bind",
            "0.0.0.0",
            "--port",
            "9001",
        ]
    )

    assert result == 0
    assert captures == {
        "bind": "0.0.0.0",
        "port": 9001,
        "viewer_dir": viewer_dir,
        "canonical_dir": canonical_dir,
        "transpiration_1m_dir": transpiration_dir,
        "final_dir": final_dir,
        "marker_dir": marker_dir,
        "repo_root": module.PROJECT_ROOT,
    }
