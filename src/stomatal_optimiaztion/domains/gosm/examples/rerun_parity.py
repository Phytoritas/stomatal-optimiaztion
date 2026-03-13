from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import json

import matplotlib
import numpy as np
import pandas as pd
from scipy.io import loadmat

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from stomatal_optimiaztion.domains.gosm.examples._plotkit import (
    FigureBundleArtifacts,
    apply_axis_theme,
    load_yaml,
    resolve_figure_paths,
)
from stomatal_optimiaztion.domains.gosm.examples.control_figure import (
    PANEL_GROUPS,
    build_control_example_payload,
    compare_control_example_to_legacy_mat,
)
from stomatal_optimiaztion.domains.gosm.examples.sensitivity import (
    run_sensitivity_environmental_conditions,
    run_sensitivity_p_soil_min_conductance_loss,
)
from stomatal_optimiaztion.domains.gosm.examples.sensitivity_figures import (
    DEFAULT_LEGACY_GOSM_EXAMPLE_DIR,
    ETA_NORMALIZER,
    PARAM_METADATA,
)

REPO_ROOT = Path(__file__).resolve().parents[5]
DEFAULT_RERUN_PARITY_OUTPUT_DIR = REPO_ROOT / "out" / "rerun_parity" / "gosm"
DEFAULT_CONTROL_RERUN_PARITY_SPEC_PATH = REPO_ROOT / "configs" / "plotkit" / "gosm" / "control_rerun_parity.yaml"
DEFAULT_SENSITIVITY_RERUN_PARITY_SPEC_PATH = REPO_ROOT / "configs" / "plotkit" / "gosm" / "sensitivity_rerun_parity.yaml"
DEFAULT_CONTROL_RERUN_LEGACY_MAT_PATH = DEFAULT_LEGACY_GOSM_EXAMPLE_DIR / "Example_Growth_Opt__control.mat"

_CONTROL_LEGACY_GROUPS = {
    "panel_a_left": (0, 0),
    "panel_a_right": (0, 1),
    "panel_b_left": (1, 0),
    "panel_c_left": (2, 0),
    "panel_c_right": (2, 1),
    "panel_d_left": (3, 0),
}

_SENSITIVITY_CASES: tuple[dict[str, Any], ...] = (
    {
        "case_id": "rh",
        "title": "RH sensitivity",
        "legacy_mat_name": "Growth_Opt_Stomata__test_sensitivity__RH.mat",
        "mode": "environmental",
        "param": "RH",
    },
    {
        "case_id": "c_a",
        "title": "Atmospheric CO2 sensitivity",
        "legacy_mat_name": "Growth_Opt_Stomata__test_sensitivity__c_a.mat",
        "mode": "environmental",
        "param": "c_a",
    },
    {
        "case_id": "p_soil",
        "title": "Soil water potential sensitivity",
        "legacy_mat_name": "Growth_Opt_Stomata__test_sensitivity__P_soil.mat",
        "mode": "environmental",
        "param": "P_soil",
    },
    {
        "case_id": "p_soil_min_true",
        "title": "Minimum soil water potential, true loss",
        "legacy_mat_name": "Growth_Opt_Stomata__test_sensitivity__P_soil_min__true_k_loss.mat",
        "mode": "p_soil_min",
        "conductance_loss": "true",
    },
    {
        "case_id": "p_soil_min_imag",
        "title": "Minimum soil water potential, imag loss",
        "legacy_mat_name": "Growth_Opt_Stomata__test_sensitivity__P_soil_min__imag_k_loss.mat",
        "mode": "p_soil_min",
        "conductance_loss": "imag",
        "slow": True,
    },
)


@dataclass(frozen=True)
class GOSMRerunParitySuiteArtifacts:
    control: FigureBundleArtifacts
    rh: FigureBundleArtifacts
    c_a: FigureBundleArtifacts
    p_soil: FigureBundleArtifacts
    p_soil_min_true: FigureBundleArtifacts
    p_soil_min_imag: FigureBundleArtifacts | None = None

    def to_summary(self) -> dict[str, Any]:
        return {
            "control": self.control.to_summary(),
            "rh": self.rh.to_summary(),
            "c_a": self.c_a.to_summary(),
            "p_soil": self.p_soil.to_summary(),
            "p_soil_min_true": self.p_soil_min_true.to_summary(),
            "p_soil_min_imag": None if self.p_soil_min_imag is None else self.p_soil_min_imag.to_summary(),
        }


