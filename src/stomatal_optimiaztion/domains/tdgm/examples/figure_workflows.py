from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import json

import matplotlib
import numpy as np
import pandas as pd
from matplotlib.patches import Patch

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from stomatal_optimiaztion.domains.tdgm.examples.adapter import (
    DEFAULT_LEGACY_POORTER_SCRIPT_PATH,
    DEFAULT_LEGACY_TDGM_OFFLINE_DIR,
    DEFAULT_LEGACY_TDGM_THORP_G_DIR,
    MAX_HEIGHT_FILE_ORDER,
    SOURCE_SINK_FILE_ORDER,
    annual_growth_by_year,
    annual_precipitation_relative,
    annual_soil_moisture_by_year,
    build_thorp_g_stress_groups,
    fit_turgor_allocation_regression,
    height_trace_on_regular_grid,
    load_height_age_reference_envelope,
    load_max_p_minus_pet,
    load_offline_scenario,
    load_poorter_smf_reference_curve,
    load_tao_height_envelope,
    load_thorp_g_scenario,
    phloem_transport_distribution,
    poorter_smf_lookup,
    regress_xylem_potentials,
    surface_soil_moisture_proxy,
    turgor_growth_rate_from_legacy,
)
from stomatal_optimiaztion.shared_plotkit import (
    FigureBundleArtifacts,
    apply_axis_theme,
    frame_digest,
    load_yaml,
    resolve_figure_paths,
)

REPO_ROOT = Path(__file__).resolve().parents[5]
DEFAULT_TDGM_EXAMPLE_OUTPUT_DIR = REPO_ROOT / "out" / "tdgm" / "example_figures"
DEFAULT_TURGOR_ALLOCATION_SPEC_PATH = REPO_ROOT / "configs" / "plotkit" / "tdgm" / "turgor_allocation.yaml"
DEFAULT_TURGOR_WATER_POTENTIAL_SPEC_PATH = REPO_ROOT / "configs" / "plotkit" / "tdgm" / "turgor_water_potentials.yaml"
DEFAULT_TURGOR_GROWTH_SCALING_SPEC_PATH = REPO_ROOT / "configs" / "plotkit" / "tdgm" / "turgor_growth_scaling.yaml"
DEFAULT_MAX_HEIGHT_SPEC_PATH = REPO_ROOT / "configs" / "plotkit" / "tdgm" / "max_height_for_soil.yaml"
DEFAULT_POORTER_SMF_SPEC_PATH = REPO_ROOT / "configs" / "plotkit" / "tdgm" / "poorter_smf.yaml"
DEFAULT_PHLOEM_TRANSPORT_SPEC_PATH = REPO_ROOT / "configs" / "plotkit" / "tdgm" / "phloem_transport.yaml"
DEFAULT_SOURCE_SINK_SPEC_PATH = REPO_ROOT / "configs" / "plotkit" / "tdgm" / "source_vs_sink_growth.yaml"
DEFAULT_THORP_G_GROWTH_SPEC_PATH = REPO_ROOT / "configs" / "plotkit" / "tdgm" / "thorp_g_growth_vs_carbon.yaml"
DEFAULT_THORP_G_PRECIP_SPEC_PATH = REPO_ROOT / "configs" / "plotkit" / "tdgm" / "thorp_g_growth_vs_carbon_precipitation.yaml"
DEFAULT_THORP_G_SOIL_SPEC_PATH = REPO_ROOT / "configs" / "plotkit" / "tdgm" / "thorp_g_growth_vs_carbon_soil_moisture.yaml"
DEFAULT_THORP_G_SOIL_DETRENDED_SPEC_PATH = REPO_ROOT / "configs" / "plotkit" / "tdgm" / "thorp_g_growth_vs_carbon_soil_moisture_detrended.yaml"
DEFAULT_THORP_G_SOIL_VS_CARBON_SPEC_PATH = REPO_ROOT / "configs" / "plotkit" / "tdgm" / "thorp_g_soil_moisture_vs_carbon.yaml"
DEFAULT_THORP_G_HEIGHT_TURGOR_SPEC_PATH = REPO_ROOT / "configs" / "plotkit" / "tdgm" / "thorp_g_height_vs_age_turgor_threshold.yaml"
DEFAULT_THORP_G_HEIGHT_WATERSTRESS_SPEC_PATH = REPO_ROOT / "configs" / "plotkit" / "tdgm" / "thorp_g_height_vs_age_waterstress.yaml"

EXPECTED_FRAME_DIGESTS: dict[str, str | None] = {
    "turgor_allocation": "5f9ae544cb825af44057fa4a5ccbd1bc9394f928a53bfa0a27080091ebe39bec",
    "turgor_water_potential": "1b9610e1cd96bf5d876fb4d81a00a20ad457a69b07c186bc4351e7f82306f631",
    "turgor_growth_scaling": "8e73d7c1f51786f52ab6962758052d82f7050e6e445f77f31a349f5d09efb86f",
    "max_height_for_soil": "c15b654e21d63b2490b187c78cb88bfbc66119255c42251c2a5c9e842fb46590",
    "poorter_smf": "eea79aa16503be96cb3ce9e679fefc3834e3ac388e44737af29b23ca87132072",
    "phloem_transport_04m": "61e4f2213180335f65d029e77c0bfaa39352e171d7a6a457b0f57ec79f8d72a1",
    "phloem_transport_44m": "e468a04ea31830092c90af7a3ec0a024025304c56dc1f2074668baf81547bbf5",
    "source_vs_sink_growth": "a95abe3d3a1bc1c053d4cc1303580e7ebfff74a40354fa12497f95685df07909",
    "thorp_g_growth_vs_carbon": "0938c09c576d223d1dbb920977a89b87432a589ec591c4f32ba1cb848a60150c",
    "thorp_g_growth_vs_carbon_precipitation": "ee8e18e08f0e9c8e7bd351ad1c37ad95307778eaaa119ce4f936350798042b0b",
    "thorp_g_growth_vs_carbon_soil_moisture": "30eebd133a76dcd520b62932b3f30567b0aa9a0558876531f72dbf615888a59c",
    "thorp_g_growth_vs_carbon_soil_moisture_detrended": "fa3e07a5b5f0c8e39cb0f64bf901b7220065080542047ebba43f4f0207ebbdde",
    "thorp_g_soil_moisture_vs_carbon": "fe0342ab730ba6605567c8880ee51c8ffd9c0b5ebfc3237284b634e84ea829be",
    "thorp_g_height_vs_age_turgor_threshold": "cea8b0e3717ed0e462bcd1203c59730e3f36c422ce8354d7359d077df117f959",
    "thorp_g_height_vs_age_waterstress": "314256cd96ea775f43266e1334ac67bd06598d9680e8bd215f8ad194adabe553",
}

SCENARIO_STYLE = {
    "control": {"label": "Control", "color": "#1D3557"},
    "precip_75": {"label": "75% Precipitation", "color": "#E76F51"},
    "precip_50": {"label": "50% Precipitation", "color": "#F4A261"},
}
GAMMA_COLORS = ["#264653", "#2A9D8F", "#E9C46A", "#F4A261", "#E76F51", "#7B2CBF"]
THORP_G_GROUP_IDS = ("precipitation", "relative_humidity", "combined")
THORP_G_GROUP_TITLES = {
    "precipitation": "Precipitation, P",
    "relative_humidity": "Relative humidity, RH",
    "combined": "Both",
}
THORP_G_STRESS_LABELS = {
    "THORP_data_Control_Turgor": "Control",
    "THORP_data_0.9Prec_Turgor": "90% P",
    "THORP_data_0.8Prec_Turgor": "80% P",
    "THORP_data_0.9RH_Turgor": "90% RH",
    "THORP_data_0.8RH_Turgor": "80% RH",
    "THORP_data_0.9Prec_0.9RH_Turgor": "90% P; 90% RH",
}
THORP_G_TURGOR_LABELS = {
    "THORP_data_Control": "Source-limited (Potkay et al., 2021)",
    "THORP_data_Control_Turgor_Gamma_minus_0.1MPa": "Gamma = 0.65 MPa",
    "THORP_data_Control_Turgor_Gamma_minus_0.05MPa": "Gamma = 0.70 MPa",
    "THORP_data_Control_Turgor": "Gamma = 0.75 MPa (Control)",
    "THORP_data_Control_Turgor_Gamma_plus_0.05MPa": "Gamma = 0.80 MPa",
    "THORP_data_Control_Turgor_Gamma_plus_0.1MPa": "Gamma = 0.85 MPa",
}
THORP_G_HEIGHT_TURGOR_FILES = (
    "THORP_data_Control.mat",
    "THORP_data_Control_Turgor_Gamma_minus_0.1MPa.mat",
    "THORP_data_Control_Turgor_Gamma_minus_0.05MPa.mat",
    "THORP_data_Control_Turgor.mat",
    "THORP_data_Control_Turgor_Gamma_plus_0.05MPa.mat",
    "THORP_data_Control_Turgor_Gamma_plus_0.1MPa.mat",
)
THORP_G_HEIGHT_WATERSTRESS_GROUPS = (
    (
        "THORP_data_Control_Turgor.mat",
        "THORP_data_0.9Prec_Turgor.mat",
        "THORP_data_0.8Prec_Turgor.mat",
    ),
    (
        "THORP_data_Control_Turgor.mat",
        "THORP_data_0.9RH_Turgor.mat",
        "THORP_data_0.8RH_Turgor.mat",
    ),
    (
        "THORP_data_Control_Turgor.mat",
        "THORP_data_0.9Prec_0.9RH_Turgor.mat",
    ),
)


@dataclass(frozen=True)
class TDGMExampleFigureSuiteArtifacts:
    turgor_allocation: FigureBundleArtifacts
    turgor_water_potential: FigureBundleArtifacts
    turgor_growth_scaling: FigureBundleArtifacts
    max_height_for_soil: FigureBundleArtifacts
    poorter_smf: FigureBundleArtifacts
    phloem_transport_04m: FigureBundleArtifacts
    phloem_transport_44m: FigureBundleArtifacts
    source_vs_sink_growth: FigureBundleArtifacts
    thorp_g_growth_vs_carbon: FigureBundleArtifacts
    thorp_g_growth_vs_carbon_precipitation: FigureBundleArtifacts
    thorp_g_growth_vs_carbon_soil_moisture: FigureBundleArtifacts
    thorp_g_growth_vs_carbon_soil_moisture_detrended: FigureBundleArtifacts
    thorp_g_soil_moisture_vs_carbon: FigureBundleArtifacts
    thorp_g_height_vs_age_turgor_threshold: FigureBundleArtifacts
    thorp_g_height_vs_age_waterstress: FigureBundleArtifacts

    def to_summary(self) -> dict[str, Any]:
        return {
            "turgor_allocation": self.turgor_allocation.to_summary(),
            "turgor_water_potential": self.turgor_water_potential.to_summary(),
            "turgor_growth_scaling": self.turgor_growth_scaling.to_summary(),
            "max_height_for_soil": self.max_height_for_soil.to_summary(),
            "poorter_smf": self.poorter_smf.to_summary(),
            "phloem_transport_04m": self.phloem_transport_04m.to_summary(),
            "phloem_transport_44m": self.phloem_transport_44m.to_summary(),
            "source_vs_sink_growth": self.source_vs_sink_growth.to_summary(),
            "thorp_g_growth_vs_carbon": self.thorp_g_growth_vs_carbon.to_summary(),
            "thorp_g_growth_vs_carbon_precipitation": self.thorp_g_growth_vs_carbon_precipitation.to_summary(),
            "thorp_g_growth_vs_carbon_soil_moisture": self.thorp_g_growth_vs_carbon_soil_moisture.to_summary(),
            "thorp_g_growth_vs_carbon_soil_moisture_detrended": self.thorp_g_growth_vs_carbon_soil_moisture_detrended.to_summary(),
            "thorp_g_soil_moisture_vs_carbon": self.thorp_g_soil_moisture_vs_carbon.to_summary(),
            "thorp_g_height_vs_age_turgor_threshold": self.thorp_g_height_vs_age_turgor_threshold.to_summary(),
            "thorp_g_height_vs_age_waterstress": self.thorp_g_height_vs_age_waterstress.to_summary(),
        }


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


def _tokens_path_from_spec(spec_path: Path, spec: dict[str, Any]) -> Path:
    return (spec_path.parent / spec["theme"]["tokens"]).resolve()


def _digest_summary(frame: pd.DataFrame, *, digest_key: str) -> dict[str, Any]:
    actual = frame_digest(frame)
    expected = EXPECTED_FRAME_DIGESTS[digest_key]
    return {
        "digest_key": digest_key,
        "expected": expected,
        "actual": actual,
        "passed": None if expected is None else expected == actual,
    }


