from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import json

import matplotlib
import numpy as np
import pandas as pd
from matplotlib.cm import ScalarMappable
from matplotlib.colors import Normalize

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from stomatal_optimiaztion.domains.thorp.examples.adapter import (
    DEFAULT_LEGACY_THORP_EXAMPLE_DIR as ADAPTER_LEGACY_THORP_EXAMPLE_DIR,
    GWT_SWEEP_DEPTHS_M,
    deep_uptake_fraction,
    load_gwt_sweep_scenario,
    load_main_text_scenario,
    simulated_groundwater_depth,
)
from stomatal_optimiaztion.domains.thorp.examples.empirical import (
    DEFAULT_ALLOCATION_SCRIPT_PATH,
    DEFAULT_MASS_FRACTION_SCRIPT_PATH,
    allocation_reference_curves,
    mass_fraction_reference_curves,
)
from stomatal_optimiaztion.shared_plotkit import (
    FigureBundleArtifacts,
    apply_axis_theme,
    frame_digest,
    load_yaml,
    resolve_figure_paths,
)

REPO_ROOT = Path(__file__).resolve().parents[5]
DEFAULT_LEGACY_THORP_EXAMPLE_DIR = ADAPTER_LEGACY_THORP_EXAMPLE_DIR
DEFAULT_THORP_EXAMPLE_OUTPUT_DIR = REPO_ROOT / "out" / "thorp" / "example_figures"
DEFAULT_MASS_FRACTION_SPEC_PATH = REPO_ROOT / "configs" / "plotkit" / "thorp" / "mass_fractions.yaml"
DEFAULT_ALLOCATION_FRACTION_SPEC_PATH = REPO_ROOT / "configs" / "plotkit" / "thorp" / "allocation_fractions.yaml"
DEFAULT_STRUCTURAL_TRAIT_SPEC_PATH = REPO_ROOT / "configs" / "plotkit" / "thorp" / "structural_traits.yaml"
DEFAULT_GROUNDWATER_SWEEP_SPEC_PATH = REPO_ROOT / "configs" / "plotkit" / "thorp" / "groundwater_sweep.yaml"
DEFAULT_ECO2_LIGHT_SPEC_PATH = REPO_ROOT / "configs" / "plotkit" / "thorp" / "eco2_light_limited_mass_fractions.yaml"

EXPECTED_FRAME_DIGESTS: dict[str, str | None] = {
    "mass_fractions": "9f1a744b3e9647dd3e6e5f63fd74d4384d877cc9a1947d6a1d0480ff0901954e",
    "allocation_fractions": "3ab7e965c3004b1fa3ba8a1b75ae49ebd3dd32185b0e5cc2446a7aeba586fef0",
    "structural_traits": "9ddb0ff426ceaab56016629f15dc5a9151f9b4b9085ba744294a4ee0a70c66ab",
    "groundwater_sweep": "85e4b2c44faa3788ff03785aaa9e7786d18b411d3608b7da350a94cd151ee1af",
    "eco2_light_limited": "023761f64da5f2629f325c5a9502d2f1c48397d93198d9fef20389ef4b85b592",
}

MAIN_SCENARIO_STYLES = {
    "control": {"label": "Control", "color": "#111111"},
    "precip_75": {"label": "75% Precipitation", "color": "#C44536"},
    "precip_50": {"label": "50% Precipitation", "color": "#D99E0B"},
    "precip_50_gwt_2m": {"label": "50% Precipitation + 2 m GWTD", "color": "#7B2CBF"},
    "light_limited": {"label": "Light-limited", "color": "#2A9D8F"},
    "eco2_600": {"label": "eCO2 600 ppm", "color": "#F77F00"},
}
GWT_TICK_DEPTHS = (2, 8, 16, 24, 32, 48, 80)
REFERENCE_IMAGE_BY_DIGEST_KEY = {
    "mass_fractions": "FIGURE_3_Control_and_reduced_Precip_(MF).jpg",
    "allocation_fractions": "FIGURE_4_Control_and_reduced_Precip_(allocation_fractions).jpg",
    "structural_traits": "FIGURE_2_Control_(H_Z_LAI_etc).jpg",
    "groundwater_sweep": "FIGURE_5_GW_(Z_RMF_fraction_E_from_below_2_m).jpg",
    "eco2_light_limited": "FIGURE_6_Control_and_eCO2_and_Light_limited_(MF).jpg",
}


@dataclass(frozen=True)
class ThorpExampleFigureSuiteArtifacts:
    mass_fractions: FigureBundleArtifacts
    allocation_fractions: FigureBundleArtifacts
    structural_traits: FigureBundleArtifacts
    groundwater_sweep: FigureBundleArtifacts
    eco2_light_limited: FigureBundleArtifacts

    def to_summary(self) -> dict[str, Any]:
        return {
            "mass_fractions": self.mass_fractions.to_summary(),
            "allocation_fractions": self.allocation_fractions.to_summary(),
            "structural_traits": self.structural_traits.to_summary(),
            "groundwater_sweep": self.groundwater_sweep.to_summary(),
            "eco2_light_limited": self.eco2_light_limited.to_summary(),
        }


def _support_dir_from_legacy_path(legacy_path: Path) -> Path:
    support_dir = legacy_path / "Simulations_and_additional_code_to_plot"
    return support_dir if support_dir.exists() else legacy_path


def _main_text_figure_dir(legacy_path: Path) -> Path:
    support_dir = _support_dir_from_legacy_path(legacy_path)
    return support_dir.parent / "Figures" / "Main Text Figs"


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


def _common_bundle_prep(
    *,
    output_dir: Path,
    spec_path: Path,
    figure_id: str,
    resolved_spec: dict[str, Any],
    frame: pd.DataFrame,
) -> tuple[dict[str, Any], dict[str, Path], dict[str, Any]]:
    spec = load_yaml(spec_path)
    tokens_path = _tokens_path_from_spec(spec_path, spec)
    tokens = load_yaml(tokens_path)
    file_paths = resolve_figure_paths(output_dir, figure_id)
    output_dir.mkdir(parents=True, exist_ok=True)

    frame.to_csv(file_paths["data_csv"], index=False)
    file_paths["spec_copy"].write_text(spec_path.read_text(encoding="utf-8"), encoding="utf-8")
    file_paths["resolved_spec"].write_text(json.dumps(resolved_spec, indent=2), encoding="utf-8")
    file_paths["tokens_copy"].write_text(tokens_path.read_text(encoding="utf-8"), encoding="utf-8")
    return spec, file_paths, tokens


