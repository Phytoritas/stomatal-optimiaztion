from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from stomatal_optimiaztion.domains.tdgm.examples.adapter import (
    DEFAULT_LEGACY_TDGM_THORP_G_DIR,
)
from stomatal_optimiaztion.domains.tdgm.thorp_g import default_params, load_mat, run
from stomatal_optimiaztion.shared_plotkit import (
    FigureBundleArtifacts,
    apply_axis_theme,
    load_yaml,
    resolve_figure_paths,
)

REPO_ROOT = Path(__file__).resolve().parents[5]
DEFAULT_RERUN_PARITY_OUTPUT_DIR = REPO_ROOT / "out" / "rerun_parity" / "tdgm"
DEFAULT_RERUN_PARITY_SPEC_PATH = REPO_ROOT / "configs" / "plotkit" / "tdgm" / "rerun_parity_case.yaml"

TDGM_RERUN_CASES: tuple[tuple[str, float, float, float], ...] = (
    ("THORP_data_Control_Turgor.mat", 1.0, 1.0, 0.0),
    ("THORP_data_0.9RH_Turgor.mat", 0.9, 1.0, 0.0),
    ("THORP_data_0.8RH_Turgor.mat", 0.8, 1.0, 0.0),
    ("THORP_data_0.9Prec_Turgor.mat", 1.0, 0.9, 0.0),
    ("THORP_data_0.8Prec_Turgor.mat", 1.0, 0.8, 0.0),
    ("THORP_data_0.9Prec_0.9RH_Turgor.mat", 0.9, 0.9, 0.0),
    ("THORP_data_Control_Turgor_Gamma_minus_0.1MPa.mat", 1.0, 1.0, -0.1),
    ("THORP_data_Control_Turgor_Gamma_minus_0.05MPa.mat", 1.0, 1.0, -0.05),
    ("THORP_data_Control_Turgor_Gamma_plus_0.05MPa.mat", 1.0, 1.0, 0.05),
    ("THORP_data_Control_Turgor_Gamma_plus_0.1MPa.mat", 1.0, 1.0, 0.1),
)

_METRICS: dict[str, dict[str, Any]] = {
    "height": {"legacy_key": "H_stor", "factor": 1.0},
    "diameter": {"legacy_key": "D_stor", "factor": 1.0},
    "assimilation": {"legacy_key": "A_n_stor", "factor": 1e6},
    "transpiration": {"legacy_key": "E_stor", "factor": 1e3},
}


@dataclass(frozen=True)
class TDGMRerunParitySuiteArtifacts:
    cases: dict[str, FigureBundleArtifacts]

    def to_summary(self) -> dict[str, Any]:
        return {case_id: artifacts.to_summary() for case_id, artifacts in self.cases.items()}


def _as_1d(values: object) -> np.ndarray:
    return np.asarray(values, dtype=float).reshape(-1)


def _case_label(mat_name: str) -> str:
    stem = Path(mat_name).stem
    return stem.replace("THORP_data_", "").replace("_", " ")


def _panel_label(ax: Any, *, tokens: dict[str, Any], letter: str) -> None:
    panel_tokens = tokens["panel_labels"]
    fonts = tokens["fonts"]
    ax.text(
        panel_tokens["x"],
        panel_tokens["y"],
        f"{panel_tokens['prefix']}{letter}{panel_tokens['suffix']}",
        transform=ax.transAxes,
        ha=panel_tokens["ha"],
        va=panel_tokens["va"],
        fontsize=fonts["panel_label_size_pt"],
        fontweight=fonts["weight_labels"],
    )


def _y_limits(values: np.ndarray, *, padding_fraction: float) -> tuple[float, float]:
    y_min = float(np.nanmin(values))
    y_max = float(np.nanmax(values))
    if np.isclose(y_min, y_max):
        baseline = abs(y_min) if y_min != 0.0 else 1.0
        return y_min - baseline * padding_fraction, y_max + baseline * padding_fraction
    pad = (y_max - y_min) * padding_fraction
    return y_min - pad, y_max + pad