@dataclass(frozen=True)
class _SensitivityPayload:
    param: str
    x_label: str
    x_ss_mat: np.ndarray
    x_in_mat: np.ndarray
    eta_test: np.ndarray
    steady_state: dict[str, np.ndarray]
    instantaneous: dict[str, np.ndarray]


def _as_1d_float(value: Any) -> np.ndarray:
    return np.asarray(value, dtype=float).reshape(-1)


def _as_2d_float(value: Any) -> np.ndarray:
    array = np.asarray(value, dtype=float)
    if array.ndim == 1:
        return array.reshape(1, -1)
    return array


def _repeat_rows(base: np.ndarray, rows: int) -> np.ndarray:
    return np.repeat(_as_2d_float(base), rows, axis=0)


def _matlab_string(value: Any) -> str:
    array = np.asarray(value)
    if array.shape == ():
        return str(array)
    if array.size == 1:
        return str(array.reshape(()))
    return str(array.squeeze())


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


def _y_limits(values: np.ndarray, *, padding_fraction: float, scale: str) -> tuple[float, float]:
    if scale == "log":
        positive = values[np.isfinite(values) & (values > 0)]
        lower = float(np.nanmin(positive))
        upper = float(np.nanmax(positive))
        return lower * (1.0 - padding_fraction * 0.5), upper * (1.0 + padding_fraction)

    y_min = float(np.nanmin(values))
    y_max = float(np.nanmax(values))
    if np.isclose(y_min, y_max):
        baseline = abs(y_min) if y_min != 0.0 else 1.0
        return y_min - baseline * padding_fraction, y_max + baseline * padding_fraction
    pad = (y_max - y_min) * padding_fraction
    return y_min - pad, y_max + pad


def _control_legacy_group_map(legacy_mat_path: Path) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    mat = loadmat(str(legacy_mat_path))
    y_plot = mat["Y_plot_data"]
    return (
        _as_1d_float(mat["g_c_vect"]),
        {group_name: np.asarray(y_plot[row_idx, col_idx], dtype=float) for group_name, (row_idx, col_idx) in _CONTROL_LEGACY_GROUPS.items()},
    )


def build_control_rerun_parity_frame(
    *,
    legacy_mat_path: Path | None = None,
) -> pd.DataFrame:
    legacy_mat_path = (legacy_mat_path or DEFAULT_CONTROL_RERUN_LEGACY_MAT_PATH).resolve()
    legacy_g_c_vec, legacy_groups = _control_legacy_group_map(legacy_mat_path)
    python_payload = build_control_example_payload()

    records: list[dict[str, Any]] = []
    for group_name, keys in PANEL_GROUPS.items():
        panel_id, axis_name = group_name.rsplit("_", maxsplit=1)
        python_group = python_payload.grouped_arrays()[group_name]
        legacy_group = legacy_groups[group_name]

        for series_idx, key in enumerate(keys):
            for source, g_c_vec, matrix in (
                ("legacy", legacy_g_c_vec, legacy_group),
                ("python", python_payload.g_c_vec, python_group),
            ):
                for x_value, y_value in zip(g_c_vec, matrix[series_idx], strict=True):
                    records.append(
                        {
                            "panel_id": panel_id,
                            "axis": axis_name,
                            "series_key": key,
                            "source": source,
                            "g_c": float(x_value),
                            "value": float(y_value),
                        }
                    )
    return pd.DataFrame.from_records(records)