def _common_bundle_state(
    *,
    output_dir: Path,
    spec_path: Path,
    frame: pd.DataFrame,
    digest_key: str,
    source_mats: list[Path],
    legacy_reference_image: Path | None = None,
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
    resolved_spec["meta"]["source_mats"] = [str(path) for path in source_mats]
    if legacy_reference_image is not None:
        resolved_spec["meta"]["legacy_reference_image"] = str(legacy_reference_image)
    spec, file_paths, tokens = _common_bundle_prep(
        output_dir=output_dir,
        spec_path=spec_path,
        figure_id=figure_id,
        resolved_spec=resolved_spec,
        frame=frame,
    )
    return spec, file_paths, tokens, digest_summary


def _main_text_source_paths(*, legacy_example_dir: Path, scenario_ids: tuple[str, ...]) -> list[Path]:
    support_dir = _support_dir_from_legacy_path(legacy_example_dir)
    return [support_dir / load_main_text_scenario(scenario_id, legacy_dir=support_dir).mat_path.name for scenario_id in scenario_ids]


def _load_main_text_scenarios(*, legacy_example_dir: Path) -> dict[str, Any]:
    support_dir = _support_dir_from_legacy_path(legacy_example_dir)
    return {
        scenario_id: load_main_text_scenario(scenario_id, legacy_dir=support_dir)
        for scenario_id in ("control", "precip_75", "precip_50", "precip_50_gwt_2m", "light_limited", "eco2_600")
    }


def _mass_fraction_panel_records(
    *,
    scenario_ids: tuple[str, ...],
    legacy_example_dir: Path,
    include_smf_height_reference: bool,
) -> pd.DataFrame:
    scenarios = _load_main_text_scenarios(legacy_example_dir=legacy_example_dir)
    refs = mass_fraction_reference_curves(script_path=DEFAULT_MASS_FRACTION_SCRIPT_PATH)
    log_mid = np.arange(2.0, 7.0, 0.1, dtype=float) + 0.05
    records: list[dict[str, Any]] = []

    for metric in ("lmf", "smf", "rmf"):
        panel_id = f"{metric}_absolute"
        for x, y in zip(refs["px"], refs[f"{metric}_all"], strict=True):
            records.append({"panel_id": panel_id, "series_id": f"{metric}_empirical_center", "kind": "reference", "x": float(x), "y": float(y)})
        for x, y in zip(refs["px"], refs[f"{metric}_all"] + refs[f"{metric}_sd"], strict=True):
            records.append({"panel_id": panel_id, "series_id": f"{metric}_empirical_upper", "kind": "reference_upper", "x": float(x), "y": float(y)})
        for x, y in zip(refs["px"], refs[f"{metric}_all"] - refs[f"{metric}_sd"], strict=True):
            records.append({"panel_id": panel_id, "series_id": f"{metric}_empirical_lower", "kind": "reference_lower", "x": float(x), "y": float(y)})
        for x, y in zip(refs["px"], refs[f"{metric}_gym"], strict=True):
            records.append({"panel_id": panel_id, "series_id": f"{metric}_gymnosperm", "kind": "gymnosperm", "x": float(x), "y": float(y)})
        for x, y in zip(refs["px"], refs[f"{metric}_ang"], strict=True):
            records.append({"panel_id": panel_id, "series_id": f"{metric}_angiosperm", "kind": "angiosperm", "x": float(x), "y": float(y)})

        control_x, control_y = scenarios["control"].mean_fraction_by_log_mass(fraction=metric)
        for scenario_id in scenario_ids:
            x_vals, y_vals = scenarios[scenario_id].mean_fraction_by_log_mass(fraction=metric)
            for x, y in zip(x_vals, y_vals, strict=True):
                records.append({"panel_id": panel_id, "series_id": scenario_id, "kind": "scenario", "x": float(x), "y": float(y)})
            if scenario_id != "control":
                for x, y in zip(control_x, y_vals - control_y, strict=True):
                    records.append({"panel_id": f"{metric}_difference", "series_id": scenario_id, "kind": "difference", "x": float(x), "y": float(y)})

    if include_smf_height_reference:
        h_vec = np.array([7.5, 30.0], dtype=float)
        d_ref = 1.0
        b0 = 64.6
        c0 = 0.6411
        rho_cw = 1.4e4
        xi = 0.5
        d_vec = d_ref * (h_vec / b0) ** (1.0 / c0)
        c_w_vec = rho_cw * xi * d_vec**2 * h_vec
        dm_w_vec = c_w_vec * 12.0 / 0.5
        smf_ref = dm_w_vec[:, None] / (10**log_mid[None, :])
        for height, y_curve in zip(h_vec, smf_ref, strict=True):
            for x, y in zip(log_mid, y_curve, strict=True):
                records.append({"panel_id": "smf_absolute", "series_id": f"height_reference_{height:.1f}m", "kind": "height_reference", "x": float(x), "y": float(y)})

    return pd.DataFrame.from_records(records)


def _allocation_means_for_scenario(scenario: Any, *, dyears: int = 10) -> pd.DataFrame:
    tau_r = 9.6e7
    tau_fr = 0.65 * 365 * 24 * 3600
    f_fr = 0.2
    f_c = 0.28

    growth = scenario.u_ts[1:] * (1.0 - f_c)
    years = min(100, int(np.ceil(scenario.t_ts[-1] / 3600 / 24 / 365)))
    if years < dyears:
        return pd.DataFrame(columns=["age_year", "leaf", "wood", "fine_root"])

    t_half = scenario.t_ts[:-1] + 0.5 * np.diff(scenario.t_ts)
    u_l = scenario.u_l_ts[1:]
    u_r = scenario.u_r_h_ts[1:] + scenario.u_r_v_ts[1:]
    c_r_tot = np.sum(scenario.c_r_by_layer_ts, axis=0)[1:]
    with np.errstate(divide="ignore", invalid="ignore"):
        u_fr = f_fr * (u_r + (c_r_tot / tau_fr - c_r_tot / tau_r) / growth)
    u_fr = np.minimum(u_fr, u_r)
    u_fr[growth == 0] = 0.0
    u_w = scenario.u_sw_ts[1:] + u_r - u_fr

    age_year: list[float] = []
    leaf_mean: list[float] = []
    wood_mean: list[float] = []
    fine_root_mean: list[float] = []
    for idx in range(years // dyears):
        t_begin = 3600 * 24 * 365 * dyears * idx
        t_end = 3600 * 24 * 365 * dyears * (idx + 1)
        selector = (t_half >= t_begin) & (t_half < t_end)
        if not np.any(selector):
            continue
        g_sel = growth[selector]
        if np.sum(g_sel) <= 0:
            continue
        u_l_mean = float(np.sum(np.nan_to_num(u_l[selector]) * g_sel) / np.sum(g_sel))
        u_w_mean = float(np.sum(np.nan_to_num(u_w[selector]) * g_sel) / np.sum(g_sel))
        u_fr_mean = float(np.sum(np.nan_to_num(u_fr[selector]) * g_sel) / np.sum(g_sel))
        total = u_l_mean + u_w_mean + u_fr_mean
        if total <= 0:
            continue
        age_year.append(float(dyears * (idx + 1)))
        leaf_mean.append(u_l_mean / total)
        wood_mean.append(u_w_mean / total)
        fine_root_mean.append(u_fr_mean / total)

    frame = pd.DataFrame({"age_year": age_year, "leaf": leaf_mean, "wood": wood_mean, "fine_root": fine_root_mean})
    frame = frame[frame["age_year"] > np.ceil(scenario.t_mass_threshold_ts / 3600 / 24 / 365)].reset_index(drop=True)
    return frame


def build_mass_fraction_frame(*, legacy_example_dir: Path | None = None) -> pd.DataFrame:
    legacy_example_dir = (legacy_example_dir or DEFAULT_LEGACY_THORP_EXAMPLE_DIR).resolve()
    return _mass_fraction_panel_records(
        scenario_ids=("control", "precip_75", "precip_50", "precip_50_gwt_2m"),
        legacy_example_dir=legacy_example_dir,
        include_smf_height_reference=False,
    )


def build_allocation_fraction_frame(*, legacy_example_dir: Path | None = None) -> pd.DataFrame:
    legacy_example_dir = (legacy_example_dir or DEFAULT_LEGACY_THORP_EXAMPLE_DIR).resolve()
    refs = allocation_reference_curves(script_path=DEFAULT_ALLOCATION_SCRIPT_PATH)
    scenarios = _load_main_text_scenarios(legacy_example_dir=legacy_example_dir)
    records: list[dict[str, Any]] = []
    for metric_key, prefix in (("leaf", "leaf"), ("wood", "wood"), ("fine_root", "fine_root")):
        combined = refs[f"{metric_key}_combined"]
        conf = refs[f"{metric_key}_conf"]
        for x, y in zip(refs["age_mid_bin"], combined, strict=True):
            records.append({"panel_id": metric_key, "series_id": f"{prefix}_combined", "kind": "combined", "x": float(x), "y": float(y)})
        for x, y in zip(refs["age_mid_bin"], combined + 2.576 * conf, strict=True):
            records.append({"panel_id": metric_key, "series_id": f"{prefix}_upper", "kind": "combined_upper", "x": float(x), "y": float(y)})
        for x, y in zip(refs["age_mid_bin"], combined - 2.576 * conf, strict=True):
            records.append({"panel_id": metric_key, "series_id": f"{prefix}_lower", "kind": "combined_lower", "x": float(x), "y": float(y)})
        for x, y in zip(refs["years"], refs[f"{metric_key}_boreal"], strict=True):
            records.append({"panel_id": metric_key, "series_id": f"{prefix}_boreal", "kind": "boreal", "x": float(x), "y": float(y)})
        for x, y in zip(refs["years"], refs[f"{metric_key}_temperate"], strict=True):
            records.append({"panel_id": metric_key, "series_id": f"{prefix}_temperate", "kind": "temperate", "x": float(x), "y": float(y)})

    for scenario_id in ("control", "precip_75", "precip_50", "precip_50_gwt_2m"):
        scenario_frame = _allocation_means_for_scenario(scenarios[scenario_id])
        for metric_key in ("leaf", "wood", "fine_root"):
            for x, y in zip(scenario_frame["age_year"], scenario_frame[metric_key], strict=True):
                records.append({"panel_id": metric_key, "series_id": scenario_id, "kind": "scenario", "x": float(x), "y": float(y)})
    return pd.DataFrame.from_records(records)


def build_structural_trait_frame(*, legacy_example_dir: Path | None = None) -> pd.DataFrame:
    legacy_example_dir = (legacy_example_dir or DEFAULT_LEGACY_THORP_EXAMPLE_DIR).resolve()
    scenarios = _load_main_text_scenarios(legacy_example_dir=legacy_example_dir)
    records: list[dict[str, Any]] = []
    for scenario_id in ("control", "precip_75", "precip_50", "precip_50_gwt_2m"):
        scenario = scenarios[scenario_id]
        z95 = scenario.root_depth_fraction(fraction=0.95, depth_axis="mid", cap_at_water_table=False)
        t_agg = scenario.four_week_mean(scenario.t_year_ts)
        h_agg = scenario.four_week_mean(scenario.h_ts)
        z_agg = scenario.four_week_mean(z95)
        dm_agg = scenario.four_week_mean(np.log10(scenario.dm_tot_g_ts))
        lai_agg = scenario.four_week_mean(scenario.lai_ts)
        la_agg = scenario.four_week_mean(scenario.la_ts)
        sa_agg = scenario.four_week_mean(scenario.sa_ts)
        hv_agg = scenario.four_week_mean(scenario.huber_value_ts)
        valid = t_agg >= scenario.t_mass_threshold_ts / 3600 / 24 / 365

        for x, y in zip(t_agg[valid], h_agg[valid], strict=True):
            records.append({"panel_id": "depth_time", "series_id": f"{scenario_id}_height", "kind": "height", "x": float(x), "y": float(y)})
        for x, y in zip(t_agg[valid], -z_agg[valid], strict=True):
            records.append({"panel_id": "depth_time", "series_id": f"{scenario_id}_z95", "kind": "root_depth", "x": float(x), "y": float(y)})
        for x, y in zip(t_agg[valid], lai_agg[valid], strict=True):
            records.append({"panel_id": "lai_time", "series_id": scenario_id, "kind": "scenario", "x": float(x), "y": float(y)})
        for x, y in zip(dm_agg[valid], h_agg[valid], strict=True):
            records.append({"panel_id": "depth_mass", "series_id": f"{scenario_id}_height", "kind": "height", "x": float(x), "y": float(y)})
        for x, y in zip(dm_agg[valid], -z_agg[valid], strict=True):
            records.append({"panel_id": "depth_mass", "series_id": f"{scenario_id}_z95", "kind": "root_depth", "x": float(x), "y": float(y)})
        for x, y in zip(dm_agg[valid], lai_agg[valid], strict=True):
            records.append({"panel_id": "lai_mass", "series_id": scenario_id, "kind": "scenario", "x": float(x), "y": float(y)})
        for x, y in zip(sa_agg[valid], la_agg[valid], strict=True):
            records.append({"panel_id": "leaf_vs_sapwood", "series_id": scenario_id, "kind": "scenario", "x": float(x), "y": float(y)})
        for x, y in zip(dm_agg[valid], hv_agg[valid], strict=True):
            records.append({"panel_id": "huber_value", "series_id": scenario_id, "kind": "scenario", "x": float(x), "y": float(y)})
    return pd.DataFrame.from_records(records)


def build_groundwater_sweep_frame(*, legacy_example_dir: Path | None = None) -> pd.DataFrame:
    legacy_example_dir = (legacy_example_dir or DEFAULT_LEGACY_THORP_EXAMPLE_DIR).resolve()
    support_dir = _support_dir_from_legacy_path(legacy_example_dir)
    refs = mass_fraction_reference_curves(script_path=DEFAULT_MASS_FRACTION_SCRIPT_PATH)
    records: list[dict[str, Any]] = []
    z95_mean: list[float] = []
    z95_std: list[float] = []
    z99_mean: list[float] = []
    z99_std: list[float] = []
    gwtd_mean: list[float] = []
    f2m_mean: list[float] = []

    for depth in GWT_SWEEP_DEPTHS_M:
        scenario = load_gwt_sweep_scenario(depth, legacy_dir=support_dir)
        z95 = scenario.root_depth_fraction(fraction=0.95, depth_axis="bottom", cap_at_water_table=True)
        z99 = scenario.root_depth_fraction(fraction=0.995, depth_axis="bottom", cap_at_water_table=True)
        gwtd = simulated_groundwater_depth(scenario)
        selector = (scenario.h_ts >= 29.0) & (scenario.h_ts <= 30.0)
        if np.any(selector):
            z95_mean.append(float(np.mean(z95[selector])))
            z95_std.append(float(np.std(z95[selector])))
            z99_mean.append(float(np.mean(z99[selector])))
            z99_std.append(float(np.std(z99[selector])))
            gwtd_mean.append(float(np.mean(gwtd[selector])))
            f2m_mean.append(deep_uptake_fraction(scenario, h_min=29.0, h_max=30.0))
        if depth in GWT_TICK_DEPTHS:
            for x, y in zip(scenario.t_year_ts, -z95, strict=True):
                records.append({"panel_id": "depth_time", "series_id": f"gwt_{depth}m", "kind": "scenario", "x": float(x), "y": float(y)})
            for x, y in zip(scenario.h_ts, -z95, strict=True):
                records.append({"panel_id": "depth_height", "series_id": f"gwt_{depth}m", "kind": "scenario", "x": float(x), "y": float(y)})
            for x, y in zip(scenario.h_ts, scenario.rmf_ts, strict=True):
                records.append({"panel_id": "rmf_height", "series_id": f"gwt_{depth}m", "kind": "scenario", "x": float(x), "y": float(y)})

    for x, y, sd in zip(gwtd_mean, z95_mean, z95_std, strict=True):
        records.append({"panel_id": "gwtd_vs_root_depth", "series_id": "z95_mean", "kind": "mean", "x": float(x), "y": float(-y)})
        records.append({"panel_id": "gwtd_vs_root_depth", "series_id": "z95_upper", "kind": "mean_upper", "x": float(x), "y": float(-(y + 2 * sd))})
        records.append({"panel_id": "gwtd_vs_root_depth", "series_id": "z95_lower", "kind": "mean_lower", "x": float(x), "y": float(-(y - 2 * sd))})
    for x, y, sd in zip(gwtd_mean, z99_mean, z99_std, strict=True):
        records.append({"panel_id": "gwtd_vs_root_depth", "series_id": "z99_mean", "kind": "mean", "x": float(x), "y": float(-y)})
        records.append({"panel_id": "gwtd_vs_root_depth", "series_id": "z99_upper", "kind": "mean_upper", "x": float(x), "y": float(-(y + 2 * sd))})
        records.append({"panel_id": "gwtd_vs_root_depth", "series_id": "z99_lower", "kind": "mean_lower", "x": float(x), "y": float(-(y - 2 * sd))})
    for x, y in zip(gwtd_mean, f2m_mean, strict=True):
        records.append({"panel_id": "deep_uptake_fraction", "series_id": "fraction_from_below_2m", "kind": "summary", "x": float(x), "y": float(y)})
    for x, y in zip(refs["px"], refs["rmf_all"] + refs["rmf_sd"], strict=True):
        records.append({"panel_id": "rmf_height", "series_id": "rmf_empirical_upper", "kind": "reference_upper", "x": float(10**x), "y": float(y)})
    for x, y in zip(refs["px"], refs["rmf_all"] - refs["rmf_sd"], strict=True):
        records.append({"panel_id": "rmf_height", "series_id": "rmf_empirical_lower", "kind": "reference_lower", "x": float(10**x), "y": float(y)})
    return pd.DataFrame.from_records(records)


def build_eco2_light_limited_frame(*, legacy_example_dir: Path | None = None) -> pd.DataFrame:
    legacy_example_dir = (legacy_example_dir or DEFAULT_LEGACY_THORP_EXAMPLE_DIR).resolve()
    return _mass_fraction_panel_records(
        scenario_ids=("control", "light_limited", "eco2_600"),
        legacy_example_dir=legacy_example_dir,
        include_smf_height_reference=True,
    )


def _scenario_order_for_frame(frame: pd.DataFrame) -> list[str]:
    ordered: list[str] = []
    for candidate in MAIN_SCENARIO_STYLES:
        if candidate in set(frame["series_id"]):
            ordered.append(candidate)
    return ordered


def _plot_mass_fraction_panel(
    ax: Any,
    *,
    panel_frame: pd.DataFrame,
    panel_spec: dict[str, Any],
    tokens: dict[str, Any],
    handles: dict[str, Any],
) -> None:
    fonts = tokens["fonts"]
    styling = panel_spec.get("styling", {})
    apply_axis_theme(ax, tokens=tokens, show_xlabels=True)
    ax.set_xlim(panel_spec["x_limits"])
    ax.set_ylim(panel_spec["y_limits"])
    ax.set_xlabel(panel_spec["x_label"], fontsize=fonts["axis_label_size_pt"])
    ax.set_ylabel(panel_spec["y_label"], fontsize=fonts["axis_label_size_pt"])
    ax.set_title(panel_spec["title"], fontsize=fonts["title_size_pt"], loc="left", pad=6)

    if panel_spec.get("difference_panel", False):
        ax.axhline(0.0, color=styling.get("baseline_color", "#7A7A7A"), linewidth=1.0)

    if {"reference_upper", "reference_lower"} <= set(panel_frame["kind"]):
        upper = panel_frame[panel_frame["kind"] == "reference_upper"].sort_values("x")
        lower = panel_frame[panel_frame["kind"] == "reference_lower"].sort_values("x")
        fill = ax.fill_between(
            upper["x"],
            lower["y"],
            upper["y"],
            color=styling.get("reference_fill_color", "#CFCFCF"),
            alpha=float(styling.get("reference_fill_alpha", 0.65)),
            linewidth=0.0,
        )
        handles.setdefault("Empirical range", fill)
    if "reference" in set(panel_frame["kind"]):
        ref = panel_frame[panel_frame["kind"] == "reference"].sort_values("x")
        line = ax.plot(
            ref["x"],
            ref["y"],
            color=styling.get("reference_line_color", "#6B6B6B"),
            linewidth=float(styling.get("reference_linewidth_pt", 1.6)),
        )[0]
        handles.setdefault("Empirical center", line)
    if "gymnosperm" in set(panel_frame["kind"]):
        gym = panel_frame[panel_frame["kind"] == "gymnosperm"].sort_values("x")
        line = ax.plot(gym["x"], gym["y"], color="#2B9348", linestyle="--", linewidth=1.8)[0]
        handles.setdefault("Woody Gymnosperms", line)
    if "angiosperm" in set(panel_frame["kind"]):
        ang = panel_frame[panel_frame["kind"] == "angiosperm"].sort_values("x")
        line = ax.plot(ang["x"], ang["y"], color="#4361EE", linestyle="-.", linewidth=1.8)[0]
        handles.setdefault("Woody Angiosperms", line)
    for series_id in sorted(series for series in set(panel_frame["series_id"]) if series.startswith("height_reference_")):
        ref = panel_frame[panel_frame["series_id"] == series_id].sort_values("x")
        label = f"Allometric height anchor ({series_id.split('_')[-1]})"
        line = ax.plot(ref["x"], ref["y"], color="#118AB2", linestyle=":", linewidth=1.6)[0]
        handles.setdefault(label, line)

    for scenario_id in _scenario_order_for_frame(panel_frame):
        scenario_frame = panel_frame[panel_frame["series_id"] == scenario_id].sort_values("x")
        if scenario_frame.empty:
            continue
        style = MAIN_SCENARIO_STYLES[scenario_id]
        line = ax.plot(
            scenario_frame["x"],
            scenario_frame["y"],
            color=style["color"],
            linewidth=float(styling.get("scenario_linewidth_pt", 2.2)),
        )[0]
        handles.setdefault(style["label"], line)


def _mass_fraction_bundle(
    *,
    frame: pd.DataFrame,
    legacy_example_dir: Path,
    output_dir: Path,
    spec_path: Path,
    digest_key: str,
) -> FigureBundleArtifacts:
    legacy_reference_image = _main_text_figure_dir(legacy_example_dir) / REFERENCE_IMAGE_BY_DIGEST_KEY[digest_key]
    scenario_ids = tuple(_scenario_order_for_frame(frame))
    spec, file_paths, tokens, digest_summary = _common_bundle_state(
        output_dir=output_dir,
        spec_path=spec_path,
        frame=frame,
        digest_key=digest_key,
        source_mats=_main_text_source_paths(legacy_example_dir=legacy_example_dir, scenario_ids=scenario_ids),
        legacy_reference_image=legacy_reference_image if legacy_reference_image.exists() else None,
    )

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
    fig.subplots_adjust(left=0.08, right=0.85, bottom=0.10, top=0.93, wspace=0.24, hspace=0.30)
    handles: dict[str, Any] = {}
    for ax, panel_id, letter in zip(axes.reshape(-1), spec["panel_order"], "abcdef", strict=True):
        _plot_mass_fraction_panel(
            ax,
            panel_frame=frame[frame["panel_id"] == panel_id],
            panel_spec=spec["panels"][panel_id],
            tokens=tokens,
            handles=handles,
        )
        _panel_label(ax, tokens=tokens, letter=letter)

    legend_order = spec["legend"]["order"]
    fig.legend(
        [handles[label] for label in legend_order if label in handles],
        [label for label in legend_order if label in handles],
        loc=spec["legend"]["loc"],
        bbox_to_anchor=tuple(spec["legend"]["bbox_to_anchor"]),
        frameon=tokens["legend"]["frameon"],
        fontsize=tokens["fonts"]["legend_size_pt"],
    )
    fig.suptitle(spec["meta"]["title"], x=0.46, y=0.985, fontsize=tokens["fonts"]["title_size_pt"] + 2, fontweight="bold")
    fig.savefig(file_paths["png"], dpi=dpi, transparent=spec["export"]["transparent"], facecolor=tokens["figure"]["background"])
    fig.savefig(file_paths["pdf"], dpi=dpi, transparent=spec["export"]["transparent"], facecolor=tokens["figure"]["background"])
    plt.close(fig)

    metadata = {
        "figure_id": spec["meta"]["id"],
        "legacy_digest_summary": digest_summary,
        "legacy_reference_image": str(legacy_reference_image) if legacy_reference_image.exists() else None,
        "outputs": {key: str(value) for key, value in file_paths.items()},
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


def _plot_allocation_panel(
    ax: Any,
    *,
    panel_frame: pd.DataFrame,
    panel_spec: dict[str, Any],
    tokens: dict[str, Any],
    handles: dict[str, Any],
) -> None:
    fonts = tokens["fonts"]
    styling = panel_spec.get("styling", {})
    apply_axis_theme(ax, tokens=tokens, show_xlabels=True)
    ax.set_xlim(panel_spec["x_limits"])
    ax.set_ylim(panel_spec["y_limits"])
    ax.set_xlabel(panel_spec["x_label"], fontsize=fonts["axis_label_size_pt"])
    ax.set_ylabel(panel_spec["y_label"], fontsize=fonts["axis_label_size_pt"])
    ax.set_title(panel_spec["title"], fontsize=fonts["title_size_pt"], loc="left", pad=6)

    upper = panel_frame[panel_frame["kind"] == "combined_upper"].sort_values("x")
    lower = panel_frame[panel_frame["kind"] == "combined_lower"].sort_values("x")
    combined = panel_frame[panel_frame["kind"] == "combined"].sort_values("x")
    fill = ax.fill_between(
        upper["x"],
        lower["y"],
        upper["y"],
        color=styling.get("confidence_fill_color", "#CFCFCF"),
        alpha=float(styling.get("confidence_fill_alpha", 0.65)),
        linewidth=0.0,
    )
    handles.setdefault("Confidence range of observations", fill)
    line = ax.plot(
        combined["x"],
        combined["y"],
        color=styling.get("combined_color", "#6B6B6B"),
        linewidth=float(styling.get("combined_linewidth_pt", 1.8)),
    )[0]
    handles.setdefault("Combined regression", line)
    for kind, label, color, linestyle in (
        ("boreal", "Boreal", "#2B9348", "--"),
        ("temperate", "Temperate", "#4361EE", "-."),
    ):
        curve = panel_frame[panel_frame["kind"] == kind].sort_values("x")
        handle = ax.plot(curve["x"], curve["y"], color=color, linestyle=linestyle, linewidth=1.8)[0]
        handles.setdefault(label, handle)

    for scenario_id in ("control", "precip_75", "precip_50", "precip_50_gwt_2m"):
        curve = panel_frame[panel_frame["series_id"] == scenario_id].sort_values("x")
        if curve.empty:
            continue
        style = MAIN_SCENARIO_STYLES[scenario_id]
        handle = ax.plot(curve["x"], curve["y"], color=style["color"], linewidth=float(styling.get("scenario_linewidth_pt", 2.2)))[0]
        handles.setdefault(style["label"], handle)


def render_mass_fraction_bundle(
    *,
    legacy_example_dir: Path | None = None,
    output_dir: Path | None = None,
    spec_path: Path | None = None,
) -> FigureBundleArtifacts:
    legacy_example_dir = (legacy_example_dir or DEFAULT_LEGACY_THORP_EXAMPLE_DIR).resolve()
    output_dir = (output_dir or DEFAULT_THORP_EXAMPLE_OUTPUT_DIR / "mass_fractions").resolve()
    spec_path = (spec_path or DEFAULT_MASS_FRACTION_SPEC_PATH).resolve()
    frame = build_mass_fraction_frame(legacy_example_dir=legacy_example_dir)
    return _mass_fraction_bundle(
        frame=frame,
        legacy_example_dir=legacy_example_dir,
        output_dir=output_dir,
        spec_path=spec_path,
        digest_key="mass_fractions",
    )


def render_allocation_fraction_bundle(
    *,
    legacy_example_dir: Path | None = None,
    output_dir: Path | None = None,
    spec_path: Path | None = None,
) -> FigureBundleArtifacts:
    legacy_example_dir = (legacy_example_dir or DEFAULT_LEGACY_THORP_EXAMPLE_DIR).resolve()
    output_dir = (output_dir or DEFAULT_THORP_EXAMPLE_OUTPUT_DIR / "allocation_fractions").resolve()
    spec_path = (spec_path or DEFAULT_ALLOCATION_FRACTION_SPEC_PATH).resolve()
    frame = build_allocation_fraction_frame(legacy_example_dir=legacy_example_dir)
    legacy_reference_image = _main_text_figure_dir(legacy_example_dir) / REFERENCE_IMAGE_BY_DIGEST_KEY["allocation_fractions"]
    spec, file_paths, tokens, digest_summary = _common_bundle_state(
        output_dir=output_dir,
        spec_path=spec_path,
        frame=frame,
        digest_key="allocation_fractions",
        source_mats=_main_text_source_paths(
            legacy_example_dir=legacy_example_dir,
            scenario_ids=("control", "precip_75", "precip_50", "precip_50_gwt_2m"),
        ),
        legacy_reference_image=legacy_reference_image if legacy_reference_image.exists() else None,
    )
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
    fig.subplots_adjust(left=0.11, right=0.85, bottom=0.08, top=0.94, hspace=0.20)
    handles: dict[str, Any] = {}
    for ax, panel_id, letter in zip(np.atleast_1d(axes).reshape(-1), spec["panel_order"], "abc", strict=True):
        _plot_allocation_panel(
            ax,
            panel_frame=frame[frame["panel_id"] == panel_id],
            panel_spec=spec["panels"][panel_id],
            tokens=tokens,
            handles=handles,
        )
        _panel_label(ax, tokens=tokens, letter=letter)
    legend_order = spec["legend"]["order"]
    fig.legend(
        [handles[label] for label in legend_order if label in handles],
        [label for label in legend_order if label in handles],
        loc=spec["legend"]["loc"],
        bbox_to_anchor=tuple(spec["legend"]["bbox_to_anchor"]),
        frameon=tokens["legend"]["frameon"],
        fontsize=tokens["fonts"]["legend_size_pt"],
    )
    fig.suptitle(spec["meta"]["title"], x=0.45, y=0.985, fontsize=tokens["fonts"]["title_size_pt"] + 2, fontweight="bold")
    fig.savefig(file_paths["png"], dpi=dpi, transparent=spec["export"]["transparent"], facecolor=tokens["figure"]["background"])
    fig.savefig(file_paths["pdf"], dpi=dpi, transparent=spec["export"]["transparent"], facecolor=tokens["figure"]["background"])
    plt.close(fig)

    metadata = {
        "figure_id": spec["meta"]["id"],
        "legacy_digest_summary": digest_summary,
        "legacy_reference_image": str(legacy_reference_image) if legacy_reference_image.exists() else None,
        "outputs": {key: str(value) for key, value in file_paths.items()},
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


def _plot_depth_panel(
    ax: Any,
    *,
    panel_frame: pd.DataFrame,
    panel_spec: dict[str, Any],
    tokens: dict[str, Any],
    handles: dict[str, Any],
) -> None:
    fonts = tokens["fonts"]
    apply_axis_theme(ax, tokens=tokens, show_xlabels=True)
    ax_right = ax.twinx()
    ax_right.set_facecolor(tokens["figure"]["background"])
    ax.set_xlim(panel_spec["x_limits"])
    ax.set_ylim(panel_spec["left_y_limits"])
    ax_right.set_ylim(panel_spec["right_y_limits"])
    ax.set_xlabel(panel_spec["x_label"], fontsize=fonts["axis_label_size_pt"])
    ax.set_ylabel(panel_spec["left_y_label"], fontsize=fonts["axis_label_size_pt"])
    ax_right.set_ylabel(panel_spec["right_y_label"], fontsize=fonts["axis_label_size_pt"])
    ax.set_title(panel_spec["title"], fontsize=fonts["title_size_pt"], loc="left", pad=6)
    ax_right.tick_params(direction="out", labelsize=fonts["base_size_pt"], colors=tokens["axes"]["tick_color"])
    ax_right.spines["right"].set_color(tokens["axes"]["spine_color"])
    ax_right.spines["right"].set_linewidth(tokens["axes"]["spine_width_pt"])
    ax_right.spines["top"].set_visible(False)
    ax_right.spines["left"].set_visible(False)
    ax_right.spines["bottom"].set_visible(False)
    ax_right.grid(False)
    ax_right.axhline(0.0, color="#7A7A7A", linestyle=":", linewidth=1.0)

    for scenario_id in ("control", "precip_75", "precip_50", "precip_50_gwt_2m"):
        height_frame = panel_frame[panel_frame["series_id"] == f"{scenario_id}_height"].sort_values("x")
        depth_frame = panel_frame[panel_frame["series_id"] == f"{scenario_id}_z95"].sort_values("x")
        if height_frame.empty and depth_frame.empty:
            continue
        style = MAIN_SCENARIO_STYLES[scenario_id]
        if not height_frame.empty:
            handle = ax.plot(height_frame["x"], height_frame["y"], color=style["color"], linestyle="--", linewidth=2.0)[0]
            handles.setdefault(f"{style['label']} height", handle)
        if not depth_frame.empty:
            handle = ax_right.plot(depth_frame["x"], depth_frame["y"], color=style["color"], linewidth=2.0)[0]
            handles.setdefault(f"{style['label']} root depth", handle)


def _plot_scenario_panel(
    ax: Any,
    *,
    panel_frame: pd.DataFrame,
    panel_spec: dict[str, Any],
    tokens: dict[str, Any],
    handles: dict[str, Any],
) -> None:
    fonts = tokens["fonts"]
    apply_axis_theme(ax, tokens=tokens, show_xlabels=True)
    ax.set_xlim(panel_spec["x_limits"])
    ax.set_ylim(panel_spec["y_limits"])
    ax.set_xlabel(panel_spec["x_label"], fontsize=fonts["axis_label_size_pt"])
    ax.set_ylabel(panel_spec["y_label"], fontsize=fonts["axis_label_size_pt"])
    ax.set_title(panel_spec["title"], fontsize=fonts["title_size_pt"], loc="left", pad=6)
    for scenario_id in ("control", "precip_75", "precip_50", "precip_50_gwt_2m"):
        scenario_frame = panel_frame[panel_frame["series_id"] == scenario_id].sort_values("x")
        if scenario_frame.empty:
            continue
        style = MAIN_SCENARIO_STYLES[scenario_id]
        handle = ax.plot(scenario_frame["x"], scenario_frame["y"], color=style["color"], linewidth=2.1)[0]
        handles.setdefault(style["label"], handle)


def render_structural_trait_bundle(
    *,
    legacy_example_dir: Path | None = None,
    output_dir: Path | None = None,
    spec_path: Path | None = None,
) -> FigureBundleArtifacts:
    legacy_example_dir = (legacy_example_dir or DEFAULT_LEGACY_THORP_EXAMPLE_DIR).resolve()
    output_dir = (output_dir or DEFAULT_THORP_EXAMPLE_OUTPUT_DIR / "structural_traits").resolve()
    spec_path = (spec_path or DEFAULT_STRUCTURAL_TRAIT_SPEC_PATH).resolve()
    frame = build_structural_trait_frame(legacy_example_dir=legacy_example_dir)
    legacy_reference_image = _main_text_figure_dir(legacy_example_dir) / REFERENCE_IMAGE_BY_DIGEST_KEY["structural_traits"]
    spec, file_paths, tokens, digest_summary = _common_bundle_state(
        output_dir=output_dir,
        spec_path=spec_path,
        frame=frame,
        digest_key="structural_traits",
        source_mats=_main_text_source_paths(
            legacy_example_dir=legacy_example_dir,
            scenario_ids=("control", "precip_75", "precip_50", "precip_50_gwt_2m"),
        ),
        legacy_reference_image=legacy_reference_image if legacy_reference_image.exists() else None,
    )
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
    fig.subplots_adjust(left=0.09, right=0.84, bottom=0.09, top=0.94, wspace=0.30, hspace=0.35)
    handles: dict[str, Any] = {}
    for ax, panel_id, letter in zip(axes.reshape(-1), spec["panel_order"], "abcdef", strict=True):
        panel_spec = spec["panels"][panel_id]
        panel_frame = frame[frame["panel_id"] == panel_id]
        if panel_spec.get("twin_axis", False):
            _plot_depth_panel(ax, panel_frame=panel_frame, panel_spec=panel_spec, tokens=tokens, handles=handles)
        else:
            _plot_scenario_panel(ax, panel_frame=panel_frame, panel_spec=panel_spec, tokens=tokens, handles=handles)
        _panel_label(ax, tokens=tokens, letter=letter)
    legend_order = spec["legend"]["order"]
    fig.legend(
        [handles[label] for label in legend_order if label in handles],
        [label for label in legend_order if label in handles],
        loc=spec["legend"]["loc"],
        bbox_to_anchor=tuple(spec["legend"]["bbox_to_anchor"]),
        frameon=tokens["legend"]["frameon"],
        fontsize=tokens["fonts"]["legend_size_pt"],
    )
    fig.suptitle(spec["meta"]["title"], x=0.44, y=0.985, fontsize=tokens["fonts"]["title_size_pt"] + 2, fontweight="bold")
    fig.savefig(file_paths["png"], dpi=dpi, transparent=spec["export"]["transparent"], facecolor=tokens["figure"]["background"])
    fig.savefig(file_paths["pdf"], dpi=dpi, transparent=spec["export"]["transparent"], facecolor=tokens["figure"]["background"])
    plt.close(fig)

    metadata = {
        "figure_id": spec["meta"]["id"],
        "legacy_digest_summary": digest_summary,
        "legacy_reference_image": str(legacy_reference_image) if legacy_reference_image.exists() else None,
        "outputs": {key: str(value) for key, value in file_paths.items()},
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


def _gwt_color(depth_m: int) -> Any:
    cmap = plt.get_cmap("cividis_r")
    norm = Normalize(vmin=min(GWT_TICK_DEPTHS), vmax=max(GWT_TICK_DEPTHS))
    return cmap(norm(depth_m))


def render_groundwater_sweep_bundle(
    *,
    legacy_example_dir: Path | None = None,
    output_dir: Path | None = None,
    spec_path: Path | None = None,
) -> FigureBundleArtifacts:
    legacy_example_dir = (legacy_example_dir or DEFAULT_LEGACY_THORP_EXAMPLE_DIR).resolve()
    output_dir = (output_dir or DEFAULT_THORP_EXAMPLE_OUTPUT_DIR / "groundwater_sweep").resolve()
    spec_path = (spec_path or DEFAULT_GROUNDWATER_SWEEP_SPEC_PATH).resolve()
    frame = build_groundwater_sweep_frame(legacy_example_dir=legacy_example_dir)
    support_dir = _support_dir_from_legacy_path(legacy_example_dir)
    legacy_reference_image = _main_text_figure_dir(legacy_example_dir) / REFERENCE_IMAGE_BY_DIGEST_KEY["groundwater_sweep"]
    source_mats = [support_dir / f"THORP_data_0.50_Precip_GWT_{depth}_m.mat" for depth in GWT_SWEEP_DEPTHS_M]
    spec, file_paths, tokens, digest_summary = _common_bundle_state(
        output_dir=output_dir,
        spec_path=spec_path,
        frame=frame,
        digest_key="groundwater_sweep",
        source_mats=source_mats,
        legacy_reference_image=legacy_reference_image if legacy_reference_image.exists() else None,
    )
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
    fig.subplots_adjust(left=0.08, right=0.86, bottom=0.09, top=0.94, wspace=0.32, hspace=0.35)
    flat_axes = axes.reshape(-1)
    handles: dict[str, Any] = {}

    for idx, ax in enumerate(flat_axes):
        if idx >= len(spec["panel_order"]):
            ax.axis("off")
            continue
        panel_id = spec["panel_order"][idx]
        panel_spec = spec["panels"][panel_id]
        panel_frame = frame[frame["panel_id"] == panel_id]
        apply_axis_theme(ax, tokens=tokens, show_xlabels=True)
        ax.set_title(panel_spec["title"], fontsize=tokens["fonts"]["title_size_pt"], loc="left", pad=6)
        ax.set_xlabel(panel_spec["x_label"], fontsize=tokens["fonts"]["axis_label_size_pt"])
        ax.set_ylabel(panel_spec["y_label"], fontsize=tokens["fonts"]["axis_label_size_pt"])
        _panel_label(ax, tokens=tokens, letter=chr(97 + idx))

        if panel_id in {"depth_time", "depth_height"}:
            ax.set_xlim(panel_spec["x_limits"])
            ax.set_ylim(panel_spec["y_limits"])
            for depth_m in GWT_TICK_DEPTHS:
                scenario_frame = panel_frame[panel_frame["series_id"] == f"gwt_{depth_m}m"].sort_values("x")
                if scenario_frame.empty:
                    continue
                handle = ax.plot(scenario_frame["x"], scenario_frame["y"], color=_gwt_color(depth_m), linewidth=1.8)[0]
                handles.setdefault(f"GWTD {depth_m} m", handle)
        elif panel_id == "gwtd_vs_root_depth":
            ax.set_xscale("log")
            ax.set_yscale("log")
            ax.set_xlim(panel_spec["x_limits"])
            ax.set_ylim(panel_spec["y_limits"])
            ax.plot(panel_spec["identity_line"], panel_spec["identity_line"], ":", color="#666666", linewidth=1.5)
            for prefix, label, color in (("z95", "Mean Z95", "#0A9396"), ("z99", "Mean Z99.5", "#005F73")):
                mean_frame = panel_frame[panel_frame["series_id"] == f"{prefix}_mean"].sort_values("x")
                upper_frame = panel_frame[panel_frame["series_id"] == f"{prefix}_upper"].sort_values("x")
                lower_frame = panel_frame[panel_frame["series_id"] == f"{prefix}_lower"].sort_values("x")
                fill = ax.fill_between(mean_frame["x"], np.abs(lower_frame["y"]), np.abs(upper_frame["y"]), color=color, alpha=0.18, linewidth=0.0)
                handle = ax.plot(mean_frame["x"], np.abs(mean_frame["y"]), color=color, marker="o", linewidth=2.0)[0]
                handles.setdefault(f"{label} range", fill)
                handles.setdefault(label, handle)
        elif panel_id == "deep_uptake_fraction":
            ax.set_xlim(panel_spec["x_limits"])
            ax.set_ylim(panel_spec["y_limits"])
            summary_frame = panel_frame.sort_values("x")
            handle = ax.plot(summary_frame["x"], summary_frame["y"], color="#0A9396", marker="o", linewidth=2.0)[0]
            handles.setdefault("Fraction of E from below 2 m", handle)
        elif panel_id == "rmf_height":
            ax.set_xlim(panel_spec["x_limits"])
            ax.set_ylim(panel_spec["y_limits"])
            upper = panel_frame[panel_frame["kind"] == "reference_upper"].sort_values("x")
            lower = panel_frame[panel_frame["kind"] == "reference_lower"].sort_values("x")
            fill = ax.fill_between(upper["x"], lower["y"], upper["y"], color="#CFCFCF", alpha=0.65, linewidth=0.0)
            handles.setdefault("Empirical RMF range", fill)
            for depth_m in GWT_TICK_DEPTHS:
                scenario_frame = panel_frame[panel_frame["series_id"] == f"gwt_{depth_m}m"].sort_values("x")
                if scenario_frame.empty:
                    continue
                handle = ax.plot(scenario_frame["x"], scenario_frame["y"], color=_gwt_color(depth_m), linewidth=1.8)[0]
                handles.setdefault(f"GWTD {depth_m} m", handle)
        else:
            raise ValueError(f"Unknown panel id: {panel_id}")

    sm = ScalarMappable(norm=Normalize(vmin=min(GWT_TICK_DEPTHS), vmax=max(GWT_TICK_DEPTHS)), cmap=plt.get_cmap("cividis_r"))
    colorbar = fig.colorbar(sm, ax=[flat_axes[0], flat_axes[1], flat_axes[4]], fraction=0.028, pad=0.02)
    colorbar.set_label("GWTD [m]", fontsize=tokens["fonts"]["axis_label_size_pt"])
    colorbar.set_ticks(list(GWT_TICK_DEPTHS))

    legend_order = spec["legend"]["order"]
    fig.legend(
        [handles[label] for label in legend_order if label in handles],
        [label for label in legend_order if label in handles],
        loc=spec["legend"]["loc"],
        bbox_to_anchor=tuple(spec["legend"]["bbox_to_anchor"]),
        frameon=tokens["legend"]["frameon"],
        fontsize=tokens["fonts"]["legend_size_pt"],
    )
    fig.suptitle(spec["meta"]["title"], x=0.42, y=0.985, fontsize=tokens["fonts"]["title_size_pt"] + 2, fontweight="bold")
    fig.savefig(file_paths["png"], dpi=dpi, transparent=spec["export"]["transparent"], facecolor=tokens["figure"]["background"])
    fig.savefig(file_paths["pdf"], dpi=dpi, transparent=spec["export"]["transparent"], facecolor=tokens["figure"]["background"])
    plt.close(fig)

    metadata = {
        "figure_id": spec["meta"]["id"],
        "legacy_digest_summary": digest_summary,
        "legacy_reference_image": str(legacy_reference_image) if legacy_reference_image.exists() else None,
        "outputs": {key: str(value) for key, value in file_paths.items()},
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


def render_eco2_light_limited_bundle(
    *,
    legacy_example_dir: Path | None = None,
    output_dir: Path | None = None,
    spec_path: Path | None = None,
) -> FigureBundleArtifacts:
    legacy_example_dir = (legacy_example_dir or DEFAULT_LEGACY_THORP_EXAMPLE_DIR).resolve()
    output_dir = (output_dir or DEFAULT_THORP_EXAMPLE_OUTPUT_DIR / "eco2_light_limited").resolve()
    spec_path = (spec_path or DEFAULT_ECO2_LIGHT_SPEC_PATH).resolve()
    frame = build_eco2_light_limited_frame(legacy_example_dir=legacy_example_dir)
    return _mass_fraction_bundle(
        frame=frame,
        legacy_example_dir=legacy_example_dir,
        output_dir=output_dir,
        spec_path=spec_path,
        digest_key="eco2_light_limited",
    )


def render_thorp_example_figure_suite(
    *,
    legacy_example_dir: Path | None = None,
    output_dir: Path | None = None,
    mass_fraction_spec_path: Path | None = None,
    allocation_fraction_spec_path: Path | None = None,
    structural_trait_spec_path: Path | None = None,
    groundwater_sweep_spec_path: Path | None = None,
    eco2_light_spec_path: Path | None = None,
) -> ThorpExampleFigureSuiteArtifacts:
    legacy_example_dir = (legacy_example_dir or DEFAULT_LEGACY_THORP_EXAMPLE_DIR).resolve()
    output_dir = (output_dir or DEFAULT_THORP_EXAMPLE_OUTPUT_DIR).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    return ThorpExampleFigureSuiteArtifacts(
        mass_fractions=render_mass_fraction_bundle(
            legacy_example_dir=legacy_example_dir,
            output_dir=output_dir / "mass_fractions",
            spec_path=mass_fraction_spec_path,
        ),
        allocation_fractions=render_allocation_fraction_bundle(
            legacy_example_dir=legacy_example_dir,
            output_dir=output_dir / "allocation_fractions",
            spec_path=allocation_fraction_spec_path,
        ),
        structural_traits=render_structural_trait_bundle(
            legacy_example_dir=legacy_example_dir,
            output_dir=output_dir / "structural_traits",
            spec_path=structural_trait_spec_path,
        ),
        groundwater_sweep=render_groundwater_sweep_bundle(
            legacy_example_dir=legacy_example_dir,
            output_dir=output_dir / "groundwater_sweep",
            spec_path=groundwater_sweep_spec_path,
        ),
        eco2_light_limited=render_eco2_light_limited_bundle(
            legacy_example_dir=legacy_example_dir,
            output_dir=output_dir / "eco2_light_limited",
            spec_path=eco2_light_spec_path,
        ),
    )
