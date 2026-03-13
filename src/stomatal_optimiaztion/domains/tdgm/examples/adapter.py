from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import re

import numpy as np
from scipy.io import loadmat

from stomatal_optimiaztion.domains.tdgm.turgor_growth import turgor_driven_growth_rate
from stomatal_optimiaztion.domains.thorp.matlab_io import load_mat

REPO_ROOT = Path(__file__).resolve().parents[5]
WORKSPACE_ROOT = REPO_ROOT.parents[1]

DEFAULT_LEGACY_TDGM_OFFLINE_DIR = (
    WORKSPACE_ROOT
    / "00. Stomatal Optimization"
    / "TDGM"
    / "example"
    / "Supplementary Code __ TDGM Offline Simulations"
)
DEFAULT_LEGACY_TDGM_THORP_G_ROOT = (
    WORKSPACE_ROOT
    / "00. Stomatal Optimization"
    / "TDGM"
    / "example"
    / "Supplementary Code __THORP_code_v1.4"
)
DEFAULT_LEGACY_TDGM_THORP_G_DIR = DEFAULT_LEGACY_TDGM_THORP_G_ROOT / "Simulations_and_code_to_plot"
DEFAULT_LEGACY_POORTER_SCRIPT_PATH = DEFAULT_LEGACY_TDGM_OFFLINE_DIR / "PLOT_Poorter_SMF.m"

DEFAULT_PHI = 3.34
H_MIN_THORP_M = 5.0
SOIL_LAYER_MIDPOINTS_M = np.array(
    [
        0.0498,
        0.1679,
        0.3297,
        0.5514,
        0.8551,
        1.2711,
        1.8410,
        2.6217,
        3.6913,
        5.1565,
        7.1639,
        9.9139,
        13.6813,
        18.8424,
        25.9129,
    ],
    dtype=float,
)
SOIL_LAYER_WIDTHS_M = np.array(
    [
        0.0997,
        0.1365,
        0.1871,
        0.2563,
        0.3511,
        0.4809,
        0.6589,
        0.9026,
        1.2365,
        1.6940,
        2.3207,
        3.1793,
        4.3555,
        5.9668,
        8.1742,
    ],
    dtype=float,
)
MAX_HEIGHT_FILE_ORDER = (
    "THORP_data_Control.mat",
    "THORP_data_0.75_Precip.mat",
    "THORP_data_0.50_Precip.mat",
)
SOURCE_SINK_FILE_ORDER = (
    "THORP_data_Control.mat",
    "THORP_data_Control_Turgor.mat",
)
SOURCE_SINK_STRESS_FILE_ORDER = (
    "THORP_data_Control_Turgor.mat",
    "THORP_data_0.9Prec_Turgor.mat",
    "THORP_data_0.8Prec_Turgor.mat",
    "THORP_data_0.9RH_Turgor.mat",
    "THORP_data_0.8RH_Turgor.mat",
    "THORP_data_0.9Prec_0.9RH_Turgor.mat",
)
PHLOEM_TRANSPORT_RESULTS = {
    "04m": DEFAULT_LEGACY_TDGM_OFFLINE_DIR / "RESULTS_Phloem_transport_04mtall.mat",
    "44m": DEFAULT_LEGACY_TDGM_OFFLINE_DIR / "RESULTS_Phloem_transport_44mtall.mat",
}
ANNUAL_PRECIP_RELATIVE_SEQUENCE = np.array(
    [1.3414, 1.0943, 0.9543, 1.3878, 0.8516, 0.9895, 0.5682, 0.9850, 0.9098, 0.9182],
    dtype=float,
)


def _vec(mat: dict[str, object], key: str) -> np.ndarray:
    return np.asarray(mat[key], dtype=float).reshape(-1)


def _mat(mat: dict[str, object], key: str) -> np.ndarray:
    return np.asarray(mat[key], dtype=float)


def _moving_average_centered(values: np.ndarray, window: int) -> np.ndarray:
    window = max(1, int(window))
    if window == 1:
        return np.asarray(values, dtype=float)
    kernel = np.ones(window, dtype=float)
    return np.convolve(values, kernel, mode="same") / np.convolve(np.ones_like(values, dtype=float), kernel, mode="same")


