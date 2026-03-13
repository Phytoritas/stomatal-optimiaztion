from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

from stomatal_optimiaztion.domains.load_cell import CANONICAL_COLUMNS


def _script_path() -> Path:
    return Path(__file__).resolve().parents[1] / "scripts" / "preprocess_incremental.py"


def _load_script_module():
    spec = importlib.util.spec_from_file_location(
        "load_cell_preprocess_incremental_script",
        _script_path(),
    )
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write_raw_file(path: Path, rows: list[str]) -> None:
    path.write_text("\n".join(rows) + "\n", encoding="latin1")


def _canonical_frame(
    values: list[float],
    *,
    start: str = "2025-01-01 00:00:00",
    freq: str = "1s",
) -> pd.DataFrame:
    index = pd.date_range(start=start, periods=len(values), freq=freq, name="timestamp")
    df = pd.DataFrame(index=index, columns=CANONICAL_COLUMNS, dtype=float)
    df.loc[:, :] = float("nan")
    df["loadcell_1_kg"] = values
    return df


def test_load_done_markers_ignores_invalid_payloads(tmp_path: Path) -> None:
    module = _load_script_module()
    marker_dir = tmp_path / "markers"
    marker_dir.mkdir()
    (marker_dir / "ok.json").write_text(
        json.dumps(
            {
                "status": "done",
                "input": "data/raw/ALMEMO500~1.csv",
                "source": {"size": 123, "mtime_ns": 456},
            }
        ),
        encoding="utf-8",
    )
    (marker_dir / "error.json").write_text(
        json.dumps({"status": "error", "input": "bad.csv"}),
        encoding="utf-8",
    )
    (marker_dir / "broken.json").write_text("{", encoding="utf-8")

    markers = module._load_done_markers(marker_dir)

    assert markers == {"data/raw/ALMEMO500~1.csv": {(123, 456)}}


def test_upsert_canonical_day_merges_existing_parquet(tmp_path: Path) -> None:
    module = _load_script_module()
    canonical_dir = tmp_path / "canonical"
    canonical_dir.mkdir()
    existing = _canonical_frame([10.0, 11.0]).reset_index()
    existing.to_parquet(
        canonical_dir / "2025-01-01_canonical_1s.parquet",
        index=False,
        engine="pyarrow",
        compression="snappy",
    )

    merged = module._upsert_canonical_day(
        date="2025-01-01",
        new_day_df_1s=_canonical_frame([12.0, 13.0], start="2025-01-01 00:00:01"),
        canonical_dir=canonical_dir,
        overwrite=False,
        log=lambda message: None,
    )

    assert list(merged.index.astype(str)) == [
        "2025-01-01 00:00:00",
        "2025-01-01 00:00:01",
        "2025-01-01 00:00:02",
    ]
    assert merged.loc[pd.Timestamp("2025-01-01 00:00:01"), "loadcell_1_kg"] == pytest.approx(12.0)


def test_viewer_helpers_write_day_json_and_dates_index(tmp_path: Path) -> None:
    module = _load_script_module()
    viewer_data_dir = tmp_path / "viewer" / "data"
    viewer_data_dir.mkdir(parents=True)

    canonical_path = tmp_path / "2025-01-01_canonical_1s.parquet"
    canonical = _canonical_frame([10.0, 9.0]).reset_index()
    canonical.to_parquet(canonical_path, index=False, engine="pyarrow", compression="snappy")

    transpiration_path = tmp_path / "2025-01-01__transpiration.parquet"
    transpiration = pd.DataFrame(
        {
            "timestamp": pd.date_range("2025-01-01 00:01:00", periods=1, freq="1min"),
            **{
                f"loadcell_{idx}_transpiration_g_min_per_plant": [float(idx)]
                for idx in range(1, 7)
            },
        }
    )
    transpiration.to_parquet(
        transpiration_path,
        index=False,
        engine="pyarrow",
        compression="snappy",
    )

    module._viewer_write_day_json(
        viewer_data_dir=viewer_data_dir,
        date="2025-01-01",
        canonical_path=canonical_path,
        transpiration_1m_path=transpiration_path,
        plants_per_loadcell=3,
        log=lambda message: None,
    )
    dates = module._viewer_refresh_dates_json(viewer_data_dir)

    payload = json.loads((viewer_data_dir / "2025-01-01.json").read_text(encoding="utf-8"))
    assert dates == ["2025-01-01"]
    assert payload["n_1s"] == 2
    assert payload["weights_dg"][0] == [100000, 90000]
    assert payload["transp1m_mg_min_per_plant"]["values"][0] == [1000]