def render_control_rerun_parity_bundle(
    *,
    legacy_mat_path: Path | None = None,
    output_dir: Path | None = None,
    spec_path: Path | None = None,
) -> FigureBundleArtifacts:
    legacy_mat_path = (legacy_mat_path or DEFAULT_CONTROL_RERUN_LEGACY_MAT_PATH).resolve()
    output_dir = (output_dir or DEFAULT_RERUN_PARITY_OUTPUT_DIR / "control").resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    spec_path = (spec_path or DEFAULT_CONTROL_RERUN_PARITY_SPEC_PATH).resolve()

    spec = load_yaml(spec_path)
    tokens_path = (spec_path.parent / spec["theme"]["tokens"]).resolve()
    tokens = load_yaml(tokens_path)
    frame = build_control_rerun_parity_frame(legacy_mat_path=legacy_mat_path)
    python_payload = build_control_example_payload()
    comparison = compare_control_example_to_legacy_mat(python_payload, legacy_mat_path=legacy_mat_path)
    figure_id = spec["meta"]["id"]
    file_paths = resolve_figure_paths(output_dir, figure_id)

    resolved_spec = deepcopy(spec)
    resolved_spec["data"] = {
        "path": str(file_paths["data_csv"].resolve()),
        "row_count": int(len(frame)),
        "columns": list(frame.columns),
    }
    resolved_spec["meta"]["legacy_mat_path"] = str(legacy_mat_path)

    frame.to_csv(file_paths["data_csv"], index=False)
    file_paths["spec_copy"].write_text(spec_path.read_text(encoding="utf-8"), encoding="utf-8")
    file_paths["resolved_spec"].write_text(json.dumps(resolved_spec, indent=2), encoding="utf-8")
    file_paths["tokens_copy"].write_text(tokens_path.read_text(encoding="utf-8"), encoding="utf-8")

    width_mm = float(spec["figure"]["width_mm"])
    height_mm = float(spec["figure"]["height_mm"])
    dpi = int(spec["export"]["dpi"])
    fig, axes = plt.subplots(
        nrows=len(spec["panels"]),
        ncols=1,
        figsize=(width_mm / 25.4, height_mm / 25.4),
        dpi=dpi,
        facecolor=tokens["figure"]["background"],
        constrained_layout=False,
    )
    fig.subplots_adjust(hspace=float(spec["layout"]["hspace"]), left=0.14, right=0.84, top=0.96, bottom=0.09)

    fonts = tokens["fonts"]
    source_handles: dict[str, Any] = {}
    for idx, (ax, panel_spec) in enumerate(zip(np.atleast_1d(axes), spec["panels"], strict=True)):
        show_xlabels = idx == len(spec["panels"]) - 1
        apply_axis_theme(ax, tokens=tokens, show_xlabels=show_xlabels)
        ax.set_xlim(tuple(spec["x_axis"]["limits"]))
        ax.set_ylabel(panel_spec["left_axis"]["label"], fontsize=fonts["axis_label_size_pt"])
        ax.set_ylim(tuple(panel_spec["left_axis"]["limits"]))
        ax.set_yscale(panel_spec["left_axis"]["scale"])
        if show_xlabels:
            ax.set_xlabel(spec["x_axis"]["label"], fontsize=fonts["axis_label_size_pt"])

        left_handles: list[Any] = []
        left_labels: list[str] = []
        panel_frame = frame[(frame["panel_id"] == panel_spec["id"]) & (frame["axis"] == "left")]
        for series_spec in panel_spec["left_axis"]["series"]:
            for source in ("legacy", "python"):
                source_spec = spec["styling"]["sources"][source]
                sub = panel_frame[
                    (panel_frame["series_key"] == series_spec["key"])
                    & (panel_frame["source"] == source)
                ].sort_values("g_c")
                line = ax.plot(
                    sub["g_c"],
                    sub["value"],
                    color=series_spec["color"],
                    linestyle=source_spec["linestyle"],
                    linewidth=float(series_spec["linewidth_pt"]),
                    alpha=float(source_spec["alpha"]),
                )[0]
                source_handles.setdefault(source_spec["label"], line)
                if source == "python":
                    left_handles.append(line)
                    left_labels.append(series_spec["label"])

        ax.legend(
            left_handles,
            left_labels,
            loc=panel_spec["left_axis"]["legend_loc"],
            frameon=tokens["legend"]["frameon"],
            fontsize=fonts["legend_size_pt"],
        )

        if panel_spec.get("right_axis"):
            ax_right = ax.twinx()
            apply_axis_theme(ax_right, tokens=tokens, show_xlabels=show_xlabels)
            ax_right.grid(False)
            ax_right.set_ylim(tuple(panel_spec["right_axis"]["limits"]))
            ax_right.set_yscale(panel_spec["right_axis"]["scale"])
            ax_right.set_ylabel(panel_spec["right_axis"]["label"], fontsize=fonts["axis_label_size_pt"])

            right_handles: list[Any] = []
            right_labels: list[str] = []
            panel_frame = frame[(frame["panel_id"] == panel_spec["id"]) & (frame["axis"] == "right")]
            for series_spec in panel_spec["right_axis"]["series"]:
                for source in ("legacy", "python"):
                    source_spec = spec["styling"]["sources"][source]
                    sub = panel_frame[
                        (panel_frame["series_key"] == series_spec["key"])
                        & (panel_frame["source"] == source)
                    ].sort_values("g_c")
                    line = ax_right.plot(
                        sub["g_c"],
                        sub["value"],
                        color=series_spec["color"],
                        linestyle=source_spec["linestyle"],
                        linewidth=float(series_spec["linewidth_pt"]),
                        alpha=float(source_spec["alpha"]),
                    )[0]
                    source_handles.setdefault(source_spec["label"], line)
                    if source == "python":
                        right_handles.append(line)
                        right_labels.append(series_spec["label"])

            ax_right.legend(
                right_handles,
                right_labels,
                loc=panel_spec["right_axis"]["legend_loc"],
                frameon=tokens["legend"]["frameon"],
                fontsize=fonts["legend_size_pt"],
            )

        _panel_label(ax, tokens=tokens, letter=panel_spec["id"])
        ax.set_title(panel_spec["title"], fontsize=fonts["title_size_pt"], loc="left", pad=10)

    source_order = [spec["styling"]["sources"][source]["label"] for source in ("python", "legacy")]
    fig.legend(
        [source_handles[label] for label in source_order],
        source_order,
        loc="center right",
        bbox_to_anchor=(0.98, 0.5),
        frameon=tokens["legend"]["frameon"],
        fontsize=fonts["legend_size_pt"],
    )
    fig.text(0.44, 0.975, spec["meta"]["title"], ha="center", va="center", fontsize=fonts["title_size_pt"] + 2, fontweight="bold")

    fig.savefig(file_paths["png"], dpi=dpi, transparent=spec["export"]["transparent"], facecolor=tokens["figure"]["background"])
    fig.savefig(file_paths["pdf"], dpi=dpi, transparent=spec["export"]["transparent"], facecolor=tokens["figure"]["background"])
    plt.close(fig)

    metadata = {
        "figure_id": figure_id,
        "legacy_mat_path": str(legacy_mat_path),
        "comparison": comparison,
        "outputs": {key: str(path) for key, path in file_paths.items()},
    }
    file_paths["metadata"].write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    return FigureBundleArtifacts(
        output_dir=output_dir,
        data_csv_path=file_paths["data_csv"],
        spec_copy_path=file_paths["spec_copy"],
        resolved_spec_path=file_paths["resolved_spec"],
        tokens_copy_path=file_paths["tokens_copy"],
        metadata_path=file_paths["metadata"],
        png_path=file_paths["png"],
        pdf_path=file_paths["pdf"],
    )