def _common_bundle_state(
    *,
    output_dir: Path,
    spec_path: Path,
    frame: pd.DataFrame,
    digest_key: str,
    legacy_sources: list[Path],
    legacy_reference_script: Path | None = None,
) -> tuple[dict[str, Any], dict[str, Path], dict[str, Any], dict[str, Any]]:
    spec = load_yaml(spec_path)
    figure_id = spec["meta"]["id"]
    digest_summary = _digest_summary(frame, digest_key=digest_key)
    resolved_spec = deepcopy(spec)
    resolved_spec["data"] = {
        "path": str((output_dir / f"{figure_id}_data.csv").resolve()),
        "row_count": int(len(frame)),
        "columns": list(frame.columns),
    }
    resolved_spec["meta"]["legacy_digest_match"] = digest_summary["passed"]
    resolved_spec["meta"]["legacy_sources"] = [str(path) for path in legacy_sources]
    if legacy_reference_script is not None:
        resolved_spec["meta"]["legacy_reference_script"] = str(legacy_reference_script)
    tokens_path = _tokens_path_from_spec(spec_path, spec)
    tokens = load_yaml(tokens_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    file_paths = resolve_figure_paths(output_dir, figure_id)
    frame.to_csv(file_paths["data_csv"], index=False)
    file_paths["spec_copy"].write_text(spec_path.read_text(encoding="utf-8"), encoding="utf-8")
    file_paths["resolved_spec"].write_text(json.dumps(resolved_spec, indent=2), encoding="utf-8")
    file_paths["tokens_copy"].write_text(tokens_path.read_text(encoding="utf-8"), encoding="utf-8")
    return spec, file_paths, tokens, digest_summary


def _finalize_bundle(
    *,
    file_paths: dict[str, Path],
    metadata: dict[str, Any],
    fig: Any,
) -> FigureBundleArtifacts:
    fig.savefig(file_paths["png"], dpi=300, bbox_inches="tight", facecolor="white")
    fig.savefig(file_paths["pdf"], bbox_inches="tight", facecolor="white")
    plt.close(fig)
    file_paths["metadata"].write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return FigureBundleArtifacts(
        output_dir=file_paths["metadata"].parent,
        data_csv_path=file_paths["data_csv"],
        spec_copy_path=file_paths["spec_copy"],
        resolved_spec_path=file_paths["resolved_spec"],
        tokens_copy_path=file_paths["tokens_copy"],
        metadata_path=file_paths["metadata"],
        png_path=file_paths["png"],
        pdf_path=file_paths["pdf"],
    )


def build_poorter_smf_frame() -> pd.DataFrame:
    carbon_mol, smf_curve, _ = load_poorter_smf_reference_curve()
    transition = (10**6) * 0.5 / 12.0
    records: list[dict[str, Any]] = []
    for x_value, y_value in zip(carbon_mol, smf_curve, strict=True):
        records.append(
            {
                "panel_id": "poorter_smf",
                "series_id": "curve" if x_value <= transition else "extrapolation",
                "kind": "line",
                "x": float(x_value),
                "y": float(y_value),
            }
        )
    return pd.DataFrame.from_records(records)


def build_phloem_transport_frame(*, height_key: str) -> pd.DataFrame:
    centers, pdf, cdf, _ = phloem_transport_distribution(height_key)
    records: list[dict[str, Any]] = []
    for x_value, y_value in zip(centers, cdf, strict=True):
        records.append(
            {
                "panel_id": f"phloem_transport_{height_key}",
                "series_id": "cdf",
                "kind": "cdf",
                "x": float(x_value),
                "y": float(y_value),
            }
        )
    for x_value, y_value in zip(centers, pdf, strict=True):
        records.append(
            {
                "panel_id": f"phloem_transport_{height_key}",
                "series_id": "pdf",
                "kind": "pdf",
                "x": float(x_value),
                "y": float(y_value),
            }
        )
    return pd.DataFrame.from_records(records)


def build_turgor_allocation_frame() -> pd.DataFrame:
    fit = fit_turgor_allocation_regression(h_curve_m=np.arange(1.0, 100.0 + 0.1, 0.1, dtype=float))
    records: list[dict[str, Any]] = []
    for x_value, y_value in zip(fit.h_filtered_m, fit.u_sw_1yr, strict=True):
        records.append({"panel_id": "allocation_regression", "series_id": "thorp_1yr", "kind": "line", "x": float(x_value), "y": float(y_value)})
    for x_value, y_value in zip(fit.h_filtered_m, fit.u_sw_10yr, strict=True):
        records.append({"panel_id": "allocation_regression", "series_id": "thorp_10yr", "kind": "line", "x": float(x_value), "y": float(y_value)})
    for x_value, y_value in zip(fit.h_curve_m, fit.u_sw_curve, strict=True):
        records.append({"panel_id": "allocation_regression", "series_id": "bimodal_fit", "kind": "fit", "x": float(x_value), "y": float(y_value)})
    return pd.DataFrame.from_records(records)


def build_turgor_water_potential_frame() -> pd.DataFrame:
    fit = regress_xylem_potentials(h_curve_m=np.arange(1.0, 100.0 + 1.0, 1.0, dtype=float))
    records: list[dict[str, Any]] = []
    for x_value, y_value in zip(fit.h_scatter_m, fit.psi_rc0_scatter_mpa, strict=True):
        records.append({"panel_id": "predawn", "series_id": "root_collar_raw", "kind": "scatter", "x": float(x_value), "y": float(y_value)})
    for x_value, y_value in zip(fit.h_scatter_m, fit.psi_s0_scatter_mpa, strict=True):
        records.append({"panel_id": "predawn", "series_id": "stem_apex_raw", "kind": "scatter", "x": float(x_value), "y": float(y_value)})
    for x_value, y_value in zip(fit.h_curve_m, fit.psi_rc0_fit_mpa, strict=True):
        records.append({"panel_id": "predawn", "series_id": "root_collar_fit", "kind": "fit", "x": float(x_value), "y": float(y_value)})
    for x_value, y_value in zip(fit.h_curve_m, fit.psi_s0_fit_mpa, strict=True):
        records.append({"panel_id": "predawn", "series_id": "stem_apex_fit", "kind": "fit", "x": float(x_value), "y": float(y_value)})
    for x_value, y_value in zip(fit.h_scatter_m, fit.psi_rc_scatter_mpa, strict=True):
        records.append({"panel_id": "midday", "series_id": "root_collar_raw", "kind": "scatter", "x": float(x_value), "y": float(y_value)})
    for x_value, y_value in zip(fit.h_scatter_m, fit.psi_s_scatter_mpa, strict=True):
        records.append({"panel_id": "midday", "series_id": "stem_apex_raw", "kind": "scatter", "x": float(x_value), "y": float(y_value)})
    for x_value, y_value in zip(fit.h_curve_m, fit.psi_rc_fit_mpa, strict=True):
        records.append({"panel_id": "midday", "series_id": "root_collar_fit", "kind": "fit", "x": float(x_value), "y": float(y_value)})
    for x_value, y_value in zip(fit.h_curve_m, fit.psi_s_fit_mpa, strict=True):
        records.append({"panel_id": "midday", "series_id": "stem_apex_fit", "kind": "fit", "x": float(x_value), "y": float(y_value)})
    return pd.DataFrame.from_records(records)


def build_turgor_growth_scaling_frame() -> pd.DataFrame:
    h_grid = np.arange(1.0, 500.0 + 0.1, 0.1, dtype=float)
    allocation_fit = fit_turgor_allocation_regression(h_curve_m=h_grid)
    potential_fit = regress_xylem_potentials(h_curve_m=h_grid)

    diameter = (h_grid / 64.6) ** (1.0 / 0.6411)
    c_w = 1.4e4 * 0.5 * diameter**2 * h_grid
    c_sw = 0.94 * c_w
    c_hw = c_w - c_sw

    c_tree = c_w.copy()
    for _ in range(100):
        smf_1 = poorter_smf_lookup(np.log10(c_tree * 12.0 * 2.0))
        c_tree_next = c_w / smf_1
        smf_2 = poorter_smf_lookup(np.log10(c_tree_next * 12.0 * 2.0))
        c_tree = c_tree_next
        if np.all(np.abs(smf_1 - smf_2) < 1e-3):
            break

    xmin = 10 ** np.floor(np.log10(np.min(c_tree)))
    xmax = 10 ** np.ceil(np.log10(np.max(c_tree)))
    gamma_plot = np.array([0.0, 0.4, 0.6, 0.7, 0.8], dtype=float)
    gamma_grid = np.unique(np.concatenate([np.arange(0.0, 1.1 + 0.01, 0.01), gamma_plot]))
    records: list[dict[str, Any]] = []
    e_values = np.full(gamma_grid.shape, np.nan, dtype=float)
    h_max_values = np.full(gamma_grid.shape, np.nan, dtype=float)
    psi_at_hmax = np.full(gamma_grid.shape, np.nan, dtype=float)

    for idx, gamma_value in enumerate(gamma_grid):
        g_rate = turgor_growth_rate_from_legacy(
            psi_s_mpa=potential_fit.psi_s0_fit_mpa,
            psi_rc_mpa=potential_fit.psi_rc0_fit_mpa,
            u_sw=allocation_fit.u_sw_curve,
            c_sw=c_sw,
            c_hw=c_hw,
            gamma_mpa=float(gamma_value),
        )
        g_max = float(np.nanmax(g_rate))
        if np.any(g_rate == g_max):
            c_tree_max = float(np.max(c_tree[g_rate == g_max]))
            if np.any(c_tree > c_tree_max):
                h_max_values[idx] = float(np.min(h_grid[g_rate == g_max]))
                h_idx = int(np.argmin(np.abs(h_grid - h_max_values[idx])))
                psi_at_hmax[idx] = float(potential_fit.psi_s0_fit_mpa[h_idx])
        else:
            c_tree_max = float(np.max(c_tree))

        valid = np.isfinite(g_rate) & (g_rate > 0) & (c_tree <= c_tree_max)
        x_log = np.log(c_tree[valid])
        y_log = np.log(g_rate[valid])
        h_valid = h_grid[valid]
        selector = h_valid <= 45.0
        if np.count_nonzero(selector) >= 2:
            e_values[idx] = float(np.sum((x_log[selector] - np.mean(x_log[selector])) * (y_log[selector] - np.mean(y_log[selector]))) / np.sum((x_log[selector] - np.mean(x_log[selector])) ** 2))

        if not np.any(np.isclose(gamma_value, gamma_plot)):
            continue

        dlog_x = 0.05
        c_tree_plot = 10 ** np.arange(np.log10(xmin) + dlog_x / 2.0, np.log10(xmax), dlog_x)
        g_plot = np.full(c_tree_plot.shape, np.nan, dtype=float)
        for k, c_tree_target in enumerate(c_tree_plot):
            local = np.abs(np.log10(c_tree) - np.log10(c_tree_target)) <= dlog_x / 2.0
            g_local = g_rate[local]
            c_local = c_tree[local]
            finite = np.isfinite(g_local) & (g_local > 0) & np.isfinite(c_local) & (c_local > 0)
            g_local = g_local[finite]
            c_local = c_local[finite]
            if g_local.size == 0:
                continue
            if g_local.size == 1:
                g_plot[k] = float(g_local[0])
                c_tree_plot[k] = float(c_local[0])
            else:
                coeff = np.polyfit(np.log10(c_local), np.log10(g_local), 1)
                g_plot[k] = float(10 ** np.polyval(coeff, np.log10(c_tree_target)))
        series_id = f"gamma_{gamma_value:.2f}"
        for x_value, y_value in zip(c_tree_plot[np.isfinite(g_plot)], g_plot[np.isfinite(g_plot)], strict=True):
            records.append({"panel_id": "growth_rate", "series_id": series_id, "kind": "line", "x": float(x_value), "y": float(y_value), "gamma": float(gamma_value)})
        if np.isfinite(g_max) and np.any(g_rate == g_max):
            records.append({"panel_id": "growth_rate", "series_id": series_id, "kind": "optimal_point", "x": c_tree_max, "y": g_max, "gamma": float(gamma_value)})

        dydx = np.full(c_tree.size - 1, np.nan, dtype=float)
        valid_pairs = (g_rate[1:] > 0.0) & (g_rate[:-1] > 0.0) & (c_tree[1:] > 0.0) & (c_tree[:-1] > 0.0)
        log_g_diff = np.diff(np.log(np.where(g_rate > 0.0, g_rate, np.nan)))
        log_c_diff = np.diff(np.log(c_tree))
        dydx[valid_pairs] = log_g_diff[valid_pairs] / log_c_diff[valid_pairs]
        c_tree_mid = (c_tree[:-1] + c_tree[1:]) / 2.0
        dydx_plot = np.full(c_tree_plot.shape, np.nan, dtype=float)
        for k, c_tree_target in enumerate(c_tree_plot):
            local = np.abs(np.log10(c_tree_mid) - np.log10(c_tree_target)) <= dlog_x / 2.0
            dydx_local = dydx[local]
            c_mid_local = c_tree_mid[local]
            finite = np.isfinite(dydx_local) & np.isfinite(c_mid_local) & (c_mid_local > 0)
            dydx_local = dydx_local[finite]
            c_mid_local = c_mid_local[finite]
            if dydx_local.size == 0:
                continue
            if dydx_local.size == 1:
                dydx_plot[k] = float(dydx_local[0])
                c_tree_plot[k] = float(c_mid_local[0])
            else:
                coeff = np.polyfit(np.log10(c_mid_local), dydx_local, 1)
                dydx_plot[k] = float(np.polyval(coeff, np.log10(c_tree_target)))
        for x_value, y_value in zip(c_tree_plot[np.isfinite(dydx_plot)], dydx_plot[np.isfinite(dydx_plot)], strict=True):
            records.append({"panel_id": "local_exponent", "series_id": series_id, "kind": "line", "x": float(x_value), "y": float(y_value), "gamma": float(gamma_value)})

    mass_window_idx = int(np.argmin(np.abs(h_grid - 45.0)))
    records.extend(
        [
            {"panel_id": "growth_rate", "series_id": "empirical_mass_window", "kind": "band_lower", "x": float(xmin), "y": 0.0},
            {"panel_id": "growth_rate", "series_id": "empirical_mass_window", "kind": "band_upper", "x": float(c_tree[mass_window_idx]), "y": 100.0},
            {"panel_id": "local_exponent", "series_id": "empirical_exponent_band", "kind": "band_lower", "x": float(xmin), "y": 0.46},
            {"panel_id": "local_exponent", "series_id": "empirical_exponent_band", "kind": "band_upper", "x": float(xmax), "y": 0.98},
            {"panel_id": "local_exponent", "series_id": "three_quarter_reference", "kind": "reference", "x": float(xmin), "y": 0.75},
            {"panel_id": "local_exponent", "series_id": "three_quarter_reference", "kind": "reference", "x": float(xmax), "y": 0.75},
        ]
    )
    for gamma_value, exponent in zip(gamma_grid, e_values, strict=True):
        records.append({"panel_id": "regressed_exponent", "series_id": "regressed_exponent", "kind": "line", "x": float(gamma_value), "y": float(exponent)})
    records.extend(
        [
            {"panel_id": "regressed_exponent", "series_id": "empirical_exponent_band", "kind": "band_lower", "x": float(np.min(gamma_grid)), "y": 0.46},
            {"panel_id": "regressed_exponent", "series_id": "empirical_exponent_band", "kind": "band_upper", "x": float(np.max(gamma_grid)), "y": 0.98},
            {"panel_id": "regressed_exponent", "series_id": "three_quarter_reference", "kind": "reference", "x": float(np.min(gamma_grid)), "y": 0.75},
            {"panel_id": "regressed_exponent", "series_id": "three_quarter_reference", "kind": "reference", "x": float(np.max(gamma_grid)), "y": 0.75},
        ]
    )
    for gamma_value, h_max, psi_value in zip(gamma_grid, h_max_values, psi_at_hmax, strict=True):
        if np.isnan(h_max):
            continue
        kind = "below_limit" if psi_value <= -2.0 else "above_limit"
        records.append({"panel_id": "max_height", "series_id": kind, "kind": kind, "x": float(gamma_value), "y": float(h_max)})
    records.extend(
        [
            {"panel_id": "max_height", "series_id": "empirical_height_band", "kind": "band_lower", "x": float(np.min(gamma_grid)), "y": 35.0},
            {"panel_id": "max_height", "series_id": "empirical_height_band", "kind": "band_upper", "x": float(np.max(gamma_grid)), "y": 45.0},
            {"panel_id": "max_height", "series_id": "ninety_meter_reference", "kind": "reference", "x": float(np.min(gamma_grid)), "y": 90.0},
            {"panel_id": "max_height", "series_id": "ninety_meter_reference", "kind": "reference", "x": float(np.max(gamma_grid)), "y": 90.0},
        ]
    )
    return pd.DataFrame.from_records(records)


def build_max_height_for_soil_frame() -> pd.DataFrame:
    h_grid = np.arange(1.0, 500.0 + 0.1, 0.1, dtype=float)
    allocation_fit = fit_turgor_allocation_regression(h_curve_m=h_grid)
    diameter = (h_grid / 64.6) ** (1.0 / 0.6411)
    c_w = 1.4e4 * 0.5 * diameter**2 * h_grid
    c_sw = 0.94 * c_w
    c_hw = c_w - c_sw
    tao = load_tao_height_envelope()
    max_p_minus_pet = load_max_p_minus_pet()
    gamma_plot = np.array([0.0, 0.2, 0.4, 0.55, 0.7, 0.75], dtype=float)
    h_breaks = (np.inf, 22.0, 14.0)

    records: list[dict[str, Any]] = []
    predawn_fits: list[tuple[np.ndarray, np.ndarray]] = []
    for file_name, h_break in zip(MAX_HEIGHT_FILE_ORDER, h_breaks, strict=True):
        scenario = load_offline_scenario(file_name)
        fit = regress_xylem_potentials(scenario=scenario, h_break_m=h_break, h_curve_m=h_grid)
        _, _, psi_soil_mean = surface_soil_moisture_proxy(scenario.psi_soil_by_layer_ts[:, scenario.h_ts < h_break])
        h_local = scenario.h_ts[scenario.h_ts < h_break]
        scenario_id = "control" if "Control" in file_name else ("precip_75" if "0.75" in file_name else "precip_50")
        predawn_fits.append((fit.psi_s0_fit_mpa, fit.psi_rc0_fit_mpa))
        for x_value, y_value in zip(fit.h_curve_m, fit.psi_s0_fit_mpa, strict=True):
            records.append({"panel_id": "water_potential_vs_height", "series_id": f"{scenario_id}_stem_apex", "kind": "fit", "x": float(x_value), "y": float(y_value)})
        for x_value, y_value in zip(fit.h_curve_m, fit.psi_rc0_fit_mpa, strict=True):
            records.append({"panel_id": "water_potential_vs_height", "series_id": f"{scenario_id}_root_collar", "kind": "fit", "x": float(x_value), "y": float(y_value)})
        for x_value, y_value in zip(h_local, psi_soil_mean, strict=True):
            records.append({"panel_id": "water_potential_vs_height", "series_id": f"{scenario_id}_soil_mean", "kind": "line", "x": float(x_value), "y": float(y_value)})

    for x_mid, y_lb, y_ub, y_outlier in zip(tao.x_range_mid, tao.y_lb, tao.y_ub, tao.y_ub_outlier, strict=True):
        records.extend(
            [
                {"panel_id": "max_height_vs_p_minus_pet", "series_id": "tao_inlier_range", "kind": "band_lower", "x": float(x_mid - 50.0), "y": float(y_lb)},
                {"panel_id": "max_height_vs_p_minus_pet", "series_id": "tao_inlier_range", "kind": "band_upper", "x": float(x_mid + 50.0), "y": float(y_ub)},
                {"panel_id": "max_height_vs_p_minus_pet", "series_id": "tao_outlier_range", "kind": "band_lower", "x": float(x_mid - 50.0), "y": float(y_ub)},
                {"panel_id": "max_height_vs_p_minus_pet", "series_id": "tao_outlier_range", "kind": "band_upper", "x": float(x_mid + 50.0), "y": float(y_outlier)},
            ]
        )

    for gamma_index, gamma_value in enumerate(gamma_plot):
        h_max = np.full(len(MAX_HEIGHT_FILE_ORDER), np.nan, dtype=float)
        for idx, _file_name in enumerate(MAX_HEIGHT_FILE_ORDER):
            psi_s_predawn, psi_rc_predawn = predawn_fits[idx]
            g_rate = turgor_growth_rate_from_legacy(
                psi_s_mpa=psi_s_predawn,
                psi_rc_mpa=psi_rc_predawn,
                u_sw=allocation_fit.u_sw_curve,
                c_sw=c_sw,
                c_hw=c_hw,
                gamma_mpa=float(gamma_value),
            )
            g_max = float(np.nanmax(g_rate))
            h_max[idx] = float(np.min(h_grid[g_rate == g_max]))
        for x_value, y_value in zip(max_p_minus_pet, h_max, strict=True):
            records.append(
                {
                    "panel_id": "max_height_vs_p_minus_pet",
                    "series_id": f"gamma_{gamma_value:.2f}",
                    "kind": "line",
                    "x": float(x_value),
                    "y": float(y_value),
                    "gamma": float(gamma_value),
                    "order": int(gamma_index),
                }
            )
    return pd.DataFrame.from_records(records)


def build_source_vs_sink_growth_frame() -> pd.DataFrame:
    source = load_thorp_g_scenario(SOURCE_SINK_FILE_ORDER[0])
    sink = load_thorp_g_scenario(SOURCE_SINK_FILE_ORDER[1])
    t_source, h_source = height_trace_on_regular_grid(scenario=source, dt_years=2.0 / 12.0)
    t_sink, h_sink = height_trace_on_regular_grid(scenario=sink, dt_years=2.0 / 12.0)
    n_min = min(len(t_source), len(t_sink))
    t_source = t_source[:n_min]
    t_sink = t_sink[:n_min]
    h_source = h_source[:n_min]
    h_sink = h_sink[:n_min]

    def _sample_with_last(values: np.ndarray, step: int) -> np.ndarray:
        return np.concatenate([values[::step], values[-1:]])

    h_1yr = np.vstack([_sample_with_last(h_source, 6), _sample_with_last(h_sink, 6)])
    t_1yr = np.vstack([_sample_with_last(t_source, 6), _sample_with_last(t_sink, 6)])
    h_10yr = np.vstack([_sample_with_last(h_source, 60), _sample_with_last(h_sink, 60)])
    t_10yr = np.vstack([_sample_with_last(t_source, 60), _sample_with_last(t_sink, 60)])

    r_1yr = np.diff(h_1yr[0]) / np.diff(h_1yr[1])
    t_half_1yr = t_1yr[0, :-1] + 0.5 * np.diff(t_1yr[0])
    r_10yr = np.diff(h_10yr[0]) / np.diff(h_10yr[1])
    t_half_10yr = t_10yr[0, :-1] + 0.5 * np.diff(t_10yr[0])

    h_source_10yr = h_10yr[0, :-1]
    h_sink_10yr = h_10yr[1, :-1]
    h_source_mid_10yr = h_source_10yr[:-1] + 0.5 * np.diff(h_source_10yr)
    h_sink_mid_10yr = h_sink_10yr[:-1] + 0.5 * np.diff(h_sink_10yr)
    dh_source_10yr = np.diff(h_source_10yr) / 10.0
    dh_sink_10yr = np.diff(h_sink_10yr) / 10.0

    h_source_1yr = h_1yr[0]
    h_sink_1yr = h_1yr[1]
    h_source_mid_1yr = h_source_1yr[:-1] + 0.5 * np.diff(h_source_1yr)
    h_sink_mid_1yr = h_sink_1yr[:-1] + 0.5 * np.diff(h_sink_1yr)
    dh_source_1yr = np.diff(h_source_1yr)
    dh_sink_1yr = np.diff(h_sink_1yr)

    records: list[dict[str, Any]] = []
    for idx in range(int(np.ceil(len(r_1yr) / 10.0)) - 1):
        start = 10 * idx
        end = min(10 * (idx + 1), len(r_1yr))
        x_min = 15.0 + float(np.min(t_half_1yr[start:end]) - 0.5)
        x_max = 15.0 + float(np.max(t_half_1yr[start:end]) + 0.5)
        records.extend(
            [
                {"panel_id": "ratio_over_age", "series_id": f"annual_range_{idx+1}", "kind": "band_lower", "x": x_min, "y": float(np.min(r_1yr[start:end]))},
                {"panel_id": "ratio_over_age", "series_id": f"annual_range_{idx+1}", "kind": "band_upper", "x": x_max, "y": float(np.max(r_1yr[start:end]))},
                {"panel_id": "ratio_over_age", "series_id": f"decadal_ratio_{idx+1}", "kind": "segment", "x": float(15.0 + t_half_10yr[idx] - 5.0), "x2": float(15.0 + t_half_10yr[idx] + 5.0), "y": float(r_10yr[idx])},
            ]
        )

    for idx in range(len(h_source_mid_10yr)):
        local = (h_source_mid_1yr >= h_source_10yr[idx]) & (h_source_mid_1yr < h_source_10yr[idx + 1])
        records.extend(
            [
                {"panel_id": "source_growth", "series_id": f"annual_range_{idx+1}", "kind": "band_lower", "x": float(h_source_10yr[idx]), "y": float(np.min(dh_source_1yr[local]))},
                {"panel_id": "source_growth", "series_id": f"annual_range_{idx+1}", "kind": "band_upper", "x": float(h_source_10yr[idx + 1]), "y": float(np.max(dh_source_1yr[local]))},
                {"panel_id": "source_growth", "series_id": f"decadal_rate_{idx+1}", "kind": "segment", "x": float(h_source_10yr[idx]), "x2": float(h_source_10yr[idx + 1]), "y": float(dh_source_10yr[idx])},
            ]
        )
    for idx in range(len(h_sink_mid_10yr)):
        local = (h_sink_mid_1yr >= h_sink_10yr[idx]) & (h_sink_mid_1yr < h_sink_10yr[idx + 1])
        records.extend(
            [
                {"panel_id": "sink_growth", "series_id": f"annual_range_{idx+1}", "kind": "band_lower", "x": float(h_sink_10yr[idx]), "y": float(np.min(dh_sink_1yr[local]))},
                {"panel_id": "sink_growth", "series_id": f"annual_range_{idx+1}", "kind": "band_upper", "x": float(h_sink_10yr[idx + 1]), "y": float(np.max(dh_sink_1yr[local]))},
                {"panel_id": "sink_growth", "series_id": f"decadal_rate_{idx+1}", "kind": "segment", "x": float(h_sink_10yr[idx]), "x2": float(h_sink_10yr[idx + 1]), "y": float(dh_sink_10yr[idx])},
            ]
        )
    return pd.DataFrame.from_records(records)


def _thorp_g_group_colors(n_series: int) -> list[tuple[float, float, float]]:
    color_top = np.array([0.0, 0.4, 0.3], dtype=float)
    color_bottom = np.array([0.8, 0.0, 0.8], dtype=float)
    if n_series <= 1:
        return [tuple(color_top)]
    return [tuple(color_top + (color_bottom - color_top) * idx / (n_series - 1)) for idx in range(n_series)]


def build_thorp_g_growth_vs_carbon_frame() -> pd.DataFrame:
    records: list[dict[str, Any]] = []
    for group_id, filenames in zip(THORP_G_GROUP_IDS, build_thorp_g_stress_groups(), strict=True):
        for order, filename in enumerate(filenames):
            scenario = load_thorp_g_scenario(filename)
            series_id = Path(filename).stem
            inst_valid = np.isfinite(scenario.c_tree_ts) & (scenario.c_tree_ts > 0.0) & np.isfinite(scenario.g_rate_ts) & (scenario.g_rate_ts > 0.0)
            for x_value, y_value in zip(scenario.c_tree_ts[inst_valid], scenario.g_rate_ts[inst_valid], strict=True):
                records.append(
                    {
                        "panel_id": f"instant_{group_id}",
                        "series_id": series_id,
                        "kind": "scatter",
                        "x": float(x_value),
                        "y": float(y_value),
                        "order": int(order),
                    }
                )
            c_mean, g_rate = annual_growth_by_year(scenario=scenario)
            ann_valid = np.isfinite(c_mean) & (c_mean > 0.0) & np.isfinite(g_rate) & (g_rate > 0.0)
            for x_value, y_value in zip(c_mean[ann_valid], g_rate[ann_valid], strict=True):
                records.append(
                    {
                        "panel_id": f"annual_{group_id}",
                        "series_id": series_id,
                        "kind": "line",
                        "x": float(x_value),
                        "y": float(y_value),
                        "order": int(order),
                    }
                )
    return pd.DataFrame.from_records(records)


def _build_thorp_g_colored_growth_frame(*, color_mode: str) -> pd.DataFrame:
    panel_files = {
        "control": "THORP_data_Control_Turgor.mat",
        "rh_80": "THORP_data_0.8RH_Turgor.mat",
    }
    records: list[dict[str, Any]] = []
    for panel_id, file_name in panel_files.items():
        scenario = load_thorp_g_scenario(file_name)
        if color_mode == "precipitation":
            c_mean, g_rate = annual_growth_by_year(scenario=scenario)
            valid = np.isfinite(c_mean) & (c_mean > 0.0) & np.isfinite(g_rate) & (g_rate > 0.0)
            c_mean = c_mean[valid]
            g_rate = g_rate[valid]
            color_values = annual_precipitation_relative(len(c_mean))
        elif color_mode in {"soil_moisture", "soil_moisture_detrended"}:
            c_mean, g_rate, s_e_mean, _s_e_regressed, s_e_detrended = annual_soil_moisture_by_year(scenario=scenario)
            color_values = s_e_mean if color_mode == "soil_moisture" else s_e_detrended
        else:
            raise KeyError(f"Unsupported color mode '{color_mode}'")
        for x_value, y_value, color_value in zip(c_mean, g_rate, color_values, strict=True):
            records.append(
                {
                    "panel_id": panel_id,
                    "series_id": Path(file_name).stem,
                    "kind": "scatter",
                    "x": float(x_value),
                    "y": float(y_value),
                    "color_value": float(color_value),
                }
            )
    return pd.DataFrame.from_records(records)


def build_thorp_g_growth_vs_carbon_precipitation_frame() -> pd.DataFrame:
    return _build_thorp_g_colored_growth_frame(color_mode="precipitation")


def build_thorp_g_growth_vs_carbon_soil_moisture_frame() -> pd.DataFrame:
    return _build_thorp_g_colored_growth_frame(color_mode="soil_moisture")


def build_thorp_g_growth_vs_carbon_soil_moisture_detrended_frame() -> pd.DataFrame:
    return _build_thorp_g_colored_growth_frame(color_mode="soil_moisture_detrended")


def build_thorp_g_soil_moisture_vs_carbon_frame() -> pd.DataFrame:
    panel_files = {
        "control": "THORP_data_Control_Turgor.mat",
        "rh_80": "THORP_data_0.8RH_Turgor.mat",
    }
    records: list[dict[str, Any]] = []
    for panel_id, file_name in panel_files.items():
        scenario = load_thorp_g_scenario(file_name)
        c_mean, _g_rate, s_e_mean, s_e_regressed, _s_e_detrended = annual_soil_moisture_by_year(scenario=scenario)
        for x_value, y_value in zip(c_mean, s_e_mean, strict=True):
            records.append(
                {
                    "panel_id": panel_id,
                    "series_id": Path(file_name).stem,
                    "kind": "scatter",
                    "x": float(x_value),
                    "y": float(y_value),
                }
            )
        for x_value, y_value in zip(c_mean, s_e_regressed, strict=True):
            records.append(
                {
                    "panel_id": panel_id,
                    "series_id": "tree_size_regression",
                    "kind": "fit",
                    "x": float(x_value),
                    "y": float(y_value),
                }
            )
    return pd.DataFrame.from_records(records)


def _build_height_reference_records(*, panel_id: str) -> list[dict[str, Any]]:
    reference = load_height_age_reference_envelope()
    records: list[dict[str, Any]] = []
    for x_value, y_lower, y_upper in zip(reference.age_bm_years, reference.h_bm_lower_m, reference.h_bm_upper_m, strict=True):
        records.extend(
            [
                {"panel_id": panel_id, "series_id": "bravo_montero_2001", "kind": "band_lower", "x": float(x_value), "y": float(y_lower)},
                {"panel_id": panel_id, "series_id": "bravo_montero_2001", "kind": "band_upper", "x": float(x_value), "y": float(y_upper)},
            ]
        )
    for x_value, y_lower, y_upper in zip(reference.age_p2004_years, reference.h_p2004_lower_m, reference.h_p2004_upper_m, strict=True):
        records.extend(
            [
                {"panel_id": panel_id, "series_id": "palahi_2004", "kind": "band_lower", "x": float(x_value), "y": float(y_lower)},
                {"panel_id": panel_id, "series_id": "palahi_2004", "kind": "band_upper", "x": float(x_value), "y": float(y_upper)},
            ]
        )
    return records


def build_thorp_g_height_vs_age_turgor_threshold_frame() -> pd.DataFrame:
    records = _build_height_reference_records(panel_id="height_vs_age")
    for order, file_name in enumerate(THORP_G_HEIGHT_TURGOR_FILES):
        scenario = load_thorp_g_scenario(file_name)
        t_grid, h_grid = height_trace_on_regular_grid(scenario=scenario, dt_years=2.0 / 12.0)
        valid = np.isfinite(t_grid) & np.isfinite(h_grid)
        series_id = Path(file_name).stem
        for x_value, y_value in zip(15.0 + t_grid[valid], h_grid[valid], strict=True):
            records.append(
                {
                    "panel_id": "height_vs_age",
                    "series_id": series_id,
                    "kind": "line",
                    "x": float(x_value),
                    "y": float(y_value),
                    "order": int(order),
                }
            )
        if np.nanmax(scenario.t_year_ts) < 99.0:
            records.append(
                {
                    "panel_id": "height_vs_age",
                    "series_id": "carbon_starvation",
                    "kind": "marker",
                    "x": float(15.0 + np.nanmax(scenario.t_year_ts)),
                    "y": float(np.nanmax(scenario.h_ts)),
                    "order": int(order),
                }
            )
    return pd.DataFrame.from_records(records)


def build_thorp_g_height_vs_age_waterstress_frame() -> pd.DataFrame:
    records: list[dict[str, Any]] = []
    for panel_id in THORP_G_GROUP_IDS:
        records.extend(_build_height_reference_records(panel_id=panel_id))
    for panel_id, filenames in zip(THORP_G_GROUP_IDS, THORP_G_HEIGHT_WATERSTRESS_GROUPS, strict=True):
        for order, file_name in enumerate(filenames):
            scenario = load_thorp_g_scenario(file_name)
            t_grid, h_grid = height_trace_on_regular_grid(scenario=scenario, dt_years=2.0 / 12.0)
            valid = np.isfinite(t_grid) & np.isfinite(h_grid)
            for x_value, y_value in zip(15.0 + t_grid[valid], h_grid[valid], strict=True):
                records.append(
                    {
                        "panel_id": panel_id,
                        "series_id": Path(file_name).stem,
                        "kind": "line",
                        "x": float(x_value),
                        "y": float(y_value),
                        "order": int(order),
                    }
                )
    return pd.DataFrame.from_records(records)


def _render_poorter_smf(*, frame: pd.DataFrame, spec: dict[str, Any], tokens: dict[str, Any]) -> Any:
    fig, ax = plt.subplots(figsize=(spec["figure"]["width_mm"] / 25.4, spec["figure"]["height_mm"] / 25.4))
    apply_axis_theme(ax, tokens=tokens, show_xlabels=True)
    for series_id, linestyle, label in (("curve", "-", "SMF fit"), ("extrapolation", ":", "SMF extrapolation")):
        sub = frame[frame["series_id"] == series_id].sort_values("x")
        ax.plot(sub["x"], sub["y"], color="#457B9D", linewidth=2.2, linestyle=linestyle, label=label)
    panel = spec["panels"]["poorter_smf"]
    ax.set_xscale("log")
    ax.set_xlim(*panel["x_limits"])
    ax.set_ylim(*panel["y_limits"])
    ax.set_xlabel(panel["x_label"])
    ax.set_ylabel(panel["y_label"])
    ax.legend(loc=spec["legend"]["loc"], frameon=False)
    _panel_label(ax, tokens=tokens, letter="a")
    fig.tight_layout()
    return fig


def _render_phloem_transport(*, frame: pd.DataFrame, spec: dict[str, Any], tokens: dict[str, Any], height_key: str) -> Any:
    fig, ax = plt.subplots(figsize=(spec["figure"]["width_mm"] / 25.4, spec["figure"]["height_mm"] / 25.4))
    apply_axis_theme(ax, tokens=tokens, show_xlabels=True)
    cdf = frame[frame["series_id"] == "cdf"].sort_values("x")
    pdf = frame[frame["series_id"] == "pdf"].sort_values("x")
    ax.plot(cdf["x"], cdf["y"], color="#355070", linewidth=2.4, label="CDF")
    ax.fill_between(pdf["x"], pdf["y"], color="#111111", alpha=0.35, step="mid", label="PDF")
    _, _, _, x_limit = phloem_transport_distribution(height_key)
    panel = spec["panels"]["distribution"]
    ax.set_xlim(0.0, x_limit)
    ax.set_ylim(*panel["y_limits"])
    ax.set_xlabel(panel["x_label"])
    ax.set_ylabel(panel["y_label"])
    ax.legend(loc=spec["legend"]["loc"], frameon=False)
    _panel_label(ax, tokens=tokens, letter="a")
    fig.tight_layout()
    return fig


def _render_turgor_allocation(*, frame: pd.DataFrame, spec: dict[str, Any], tokens: dict[str, Any]) -> Any:
    fig, ax = plt.subplots(figsize=(spec["figure"]["width_mm"] / 25.4, spec["figure"]["height_mm"] / 25.4))
    apply_axis_theme(ax, tokens=tokens, show_xlabels=True)
    style_map = {
        "thorp_1yr": {"color": "#6C757D", "label": "THORP 1 yr moving average"},
        "thorp_10yr": {"color": "#9B5DE5", "label": "THORP 10 yr moving average"},
        "bimodal_fit": {"color": "#111111", "label": "Bimodal power-law regression", "linestyle": "--"},
    }
    for series_id, style in style_map.items():
        sub = frame[frame["series_id"] == series_id].sort_values("x")
        ax.plot(sub["x"], sub["y"], color=style["color"], linewidth=2.4, linestyle=style.get("linestyle", "-"), label=style["label"])
    panel = spec["panels"]["allocation_regression"]
    ax.set_xlim(*panel["x_limits"])
    ax.set_ylim(*panel["y_limits"])
    ax.set_xlabel(panel["x_label"])
    ax.set_ylabel(panel["y_label"])
    ax.legend(loc=spec["legend"]["loc"], frameon=False)
    _panel_label(ax, tokens=tokens, letter="a")
    fig.tight_layout()
    return fig


def _render_turgor_water_potentials(*, frame: pd.DataFrame, spec: dict[str, Any], tokens: dict[str, Any]) -> Any:
    fig, axes = plt.subplots(1, 2, figsize=(spec["figure"]["width_mm"] / 25.4, spec["figure"]["height_mm"] / 25.4))
    for ax, panel_id, letter in zip(axes, ("predawn", "midday"), ("a", "b"), strict=True):
        apply_axis_theme(ax, tokens=tokens, show_xlabels=True)
        for series_id, color in (("root_collar_raw", "#9B5DE5"), ("stem_apex_raw", "#4361EE")):
            sub = frame[(frame["panel_id"] == panel_id) & (frame["series_id"] == series_id)].sort_values("x")
            ax.plot(sub["x"], sub["y"], color=color, linewidth=1.2, alpha=0.45)
        for series_id, color, label in (("root_collar_fit", "#9B5DE5", "Root collar"), ("stem_apex_fit", "#4361EE", "Stem apex")):
            sub = frame[(frame["panel_id"] == panel_id) & (frame["series_id"] == series_id)].sort_values("x")
            ax.plot(sub["x"], sub["y"], color=color, linewidth=2.4, linestyle="--", label=label)
        panel = spec["panels"][panel_id]
        ax.set_xlim(*panel["x_limits"])
        ax.set_ylim(*panel["y_limits"])
        ax.set_xlabel(panel["x_label"])
        ax.set_ylabel(panel["y_label"])
        ax.legend(loc=spec["legend"]["loc"], frameon=False)
        _panel_label(ax, tokens=tokens, letter=letter)
    fig.tight_layout()
    return fig


def _render_turgor_growth_scaling(*, frame: pd.DataFrame, spec: dict[str, Any], tokens: dict[str, Any]) -> Any:
    fig, axes = plt.subplots(2, 2, figsize=(spec["figure"]["width_mm"] / 25.4, spec["figure"]["height_mm"] / 25.4))
    panel_axes = {"growth_rate": axes[0, 0], "regressed_exponent": axes[0, 1], "local_exponent": axes[1, 0], "max_height": axes[1, 1]}
    for panel_id, ax in panel_axes.items():
        apply_axis_theme(ax, tokens=tokens, show_xlabels=True)
        panel = spec["panels"][panel_id]
        if panel.get("x_scale") == "log":
            ax.set_xscale("log")
        if panel.get("y_scale") == "log":
            ax.set_yscale("log")
        ax.set_xlim(*panel["x_limits"])
        ax.set_ylim(*panel["y_limits"])
        ax.set_xlabel(panel["x_label"])
        ax.set_ylabel(panel["y_label"])
    for idx, gamma_value in enumerate((0.0, 0.4, 0.6, 0.7, 0.8)):
        color = GAMMA_COLORS[idx]
        series_id = f"gamma_{gamma_value:.2f}"
        growth = frame[(frame["panel_id"] == "growth_rate") & (frame["series_id"] == series_id) & (frame["kind"] == "line")].sort_values("x")
        panel_axes["growth_rate"].plot(growth["x"], growth["y"], color=color, linewidth=2.0, label=f"Gamma={gamma_value:g}")
        point = frame[(frame["panel_id"] == "growth_rate") & (frame["series_id"] == series_id) & (frame["kind"] == "optimal_point")]
        if not point.empty:
            panel_axes["growth_rate"].plot(point["x"], point["y"], "p", color=color, markeredgecolor="#111111", markersize=6)
        local = frame[(frame["panel_id"] == "local_exponent") & (frame["series_id"] == series_id)].sort_values("x")
        panel_axes["local_exponent"].plot(local["x"], local["y"], color=color, linewidth=2.0)
    for panel_id in ("local_exponent", "regressed_exponent", "max_height"):
        lower = frame[(frame["panel_id"] == panel_id) & (frame["kind"] == "band_lower")]
        upper = frame[(frame["panel_id"] == panel_id) & (frame["kind"] == "band_upper")]
        if not lower.empty and not upper.empty:
            panel_axes[panel_id].fill_between([float(lower["x"].iloc[0]), float(upper["x"].iloc[0])], float(lower["y"].iloc[0]), float(upper["y"].iloc[0]), color="#BDBDBD", alpha=0.25)
        reference = frame[(frame["panel_id"] == panel_id) & (frame["kind"] == "reference")].sort_values("x")
        if not reference.empty:
            panel_axes[panel_id].plot(reference["x"], reference["y"], "--", color="#111111", linewidth=1.6)
    mass_band = frame[(frame["panel_id"] == "growth_rate") & (frame["kind"] == "band_lower")]
    mass_upper = frame[(frame["panel_id"] == "growth_rate") & (frame["kind"] == "band_upper")]
    panel_axes["growth_rate"].axvspan(float(mass_band["x"].iloc[0]), float(mass_upper["x"].iloc[0]), color="#BDBDBD", alpha=0.25)
    regressed = frame[(frame["panel_id"] == "regressed_exponent") & (frame["kind"] == "line")].sort_values("x")
    panel_axes["regressed_exponent"].plot(regressed["x"], regressed["y"], color="#355070", linewidth=2.2)
    below = frame[(frame["panel_id"] == "max_height") & (frame["kind"] == "below_limit")].sort_values("x")
    above = frame[(frame["panel_id"] == "max_height") & (frame["kind"] == "above_limit")].sort_values("x")
    if not below.empty:
        panel_axes["max_height"].plot(below["x"], below["y"], color="#2A9D8F", linewidth=2.2, label="Within predawn limit")
    if not above.empty:
        panel_axes["max_height"].plot(above["x"], above["y"], "--", color="#E76F51", linewidth=2.2, label="Beyond predawn limit")
    panel_axes["growth_rate"].legend(loc="lower right", frameon=False, fontsize=tokens["fonts"]["base_size_pt"] - 1)
    panel_axes["max_height"].legend(loc="lower left", frameon=False, fontsize=tokens["fonts"]["base_size_pt"] - 1)
    for letter, panel_id in zip(("a", "b", "c", "d"), panel_axes.keys(), strict=True):
        _panel_label(panel_axes[panel_id], tokens=tokens, letter=letter)
    fig.tight_layout()
    return fig


def _render_max_height_for_soil(*, frame: pd.DataFrame, spec: dict[str, Any], tokens: dict[str, Any]) -> Any:
    fig, axes = plt.subplots(1, 2, figsize=(spec["figure"]["width_mm"] / 25.4, spec["figure"]["height_mm"] / 25.4))
    panel_axes = {"water_potential_vs_height": axes[0], "max_height_vs_p_minus_pet": axes[1]}
    for panel_id, ax in panel_axes.items():
        apply_axis_theme(ax, tokens=tokens, show_xlabels=True)
        panel = spec["panels"][panel_id]
        if panel.get("y_scale") == "log":
            ax.set_yscale("log")
        ax.set_xlim(*panel["x_limits"])
        ax.set_ylim(*panel["y_limits"])
        ax.set_xlabel(panel["x_label"])
        ax.set_ylabel(panel["y_label"])
    for scenario_id, style in SCENARIO_STYLE.items():
        for suffix, linestyle in (("stem_apex", "--"), ("root_collar", "-."), ("soil_mean", ":")):
            sub = frame[(frame["panel_id"] == "water_potential_vs_height") & (frame["series_id"] == f"{scenario_id}_{suffix}")].sort_values("x")
            panel_axes["water_potential_vs_height"].plot(sub["x"], sub["y"], color=style["color"], linewidth=2.0 if suffix != "soil_mean" else 1.5, linestyle=linestyle)
    inlier_lowers = frame[(frame["panel_id"] == "max_height_vs_p_minus_pet") & (frame["series_id"] == "tao_inlier_range") & (frame["kind"] == "band_lower")].sort_values("x")
    inlier_uppers = frame[(frame["panel_id"] == "max_height_vs_p_minus_pet") & (frame["series_id"] == "tao_inlier_range") & (frame["kind"] == "band_upper")].sort_values("x")
    for (_, low), (_, up) in zip(inlier_lowers.iterrows(), inlier_uppers.iterrows(), strict=True):
        panel_axes["max_height_vs_p_minus_pet"].fill_between([low["x"], up["x"]], low["y"], up["y"], color="#A8DADC", alpha=0.35)
    out_lowers = frame[(frame["panel_id"] == "max_height_vs_p_minus_pet") & (frame["series_id"] == "tao_outlier_range") & (frame["kind"] == "band_lower")].sort_values("x")
    out_uppers = frame[(frame["panel_id"] == "max_height_vs_p_minus_pet") & (frame["series_id"] == "tao_outlier_range") & (frame["kind"] == "band_upper")].sort_values("x")
    for (_, low), (_, up) in zip(out_lowers.iterrows(), out_uppers.iterrows(), strict=True):
        panel_axes["max_height_vs_p_minus_pet"].fill_between([low["x"], up["x"]], low["y"], up["y"], color="#CFCFCF", alpha=0.25)
    gamma_series = [sid for sid in sorted(frame[frame["panel_id"] == "max_height_vs_p_minus_pet"]["series_id"].dropna().unique()) if str(sid).startswith("gamma_")]
    for idx, series_id in enumerate(gamma_series):
        sub = frame[(frame["panel_id"] == "max_height_vs_p_minus_pet") & (frame["series_id"] == series_id)].sort_values("x")
        gamma_value = float(sub["gamma"].iloc[0])
        panel_axes["max_height_vs_p_minus_pet"].plot(sub["x"], sub["y"], "-o", color=GAMMA_COLORS[idx % len(GAMMA_COLORS)], linewidth=1.8, markersize=4, label=f"Gamma={gamma_value:g}")
    panel_axes["max_height_vs_p_minus_pet"].legend(loc="lower right", frameon=False, fontsize=tokens["fonts"]["base_size_pt"] - 1)
    for letter, panel_id in zip(("a", "b"), panel_axes.keys(), strict=True):
        _panel_label(panel_axes[panel_id], tokens=tokens, letter=letter)
    fig.tight_layout()
    return fig


def _render_source_vs_sink(*, frame: pd.DataFrame, spec: dict[str, Any], tokens: dict[str, Any]) -> Any:
    fig = plt.figure(figsize=(spec["figure"]["width_mm"] / 25.4, spec["figure"]["height_mm"] / 25.4), constrained_layout=True)
    gs = fig.add_gridspec(2, 2, hspace=0.35, wspace=0.28)
    axes = {"ratio_over_age": fig.add_subplot(gs[0, :]), "source_growth": fig.add_subplot(gs[1, 0]), "sink_growth": fig.add_subplot(gs[1, 1])}
    for panel_id, ax in axes.items():
        apply_axis_theme(ax, tokens=tokens, show_xlabels=True)
        panel = spec["panels"][panel_id]
        ax.set_xlim(*panel["x_limits"])
        ax.set_ylim(*panel["y_limits"])
        ax.set_xlabel(panel["x_label"])
        ax.set_ylabel(panel["y_label"])
    for panel_id, line_color in (("ratio_over_age", "#5E60CE"), ("source_growth", "#B5179E"), ("sink_growth", "#118AB2")):
        ax = axes[panel_id]
        prefix = "decadal_ratio" if panel_id == "ratio_over_age" else "decadal_rate"
        for series_id in sorted({sid for sid in frame[frame["panel_id"] == panel_id]["series_id"] if str(sid).startswith("annual_range_")}):
            low = frame[(frame["panel_id"] == panel_id) & (frame["series_id"] == series_id) & (frame["kind"] == "band_lower")].iloc[0]
            high = frame[(frame["panel_id"] == panel_id) & (frame["series_id"] == series_id) & (frame["kind"] == "band_upper")].iloc[0]
            ax.fill_between([float(low["x"]), float(high["x"])], float(low["y"]), float(high["y"]), color="#BDBDBD", alpha=0.3)
        for series_id in sorted({sid for sid in frame[frame["panel_id"] == panel_id]["series_id"] if str(sid).startswith(prefix)}):
            row = frame[(frame["panel_id"] == panel_id) & (frame["series_id"] == series_id) & (frame["kind"] == "segment")].iloc[0]
            ax.plot([float(row["x"]), float(row["x2"])], [float(row["y"]), float(row["y"])], color=line_color, linewidth=2.6)
    for letter, panel_id in zip(("a", "b", "c"), axes.keys(), strict=True):
        _panel_label(axes[panel_id], tokens=tokens, letter=letter)
    return fig


def _render_thorp_g_growth_vs_carbon(*, frame: pd.DataFrame, spec: dict[str, Any], tokens: dict[str, Any]) -> Any:
    fig, axes = plt.subplots(2, 3, figsize=(spec["figure"]["width_mm"] / 25.4, spec["figure"]["height_mm"] / 25.4))
    panel_axes = {
        "instant_precipitation": axes[0, 0],
        "instant_relative_humidity": axes[0, 1],
        "instant_combined": axes[0, 2],
        "annual_precipitation": axes[1, 0],
        "annual_relative_humidity": axes[1, 1],
        "annual_combined": axes[1, 2],
    }
    for panel_id, ax in panel_axes.items():
        apply_axis_theme(ax, tokens=tokens, show_xlabels=True)
        panel = spec["panels"][panel_id]
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlim(*panel["x_limits"])
        ax.set_ylim(*panel["y_limits"])
        ax.set_xlabel(panel["x_label"])
        ax.set_ylabel(panel["y_label"])
        if title := panel.get("title"):
            ax.set_title(title, fontsize=tokens["fonts"]["base_size_pt"] + 1, pad=8)
        if panel_id.startswith("instant_"):
            ax.set_xlabel("")
        if not panel_id.endswith("precipitation"):
            ax.set_ylabel("")
    for col_idx, group_id in enumerate(THORP_G_GROUP_IDS):
        colors = _thorp_g_group_colors(len(build_thorp_g_stress_groups()[col_idx]))
        markers = ["o", "s", "D"]
        for order, series_id in enumerate(sorted(frame[frame["panel_id"] == f"instant_{group_id}"]["series_id"].unique(), key=lambda value: frame[(frame["panel_id"] == f"instant_{group_id}") & (frame["series_id"] == value)]["order"].min())):
            label = THORP_G_STRESS_LABELS.get(str(series_id), str(series_id))
            color = colors[min(order, len(colors) - 1)]
            marker = markers[min(order, len(markers) - 1)]
            inst = frame[(frame["panel_id"] == f"instant_{group_id}") & (frame["series_id"] == series_id)].sort_values("x")
            annual = frame[(frame["panel_id"] == f"annual_{group_id}") & (frame["series_id"] == series_id)].sort_values("x")
            panel_axes[f"instant_{group_id}"].plot(inst["x"], inst["y"], linestyle="None", marker=marker, markersize=4.5, color=color, markerfacecolor=color, label=label, alpha=0.8)
            panel_axes[f"annual_{group_id}"].plot(annual["x"], annual["y"], marker=marker, markersize=4.2, linewidth=1.9, color=color, markerfacecolor=color, label=label)
        for panel_id, exponents in (
            (f"instant_{group_id}", ((1.0, "--"),)),
            (f"annual_{group_id}", ((0.5, "-."), (0.75, "-"), (1.0, "--"))),
        ):
            ax = panel_axes[panel_id]
            panel = spec["panels"][panel_id]
            x_ref = np.logspace(np.log10(panel["x_limits"][0]), np.log10(panel["x_limits"][1]), 100)
            y_anchor = panel["reference_anchor_y"]
            x_anchor = panel["reference_anchor_x"]
            for exponent, linestyle in exponents:
                y_ref = y_anchor * (x_ref / x_anchor) ** exponent
                ax.plot(x_ref, y_ref, linestyle=linestyle, linewidth=1.0, color="#4F4F4F", alpha=0.8)
        panel_axes[f"instant_{group_id}"].legend(loc="upper left", frameon=False, fontsize=tokens["fonts"]["base_size_pt"] - 1)
        panel_axes[f"annual_{group_id}"].legend(loc="upper left", frameon=False, fontsize=tokens["fonts"]["base_size_pt"] - 1)
    for letter, panel_id in zip(("a", "b", "c", "d", "e", "f"), panel_axes.keys(), strict=True):
        _panel_label(panel_axes[panel_id], tokens=tokens, letter=letter)
    fig.tight_layout()
    return fig


def _render_thorp_g_colored_growth(*, frame: pd.DataFrame, spec: dict[str, Any], tokens: dict[str, Any]) -> Any:
    fig, axes = plt.subplots(
        1,
        2,
        figsize=(spec["figure"]["width_mm"] / 25.4, spec["figure"]["height_mm"] / 25.4),
        constrained_layout=True,
    )
    panel_axes = {"control": axes[0], "rh_80": axes[1]}
    colorbar_artist = None
    for panel_id, ax in panel_axes.items():
        apply_axis_theme(ax, tokens=tokens, show_xlabels=True)
        panel = spec["panels"][panel_id]
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlim(*panel["x_limits"])
        ax.set_ylim(*panel["y_limits"])
        ax.set_xlabel(panel["x_label"])
        ax.set_ylabel(panel["y_label"])
        if title := panel.get("title"):
            ax.set_title(title, fontsize=tokens["fonts"]["base_size_pt"] + 1, pad=8)
        if panel_id != "control":
            ax.set_ylabel("")
        sub = frame[frame["panel_id"] == panel_id].sort_values("x")
        colorbar_artist = ax.scatter(
            sub["x"],
            sub["y"],
            c=sub["color_value"],
            cmap=spec["colorbar"]["cmap"],
            vmin=spec["colorbar"]["v_limits"][0],
            vmax=spec["colorbar"]["v_limits"][1],
            s=28,
            edgecolors="none",
        )
        x_ref = np.logspace(np.log10(panel["x_limits"][0]), np.log10(panel["x_limits"][1]), 100)
        for exponent, linestyle in ((0.5, "-."), (0.75, "-"), (1.0, "--")):
            y_ref = panel["reference_anchor_y"] * (x_ref / panel["reference_anchor_x"]) ** exponent
            ax.plot(x_ref, y_ref, linestyle=linestyle, linewidth=1.0, color="#4F4F4F", alpha=0.85)
    assert colorbar_artist is not None
    cbar = fig.colorbar(colorbar_artist, ax=list(panel_axes.values()), fraction=0.05, pad=0.04)
    cbar.set_label(spec["colorbar"]["label"], fontsize=tokens["fonts"]["base_size_pt"])
    for letter, panel_id in zip(("a", "b"), panel_axes.keys(), strict=True):
        _panel_label(panel_axes[panel_id], tokens=tokens, letter=letter)
    return fig


def _render_thorp_g_soil_moisture_vs_carbon(*, frame: pd.DataFrame, spec: dict[str, Any], tokens: dict[str, Any]) -> Any:
    fig, axes = plt.subplots(1, 2, figsize=(spec["figure"]["width_mm"] / 25.4, spec["figure"]["height_mm"] / 25.4))
    panel_axes = {"control": axes[0], "rh_80": axes[1]}
    for panel_id, ax in panel_axes.items():
        apply_axis_theme(ax, tokens=tokens, show_xlabels=True)
        panel = spec["panels"][panel_id]
        ax.set_xlim(*panel["x_limits"])
        ax.set_ylim(*panel["y_limits"])
        ax.set_xlabel(panel["x_label"])
        ax.set_ylabel(panel["y_label"])
        if title := panel.get("title"):
            ax.set_title(title, fontsize=tokens["fonts"]["base_size_pt"] + 1, pad=8)
        if panel_id != "control":
            ax.set_ylabel("")
        scatter = frame[(frame["panel_id"] == panel_id) & (frame["kind"] == "scatter")].sort_values("x")
        fit = frame[(frame["panel_id"] == panel_id) & (frame["kind"] == "fit")].sort_values("x")
        ax.plot(scatter["x"], scatter["y"], "o", color="#111111", markersize=4.2, markerfacecolor="#111111", label="Annual mean")
        ax.plot(fit["x"], fit["y"], "--", color="#C1121F", linewidth=2.4, label="Tree-size regression")
        ax.legend(loc="upper right", frameon=False, fontsize=tokens["fonts"]["base_size_pt"] - 1)
    for letter, panel_id in zip(("a", "b"), panel_axes.keys(), strict=True):
        _panel_label(panel_axes[panel_id], tokens=tokens, letter=letter)
    fig.tight_layout()
    return fig


def _render_height_reference(ax: Any, frame: pd.DataFrame, *, panel_id: str) -> list[Any]:
    handles: list[Any] = []
    for series_id, color, label in (
        ("bravo_montero_2001", "#A0A0A0", "Bravo & Montero (2001)"),
        ("palahi_2004", "#A8C8FF", "Palahi et al. (2004)"),
    ):
        lower = frame[(frame["panel_id"] == panel_id) & (frame["series_id"] == series_id) & (frame["kind"] == "band_lower")].sort_values("x")
        upper = frame[(frame["panel_id"] == panel_id) & (frame["series_id"] == series_id) & (frame["kind"] == "band_upper")].sort_values("x")
        if lower.empty or upper.empty:
            continue
        ax.fill_between(lower["x"], lower["y"], upper["y"], color=color, alpha=0.35 if series_id == "palahi_2004" else 0.25)
        ax.plot(lower["x"], lower["y"], "--", color="#555555" if series_id == "bravo_montero_2001" else "#5B7DB1", linewidth=1.4)
        ax.plot(upper["x"], upper["y"], "--", color="#555555" if series_id == "bravo_montero_2001" else "#5B7DB1", linewidth=1.4)
        handles.append(Patch(facecolor=color, edgecolor="none", alpha=0.35 if series_id == "palahi_2004" else 0.25, label=label))
    return handles


def _render_thorp_g_height_vs_age_turgor_threshold(*, frame: pd.DataFrame, spec: dict[str, Any], tokens: dict[str, Any]) -> Any:
    fig, ax = plt.subplots(figsize=(spec["figure"]["width_mm"] / 25.4, spec["figure"]["height_mm"] / 25.4))
    apply_axis_theme(ax, tokens=tokens, show_xlabels=True)
    panel = spec["panels"]["height_vs_age"]
    ax.set_xlim(*panel["x_limits"])
    ax.set_ylim(*panel["y_limits"])
    ax.set_xlabel(panel["x_label"])
    ax.set_ylabel(panel["y_label"])
    handles = _render_height_reference(ax, frame, panel_id="height_vs_age")
    line_colors = ["#B36A1E", "#1D3557", "#2A9D8F", "#3A86FF", "#6A4C93", "#E76F51"]
    line_handles: list[Any] = []
    for order, series_id in enumerate(sorted({sid for sid in frame[frame["kind"] == "line"]["series_id"].unique()}, key=lambda value: frame[(frame["kind"] == "line") & (frame["series_id"] == value)]["order"].min())):
        sub = frame[(frame["panel_id"] == "height_vs_age") & (frame["series_id"] == series_id) & (frame["kind"] == "line")].sort_values("x")
        handle = ax.plot(sub["x"], sub["y"], color=line_colors[order % len(line_colors)], linewidth=2.4, label=THORP_G_TURGOR_LABELS.get(str(series_id), str(series_id)))[0]
        line_handles.append(handle)
    starvation = frame[(frame["panel_id"] == "height_vs_age") & (frame["kind"] == "marker")]
    starvation_handle = None
    if not starvation.empty:
        starvation_handle = ax.plot(starvation["x"], starvation["y"], "p", markersize=8, color="#7B2CBF", markerfacecolor="#7B2CBF", linestyle="None", label="C starvation")[0]
    legend_handles = handles + line_handles
    if starvation_handle is not None:
        legend_handles.append(starvation_handle)
    ax.legend(handles=legend_handles, loc="upper left", frameon=False, fontsize=tokens["fonts"]["base_size_pt"] - 1)
    _panel_label(ax, tokens=tokens, letter="a")
    fig.tight_layout()
    return fig


def _render_thorp_g_height_vs_age_waterstress(*, frame: pd.DataFrame, spec: dict[str, Any], tokens: dict[str, Any]) -> Any:
    fig, axes = plt.subplots(1, 3, figsize=(spec["figure"]["width_mm"] / 25.4, spec["figure"]["height_mm"] / 25.4))
    panel_axes = dict(zip(THORP_G_GROUP_IDS, axes, strict=True))
    for panel_id, ax in panel_axes.items():
        apply_axis_theme(ax, tokens=tokens, show_xlabels=True)
        panel = spec["panels"][panel_id]
        ax.set_xlim(*panel["x_limits"])
        ax.set_ylim(*panel["y_limits"])
        ax.set_xlabel(panel["x_label"])
        ax.set_ylabel(panel["y_label"])
        if title := panel.get("title"):
            ax.set_title(title, fontsize=tokens["fonts"]["base_size_pt"] + 1, pad=8)
        if panel_id != "precipitation":
            ax.set_ylabel("")
        reference_handles = _render_height_reference(ax, frame, panel_id=panel_id)
        colors = _thorp_g_group_colors(len(THORP_G_HEIGHT_WATERSTRESS_GROUPS[THORP_G_GROUP_IDS.index(panel_id)]))
        line_handles: list[Any] = []
        ordered_series = sorted(
            {sid for sid in frame[frame["panel_id"] == panel_id]["series_id"].unique() if sid not in {"bravo_montero_2001", "palahi_2004"}},
            key=lambda value: frame[(frame["panel_id"] == panel_id) & (frame["series_id"] == value)]["order"].min(),
        )
        for order, series_id in enumerate(ordered_series):
            sub = frame[(frame["panel_id"] == panel_id) & (frame["series_id"] == series_id) & (frame["kind"] == "line")].sort_values("x")
            handle = ax.plot(sub["x"], sub["y"], color=colors[min(order, len(colors) - 1)], linewidth=2.3, label=THORP_G_STRESS_LABELS.get(str(series_id), str(series_id)))[0]
            line_handles.append(handle)
        legend_handles = reference_handles + line_handles if panel_id == "precipitation" else line_handles
        ax.legend(handles=legend_handles, loc="upper left", frameon=False, fontsize=tokens["fonts"]["base_size_pt"] - 1)
    for letter, panel_id in zip(("a", "b", "c"), THORP_G_GROUP_IDS, strict=True):
        _panel_label(panel_axes[panel_id], tokens=tokens, letter=letter)
    fig.tight_layout()
    return fig


def render_poorter_smf_bundle(*, output_dir: Path | None = None, spec_path: Path | None = None) -> FigureBundleArtifacts:
    output_dir = (output_dir or (DEFAULT_TDGM_EXAMPLE_OUTPUT_DIR / "poorter_smf")).resolve()
    spec_path = (spec_path or DEFAULT_POORTER_SMF_SPEC_PATH).resolve()
    frame = build_poorter_smf_frame()
    spec, file_paths, tokens, digest_summary = _common_bundle_state(
        output_dir=output_dir,
        spec_path=spec_path,
        frame=frame,
        digest_key="poorter_smf",
        legacy_sources=[DEFAULT_LEGACY_POORTER_SCRIPT_PATH],
        legacy_reference_script=DEFAULT_LEGACY_POORTER_SCRIPT_PATH,
    )
    fig = _render_poorter_smf(frame=frame, spec=spec, tokens=tokens)
    return _finalize_bundle(
        file_paths=file_paths,
        metadata={"legacy_digest_summary": digest_summary, "legacy_reference_script": str(DEFAULT_LEGACY_POORTER_SCRIPT_PATH)},
        fig=fig,
    )


def render_phloem_transport_bundle(*, height_key: str, output_dir: Path | None = None, spec_path: Path | None = None) -> FigureBundleArtifacts:
    output_dir = (output_dir or (DEFAULT_TDGM_EXAMPLE_OUTPUT_DIR / f"phloem_transport_{height_key}")).resolve()
    spec_path = (spec_path or DEFAULT_PHLOEM_TRANSPORT_SPEC_PATH).resolve()
    frame = build_phloem_transport_frame(height_key=height_key)
    script_path = DEFAULT_LEGACY_TDGM_OFFLINE_DIR / f"ANALYSIS_Phloem_transport_{height_key}tall.m"
    result_path = DEFAULT_LEGACY_TDGM_OFFLINE_DIR / f"RESULTS_Phloem_transport_{height_key}tall.mat"
    spec, file_paths, tokens, digest_summary = _common_bundle_state(
        output_dir=output_dir,
        spec_path=spec_path,
        frame=frame,
        digest_key=f"phloem_transport_{height_key}",
        legacy_sources=[script_path, result_path],
        legacy_reference_script=script_path,
    )
    fig = _render_phloem_transport(frame=frame, spec=spec, tokens=tokens, height_key=height_key)
    return _finalize_bundle(file_paths=file_paths, metadata={"legacy_digest_summary": digest_summary, "legacy_reference_script": str(script_path)}, fig=fig)


def render_turgor_allocation_bundle(*, output_dir: Path | None = None, spec_path: Path | None = None) -> FigureBundleArtifacts:
    output_dir = (output_dir or (DEFAULT_TDGM_EXAMPLE_OUTPUT_DIR / "turgor_allocation")).resolve()
    spec_path = (spec_path or DEFAULT_TURGOR_ALLOCATION_SPEC_PATH).resolve()
    frame = build_turgor_allocation_frame()
    script_path = DEFAULT_LEGACY_TDGM_OFFLINE_DIR / "ANALYSIS_Turgor_driven_growth.m"
    spec, file_paths, tokens, digest_summary = _common_bundle_state(
        output_dir=output_dir,
        spec_path=spec_path,
        frame=frame,
        digest_key="turgor_allocation",
        legacy_sources=[script_path, DEFAULT_LEGACY_TDGM_OFFLINE_DIR / "THORP_data_Control.mat"],
        legacy_reference_script=script_path,
    )
    fig = _render_turgor_allocation(frame=frame, spec=spec, tokens=tokens)
    return _finalize_bundle(file_paths=file_paths, metadata={"legacy_digest_summary": digest_summary, "legacy_reference_script": str(script_path)}, fig=fig)


def render_turgor_water_potential_bundle(*, output_dir: Path | None = None, spec_path: Path | None = None) -> FigureBundleArtifacts:
    output_dir = (output_dir or (DEFAULT_TDGM_EXAMPLE_OUTPUT_DIR / "turgor_water_potentials")).resolve()
    spec_path = (spec_path or DEFAULT_TURGOR_WATER_POTENTIAL_SPEC_PATH).resolve()
    frame = build_turgor_water_potential_frame()
    script_path = DEFAULT_LEGACY_TDGM_OFFLINE_DIR / "ANALYSIS_Turgor_driven_growth.m"
    spec, file_paths, tokens, digest_summary = _common_bundle_state(
        output_dir=output_dir,
        spec_path=spec_path,
        frame=frame,
        digest_key="turgor_water_potential",
        legacy_sources=[script_path, DEFAULT_LEGACY_TDGM_OFFLINE_DIR / "THORP_data_Control.mat"],
        legacy_reference_script=script_path,
    )
    fig = _render_turgor_water_potentials(frame=frame, spec=spec, tokens=tokens)
    return _finalize_bundle(file_paths=file_paths, metadata={"legacy_digest_summary": digest_summary, "legacy_reference_script": str(script_path)}, fig=fig)


def render_turgor_growth_scaling_bundle(*, output_dir: Path | None = None, spec_path: Path | None = None) -> FigureBundleArtifacts:
    output_dir = (output_dir or (DEFAULT_TDGM_EXAMPLE_OUTPUT_DIR / "turgor_growth_scaling")).resolve()
    spec_path = (spec_path or DEFAULT_TURGOR_GROWTH_SCALING_SPEC_PATH).resolve()
    frame = build_turgor_growth_scaling_frame()
    script_path = DEFAULT_LEGACY_TDGM_OFFLINE_DIR / "ANALYSIS_Turgor_driven_growth.m"
    spec, file_paths, tokens, digest_summary = _common_bundle_state(
        output_dir=output_dir,
        spec_path=spec_path,
        frame=frame,
        digest_key="turgor_growth_scaling",
        legacy_sources=[script_path, DEFAULT_LEGACY_TDGM_OFFLINE_DIR / "THORP_data_Control.mat"],
        legacy_reference_script=script_path,
    )
    fig = _render_turgor_growth_scaling(frame=frame, spec=spec, tokens=tokens)
    return _finalize_bundle(file_paths=file_paths, metadata={"legacy_digest_summary": digest_summary, "legacy_reference_script": str(script_path)}, fig=fig)


def render_max_height_for_soil_bundle(*, output_dir: Path | None = None, spec_path: Path | None = None) -> FigureBundleArtifacts:
    output_dir = (output_dir or (DEFAULT_TDGM_EXAMPLE_OUTPUT_DIR / "max_height_for_soil")).resolve()
    spec_path = (spec_path or DEFAULT_MAX_HEIGHT_SPEC_PATH).resolve()
    frame = build_max_height_for_soil_frame()
    script_path = DEFAULT_LEGACY_TDGM_OFFLINE_DIR / "ANALYSIS_Max_height_for_soil.m"
    spec, file_paths, tokens, digest_summary = _common_bundle_state(
        output_dir=output_dir,
        spec_path=spec_path,
        frame=frame,
        digest_key="max_height_for_soil",
        legacy_sources=[
            script_path,
            DEFAULT_LEGACY_TDGM_OFFLINE_DIR / "THORP_data_Control.mat",
            DEFAULT_LEGACY_TDGM_OFFLINE_DIR / "THORP_data_0.75_Precip.mat",
            DEFAULT_LEGACY_TDGM_OFFLINE_DIR / "THORP_data_0.50_Precip.mat",
            DEFAULT_LEGACY_TDGM_OFFLINE_DIR / "Taoetal2016.mat",
            DEFAULT_LEGACY_TDGM_OFFLINE_DIR / "P_minus_PET.mat",
        ],
        legacy_reference_script=script_path,
    )
    fig = _render_max_height_for_soil(frame=frame, spec=spec, tokens=tokens)
    return _finalize_bundle(file_paths=file_paths, metadata={"legacy_digest_summary": digest_summary, "legacy_reference_script": str(script_path)}, fig=fig)


def render_source_vs_sink_growth_bundle(*, output_dir: Path | None = None, spec_path: Path | None = None) -> FigureBundleArtifacts:
    output_dir = (output_dir or (DEFAULT_TDGM_EXAMPLE_OUTPUT_DIR / "source_vs_sink_growth")).resolve()
    spec_path = (spec_path or DEFAULT_SOURCE_SINK_SPEC_PATH).resolve()
    frame = build_source_vs_sink_growth_frame()
    script_path = DEFAULT_LEGACY_TDGM_THORP_G_DIR / "PLOT_source_vs_sink_G.m"
    spec, file_paths, tokens, digest_summary = _common_bundle_state(
        output_dir=output_dir,
        spec_path=spec_path,
        frame=frame,
        digest_key="source_vs_sink_growth",
        legacy_sources=[script_path, DEFAULT_LEGACY_TDGM_THORP_G_DIR / "THORP_data_Control.mat", DEFAULT_LEGACY_TDGM_THORP_G_DIR / "THORP_data_Control_Turgor.mat"],
        legacy_reference_script=script_path,
    )
    fig = _render_source_vs_sink(frame=frame, spec=spec, tokens=tokens)
    return _finalize_bundle(file_paths=file_paths, metadata={"legacy_digest_summary": digest_summary, "legacy_reference_script": str(script_path)}, fig=fig)


def render_thorp_g_growth_vs_carbon_bundle(*, output_dir: Path | None = None, spec_path: Path | None = None) -> FigureBundleArtifacts:
    output_dir = (output_dir or (DEFAULT_TDGM_EXAMPLE_OUTPUT_DIR / "thorp_g_growth_vs_carbon")).resolve()
    spec_path = (spec_path or DEFAULT_THORP_G_GROWTH_SPEC_PATH).resolve()
    frame = build_thorp_g_growth_vs_carbon_frame()
    script_path = DEFAULT_LEGACY_TDGM_THORP_G_DIR / "PLOT_G_versus_C.m"
    legacy_sources = [script_path, *[DEFAULT_LEGACY_TDGM_THORP_G_DIR / file_name for group in build_thorp_g_stress_groups() for file_name in group]]
    spec, file_paths, tokens, digest_summary = _common_bundle_state(
        output_dir=output_dir,
        spec_path=spec_path,
        frame=frame,
        digest_key="thorp_g_growth_vs_carbon",
        legacy_sources=legacy_sources,
        legacy_reference_script=script_path,
    )
    fig = _render_thorp_g_growth_vs_carbon(frame=frame, spec=spec, tokens=tokens)
    return _finalize_bundle(file_paths=file_paths, metadata={"legacy_digest_summary": digest_summary, "legacy_reference_script": str(script_path)}, fig=fig)


def render_thorp_g_growth_vs_carbon_precipitation_bundle(*, output_dir: Path | None = None, spec_path: Path | None = None) -> FigureBundleArtifacts:
    output_dir = (output_dir or (DEFAULT_TDGM_EXAMPLE_OUTPUT_DIR / "thorp_g_growth_vs_carbon_precipitation")).resolve()
    spec_path = (spec_path or DEFAULT_THORP_G_PRECIP_SPEC_PATH).resolve()
    frame = build_thorp_g_growth_vs_carbon_precipitation_frame()
    script_path = DEFAULT_LEGACY_TDGM_THORP_G_DIR / "PLOT_G_versus_C_versus_Precipitation.m"
    legacy_sources = [
        script_path,
        DEFAULT_LEGACY_TDGM_THORP_G_DIR / "THORP_data_Control_Turgor.mat",
        DEFAULT_LEGACY_TDGM_THORP_G_DIR / "THORP_data_0.8RH_Turgor.mat",
    ]
    spec, file_paths, tokens, digest_summary = _common_bundle_state(
        output_dir=output_dir,
        spec_path=spec_path,
        frame=frame,
        digest_key="thorp_g_growth_vs_carbon_precipitation",
        legacy_sources=legacy_sources,
        legacy_reference_script=script_path,
    )
    fig = _render_thorp_g_colored_growth(frame=frame, spec=spec, tokens=tokens)
    return _finalize_bundle(file_paths=file_paths, metadata={"legacy_digest_summary": digest_summary, "legacy_reference_script": str(script_path)}, fig=fig)


def render_thorp_g_growth_vs_carbon_soil_moisture_bundle(*, output_dir: Path | None = None, spec_path: Path | None = None) -> FigureBundleArtifacts:
    output_dir = (output_dir or (DEFAULT_TDGM_EXAMPLE_OUTPUT_DIR / "thorp_g_growth_vs_carbon_soil_moisture")).resolve()
    spec_path = (spec_path or DEFAULT_THORP_G_SOIL_SPEC_PATH).resolve()
    frame = build_thorp_g_growth_vs_carbon_soil_moisture_frame()
    script_path = DEFAULT_LEGACY_TDGM_THORP_G_DIR / "PLOT_G_versus_C_versus_Soilmoisture.m"
    legacy_sources = [
        script_path,
        DEFAULT_LEGACY_TDGM_THORP_G_DIR / "THORP_data_Control_Turgor.mat",
        DEFAULT_LEGACY_TDGM_THORP_G_DIR / "THORP_data_0.8RH_Turgor.mat",
    ]
    spec, file_paths, tokens, digest_summary = _common_bundle_state(
        output_dir=output_dir,
        spec_path=spec_path,
        frame=frame,
        digest_key="thorp_g_growth_vs_carbon_soil_moisture",
        legacy_sources=legacy_sources,
        legacy_reference_script=script_path,
    )
    fig = _render_thorp_g_colored_growth(frame=frame, spec=spec, tokens=tokens)
    return _finalize_bundle(file_paths=file_paths, metadata={"legacy_digest_summary": digest_summary, "legacy_reference_script": str(script_path)}, fig=fig)


def render_thorp_g_growth_vs_carbon_soil_moisture_detrended_bundle(*, output_dir: Path | None = None, spec_path: Path | None = None) -> FigureBundleArtifacts:
    output_dir = (output_dir or (DEFAULT_TDGM_EXAMPLE_OUTPUT_DIR / "thorp_g_growth_vs_carbon_soil_moisture_detrended")).resolve()
    spec_path = (spec_path or DEFAULT_THORP_G_SOIL_DETRENDED_SPEC_PATH).resolve()
    frame = build_thorp_g_growth_vs_carbon_soil_moisture_detrended_frame()
    script_path = DEFAULT_LEGACY_TDGM_THORP_G_DIR / "PLOT_G_versus_C_versus_Soilmoisture_detrended.m"
    legacy_sources = [
        script_path,
        DEFAULT_LEGACY_TDGM_THORP_G_DIR / "THORP_data_Control_Turgor.mat",
        DEFAULT_LEGACY_TDGM_THORP_G_DIR / "THORP_data_0.8RH_Turgor.mat",
    ]
    spec, file_paths, tokens, digest_summary = _common_bundle_state(
        output_dir=output_dir,
        spec_path=spec_path,
        frame=frame,
        digest_key="thorp_g_growth_vs_carbon_soil_moisture_detrended",
        legacy_sources=legacy_sources,
        legacy_reference_script=script_path,
    )
    fig = _render_thorp_g_colored_growth(frame=frame, spec=spec, tokens=tokens)
    return _finalize_bundle(file_paths=file_paths, metadata={"legacy_digest_summary": digest_summary, "legacy_reference_script": str(script_path)}, fig=fig)


def render_thorp_g_soil_moisture_vs_carbon_bundle(*, output_dir: Path | None = None, spec_path: Path | None = None) -> FigureBundleArtifacts:
    output_dir = (output_dir or (DEFAULT_TDGM_EXAMPLE_OUTPUT_DIR / "thorp_g_soil_moisture_vs_carbon")).resolve()
    spec_path = (spec_path or DEFAULT_THORP_G_SOIL_VS_CARBON_SPEC_PATH).resolve()
    frame = build_thorp_g_soil_moisture_vs_carbon_frame()
    script_path = DEFAULT_LEGACY_TDGM_THORP_G_DIR / "PLOT_S_e_versus_C.m"
    legacy_sources = [
        script_path,
        DEFAULT_LEGACY_TDGM_THORP_G_DIR / "THORP_data_Control_Turgor.mat",
        DEFAULT_LEGACY_TDGM_THORP_G_DIR / "THORP_data_0.8RH_Turgor.mat",
    ]
    spec, file_paths, tokens, digest_summary = _common_bundle_state(
        output_dir=output_dir,
        spec_path=spec_path,
        frame=frame,
        digest_key="thorp_g_soil_moisture_vs_carbon",
        legacy_sources=legacy_sources,
        legacy_reference_script=script_path,
    )
    fig = _render_thorp_g_soil_moisture_vs_carbon(frame=frame, spec=spec, tokens=tokens)
    return _finalize_bundle(file_paths=file_paths, metadata={"legacy_digest_summary": digest_summary, "legacy_reference_script": str(script_path)}, fig=fig)


def render_thorp_g_height_vs_age_turgor_threshold_bundle(*, output_dir: Path | None = None, spec_path: Path | None = None) -> FigureBundleArtifacts:
    output_dir = (output_dir or (DEFAULT_TDGM_EXAMPLE_OUTPUT_DIR / "thorp_g_height_vs_age_turgor_threshold")).resolve()
    spec_path = (spec_path or DEFAULT_THORP_G_HEIGHT_TURGOR_SPEC_PATH).resolve()
    frame = build_thorp_g_height_vs_age_turgor_threshold_frame()
    script_path = DEFAULT_LEGACY_TDGM_THORP_G_DIR / "PLOT_H_versus_age_turgorthreshold.m"
    legacy_sources = [script_path, *[DEFAULT_LEGACY_TDGM_THORP_G_DIR / file_name for file_name in THORP_G_HEIGHT_TURGOR_FILES]]
    spec, file_paths, tokens, digest_summary = _common_bundle_state(
        output_dir=output_dir,
        spec_path=spec_path,
        frame=frame,
        digest_key="thorp_g_height_vs_age_turgor_threshold",
        legacy_sources=legacy_sources,
        legacy_reference_script=script_path,
    )
    fig = _render_thorp_g_height_vs_age_turgor_threshold(frame=frame, spec=spec, tokens=tokens)
    return _finalize_bundle(file_paths=file_paths, metadata={"legacy_digest_summary": digest_summary, "legacy_reference_script": str(script_path)}, fig=fig)


def render_thorp_g_height_vs_age_waterstress_bundle(*, output_dir: Path | None = None, spec_path: Path | None = None) -> FigureBundleArtifacts:
    output_dir = (output_dir or (DEFAULT_TDGM_EXAMPLE_OUTPUT_DIR / "thorp_g_height_vs_age_waterstress")).resolve()
    spec_path = (spec_path or DEFAULT_THORP_G_HEIGHT_WATERSTRESS_SPEC_PATH).resolve()
    frame = build_thorp_g_height_vs_age_waterstress_frame()
    script_path = DEFAULT_LEGACY_TDGM_THORP_G_DIR / "PLOT_H_versus_age_waterstress.m"
    legacy_sources = [script_path, *[DEFAULT_LEGACY_TDGM_THORP_G_DIR / file_name for group in THORP_G_HEIGHT_WATERSTRESS_GROUPS for file_name in group]]
    spec, file_paths, tokens, digest_summary = _common_bundle_state(
        output_dir=output_dir,
        spec_path=spec_path,
        frame=frame,
        digest_key="thorp_g_height_vs_age_waterstress",
        legacy_sources=legacy_sources,
        legacy_reference_script=script_path,
    )
    fig = _render_thorp_g_height_vs_age_waterstress(frame=frame, spec=spec, tokens=tokens)
    return _finalize_bundle(file_paths=file_paths, metadata={"legacy_digest_summary": digest_summary, "legacy_reference_script": str(script_path)}, fig=fig)


def render_tdgm_example_figure_suite(*, output_dir: Path | None = None) -> TDGMExampleFigureSuiteArtifacts:
    root_output_dir = (output_dir or DEFAULT_TDGM_EXAMPLE_OUTPUT_DIR).resolve()
    return TDGMExampleFigureSuiteArtifacts(
        turgor_allocation=render_turgor_allocation_bundle(output_dir=root_output_dir / "turgor_allocation"),
        turgor_water_potential=render_turgor_water_potential_bundle(output_dir=root_output_dir / "turgor_water_potentials"),
        turgor_growth_scaling=render_turgor_growth_scaling_bundle(output_dir=root_output_dir / "turgor_growth_scaling"),
        max_height_for_soil=render_max_height_for_soil_bundle(output_dir=root_output_dir / "max_height_for_soil"),
        poorter_smf=render_poorter_smf_bundle(output_dir=root_output_dir / "poorter_smf"),
        phloem_transport_04m=render_phloem_transport_bundle(height_key="04m", output_dir=root_output_dir / "phloem_transport_04m"),
        phloem_transport_44m=render_phloem_transport_bundle(height_key="44m", output_dir=root_output_dir / "phloem_transport_44m"),
        source_vs_sink_growth=render_source_vs_sink_growth_bundle(output_dir=root_output_dir / "source_vs_sink_growth"),
        thorp_g_growth_vs_carbon=render_thorp_g_growth_vs_carbon_bundle(output_dir=root_output_dir / "thorp_g_growth_vs_carbon"),
        thorp_g_growth_vs_carbon_precipitation=render_thorp_g_growth_vs_carbon_precipitation_bundle(output_dir=root_output_dir / "thorp_g_growth_vs_carbon_precipitation"),
        thorp_g_growth_vs_carbon_soil_moisture=render_thorp_g_growth_vs_carbon_soil_moisture_bundle(output_dir=root_output_dir / "thorp_g_growth_vs_carbon_soil_moisture"),
        thorp_g_growth_vs_carbon_soil_moisture_detrended=render_thorp_g_growth_vs_carbon_soil_moisture_detrended_bundle(output_dir=root_output_dir / "thorp_g_growth_vs_carbon_soil_moisture_detrended"),
        thorp_g_soil_moisture_vs_carbon=render_thorp_g_soil_moisture_vs_carbon_bundle(output_dir=root_output_dir / "thorp_g_soil_moisture_vs_carbon"),
        thorp_g_height_vs_age_turgor_threshold=render_thorp_g_height_vs_age_turgor_threshold_bundle(output_dir=root_output_dir / "thorp_g_height_vs_age_turgor_threshold"),
        thorp_g_height_vs_age_waterstress=render_thorp_g_height_vs_age_waterstress_bundle(output_dir=root_output_dir / "thorp_g_height_vs_age_waterstress"),
    )
