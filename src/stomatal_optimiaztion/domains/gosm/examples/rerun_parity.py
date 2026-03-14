from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import matplotlib
import numpy as np
import pandas as pd
from scipy.io import loadmat

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

from stomatal_optimiaztion.domains.gosm.examples.control import run_control_plot_data
from stomatal_optimiaztion.domains.gosm.examples.sensitivity import (
    run_sensitivity_environmental_conditions,
    run_sensitivity_p_soil_min_conductance_loss,
)
from stomatal_optimiaztion.domains.gosm.params import BaselineInputs
from stomatal_optimiaztion.shared_plotkit import (
    FigureBundleArtifacts,
    apply_axis_theme,
    load_yaml,
    resolve_figure_paths,
)

REPO_ROOT = Path(__file__).resolve().parents[5]
WORKSPACE_ROOT = REPO_ROOT.parents[1]
DEFAULT_LEGACY_GOSM_EXAMPLE_DIR = WORKSPACE_ROOT / "00. Stomatal Optimization" / "GOSM" / "example"
DEFAULT_RERUN_PARITY_OUTPUT_DIR = REPO_ROOT / "out" / "rerun_parity" / "gosm"
DEFAULT_CONTROL_RERUN_PARITY_SPEC_PATH = REPO_ROOT / "configs" / "plotkit" / "gosm" / "control_rerun_parity.yaml"
DEFAULT_SENSITIVITY_RERUN_PARITY_SPEC_PATH = REPO_ROOT / "configs" / "plotkit" / "gosm" / "sensitivity_rerun_parity.yaml"
DEFAULT_CONTROL_RERUN_LEGACY_MAT_PATH = DEFAULT_LEGACY_GOSM_EXAMPLE_DIR / "Example_Growth_Opt__control.mat"

PANEL_GROUPS: dict[str, tuple[str, ...]] = {
    "panel_a_left": ("g0_umol_c_s", "g_umol_c_s"),
    "panel_a_right": ("c_nsc_mol",),
    "panel_b_left": ("a_n_umol_m2_s", "e_mmol_m2_s"),
    "panel_c_left": ("t_l_c",),
    "panel_c_right": ("vpd_kpa",),
    "panel_d_left": ("neg_psi_l_mpa", "neg_psi_s_mpa", "neg_psi_rc_mpa"),
}
_CONTROL_LEGACY_GROUPS = {
    "panel_a_left": (0, 0),
    "panel_a_right": (0, 1),
    "panel_b_left": (1, 0),
    "panel_c_left": (2, 0),
    "panel_c_right": (2, 1),
    "panel_d_left": (3, 0),
}
ETA_NORMALIZER = 1.0 - BaselineInputs.matlab_default().f_c
PARAM_METADATA = {
    "RH": {
        "x_label": "Vapor pressure deficit (VPD), D_L [kPa]",
        "multiplier": 1.0,
    },
    "c_a": {
        "x_label": "Atmospheric CO2 pressure, c_a [Pa]",
        "multiplier": 101.325 * 1e3,
    },
    "P_soil": {
        "x_label": "Soil water potential, -psi_soil [MPa]",
        "multiplier": -1.0,
    },
    "P_soil_min": {
        "x_label": "Minimum experienced soil water potential, -psi_soil^min [MPa]",
        "multiplier": -1.0,
    },
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


def _source_plot_kwargs(
    *,
    source_spec: dict[str, Any],
    base_linewidth: float,
    color: Any,
) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "color": color,
        "linestyle": source_spec["linestyle"],
        "linewidth": base_linewidth * float(source_spec.get("linewidth_scale", 1.0)),
        "alpha": float(source_spec.get("alpha", 1.0)),
        "zorder": float(source_spec.get("zorder", 2.0)),
    }
    marker = source_spec.get("marker")
    if marker:
        kwargs["marker"] = marker
        kwargs["markersize"] = float(source_spec.get("markersize_pt", 3.0))
        kwargs["markevery"] = int(source_spec.get("markevery", 1))
        if "markerfacecolor" in source_spec:
            kwargs["markerfacecolor"] = source_spec["markerfacecolor"]
        if "markeredgecolor" in source_spec:
            kwargs["markeredgecolor"] = source_spec["markeredgecolor"]
        if "markeredgewidth_pt" in source_spec:
            kwargs["markeredgewidth"] = float(source_spec["markeredgewidth_pt"])
    return kwargs