def _sensitivity_payload_from_result(result: dict[str, Any]) -> _SensitivityPayload:
    param = _matlab_string(result["PARAM"]).strip()
    metadata = PARAM_METADATA[param]
    multiplier = float(metadata["multiplier"])
    param_test = _as_2d_float(result["PARAM_TEST"])
    eta_test = _as_1d_float(result["eta_test"])

    if param == "RH":
        x_ss_mat = multiplier * _as_2d_float(result["VPD_ss_test"])
        x_in_mat = multiplier * _as_2d_float(result["VPD_test"])
    else:
        x_ss_mat = multiplier * _repeat_rows(param_test, rows=_as_2d_float(result["g_c_ss_test"]).shape[0])
        x_in_mat = multiplier * _repeat_rows(param_test, rows=eta_test.size)

    return _SensitivityPayload(
        param=param,
        x_label=str(metadata["x_label"]),
        x_ss_mat=x_ss_mat,
        x_in_mat=x_in_mat,
        eta_test=eta_test,
        steady_state={
            "g_c": _as_2d_float(result["g_c_ss_test"]),
            "growth": 1e6 * _as_2d_float(result["G_ss_test"]),
        },
        instantaneous={
            "g_c": _as_2d_float(result["g_c_test"]),
            "growth": 1e6 * _as_2d_float(result["G_test"]),
        },
    )