def _linear_regression(x: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    slope = float(np.sum((x - np.mean(x)) * (y - np.mean(y))) / np.sum((x - np.mean(x)) ** 2))
    intercept = float(np.mean(y) - slope * np.mean(x))
    return slope, intercept


def _power_law_fit(x: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    slope, intercept = _linear_regression(np.log(x), np.log(y))
    return float(np.exp(intercept)), float(slope)


def _parse_matlab_matrix(body: str) -> np.ndarray:
    cleaned = re.sub(r"%.*", "", body).replace("...", " ")
    parsed_rows = [np.fromstring(row.strip().replace(",", " "), sep=" ", dtype=float) for row in cleaned.split(";") if row.strip()]
    widths = [row.size for row in parsed_rows if row.size > 0]
    if not widths:
        return np.empty((0, 0), dtype=float)
    row_width = max(set(widths), key=widths.count)
    normalized_rows: list[np.ndarray] = []
    for row in parsed_rows:
        if row.size == 0:
            continue
        if row.size % row_width != 0:
            raise ValueError(f"Unable to normalize MATLAB matrix row width {row.size} to {row_width}")
        for idx in range(0, row.size, row_width):
            normalized_rows.append(row[idx : idx + row_width])
    return np.vstack(normalized_rows)


def _extract_matlab_matrix(script_text: str, variable_name: str) -> np.ndarray:
    match = re.search(rf"{re.escape(variable_name)}\s*=\s*\[(.*?)\];", script_text, flags=re.DOTALL)
    if match is None:
        raise ValueError(f"Could not extract MATLAB matrix '{variable_name}'")
    return _parse_matlab_matrix(match.group(1))


def _split_restart_curve(xy: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    x = np.asarray(xy[:, 0], dtype=float)
    restart_idx = int(np.where(np.diff(x) == np.min(np.diff(x)))[0][0] + 1)
    return xy[:restart_idx], xy[restart_idx:]


@dataclass(frozen=True)
class TDGMLegacyScenario:
    scenario_id: str
    mat_path: Path
    t_ts: np.ndarray
    h_ts: np.ndarray
    d_ts: np.ndarray
    d_hw_ts: np.ndarray
    w_ts: np.ndarray
    c_l_ts: np.ndarray
    c_sw_ts: np.ndarray
    c_hw_ts: np.ndarray
    c_nsc_ts: np.ndarray
    c_r_h_by_layer_ts: np.ndarray
    c_r_v_by_layer_ts: np.ndarray
    u_l_ts: np.ndarray
    u_sw_ts: np.ndarray
    u_r_h_ts: np.ndarray
    u_r_v_ts: np.ndarray
    u_ts: np.ndarray
    psi_l_ts: np.ndarray
    psi_rc0_ts: np.ndarray
    psi_rc_ts: np.ndarray
    psi_s_ts: np.ndarray
    psi_soil_by_layer_ts: np.ndarray

    @property
    def t_year_ts(self) -> np.ndarray:
        return self.t_ts / 365.0 / 24.0 / 3600.0

    @property
    def c_r_by_layer_ts(self) -> np.ndarray:
        return self.c_r_h_by_layer_ts + self.c_r_v_by_layer_ts

    @property
    def c_r_ts(self) -> np.ndarray:
        return np.sum(self.c_r_by_layer_ts, axis=0)

    @property
    def c_w_ts(self) -> np.ndarray:
        return self.c_sw_ts + self.c_hw_ts

    @property
    def c_tree_ts(self) -> np.ndarray:
        return self.c_r_ts + self.c_l_ts + self.c_w_ts

    @property
    def dm_w_g_ts(self) -> np.ndarray:
        return self.c_w_ts * 12.0 / 0.5

    @property
    def dm_r_g_ts(self) -> np.ndarray:
        return self.c_r_ts * 12.0 / 0.55

    @property
    def dm_l_g_ts(self) -> np.ndarray:
        return self.c_l_ts * 12.0 / 0.5

    @property
    def dm_tot_g_ts(self) -> np.ndarray:
        return self.dm_w_g_ts + self.dm_r_g_ts + self.dm_l_g_ts

    @property
    def g_rate_ts(self) -> np.ndarray:
        return self.u_ts * (1.0 - 0.28)

    @property
    def lai_ts(self) -> np.ndarray:
        la_ts = 0.08 * self.c_l_ts
        return la_ts / DEFAULT_PHI / (self.w_ts**2)

    @property
    def huber_value_ts(self) -> np.ndarray:
        la_ts = 0.08 * self.c_l_ts
        sa_ts = np.pi / 4.0 * (self.d_ts**2 - self.d_hw_ts**2)
        return sa_ts / la_ts


def load_legacy_tdgm_scenario(*, mat_path: Path, scenario_id: str) -> TDGMLegacyScenario:
    mat = load_mat(mat_path)
    return TDGMLegacyScenario(
        scenario_id=scenario_id,
        mat_path=mat_path.resolve(),
        t_ts=_vec(mat, "t_stor"),
        h_ts=_vec(mat, "H_stor"),
        d_ts=_vec(mat, "D_stor"),
        d_hw_ts=_vec(mat, "D_hw_stor"),
        w_ts=_vec(mat, "W_stor"),
        c_l_ts=_vec(mat, "c_l_stor"),
        c_sw_ts=_vec(mat, "c_sw_stor"),
        c_hw_ts=_vec(mat, "c_hw_stor"),
        c_nsc_ts=_vec(mat, "c_NSC_stor"),
        c_r_h_by_layer_ts=_mat(mat, "c_r_H_stor"),
        c_r_v_by_layer_ts=_mat(mat, "c_r_V_stor"),
        u_l_ts=_vec(mat, "u_l_stor"),
        u_sw_ts=_vec(mat, "u_sw_stor"),
        u_r_h_ts=_vec(mat, "u_r_H_stor"),
        u_r_v_ts=_vec(mat, "u_r_V_stor"),
        u_ts=_vec(mat, "U_stor"),
        psi_l_ts=_vec(mat, "P_x_l_stor"),
        psi_rc0_ts=_vec(mat, "P_x_r0_stor"),
        psi_rc_ts=_vec(mat, "P_x_r_stor"),
        psi_s_ts=_vec(mat, "P_x_s_stor"),
        psi_soil_by_layer_ts=_mat(mat, "P_soil_stor"),
    )


@lru_cache(maxsize=None)
def load_offline_scenario(filename: str) -> TDGMLegacyScenario:
    return load_legacy_tdgm_scenario(
        mat_path=DEFAULT_LEGACY_TDGM_OFFLINE_DIR / filename,
        scenario_id=Path(filename).stem,
    )


@lru_cache(maxsize=None)
def load_thorp_g_scenario(filename: str) -> TDGMLegacyScenario:
    return load_legacy_tdgm_scenario(
        mat_path=DEFAULT_LEGACY_TDGM_THORP_G_DIR / filename,
        scenario_id=Path(filename).stem,
    )


@dataclass(frozen=True)
class TurgorAllocationRegression:
    h_filtered_m: np.ndarray
    u_sw_1yr: np.ndarray
    u_sw_10yr: np.ndarray
    h_curve_m: np.ndarray
    u_sw_curve: np.ndarray
    regime_break_m: float


def fit_turgor_allocation_regression(
    *,
    scenario: TDGMLegacyScenario | None = None,
    h_curve_m: np.ndarray | None = None,
) -> TurgorAllocationRegression:
    scenario = scenario or load_offline_scenario("THORP_data_Control.mat")
    dt_s = float(np.mean(np.diff(scenario.t_ts)))
    n_dt = int(np.floor((365.0 * 24.0 * 3600.0) / dt_s))
    u_sw_1yr = _moving_average_centered(scenario.u_sw_ts, n_dt)
    u_sw_10yr = _moving_average_centered(scenario.u_sw_ts, 10 * n_dt)

    selector = scenario.h_ts >= H_MIN_THORP_M
    h_filtered = scenario.h_ts[selector]
    u_sw_1yr = u_sw_1yr[selector]
    u_sw_10yr = u_sw_10yr[selector]

    regime_break = float(h_filtered[int(np.nanargmax(u_sw_10yr))])
    regime1 = h_filtered < regime_break
    regime2 = h_filtered > regime_break
    a1, b1 = _power_law_fit(h_filtered[regime1], u_sw_10yr[regime1])
    a2, b2 = _power_law_fit(h_filtered[regime2] - regime_break, u_sw_10yr[regime2])

    def u_sw1(h: np.ndarray) -> np.ndarray:
        return a1 * h**b1

    def u_sw2(h: np.ndarray) -> np.ndarray:
        h = np.asarray(h, dtype=float)
        delta_h = np.maximum(h - regime_break, 0.0)
        values = np.full(h.shape, np.nanmax(u_sw_10yr), dtype=float)
        positive = delta_h > 0.0
        values[positive] = np.minimum(np.nanmax(u_sw_10yr), a2 * delta_h[positive] ** b2)
        return values

    dx_smooth = 12.0
    d_h = 0.1

    def u_disc(h: np.ndarray) -> np.ndarray:
        return np.where(h < regime_break, u_sw1(h), u_sw2(h))

    u_bottom = float(u_disc(np.array([regime_break - dx_smooth / 2.0]))[0])
    u_top = float(u_disc(np.array([regime_break + dx_smooth / 2.0]))[0])
    du_dh_bottom = float(
        (u_disc(np.array([regime_break - dx_smooth / 2.0]))[0] - u_disc(np.array([regime_break - dx_smooth / 2.0 - d_h]))[0])
        / d_h
    )
    du_dh_top = float(
        (u_disc(np.array([regime_break + dx_smooth / 2.0]))[0] - u_disc(np.array([regime_break + dx_smooth / 2.0 - d_h]))[0])
        / d_h
    )
    dfdx_bottom = du_dh_bottom * dx_smooth / (u_top - u_bottom)
    dfdx_top = du_dh_top * dx_smooth / (u_top - u_bottom)
    coeff_a = dfdx_bottom
    coeff_c = dfdx_top - 2.0 + coeff_a
    coeff_b = 1.0 - coeff_a - coeff_c

    def u_curve(h: np.ndarray) -> np.ndarray:
        h = np.asarray(h, dtype=float)
        curve = np.empty_like(h)
        low = h < regime_break - dx_smooth / 2.0
        high = h >= regime_break + dx_smooth / 2.0
        mid = ~(low | high)
        curve[low] = u_sw1(h[low])
        curve[high] = u_sw2(h[high])
        x_mid = (h[mid] - regime_break + dx_smooth / 2.0) / dx_smooth
        blend = coeff_a * x_mid + coeff_b * x_mid**2 + coeff_c * x_mid**3
        curve[mid] = u_bottom + (u_top - u_bottom) * blend
        return curve

    h_curve = np.asarray(
        h_curve_m if h_curve_m is not None else np.arange(1.0, 500.0 + 0.1, 0.1, dtype=float),
        dtype=float,
    )
    return TurgorAllocationRegression(
        h_filtered_m=np.asarray(h_filtered, dtype=float),
        u_sw_1yr=np.asarray(u_sw_1yr, dtype=float),
        u_sw_10yr=np.asarray(u_sw_10yr, dtype=float),
        h_curve_m=h_curve,
        u_sw_curve=u_curve(h_curve),
        regime_break_m=regime_break,
    )


@dataclass(frozen=True)
class XylemPotentialRegression:
    h_scatter_m: np.ndarray
    psi_rc0_scatter_mpa: np.ndarray
    psi_s0_scatter_mpa: np.ndarray
    psi_rc_scatter_mpa: np.ndarray
    psi_s_scatter_mpa: np.ndarray
    h_curve_m: np.ndarray
    psi_rc0_fit_mpa: np.ndarray
    psi_s0_fit_mpa: np.ndarray
    psi_rc_fit_mpa: np.ndarray
    psi_s_fit_mpa: np.ndarray


def regress_xylem_potentials(
    *,
    scenario: TDGMLegacyScenario | None = None,
    h_break_m: float | None = None,
    h_curve_m: np.ndarray | None = None,
) -> XylemPotentialRegression:
    scenario = scenario or load_offline_scenario("THORP_data_Control.mat")
    rho = 998.0
    g_grav = 9.81
    h_break_m = float(h_break_m) if h_break_m is not None else np.inf
    psi_s0_ts = scenario.psi_rc0_ts - 1e-6 * rho * g_grav * scenario.h_ts

    potentials = (
        scenario.psi_rc0_ts,
        scenario.psi_rc_ts,
        psi_s0_ts,
        scenario.psi_s_ts,
    )
    h_filtered = scenario.h_ts[scenario.h_ts < h_break_m]
    fit_series: list[np.ndarray] = []
    d_h = 2.5
    h_curve = np.asarray(h_curve_m if h_curve_m is not None else np.arange(1.0, 100.0 + 1.0, 1.0, dtype=float), dtype=float)
    for potential in potentials:
        y_filtered = np.asarray(potential[scenario.h_ts < h_break_m], dtype=float)
        h_bin = np.arange(H_MIN_THORP_M, min(d_h * np.ceil(np.max(h_filtered) / d_h), d_h * np.ceil(np.max(h_filtered) / d_h)) + d_h, d_h)
        h_bin = (h_bin[:-1] + h_bin[1:]) / 2.0
        if h_bin.size == 0:
            h_bin = np.array([H_MIN_THORP_M], dtype=float)
        p_bin = np.full(h_bin.shape, np.nan, dtype=float)
        for idx, h_center in enumerate(h_bin):
            selector = (h_filtered < (h_center + d_h / 2.0)) & (h_filtered >= (h_center - d_h / 2.0))
            h_local = h_filtered[selector]
            p_local = y_filtered[selector]
            if h_local.size < 2:
                continue
            slope_local, _ = _linear_regression(h_local, p_local)
            residual = p_local - slope_local * h_local
            p_bin[idx] = float(np.mean(residual) + 1.96 * np.std(residual) + slope_local * np.mean(h_local))
        valid = np.isfinite(p_bin)
        slope, intercept = _linear_regression(h_bin[valid], p_bin[valid])
        fit_series.append(intercept + slope * h_curve)
    return XylemPotentialRegression(
        h_scatter_m=np.asarray(h_filtered, dtype=float),
        psi_rc0_scatter_mpa=np.asarray(scenario.psi_rc0_ts[scenario.h_ts < h_break_m], dtype=float),
        psi_s0_scatter_mpa=np.asarray(psi_s0_ts[scenario.h_ts < h_break_m], dtype=float),
        psi_rc_scatter_mpa=np.asarray(scenario.psi_rc_ts[scenario.h_ts < h_break_m], dtype=float),
        psi_s_scatter_mpa=np.asarray(scenario.psi_s_ts[scenario.h_ts < h_break_m], dtype=float),
        h_curve_m=h_curve,
        psi_rc0_fit_mpa=fit_series[0],
        psi_rc_fit_mpa=fit_series[1],
        psi_s0_fit_mpa=fit_series[2],
        psi_s_fit_mpa=fit_series[3],
    )


@dataclass(frozen=True)
class TaoHeightEnvelope:
    x_range_mid: np.ndarray
    y_lb: np.ndarray
    y_ub: np.ndarray
    y_ub_outlier: np.ndarray


def load_tao_height_envelope() -> TaoHeightEnvelope:
    mat = loadmat(DEFAULT_LEGACY_TDGM_OFFLINE_DIR / "Taoetal2016.mat")
    return TaoHeightEnvelope(
        x_range_mid=np.asarray(mat["x_range_mid"], dtype=float).reshape(-1),
        y_lb=np.asarray(mat["y_lb"], dtype=float).reshape(-1),
        y_ub=np.asarray(mat["y_ub"], dtype=float).reshape(-1),
        y_ub_outlier=np.asarray(mat["y_ub_outlier"], dtype=float).reshape(-1),
    )


def load_max_p_minus_pet() -> np.ndarray:
    mat = loadmat(DEFAULT_LEGACY_TDGM_OFFLINE_DIR / "P_minus_PET.mat")
    return np.asarray(mat["maxPmPET"], dtype=float).reshape(-1)


def surface_soil_moisture_proxy(psi_soil_by_layer_ts: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    n_vg = 2.70
    alpha_vg = 1.4642
    e_z_n = 13.6
    vwc_sat = 0.4 * np.exp(-SOIL_LAYER_MIDPOINTS_M / e_z_n)
    s_e = (1.0 + np.abs(alpha_vg * psi_soil_by_layer_ts) ** n_vg) ** -(1.0 - 1.0 / n_vg)
    vwc = (vwc_sat[:, None]) * s_e
    vwc_mean = np.sum(vwc * SOIL_LAYER_WIDTHS_M[:, None], axis=0) / np.sum(SOIL_LAYER_WIDTHS_M)
    s_e_mean = np.sum(s_e * SOIL_LAYER_WIDTHS_M[:, None], axis=0) / np.sum(SOIL_LAYER_WIDTHS_M)
    psi_soil_mean = -(np.abs(s_e_mean ** (-1.0 / (1.0 - 1.0 / n_vg)) - 1.0) ** (1.0 / n_vg)) / alpha_vg
    return np.asarray(vwc_mean, dtype=float), np.asarray(s_e_mean, dtype=float), np.asarray(psi_soil_mean, dtype=float)


def turgor_growth_rate_from_legacy(
    *,
    psi_s_mpa: np.ndarray,
    psi_rc_mpa: np.ndarray,
    u_sw: np.ndarray,
    c_sw: np.ndarray,
    c_hw: np.ndarray,
    gamma_mpa: float,
    phi: float = 2.8e-7,
    rho_w: float = 998.0,
    r_gas: float = 8.314,
    t_a_c: float = 25.0,
) -> np.ndarray:
    return turgor_driven_growth_rate(
        psi_s=psi_s_mpa,
        psi_rc=psi_rc_mpa,
        phi=phi,
        p_turgor_crit=gamma_mpa,
        u_sw=u_sw,
        c_sw=c_sw,
        c_hw=c_hw,
        rho_w=rho_w,
        r_gas=r_gas,
        t_a=t_a_c,
        a=1.5,
        b=2.0 / 3.0,
    )


@lru_cache(maxsize=1)
def load_poorter_smf_reference_curve(
    *,
    script_path: Path = DEFAULT_LEGACY_POORTER_SCRIPT_PATH,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    text = script_path.read_text(encoding="utf-8")
    match = re.search(r"xy\s*=\s*\[(.*?)\];", text, flags=re.DOTALL)
    if match is None:
        raise ValueError(f"Could not extract SMF reference data from {script_path}")
    xy = _parse_matlab_matrix(match.group(1))
    px = np.linspace(-2.6, 6.0, 1000)
    gym, ang = _split_restart_curve(xy)
    p_gym = np.polyfit(gym[:, 0], gym[:, 1], 6)
    p_ang = np.polyfit(ang[:, 0], ang[:, 1], 6)
    smf_gym = np.polyval(p_gym, px)
    smf_ang = np.polyval(p_ang, px)
    smf_all = 10 ** ((np.log10(smf_gym) + np.log10(smf_ang)) / 2)
    p_all = np.polyfit(px, smf_all, 6)

    def smf_1(x: np.ndarray) -> np.ndarray:
        return np.polyval(p_all, x)

    def smf_2(x: np.ndarray) -> np.ndarray:
        return smf_1(np.array([px[-1]], dtype=float))[0] + (
            (smf_1(np.array([px[-1]], dtype=float))[0] - smf_1(np.array([px[-2]], dtype=float))[0]) / (px[-1] - px[-2])
        ) * (x - px[-1])

    px_extended = np.concatenate([px, np.linspace(6.0, 8.5, 200)])
    smf_curve = np.where(px_extended <= 6.0, smf_1(px_extended), smf_2(px_extended))
    carbon_mol = (10**px_extended) * 0.5 / 12.0
    return np.asarray(carbon_mol, dtype=float), np.asarray(smf_curve, dtype=float), np.asarray(xy, dtype=float)


@lru_cache(maxsize=1)
def build_poorter_smf_lookup(
    *,
    script_path: Path = DEFAULT_LEGACY_POORTER_SCRIPT_PATH,
) -> tuple[np.poly1d, float, float, float]:
    text = script_path.read_text(encoding="utf-8")
    match = re.search(r"xy\s*=\s*\[(.*?)\];", text, flags=re.DOTALL)
    if match is None:
        raise ValueError(f"Could not extract SMF reference data from {script_path}")
    xy = _parse_matlab_matrix(match.group(1))
    gym, ang = _split_restart_curve(xy)
    px = np.linspace(-2.6, 6.0, 1000)
    p_gym = np.polyfit(gym[:, 0], gym[:, 1], 6)
    p_ang = np.polyfit(ang[:, 0], ang[:, 1], 6)
    smf_gym = np.polyval(p_gym, px)
    smf_ang = np.polyval(p_ang, px)
    smf_all = 10 ** ((np.log10(smf_gym) + np.log10(smf_ang)) / 2)
    poly = np.poly1d(np.polyfit(px, smf_all, 6))
    anchor_x = float(px[-1])
    anchor_y = float(poly(anchor_x))
    anchor_prev = float(poly(px[-2]))
    slope = float((anchor_y - anchor_prev) / (px[-1] - px[-2]))
    return poly, anchor_x, anchor_y, slope


def poorter_smf_lookup(log_total_dry_mass_g: np.ndarray | float) -> np.ndarray:
    poly, anchor_x, anchor_y, slope = build_poorter_smf_lookup()
    x = np.asarray(log_total_dry_mass_g, dtype=float)
    return np.where(x <= anchor_x, poly(x), anchor_y + slope * (x - anchor_x))


def phloem_transport_distribution(height_key: str) -> tuple[np.ndarray, np.ndarray, np.ndarray, float]:
    if height_key not in PHLOEM_TRANSPORT_RESULTS:
        raise KeyError(f"Unsupported phloem transport height key '{height_key}'")
    mat = loadmat(PHLOEM_TRANSPORT_RESULTS[height_key])
    values = np.asarray(mat["c_p_norm"], dtype=float).reshape(-1)
    if height_key == "04m":
        n_bins = 100
    else:
        n_bins = 800
    d_x = float(np.ptp(values) / (n_bins - 1))
    bins = np.arange(np.min(values), np.max(values) + d_x, d_x, dtype=float)
    counts, centers = np.histogram(values, bins=bins)
    centers = (bins[:-1] + bins[1:]) / 2.0
    pdf = counts / np.sum(counts)
    cdf = np.cumsum(counts) / np.sum(counts)
    x_limit = float(np.max(centers[cdf <= np.min(cdf[cdf > 0.995])]))
    return np.asarray(centers, dtype=float), np.asarray(pdf, dtype=float), np.asarray(cdf, dtype=float), x_limit


def height_trace_on_regular_grid(*, scenario: TDGMLegacyScenario, dt_years: float) -> tuple[np.ndarray, np.ndarray]:
    dt_years = float(dt_years)
    t_year = scenario.t_year_ts
    t_grid = np.arange(dt_years, np.max(t_year) + 1e-12, dt_years, dtype=float)
    h_grid = np.full(t_grid.shape, np.nan, dtype=float)
    for idx, t_cutoff in enumerate(t_grid):
        valid = scenario.h_ts[t_year <= t_cutoff]
        if valid.size:
            h_grid[idx] = float(np.max(valid))
    return t_grid, h_grid


def annual_growth_by_year(*, scenario: TDGMLegacyScenario, dt_years: float = 1.0) -> tuple[np.ndarray, np.ndarray]:
    t_year = scenario.t_year_ts
    t_grid = np.arange(dt_years, np.ceil(np.max(t_year)) + 1e-12, dt_years, dtype=float)
    c_mean = np.full(t_grid.shape, np.nan, dtype=float)
    g_rate = np.full(t_grid.shape, np.nan, dtype=float)
    for idx, t_end in enumerate(t_grid):
        selector = (t_year <= t_end) & (t_year > (t_end - dt_years))
        c_local = scenario.c_tree_ts[selector]
        if c_local.size:
            c_mean[idx] = float(np.mean(c_local))
            g_rate[idx] = float((np.max(c_local) - np.min(c_local)) / dt_years / (365.0 * 24.0 * 3600.0))
    return c_mean, g_rate


def annual_soil_moisture_by_year(
    *,
    scenario: TDGMLegacyScenario,
    dt_years: float = 1.0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    _, s_e_ts, _ = surface_soil_moisture_proxy(scenario.psi_soil_by_layer_ts)
    t_year = scenario.t_year_ts
    t_grid = np.arange(dt_years, np.ceil(np.max(t_year)) + 1e-12, dt_years, dtype=float)
    c_mean = np.full(t_grid.shape, np.nan, dtype=float)
    g_rate = np.full(t_grid.shape, np.nan, dtype=float)
    s_e_mean = np.full(t_grid.shape, np.nan, dtype=float)
    for idx, t_end in enumerate(t_grid):
        selector = (t_year <= t_end) & (t_year > (t_end - dt_years))
        c_local = scenario.c_tree_ts[selector]
        s_local = s_e_ts[selector]
        if c_local.size:
            c_mean[idx] = float(np.mean(c_local))
            g_rate[idx] = float((np.max(c_local) - np.min(c_local)) / dt_years / (365.0 * 24.0 * 3600.0))
        if s_local.size:
            s_e_mean[idx] = float(np.mean(s_local))
    valid = np.isfinite(c_mean) & (c_mean > 0.0) & np.isfinite(g_rate) & (g_rate > 0.0) & np.isfinite(s_e_mean) & (s_e_mean > 0.0)
    c_mean = c_mean[valid]
    g_rate = g_rate[valid]
    s_e_mean = s_e_mean[valid]
    coeff = np.polyfit(np.log(c_mean), np.log(s_e_mean), 2)
    s_e_regressed = np.exp(np.polyval(coeff, np.log(c_mean)))
    s_e_detrended = s_e_mean - s_e_regressed
    return c_mean, g_rate, s_e_mean, s_e_regressed, s_e_detrended


def annual_precipitation_relative(n_years: int) -> np.ndarray:
    n_years = int(n_years)
    if n_years <= 0:
        return np.empty(0, dtype=float)
    repeats = int(np.ceil(n_years / len(ANNUAL_PRECIP_RELATIVE_SEQUENCE)))
    return np.tile(ANNUAL_PRECIP_RELATIVE_SEQUENCE, repeats)[:n_years]


@dataclass(frozen=True)
class HeightAgeReferenceEnvelope:
    age_bm_years: np.ndarray
    h_bm_lower_m: np.ndarray
    h_bm_upper_m: np.ndarray
    age_p2004_years: np.ndarray
    h_p2004_lower_m: np.ndarray
    h_p2004_upper_m: np.ndarray


def _extend_hossfeld_curve(age_years: np.ndarray, height_m: np.ndarray, *, age_end_years: float = 150.0) -> tuple[np.ndarray, np.ndarray]:
    y_values = age_years**2 / height_m
    coeff = np.polyfit(age_years, y_values, 3)
    age_ext = np.unique(np.concatenate([np.arange(np.max(age_years), age_end_years + 1.0, 1.0), np.array([age_end_years], dtype=float)]))
    y_ext = np.polyval(coeff, age_ext)
    height_ext = age_ext**2 / y_ext
    max_idx = int(np.argmax(height_ext))
    height_ext[age_ext > age_ext[max_idx]] = float(height_ext[max_idx])
    return age_ext, height_ext


@lru_cache(maxsize=1)
def load_height_age_reference_envelope(
    *,
    script_path: Path = DEFAULT_LEGACY_TDGM_THORP_G_DIR / "PLOT_H_versus_age_turgorthreshold.m",
) -> HeightAgeReferenceEnvelope:
    script_text = script_path.read_text(encoding="utf-8")
    bm2001 = _extract_matlab_matrix(script_text, "BM2001")
    p2004 = _extract_matlab_matrix(script_text, "P2004")

    age_bm = np.asarray(bm2001[:, 0], dtype=float)
    height_bm = np.asarray(bm2001[:, 1], dtype=float)
    age_p = np.asarray(p2004[:, 0], dtype=float)
    height_p = np.asarray(p2004[:, 1], dtype=float)

    age_upper_bm_raw = age_bm[:12]
    height_upper_bm_raw = height_bm[:12]
    age_lower_bm_raw = age_bm[16:]
    height_lower_bm_raw = height_bm[16:]
    age_upper_bm_fit = age_bm[3:12]
    height_upper_bm_fit = height_bm[3:12]
    age_lower_bm_fit = age_bm[16:22]
    height_lower_bm_fit = height_bm[16:22]
    age_upper_bm_ext, height_upper_bm_ext = _extend_hossfeld_curve(age_upper_bm_fit, height_upper_bm_fit)
    age_lower_bm_ext, height_lower_bm_ext = _extend_hossfeld_curve(age_lower_bm_fit, height_lower_bm_fit)
    age_upper_bm = np.concatenate([age_upper_bm_raw, age_upper_bm_ext])
    height_upper_bm = np.concatenate([height_upper_bm_raw, height_upper_bm_ext])
    lower_bm_order = np.argsort(np.concatenate([age_lower_bm_raw, age_lower_bm_ext]))
    age_lower_bm = np.concatenate([age_lower_bm_raw, age_lower_bm_ext])[lower_bm_order]
    height_lower_bm = np.concatenate([height_lower_bm_raw, height_lower_bm_ext])[lower_bm_order]

    age_upper_p = age_p[:32]
    height_upper_p = height_p[:32]
    age_lower_p = age_p[32:]
    height_lower_p = height_p[32:]
    p_lower_order = np.argsort(age_lower_p)
    age_lower_p = age_lower_p[p_lower_order]
    height_lower_p = height_lower_p[p_lower_order]

    age_bm_grid = np.linspace(0.0, 150.0, 601)
    height_upper_bm_grid = np.interp(age_bm_grid, age_upper_bm, height_upper_bm, left=np.nan, right=np.nan)
    height_lower_bm_grid = np.interp(age_bm_grid, age_lower_bm, height_lower_bm, left=np.nan, right=np.nan)
    height_lower_p_grid = np.interp(age_bm_grid, age_lower_p, height_lower_p, left=np.nan, right=np.nan)
    hybrid_lower = height_lower_bm_grid.copy()
    overlap = np.isfinite(height_lower_p_grid)
    hybrid_lower[overlap] = np.minimum(hybrid_lower[overlap], height_lower_p_grid[overlap])
    valid_bm = np.isfinite(height_upper_bm_grid) & np.isfinite(hybrid_lower)

    age_p_grid = np.linspace(0.0, 160.5, 643)
    height_upper_p_grid = np.interp(age_p_grid, age_upper_p, height_upper_p, left=np.nan, right=np.nan)
    height_lower_p_full_grid = np.interp(age_p_grid, age_lower_p, height_lower_p, left=np.nan, right=np.nan)
    valid_p = np.isfinite(height_upper_p_grid) & np.isfinite(height_lower_p_full_grid)

    return HeightAgeReferenceEnvelope(
        age_bm_years=age_bm_grid[valid_bm],
        h_bm_lower_m=hybrid_lower[valid_bm],
        h_bm_upper_m=height_upper_bm_grid[valid_bm],
        age_p2004_years=age_p_grid[valid_p],
        h_p2004_lower_m=height_lower_p_full_grid[valid_p],
        h_p2004_upper_m=height_upper_p_grid[valid_p],
    )


def build_thorp_g_stress_groups() -> tuple[tuple[str, ...], ...]:
    return (
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