def _source_legend_handle(*, source_spec: dict[str, Any], tokens: dict[str, Any]) -> Line2D:
    legend_color = str(tokens["axes"]["tick_color"])
    return Line2D(
        [0],
        [0],
        label=source_spec["label"],
        **_source_plot_kwargs(
            source_spec=source_spec,
            base_linewidth=1.8,
            color=legend_color,
        ),
    )


def _y_limits(values: np.ndarray, *, padding_fraction: float, scale: str = "linear") -> tuple[float, float]:
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


def _add_diff_columns(diff_frame: pd.DataFrame) -> pd.DataFrame:
    legacy_value = diff_frame["legacy_value"].to_numpy(dtype=float)
    python_value = diff_frame["python_value"].to_numpy(dtype=float)
    same_inf = (
        np.isinf(legacy_value)
        & np.isinf(python_value)
        & (np.signbit(legacy_value) == np.signbit(python_value))
    )
    same_nan = np.isnan(legacy_value) & np.isnan(python_value)
    with np.errstate(invalid="ignore"):
        signed_diff = python_value - legacy_value
    signed_diff[same_inf | same_nan] = 0.0
    diff_frame["signed_diff"] = signed_diff
    diff_frame["abs_diff"] = np.abs(signed_diff)
    return diff_frame


def _load_control_group_map(legacy_mat_path: Path) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    mat = loadmat(str(legacy_mat_path))
    y_plot = mat["Y_plot_data"]
    return (
        _as_1d_float(mat["g_c_vect"]),
        {group_name: np.asarray(y_plot[row_idx, col_idx], dtype=float) for group_name, (row_idx, col_idx) in _CONTROL_LEGACY_GROUPS.items()},
    )


def _python_control_group_map() -> tuple[np.ndarray, dict[str, np.ndarray]]:
    y_plot_data, g_c_vect = run_control_plot_data()
    return (
        _as_1d_float(g_c_vect),
        {group_name: np.asarray(y_plot_data[row_idx, col_idx], dtype=float) for group_name, (row_idx, col_idx) in _CONTROL_LEGACY_GROUPS.items()},
    )