def _resolve_case_params(mat_name: str) -> tuple[float, float, float]:
    for case_name, rh_scale, precip_scale, gamma_shift in TDGM_RERUN_CASES:
        if case_name == mat_name:
            return rh_scale, precip_scale, gamma_shift
    raise KeyError(f"Unknown TDGM rerun parity case: {mat_name}")


def build_case_rerun_parity_frame(
    *,
    legacy_mat_path: Path,
    max_steps: int = 60,
) -> pd.DataFrame:
    legacy_mat_path = legacy_mat_path.resolve()
    legacy = load_mat(legacy_mat_path)
    rh_scale, precip_scale, gamma_shift = _resolve_case_params(legacy_mat_path.name)
    params0 = default_params(
        forcing_repeat_q=1,
        forcing_rh_scale=rh_scale,
        forcing_precip_scale=precip_scale,
    )
    params = replace(params0, gamma_turgor_shift=float(gamma_shift))
    python_out = run(params=params, max_steps=max_steps).as_mat_dict()

    records: list[dict[str, Any]] = []
    for panel_id, metric in _METRICS.items():
        legacy_time = _as_1d(legacy["t_stor"]) / (24.0 * 3600.0)
        python_time = _as_1d(python_out["t_stor"]) / (24.0 * 3600.0)
        legacy_values = metric["factor"] * _as_1d(legacy[metric["legacy_key"]])[: legacy_time.size]
        python_values = metric["factor"] * _as_1d(python_out[metric["legacy_key"]])[: python_time.size]

        for source, time_vec, value_vec in (
            ("legacy", legacy_time, legacy_values),
            ("python", python_time, python_values),
        ):
            for x_value, y_value in zip(time_vec, value_vec, strict=True):
                records.append(
                    {
                        "panel_id": panel_id,
                        "source": source,
                        "time_day": float(x_value),
                        "value": float(y_value),
                    }
                )
    return pd.DataFrame.from_records(records)