def build_sensitivity_case_rerun_parity_frame(
    *,
    legacy_mat_path: Path,
    mode: str,
    param: str | None = None,
    conductance_loss: str | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    legacy = loadmat(str(legacy_mat_path))
    legacy_payload = _sensitivity_payload_from_result(legacy)

    if mode == "environmental":
        if param is None:
            raise ValueError("param is required for environmental sensitivity parity rendering")
        python_result = run_sensitivity_environmental_conditions(
            param=param,
            param_test=legacy["PARAM_TEST"],
            eta_test=legacy["eta_test"],
        )
    elif mode == "p_soil_min":
        if conductance_loss is None:
            raise ValueError("conductance_loss is required for P_soil_min sensitivity parity rendering")
        python_result = run_sensitivity_p_soil_min_conductance_loss(
            param_test=legacy["PARAM_TEST"],
            eta_test=legacy["eta_test"],
            conductance_loss=conductance_loss,
        )
    else:
        raise ValueError(f"Unknown sensitivity parity mode: {mode}")

    python_payload = _sensitivity_payload_from_result(python_result)

    records: list[dict[str, Any]] = []
    for source, payload in (("legacy", legacy_payload), ("python", python_payload)):
        for panel_id, metric_key, x_matrix, y_matrix in (
            ("g_c_steady_state", "g_c", payload.x_ss_mat, payload.steady_state["g_c"]),
            ("growth_steady_state", "growth", payload.x_ss_mat, payload.steady_state["growth"]),
            ("g_c_instantaneous", "g_c", payload.x_in_mat, payload.instantaneous["g_c"]),
            ("growth_instantaneous", "growth", payload.x_in_mat, payload.instantaneous["growth"]),
        ):
            for line_idx in range(y_matrix.shape[0]):
                for x_value, y_value in zip(x_matrix[line_idx], y_matrix[line_idx], strict=True):
                    records.append(
                        {
                            "panel_id": panel_id,
                            "metric": metric_key,
                            "source": source,
                            "line_index": line_idx,
                            "eta_factor": None if "steady" in panel_id else float(payload.eta_test[line_idx] / ETA_NORMALIZER),
                            "x": float(x_value),
                            "y": float(y_value),
                        }
                    )

    diff_summary = {
        "g_c_steady_state": float(np.nanmax(np.abs(python_payload.steady_state["g_c"] - legacy_payload.steady_state["g_c"]))),
        "growth_steady_state": float(np.nanmax(np.abs(python_payload.steady_state["growth"] - legacy_payload.steady_state["growth"]))),
        "g_c_instantaneous": float(np.nanmax(np.abs(python_payload.instantaneous["g_c"] - legacy_payload.instantaneous["g_c"]))),
        "growth_instantaneous": float(np.nanmax(np.abs(python_payload.instantaneous["growth"] - legacy_payload.instantaneous["growth"]))),
    }
    return pd.DataFrame.from_records(records), {
        "x_label": legacy_payload.x_label,
        "param": legacy_payload.param,
        "diff_summary": diff_summary,
        "eta_factors": [float(value / ETA_NORMALIZER) for value in legacy_payload.eta_test],
    }


def render_sensitivity_case_rerun_parity_bundle(
    *,
    legacy_mat_path: Path,
    case_id: str,
    case_title: str,
    mode: str,
    param: str | None = None,
    conductance_loss: str | None = None,
    output_dir: Path | None = None,
    spec_path: Path | None = None,
) -> FigureBundleArtifacts:
    output_dir = (output_dir or DEFAULT_RERUN_PARITY_OUTPUT_DIR / case_id).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    spec_path = (spec_path or DEFAULT_SENSITIVITY_RERUN_PARITY_SPEC_PATH).resolve()
    legacy_mat_path = legacy_mat_path.resolve()

    spec = load_yaml(spec_path)
    tokens_path = (spec_path.parent / spec["theme"]["tokens"]).resolve()
    tokens = load_yaml(tokens_path)
    frame, info = build_sensitivity_case_rerun_parity_frame(
        legacy_mat_path=legacy_mat_path,
        mode=mode,
        param=param,
        conductance_loss=conductance_loss,
    )
    figure_id = f"{spec['meta']['id']}_{case_id}"
    file_paths = resolve_figure_paths(output_dir, figure_id)

    resolved_spec = deepcopy(spec)
    resolved_spec["meta"]["title"] = f"{spec['meta']['title']} ({case_title})"
    resolved_spec["meta"]["legacy_mat_path"] = str(legacy_mat_path)
    resolved_spec["x_axis"] = {"label": info["x_label"]}
    resolved_spec["data"] = {
        "path": str(file_paths["data_csv"].resolve()),
        "row_count": int(len(frame)),
        "columns": list(frame.columns),
    }
    for panel_id in spec["panel_order"]:
        panel_frame = frame[frame["panel_id"] == panel_id]
        resolved_spec["panels"][panel_id]["resolved_y_limits"] = list(
            _y_limits(
                panel_frame["y"].to_numpy(dtype=float),
                padding_fraction=float(spec["panels"][panel_id].get("y_padding_fraction", 0.08)),
                scale=str(spec["panels"][panel_id]["scale"]),
            )
        )

    frame.to_csv(file_paths["data_csv"], index=False)
    file_paths["spec_copy"].write_text(spec_path.read_text(encoding="utf-8"), encoding="utf-8")
    file_paths["resolved_spec"].write_text(json.dumps(resolved_spec, indent=2), encoding="utf-8")
    file_paths["tokens_copy"].write_text(tokens_path.read_text(encoding="utf-8"), encoding="utf-8")

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
    fig.subplots_adjust(left=0.10, right=0.83, bottom=0.12, top=0.90, hspace=float(spec["layout"]["hspace"]), wspace=float(spec["layout"]["wspace"]))

    source_styles = spec["styling"]["source_styles"]
    source_handles: dict[str, Any] = {}
    eta_handles: dict[str, Any] = {}
    fonts = tokens["fonts"]
    panel_letters = iter("abcd")
    for idx, (ax, panel_id) in enumerate(zip(np.atleast_1d(axes).reshape(-1), spec["panel_order"], strict=True)):
        panel_spec = spec["panels"][panel_id]
        panel_frame = frame[frame["panel_id"] == panel_id]
        show_xlabels = idx >= 2
        apply_axis_theme(ax, tokens=tokens, show_xlabels=show_xlabels)
        ax.set_title(panel_spec["title"], fontsize=fonts["title_size_pt"], loc="left", pad=6)
        ax.set_ylabel(panel_spec["y_label"], fontsize=fonts["axis_label_size_pt"])
        if show_xlabels:
            ax.set_xlabel(info["x_label"], fontsize=fonts["axis_label_size_pt"])
        ax.set_yscale(panel_spec["scale"])
        ax.set_ylim(resolved_spec["panels"][panel_id]["resolved_y_limits"])
        ax.set_xlim(
            float(panel_frame["x"].min()),
            float(panel_frame["x"].max()),
        )

        if "steady" in panel_id:
            for source in ("legacy", "python"):
                source_spec = source_styles[source]
                sub = panel_frame[panel_frame["source"] == source].sort_values("x")
                handle = ax.plot(
                    sub["x"],
                    sub["y"],
                    color=source_spec["color"],
                    linestyle=source_spec["linestyle"],
                    linewidth=float(spec["styling"]["steady_state_linewidth_pt"]),
                    alpha=float(source_spec["alpha"]),
                )[0]
                source_handles.setdefault(source_spec["label"], handle)
        else:
            eta_values = sorted(value for value in panel_frame["eta_factor"].dropna().unique())
            colors = plt.get_cmap(spec["styling"]["instantaneous_cmap"])(np.linspace(0.25, 0.85, len(eta_values)))
            for color, eta_value in zip(colors, eta_values, strict=True):
                eta_label = f"eta={eta_value:.3f}"
                for source in ("legacy", "python"):
                    source_spec = source_styles[source]
                    sub = panel_frame[
                        (panel_frame["source"] == source)
                        & (np.isclose(panel_frame["eta_factor"], eta_value))
                    ].sort_values("x")
                    handle = ax.plot(
                        sub["x"],
                        sub["y"],
                        color=color,
                        linestyle=source_spec["linestyle"],
                        linewidth=float(spec["styling"]["instantaneous_linewidth_pt"]),
                        alpha=float(source_spec["alpha"]),
                    )[0]
                    source_handles.setdefault(source_spec["label"], handle)
                    eta_handles.setdefault(eta_label, handle)

        _panel_label(ax, tokens=tokens, letter=next(panel_letters))

    source_order = [source_styles[source]["label"] for source in ("python", "legacy")]
    fig.legend(
        [source_handles[label] for label in source_order],
        source_order,
        loc="upper right",
        bbox_to_anchor=(0.985, 0.95),
        frameon=tokens["legend"]["frameon"],
        fontsize=fonts["legend_size_pt"],
    )
    eta_order = sorted(eta_handles)
    fig.legend(
        [eta_handles[label] for label in eta_order],
        eta_order,
        loc="center right",
        bbox_to_anchor=(0.995, 0.40),
        frameon=tokens["legend"]["frameon"],
        fontsize=fonts["legend_size_pt"] - 0.4,
    )
    fig.text(0.44, 0.965, resolved_spec["meta"]["title"], ha="center", va="center", fontsize=fonts["title_size_pt"] + 2, fontweight="bold")

    fig.savefig(file_paths["png"], dpi=dpi, transparent=spec["export"]["transparent"], facecolor=tokens["figure"]["background"])
    fig.savefig(file_paths["pdf"], dpi=dpi, transparent=spec["export"]["transparent"], facecolor=tokens["figure"]["background"])
    plt.close(fig)

    metadata = {
        "figure_id": figure_id,
        "case_id": case_id,
        "legacy_mat_path": str(legacy_mat_path),
        "param": info["param"],
        "diff_summary": info["diff_summary"],
        "outputs": {key: str(path) for key, path in file_paths.items()},
    }
    file_paths["metadata"].write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    return FigureBundleArtifacts(
        output_dir=output_dir,
        data_csv_path=file_paths["data_csv"],
        spec_copy_path=file_paths["spec_copy"],
        resolved_spec_path=file_paths["resolved_spec"],
        tokens_copy_path=file_paths["tokens_copy"],
        metadata_path=file_paths["metadata"],
        png_path=file_paths["png"],
        pdf_path=file_paths["pdf"],
    )


def render_rerun_parity_suite(
    *,
    output_dir: Path | None = None,
    include_slow_imag: bool = False,
) -> GOSMRerunParitySuiteArtifacts:
    output_dir = (output_dir or DEFAULT_RERUN_PARITY_OUTPUT_DIR).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    bundles: dict[str, FigureBundleArtifacts | None] = {
        "control": render_control_rerun_parity_bundle(output_dir=output_dir / "control"),
    }
    for case in _SENSITIVITY_CASES:
        if case.get("slow", False) and not include_slow_imag:
            bundles[case["case_id"]] = None
            continue
        bundles[case["case_id"]] = render_sensitivity_case_rerun_parity_bundle(
            legacy_mat_path=DEFAULT_LEGACY_GOSM_EXAMPLE_DIR / case["legacy_mat_name"],
            case_id=case["case_id"],
            case_title=case["title"],
            mode=case["mode"],
            param=case.get("param"),
            conductance_loss=case.get("conductance_loss"),
            output_dir=output_dir / case["case_id"],
        )

    return GOSMRerunParitySuiteArtifacts(
        control=bundles["control"],
        rh=bundles["rh"],
        c_a=bundles["c_a"],
        p_soil=bundles["p_soil"],
        p_soil_min_true=bundles["p_soil_min_true"],
        p_soil_min_imag=bundles["p_soil_min_imag"],
    )
