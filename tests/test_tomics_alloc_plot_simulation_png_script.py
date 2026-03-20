from __future__ import annotations

import builtins
import importlib.util
from pathlib import Path
import sys

import pandas as pd
import pytest


def _script_path() -> Path:
    return Path(__file__).resolve().parents[1] / "scripts" / "plot_simulation_png.py"


def _load_script_module():
    spec = importlib.util.spec_from_file_location("plot_simulation_png_script", _script_path())
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load plot_simulation_png.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_plot_simulation_script_main_subsamples_rows_and_prints_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = _load_script_module()
    input_path = tmp_path / "simulation.csv"
    output_path = tmp_path / "out" / "summary.png"

    pd.DataFrame(
        {
            "datetime": pd.date_range("2026-01-01", periods=5, freq="6h"),
            "LAI": [1.0, 1.1, 1.2, 1.3, 1.4],
            "total_dry_weight_g_m2": [10, 11, 12, 13, 14],
        }
    ).to_csv(input_path, index=False)

    captured: dict[str, object] = {}

    def fake_plot(df: pd.DataFrame, *, out_path: Path, dpi: int, spec_path: Path) -> None:
        captured["rows"] = len(df)
        captured["datetimes"] = list(df["datetime"])
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
            "--input",
            str(input_path),
            "--output",
            str(output_path),
            "--every",
            "2",
            "--dpi",
            "200",
        ],
    )

    assert module.main() == 0
    assert captured["rows"] == 3
    assert captured["dpi"] == 200
    assert captured["out_path"] == output_path.resolve()
    assert captured["spec_path"] == module.DEFAULT_SIMULATION_SPEC_PATH.resolve()
    assert output_path.exists()
    assert Path(capsys.readouterr().out.strip()) == output_path.resolve()


def test_plot_simulation_script_rejects_empty_input_csv(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_script_module()
    input_path = tmp_path / "empty.csv"
    pd.DataFrame(columns=["datetime"]).to_csv(input_path, index=False)

    monkeypatch.setattr(sys, "argv", [str(_script_path()), "--input", str(input_path)])

    with pytest.raises(ValueError, match="Input CSV is empty"):
        module.main()


def test_plot_simulation_script_plot_raises_helpful_error_without_matplotlib(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_script_module()
    df = pd.DataFrame({"datetime": pd.date_range("2026-01-01", periods=2, freq="6h"), "LAI": [1.0, 1.1]})
    out_path = tmp_path / "summary.png"
    real_import = builtins.__import__

    def fake_import(name: str, globals=None, locals=None, fromlist=(), level: int = 0):
        if name.startswith("matplotlib"):
            raise ModuleNotFoundError("No module named 'matplotlib'")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    with pytest.raises(ModuleNotFoundError, match="Plotkit-style rendering requires matplotlib"):
        module._plot(
            df,
            out_path=out_path,
            dpi=160,
            spec_path=module.DEFAULT_SIMULATION_SPEC_PATH.resolve(),
        )
