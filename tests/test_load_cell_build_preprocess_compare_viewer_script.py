from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pandas as pd


def _script_path() -> Path:
    return Path(__file__).resolve().parents[1] / "scripts" / "build_preprocess_compare_viewer.py"


def _load_script_module():
    spec = importlib.util.spec_from_file_location(
        "load_cell_build_preprocess_compare_viewer_script",
        _script_path(),
    )
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _canonical_frame(
    values: list[float],
    *,
    start: str = "2025-01-01 00:00:00",
    freq: str = "1s",
) -> pd.DataFrame:
    index = pd.date_range(start=start, periods=len(values), freq=freq, name="timestamp")
    data = {"timestamp": index}
    for idx in range(1, 7):
        data[f"loadcell_{idx}_kg"] = values
    return pd.DataFrame(data)


def _write_canonical(path: Path, values: list[float], *, start: str = "2025-01-01 00:00:00") -> None:
    _canonical_frame(values, start=start).to_parquet(
        path,
        index=False,
        engine="pyarrow",
        compression="snappy",
    )


def test_select_days_filters_by_range_and_latest_limit(tmp_path: Path) -> None:
    module = _load_script_module()
    canonical_dir = tmp_path / "canonical"
    canonical_dir.mkdir()
    for day in ("2025-01-01", "2025-01-02", "2025-01-03"):
        _write_canonical(canonical_dir / f"{day}_canonical_1s.parquet", [10.0, 9.99])

    days = module._list_canonical_days(canonical_dir)

    selected = module._select_days(
        days,
        dates=None,
        start_date="2025-01-02",
        end_date=None,
        max_days=1,
        all_days=False,
    )
    explicit = module._select_days(
        days,
        dates=["2025-01-01", "2025-01-03"],
        start_date=None,
        end_date=None,
        max_days=None,
        all_days=False,
    )

    assert [day.date for day in days] == ["2025-01-01", "2025-01-02", "2025-01-03"]
    assert [day.date for day in selected] == ["2025-01-03"]
    assert [day.date for day in explicit] == ["2025-01-01", "2025-01-03"]


def test_main_writes_static_assets_and_fallback_day_json(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module = _load_script_module()
    monkeypatch.chdir(tmp_path)

    canonical_dir = tmp_path / "data" / "processed" / "canonical_1s"
    canonical_dir.mkdir(parents=True)
    values = [10.0 - (0.001 * idx) for idx in range(61)]
    _write_canonical(canonical_dir / "2025-01-01_canonical_1s.parquet", values)

    viewer_data_dir = tmp_path / "artifacts" / "preprocess_compare" / "data"
    viewer_data_dir.mkdir(parents=True)
    (viewer_data_dir / "2025-01-03.json").write_text("{}", encoding="utf-8")

    result = module.main([])

    output_dir = tmp_path / "artifacts" / "preprocess_compare"
    payload = json.loads((output_dir / "data" / "2025-01-01.json").read_text(encoding="utf-8"))
    dates = json.loads((output_dir / "data" / "dates.json").read_text(encoding="utf-8"))
    index_html = (output_dir / "index.html").read_text(encoding="utf-8")
    app_js = (output_dir / "app.js").read_text(encoding="utf-8")

    assert result == 0
    assert (output_dir / "style.css").exists()
    assert payload["plants_per_loadcell"] == 3
    assert payload["n_1s"] == 61
    assert payload["weights_dg"][0][0] == 100000
    assert payload["transp1m_mg_min_per_plant"]["dt_sec"] == 60
    assert payload["transp1m_mg_min_per_plant"]["values"][0] == [0, 20000]
    assert dates == ["2025-01-01", "2025-01-03"]
    assert "python scripts/preprocess_compare_server.py" in index_html
    assert "python scripts/preprocess_compare_server.py" in app_js


def test_main_prefers_existing_transpiration_1m_file(tmp_path: Path) -> None:
    module = _load_script_module()

    canonical_dir = tmp_path / "canonical"
    transpiration_dir = tmp_path / "transpiration_1m"
    output_dir = tmp_path / "viewer"
    canonical_dir.mkdir()
    transpiration_dir.mkdir()

    _write_canonical(canonical_dir / "2025-01-01_canonical_1s.parquet", [10.0, 9.9])
    pd.DataFrame(
        {
            "timestamp": pd.date_range("2025-01-01 00:00:00", periods=2, freq="1min"),
            **{
                f"loadcell_{idx}_transpiration_g_min_per_plant": [1.25, 2.5]
                for idx in range(1, 7)
            },
        }
    ).to_parquet(
        transpiration_dir / "2025-01-01__transpiration_1m__diff60__g_min_per_plant__p3.parquet",
        index=False,
        engine="pyarrow",
        compression="snappy",
    )

    result = module.main(
        [
            "--canonical-dir",
            str(canonical_dir),
            "--transpiration-1m-dir",
            str(transpiration_dir),
            "--output-dir",
            str(output_dir),
            "--dates",
            "2025-01-01",
        ]
    )

    payload = json.loads((output_dir / "data" / "2025-01-01.json").read_text(encoding="utf-8"))
    assert result == 0
    assert payload["transp1m_mg_min_per_plant"]["values"][0] == [1250, 2500]


def test_build_parser_defaults_match_legacy_contract() -> None:
    module = _load_script_module()

    args = module.build_parser().parse_args([])

    assert args.canonical_dir == Path("data/processed/canonical_1s")
    assert args.transpiration_1m_dir == Path("data/processed/transpiration_1m")
    assert args.output_dir == Path("artifacts/preprocess_compare")
    assert args.plants_per_loadcell == 3
    assert args.max_days == 31
