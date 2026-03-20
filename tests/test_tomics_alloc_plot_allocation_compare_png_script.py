from __future__ import annotations

import builtins
import importlib.util
from pathlib import Path
import sys

import pandas as pd
import pytest


def _script_path() -> Path:
    return Path(__file__).resolve().parents[1] / "scripts" / "plot_allocation_compare_png.py"


def _load_script_module():
    spec = importlib.util.spec_from_file_location("plot_allocation_compare_png_script", _script_path())
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load plot_allocation_compare_png.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_alloc_csv(path: Path, *, timestamps: list[str], fruit: list[float]) -> None:
    pd.DataFrame(
        {
            "datetime": timestamps,
            "alloc_frac_fruit": fruit,
            "alloc_frac_leaf": [0.2] * len(timestamps),
            "alloc_frac_stem": [0.3] * len(timestamps),
            "alloc_frac_root": [0.4] * len(timestamps),
        }
    ).to_csv(path, index=False)


def test_plot_allocation_compare_script_reads_and_renames_alloc_columns(tmp_path: Path) -> None:
    module = _load_script_module()
    input_path = tmp_path / "baseline.csv"
    _write_alloc_csv(
        input_path,
        timestamps=["2026-01-01T12:00:00", "2026-01-01T00:00:00"],
        fruit=[0.6, 0.4],
    )

    out = module._read_alloc_csv(input_path, suffix="__baseline")

    assert list(out.columns) == [
        "datetime",
        "alloc_frac_fruit__baseline",
        "alloc_frac_leaf__baseline",
        "alloc_frac_stem__baseline",
        "alloc_frac_root__baseline",
    ]
    assert out["datetime"].tolist() == [
        pd.Timestamp("2026-01-01 00:00:00"),
        pd.Timestamp("2026-01-01 12:00:00"),
    ]


def test_plot_allocation_compare_script_main_merges_subsamples_and_prints_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = _load_script_module()
    baseline_path = tmp_path / "baseline.csv"
    candidate_path = tmp_path / "candidate.csv"
    output_path = tmp_path / "out" / "alloc.png"
    timestamps = [
        "2026-01-01T00:00:00",
        "2026-01-01T06:00:00",
        "2026-01-01T12:00:00",
        "2026-01-01T18:00:00",
    ]
    _write_alloc_csv(baseline_path, timestamps=timestamps, fruit=[0.1, 0.2, 0.3, 0.4])
    _write_alloc_csv(candidate_path, timestamps=timestamps, fruit=[0.2, 0.3, 0.4, 0.5])

    captured: dict[str, object] = {}

    def fake_plot(
        merged: pd.DataFrame,
        *,
        baseline_label: str,
        candidate_label: str,
        out_path: Path,
        dpi: int,
        spec_path: Path,
    ) -> None:
        captured["rows"] = len(merged)
        captured["baseline_label"] = baseline_label
        captured["candidate_label"] = candidate_label
        captured["out_path"] = out_path
        captured["dpi"] = dpi
        captured["spec_path"] = spec_path
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text("fake-png", encoding="utf-8")

    monkeypatch.setattr(module, "_plot", fake_plot)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            str(_script_path()),
            "--baseline",
            str(baseline_path),
            "--candidate",
            str(candidate_path),
            "--baseline-label",
            "baseline-run",
            "--candidate-label",
            "candidate-run",
            "--output",
            str(output_path),
            "--every",
            "2",
            "--dpi",
            "210",
        ],
    )

    assert module.main() == 0
    assert captured == {
        "rows": 2,
        "baseline_label": "baseline-run",
        "candidate_label": "candidate-run",
        "out_path": output_path.resolve(),
        "dpi": 210,
        "spec_path": module.DEFAULT_ALLOCATION_COMPARE_SPEC_PATH.resolve(),
    }
    assert output_path.exists()
    assert Path(capsys.readouterr().out.strip()) == output_path.resolve()


def test_plot_allocation_compare_script_rejects_non_overlapping_datetimes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_script_module()
    baseline_path = tmp_path / "baseline.csv"
    candidate_path = tmp_path / "candidate.csv"
    _write_alloc_csv(baseline_path, timestamps=["2026-01-01T00:00:00"], fruit=[0.2])
    _write_alloc_csv(candidate_path, timestamps=["2026-01-02T00:00:00"], fruit=[0.3])

    monkeypatch.setattr(
        sys,
        "argv",
        [
            str(_script_path()),
            "--baseline",
            str(baseline_path),
            "--candidate",
            str(candidate_path),
        ],
    )

    with pytest.raises(ValueError, match="No overlapping datetime rows"):
        module.main()


def test_plot_allocation_compare_script_plot_raises_helpful_error_without_matplotlib(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_script_module()
    merged = pd.DataFrame(
        {
            "datetime": pd.date_range("2026-01-01", periods=2, freq="6h"),
            "alloc_frac_fruit__baseline": [0.1, 0.2],
            "alloc_frac_leaf__baseline": [0.2, 0.3],
            "alloc_frac_stem__baseline": [0.3, 0.4],
            "alloc_frac_root__baseline": [0.4, 0.5],
            "alloc_frac_fruit__candidate": [0.2, 0.3],
            "alloc_frac_leaf__candidate": [0.3, 0.4],
            "alloc_frac_stem__candidate": [0.4, 0.5],
            "alloc_frac_root__candidate": [0.5, 0.6],
        }
    )
    out_path = tmp_path / "alloc.png"
    real_import = builtins.__import__

    def fake_import(name: str, globals=None, locals=None, fromlist=(), level: int = 0):
        if name.startswith("matplotlib"):
            raise ModuleNotFoundError("No module named 'matplotlib'")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    with pytest.raises(ModuleNotFoundError, match="Plotkit-style rendering requires matplotlib"):
        module._plot(
            merged,
            baseline_label="baseline",
            candidate_label="candidate",
            out_path=out_path,
            dpi=170,
            spec_path=module.DEFAULT_ALLOCATION_COMPARE_SPEC_PATH.resolve(),
        )