def build_control_rerun_parity_tables(
    *,
    legacy_mat_path: Path | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    legacy_mat_path = (legacy_mat_path or DEFAULT_CONTROL_RERUN_LEGACY_MAT_PATH).resolve()
    legacy_g_c_vec, legacy_groups = _load_control_group_map(legacy_mat_path)
    python_g_c_vec, python_groups = _python_control_group_map()

    def _build_frame(*, g_c_vec: np.ndarray, group_map: dict[str, np.ndarray], source: str) -> pd.DataFrame:
        records: list[dict[str, Any]] = []
        for group_name, keys in PANEL_GROUPS.items():
            panel_id, axis_name = group_name.rsplit("_", maxsplit=1)
            matrix = group_map[group_name]
            for series_idx, key in enumerate(keys):
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

    legacy_frame = _build_frame(g_c_vec=legacy_g_c_vec, group_map=legacy_groups, source="legacy")
    python_frame = _build_frame(g_c_vec=python_g_c_vec, group_map=python_groups, source="python")
    diff_frame = (
        legacy_frame.drop(columns="source")
        .rename(columns={"value": "legacy_value"})
        .merge(
            python_frame.drop(columns="source").rename(columns={"value": "python_value"}),
            on=["panel_id", "axis", "series_key", "g_c"],
            how="outer",
            validate="one_to_one",
        )
        .sort_values(["panel_id", "axis", "series_key", "g_c"])
        .reset_index(drop=True)
    )
    return legacy_frame, python_frame, _add_diff_columns(diff_frame)


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
    legacy_frame, python_frame, diff_frame = build_control_rerun_parity_tables(
        legacy_mat_path=legacy_mat_path,
    )
    frame = pd.concat([legacy_frame, python_frame], ignore_index=True)
    figure_id = spec["meta"]["id"]
    file_paths = resolve_figure_paths(output_dir, figure_id)
    python_csv_path = output_dir / f"{figure_id}_python.csv"
    legacy_csv_path = output_dir / f"{figure_id}_legacy.csv"
    diff_csv_path = output_dir / f"{figure_id}_diff.csv"

    legacy_frame.to_csv(legacy_csv_path, index=False)
    python_frame.to_csv(python_csv_path, index=False)
    diff_frame.to_csv(diff_csv_path, index=False)
    for extra_key in ("data_csv", "spec_copy", "resolved_spec", "tokens_copy", "metadata", "pdf"):
        file_paths[extra_key].unlink(missing_ok=True)

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
    source_styles = spec["styling"]["sources"]
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
                source_spec = source_styles[source]
                sub = panel_frame[
                    (panel_frame["series_key"] == series_spec["key"])
                    & (panel_frame["source"] == source)
                ].sort_values("g_c")
                line = ax.plot(
                    sub["g_c"],
                    sub["value"],
                    **_source_plot_kwargs(
                        source_spec=source_spec,
                        base_linewidth=float(series_spec["linewidth_pt"]),
                        color=series_spec["color"],
                    ),
                )[0]
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
                    source_spec = source_styles[source]
                    sub = panel_frame[
                        (panel_frame["series_key"] == series_spec["key"])
                        & (panel_frame["source"] == source)
                    ].sort_values("g_c")
                    line = ax_right.plot(
                        sub["g_c"],
                        sub["value"],
                        **_source_plot_kwargs(
                            source_spec=source_spec,
                            base_linewidth=float(series_spec["linewidth_pt"]),
                            color=series_spec["color"],
                        ),
                    )[0]
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

    source_order = [source_styles[source]["label"] for source in ("python", "legacy")]
    fig.legend(
        [_source_legend_handle(source_spec=source_styles[source], tokens=tokens) for source in ("python", "legacy")],
        source_order,
        loc="center right",
        bbox_to_anchor=(0.98, 0.5),
        frameon=tokens["legend"]["frameon"],
        fontsize=fonts["legend_size_pt"],
    )
    fig.text(
        0.44,
        0.975,
        spec["meta"]["title"],
        ha="center",
        va="center",
        fontsize=fonts["title_size_pt"] + 2,
        fontweight="bold",
    )

    fig.savefig(
        file_paths["png"],
        dpi=dpi,
        transparent=spec["export"]["transparent"],
        facecolor=tokens["figure"]["background"],
    )
    plt.close(fig)
    return FigureBundleArtifacts(
        output_dir=output_dir,
        png_path=file_paths["png"],
        python_csv_path=python_csv_path,
        legacy_csv_path=legacy_csv_path,
        diff_csv_path=diff_csv_path,
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


def build_sensitivity_case_rerun_parity_tables(
    *,
    legacy_mat_path: Path,
    mode: str,
    param: str | None = None,
    conductance_loss: str | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, Any]]:
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

    def _build_frame(*, payload: _SensitivityPayload, source: str) -> pd.DataFrame:
        records: list[dict[str, Any]] = []
        for panel_id, metric_key, x_matrix, y_matrix in (
            ("g_c_steady_state", "g_c", payload.x_ss_mat, payload.steady_state["g_c"]),
            ("growth_steady_state", "growth", payload.x_ss_mat, payload.steady_state["growth"]),
            ("g_c_instantaneous", "g_c", payload.x_in_mat, payload.instantaneous["g_c"]),
            ("growth_instantaneous", "growth", payload.x_in_mat, payload.instantaneous["growth"]),
        ):
            for line_idx in range(y_matrix.shape[0]):
                eta_factor = None if "steady" in panel_id else float(payload.eta_test[line_idx] / ETA_NORMALIZER)
                for x_value, y_value in zip(x_matrix[line_idx], y_matrix[line_idx], strict=True):
                    records.append(
                        {
                            "panel_id": panel_id,
                            "metric": metric_key,
                            "source": source,
                            "line_index": line_idx,
                            "eta_factor": eta_factor,
                            "x": float(x_value),
                            "y": float(y_value),
                        }
                    )
        return pd.DataFrame.from_records(records)

    legacy_frame = _build_frame(payload=legacy_payload, source="legacy")
    python_frame = _build_frame(payload=python_payload, source="python")
    diff_frame = (
        legacy_frame.drop(columns="source")
        .rename(columns={"y": "legacy_value"})
        .merge(
            python_frame.drop(columns="source").rename(columns={"y": "python_value"}),
            on=["panel_id", "metric", "line_index", "eta_factor", "x"],
            how="outer",
            validate="one_to_one",
        )
        .sort_values(["panel_id", "metric", "line_index", "x"])
        .reset_index(drop=True)
    )
    return legacy_frame, python_frame, _add_diff_columns(diff_frame), {
        "x_label": legacy_payload.x_label,
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
    legacy_frame, python_frame, diff_frame, info = build_sensitivity_case_rerun_parity_tables(
        legacy_mat_path=legacy_mat_path,
        mode=mode,
        param=param,
        conductance_loss=conductance_loss,
    )
    frame = pd.concat([legacy_frame, python_frame], ignore_index=True)
    figure_id = f"{spec['meta']['id']}_{case_id}"
    file_paths = resolve_figure_paths(output_dir, figure_id)
    python_csv_path = output_dir / f"{figure_id}_python.csv"
    legacy_csv_path = output_dir / f"{figure_id}_legacy.csv"
    diff_csv_path = output_dir / f"{figure_id}_diff.csv"

    legacy_frame.to_csv(legacy_csv_path, index=False)
    python_frame.to_csv(python_csv_path, index=False)
    diff_frame.to_csv(diff_csv_path, index=False)
    for extra_key in ("data_csv", "spec_copy", "resolved_spec", "tokens_copy", "metadata", "pdf"):
        file_paths[extra_key].unlink(missing_ok=True)

    resolved_title = f"{spec['meta']['title']} ({case_title})"
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
        ax.set_ylim(
            _y_limits(
                panel_frame["y"].to_numpy(dtype=float),
                padding_fraction=float(panel_spec.get("y_padding_fraction", 0.08)),
                scale=str(panel_spec["scale"]),
            )
        )
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
                    **_source_plot_kwargs(
                        source_spec=source_spec,
                        base_linewidth=float(spec["styling"]["steady_state_linewidth_pt"]),
                        color=source_spec["color"],
                    ),
                )[0]
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
                        **_source_plot_kwargs(
                            source_spec=source_spec,
                            base_linewidth=float(spec["styling"]["instantaneous_linewidth_pt"]),
                            color=color,
                        ),
                    )[0]
                    eta_handles.setdefault(eta_label, handle)

        _panel_label(ax, tokens=tokens, letter=next(panel_letters))

    source_order = [source_styles[source]["label"] for source in ("python", "legacy")]
    fig.legend(
        [_source_legend_handle(source_spec=source_styles[source], tokens=tokens) for source in ("python", "legacy")],
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
    fig.text(0.44, 0.965, resolved_title, ha="center", va="center", fontsize=fonts["title_size_pt"] + 2, fontweight="bold")

    fig.savefig(
        file_paths["png"],
        dpi=dpi,
        transparent=spec["export"]["transparent"],
        facecolor=tokens["figure"]["background"],
    )
    plt.close(fig)
    return FigureBundleArtifacts(
        output_dir=output_dir,
        png_path=file_paths["png"],
        python_csv_path=python_csv_path,
        legacy_csv_path=legacy_csv_path,
        diff_csv_path=diff_csv_path,
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