def test_run_incremental_preprocess_writes_outputs_and_skips_completed_source(tmp_path: Path) -> None:
    module = _load_script_module()
    raw_dir = tmp_path / "data" / "raw"
    raw_dir.mkdir(parents=True)
    _write_raw_file(
        raw_dir / "ALMEMO500~1.csv",
        [
            "metadata;;;;;;;;",
            "DATE:;TIME:;M000.0 N",
            "01.01.25;12:00:00.000;10.0",
            "01.01.25;12:01:00.000;9.0",
        ],
    )
    cfg = module.PreprocessConfig(
        repo_root=tmp_path,
        raw_dir=Path("data/raw"),
        raw_pattern="ALMEMO500~*.csv",
        canonical_dir=Path("data/processed/canonical_1s"),
        transpiration_1m_dir=Path("data/processed/transpiration_1m"),
        marker_dir=Path("data/processed/_batch_markers"),
        viewer_dir=Path("artifacts/preprocess_compare"),
    )
    logs: list[str] = []

    first = module.run_incremental_preprocess(cfg, log=logs.append)
    second = module.run_incremental_preprocess(cfg, log=logs.append)

    canonical_path = (
        tmp_path / "data" / "processed" / "canonical_1s" / "2025-01-01_canonical_1s.parquet"
    )
    transpiration_path = (
        tmp_path
        / "data"
        / "processed"
        / "transpiration_1m"
        / "2025-01-01__transpiration_1m__diff60__g_min_per_plant__p3.parquet"
    )
    marker_files = list((tmp_path / "data" / "processed" / "_batch_markers").glob("*.json"))
    viewer_day_path = tmp_path / "artifacts" / "preprocess_compare" / "data" / "2025-01-01.json"

    assert first == module.PreprocessResult(
        raw_total=1,
        raw_skipped=0,
        raw_processed=1,
        raw_failed=0,
        updated_dates=["2025-01-01"],
    )
    assert second == module.PreprocessResult(
        raw_total=1,
        raw_skipped=1,
        raw_processed=0,
        raw_failed=0,
        updated_dates=[],
    )
    assert canonical_path.exists()
    assert transpiration_path.exists()
    assert viewer_day_path.exists()
    assert len(marker_files) == 1
    transpiration = pd.read_parquet(transpiration_path)
    assert float(
        transpiration["loadcell_1_transpiration_g_min_per_plant"].iloc[-1]
    ) == pytest.approx(1000.0 / 3.0)


def test_run_incremental_preprocess_honors_cancellation(tmp_path: Path) -> None:
    module = _load_script_module()
    raw_dir = tmp_path / "data" / "raw"
    raw_dir.mkdir(parents=True)
    for idx in (1, 2):
        _write_raw_file(
            raw_dir / f"ALMEMO500~{idx}.csv",
            [
                "metadata;;;;;;;;",
                "DATE:;TIME:;M000.0 N",
                "01.01.25;12:00:00.000;10.0",
            ],
        )

    cfg = module.PreprocessConfig(
        repo_root=tmp_path,
        raw_dir=Path("data/raw"),
        raw_pattern="ALMEMO500~*.csv",
        canonical_dir=Path("data/processed/canonical_1s"),
        transpiration_1m_dir=Path("data/processed/transpiration_1m"),
        marker_dir=Path("data/processed/_batch_markers"),
        viewer_dir=None,
    )

    result = module.run_incremental_preprocess(
        cfg,
        log=lambda message: None,
        should_cancel=lambda: True,
    )

    assert result == module.PreprocessResult(
        raw_total=2,
        raw_skipped=0,
        raw_processed=0,
        raw_failed=0,
        updated_dates=[],
    )


def test_run_incremental_preprocess_writes_error_marker_on_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_script_module()
    raw_dir = tmp_path / "data" / "raw"
    raw_dir.mkdir(parents=True)
    _write_raw_file(raw_dir / "ALMEMO500~1.csv", ["DATE:;TIME:;M000.0 N"])

    monkeypatch.setattr(module, "read_almemo_raw_csv", lambda path, encoding: (_ for _ in ()).throw(ValueError("boom")))
    cfg = module.PreprocessConfig(
        repo_root=tmp_path,
        raw_dir=Path("data/raw"),
        raw_pattern="ALMEMO500~*.csv",
        canonical_dir=Path("data/processed/canonical_1s"),
        transpiration_1m_dir=Path("data/processed/transpiration_1m"),
        marker_dir=Path("data/processed/_batch_markers"),
        viewer_dir=None,
    )

    result = module.run_incremental_preprocess(cfg, log=lambda message: None)

    marker_paths = list((tmp_path / "data" / "processed" / "_batch_markers").glob("*.json"))
    marker_payload = json.loads(marker_paths[0].read_text(encoding="utf-8"))
    assert result.raw_failed == 1
    assert marker_payload["status"] == "error"
    assert marker_payload["result"]["error"] == "boom"


def test_main_uses_legacy_defaults_and_prints_json_summary(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = _load_script_module()
    captures: dict[str, object] = {}

    def fake_run_incremental_preprocess(cfg, *, log, should_cancel=None):
        captures["cfg"] = cfg
        log("[info] test log")
        return module.PreprocessResult(
            raw_total=2,
            raw_skipped=1,
            raw_processed=1,
            raw_failed=0,
            updated_dates=["2025-01-01"],
        )

    monkeypatch.setattr(module, "run_incremental_preprocess", fake_run_incremental_preprocess)

    result = module.main([])

    stdout, stderr = capsys.readouterr()
    payload = json.loads(stdout)
    cfg = captures["cfg"]
    assert result == 0
    assert payload == {
        "raw_failed": 0,
        "raw_processed": 1,
        "raw_skipped": 1,
        "raw_total": 2,
        "updated_dates": ["2025-01-01"],
    }
    assert cfg.raw_dir == module.PROJECT_ROOT / "data" / "raw"
    assert cfg.canonical_dir == module.PROJECT_ROOT / "data" / "processed" / "canonical_1s"
    assert cfg.transpiration_1m_dir == module.PROJECT_ROOT / "data" / "processed" / "transpiration_1m"
    assert cfg.marker_dir == module.PROJECT_ROOT / "data" / "processed" / "_batch_markers"
    assert cfg.viewer_dir == module.PROJECT_ROOT / "artifacts" / "preprocess_compare"
    assert cfg.raw_pattern == "ALMEMO500~*.csv"
    assert cfg.plants_per_loadcell == 3
    assert cfg.encoding == "latin1"
    assert "[info] test log" in stderr