def render_case_rerun_parity_bundle(
    *,
    legacy_mat_path: Path,
    output_dir: Path | None = None,
    spec_path: Path | None = None,
    max_steps: int = 60,
) -> FigureBundleArtifacts:
    legacy_mat_path = legacy_mat_path.resolve()
    case_id = legacy_mat_path.stem.lower()
    output_dir = (output_dir or DEFAULT_RERUN_PARITY_OUTPUT_DIR / case_id).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    spec_path = (spec_path or DEFAULT_RERUN_PARITY_SPEC_PATH).resolve()

    spec = load_yaml(spec_path)
    tokens_path = (spec_path.parent / spec["theme"]["tokens"]).resolve()
    tokens = load_yaml(tokens_path)
    frame = build_case_rerun_parity_frame(legacy_mat_path=legacy_mat_path, max_steps=max_steps)
    figure_id = f"{spec['meta']['id']}_{case_id}"
    file_paths = resolve_figure_paths(output_dir, figure_id)

    diff_summary: dict[str, dict[str, Any]] = {}
    resolved_title = f"{spec['meta']['title']} ({_case_label(legacy_mat_path.name)})"
    resolved_y_limits: dict[str, tuple[float, float]] = {}

    for panel_id in spec["panel_order"]:
        panel_frame = frame[frame["panel_id"] == panel_id]
        pivot = (
            panel_frame.pivot_table(index="time_day", columns="source", values="value")
            .reset_index()
            .sort_values("time_day")
        )
        diff_summary[panel_id] = {
            "max_abs_diff": float(np.nanmax(np.abs(pivot["python"] - pivot["legacy"]))),
        }
        resolved_y_limits[panel_id] = _y_limits(
            panel_frame["value"].to_numpy(dtype=float),
            padding_fraction=float(spec["panels"][panel_id].get("y_padding_fraction", 0.08)),
        )

    frame.to_csv(file_paths["data_csv"], index=False)
    for extra_key in ("spec_copy", "resolved_spec", "tokens_copy", "metadata", "pdf"):
        file_paths[extra_key].unlink(missing_ok=True)

    width_mm = float(spec["figure"]["width_mm"])
    height_mm = float(spec["figure"]["height_mm"])
    dpi = int(spec["export"]["dpi"])
    fig, axes = plt.subplots(
        spec["layout"]["rows"],
        spec["layout"]["cols"],
        figsize=(width_mm / 25.4, height_mm / 25.4),
        dpi=dpi,
        facecolor=tokens["figure"]["background"],
        constrained_layout=False,
    )
    fig.subplots_adjust(left=0.10, right=0.84, bottom=0.12, top=0.90, hspace=float(spec["layout"]["hspace"]), wspace=float(spec["layout"]["wspace"]))

    handles: dict[str, Any] = {}
    fonts = tokens["fonts"]
    for ax, panel_id, letter in zip(np.atleast_1d(axes).reshape(-1), spec["panel_order"], "abcd", strict=True):
        panel_spec = spec["panels"][panel_id]
        panel_frame = frame[frame["panel_id"] == panel_id]
        apply_axis_theme(ax, tokens=tokens, show_xlabels=True)
        ax.set_title(panel_spec["title"], fontsize=fonts["title_size_pt"], loc="left", pad=6)
        ax.set_xlabel(panel_spec["x_label"], fontsize=fonts["axis_label_size_pt"])
        ax.set_ylabel(panel_spec["y_label"], fontsize=fonts["axis_label_size_pt"])
        ax.set_yscale(panel_spec["scale"])
        ax.set_xlim(float(panel_frame["time_day"].min()) - 0.5, float(panel_frame["time_day"].max()) + 0.5)
        ax.set_ylim(resolved_y_limits[panel_id])

        for source in ("legacy", "python"):
            source_spec = spec["styling"]["sources"][source]
            sub = panel_frame[panel_frame["source"] == source].sort_values("time_day")
            handle = ax.plot(
                sub["time_day"],
                sub["value"],
                color=source_spec["color"],
                linestyle=source_spec["linestyle"],
                marker=source_spec["marker"],
                linewidth=float(source_spec["linewidth_pt"]),
                label=source_spec["label"],
            )[0]
            handles.setdefault(source_spec["label"], handle)

        _panel_label(ax, tokens=tokens, letter=letter)

    legend_order = [spec["styling"]["sources"][source]["label"] for source in ("python", "legacy")]
    fig.legend(
        [handles[label] for label in legend_order],
        legend_order,
        loc="center right",
        bbox_to_anchor=(0.985, 0.5),
        frameon=tokens["legend"]["frameon"],
        fontsize=fonts["legend_size_pt"],
    )
    fig.text(0.43, 0.965, resolved_title, ha="center", va="center", fontsize=fonts["title_size_pt"] + 2, fontweight="bold")

    fig.savefig(file_paths["png"], dpi=dpi, transparent=spec["export"]["transparent"], facecolor=tokens["figure"]["background"])
    plt.close(fig)
    return FigureBundleArtifacts(
        output_dir=output_dir,
        data_csv_path=file_paths["data_csv"],
        png_path=file_paths["png"],
    )


def render_rerun_parity_suite(
    *,
    output_dir: Path | None = None,
    case_names: list[str] | None = None,
) -> TDGMRerunParitySuiteArtifacts:
    output_dir = (output_dir or DEFAULT_RERUN_PARITY_OUTPUT_DIR).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    selected_names = case_names or [case_name for case_name, *_ in TDGM_RERUN_CASES]
    cases: dict[str, FigureBundleArtifacts] = {}
    for case_name in selected_names:
        legacy_mat_path = DEFAULT_LEGACY_TDGM_THORP_G_DIR / case_name
        cases[Path(case_name).stem.lower()] = render_case_rerun_parity_bundle(
            legacy_mat_path=legacy_mat_path,
            output_dir=output_dir / Path(case_name).stem.lower(),
        )
    return TDGMRerunParitySuiteArtifacts(cases=cases)
