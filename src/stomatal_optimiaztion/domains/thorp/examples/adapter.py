from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Literal

import numpy as np

from stomatal_optimiaztion.domains.thorp.defaults import default_params as default_bundle_params
from stomatal_optimiaztion.domains.thorp.hydraulics import e_from_soil_to_root_collar
from stomatal_optimiaztion.domains.thorp.matlab_io import load_mat
from stomatal_optimiaztion.domains.thorp.soil_initialization import initial_soil_and_roots

REPO_ROOT = Path(__file__).resolve().parents[5]
WORKSPACE_ROOT = REPO_ROOT.parents[1]
DEFAULT_LEGACY_THORP_EXAMPLE_DIR = WORKSPACE_ROOT / "00. Stomatal Optimization" / "THORP" / "example" / "THORP_code_forcing_outputs_plotting"
DEFAULT_LEGACY_THORP_SUPPORT_DIR = DEFAULT_LEGACY_THORP_EXAMPLE_DIR / "Simulations_and_additional_code_to_plot"

MAIN_TEXT_SCENARIOS = {
    "control": "THORP_data_Control.mat",
    "precip_75": "THORP_data_0.75_Precip.mat",
    "precip_50": "THORP_data_0.50_Precip.mat",
    "precip_50_gwt_2m": "THORP_data_0.50_Precip_GWT_2_m.mat",
    "light_limited": "THORP_data_overstory_30_m_LAI_3.mat",
    "eco2_600": "THORP_data_eCO2_600_ppm.mat",
}
GWT_SWEEP_DEPTHS_M = (2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 24, 28, 32, 36, 40, 48, 56, 64, 72, 80)
DEFAULT_PHI = 3.34


def _vec(mat: dict[str, object], key: str) -> np.ndarray:
    return np.asarray(mat[key], dtype=float).reshape(-1)


def _mat(mat: dict[str, object], key: str) -> np.ndarray:
    return np.asarray(mat[key], dtype=float)


@dataclass(frozen=True)
class SoilGridView:
    dz: np.ndarray
    z_mid: np.ndarray
    z_bttm: np.ndarray
    z_wt: float


@dataclass(frozen=True)
class ThorpLegacyScenario:
    scenario_id: str
    mat_path: Path
    grid: SoilGridView
    t_ts: np.ndarray
    c_l_ts: np.ndarray
    c_sw_ts: np.ndarray
    c_hw_ts: np.ndarray
    c_r_h_by_layer_ts: np.ndarray
    c_r_v_by_layer_ts: np.ndarray
    u_l_ts: np.ndarray
    u_sw_ts: np.ndarray
    u_r_h_ts: np.ndarray
    u_r_v_ts: np.ndarray
    u_ts: np.ndarray
    h_ts: np.ndarray
    w_ts: np.ndarray
    d_ts: np.ndarray
    d_hw_ts: np.ndarray
    psi_l_ts: np.ndarray
    psi_s_ts: np.ndarray
    psi_rc_ts: np.ndarray
    psi_rc0_ts: np.ndarray
    psi_soil_by_layer_ts: np.ndarray
    a_n_ts: np.ndarray
    e_ts: np.ndarray

    @property
    def t_year_ts(self) -> np.ndarray:
        return self.t_ts / 365.0 / 24.0 / 3600.0

    @property
    def c_r_by_layer_ts(self) -> np.ndarray:
        return self.c_r_h_by_layer_ts + self.c_r_v_by_layer_ts

    @property
    def c_w_ts(self) -> np.ndarray:
        return self.c_sw_ts + self.c_hw_ts

    @property
    def dm_w_g_ts(self) -> np.ndarray:
        return self.c_w_ts * 12.0 / 0.5

    @property
    def dm_r_g_ts(self) -> np.ndarray:
        return np.sum(self.c_r_by_layer_ts, axis=0) * 12.0 / 0.55

    @property
    def dm_l_g_ts(self) -> np.ndarray:
        return self.c_l_ts * 12.0 / 0.5

    @property
    def dm_tot_g_ts(self) -> np.ndarray:
        return self.dm_w_g_ts + self.dm_r_g_ts + self.dm_l_g_ts

    @property
    def lmf_ts(self) -> np.ndarray:
        return self.dm_l_g_ts / self.dm_tot_g_ts

    @property
    def smf_ts(self) -> np.ndarray:
        return self.dm_w_g_ts / self.dm_tot_g_ts

    @property
    def rmf_ts(self) -> np.ndarray:
        return self.dm_r_g_ts / self.dm_tot_g_ts

    @property
    def la_ts(self) -> np.ndarray:
        return _default_bundle().allocation.sla * self.c_l_ts

    @property
    def lai_ts(self) -> np.ndarray:
        return self.la_ts / DEFAULT_PHI / (self.w_ts**2)

    @property
    def sa_ts(self) -> np.ndarray:
        return np.pi / 4.0 * (self.d_ts**2 - self.d_hw_ts**2)

    @property
    def huber_value_ts(self) -> np.ndarray:
        return self.sa_ts / self.la_ts

    @property
    def t_mass_threshold_ts(self) -> float:
        idx = int(np.argmin(np.abs(self.dm_tot_g_ts - 1e3)))
        return float(self.t_ts[idx])

    def mean_fraction_by_log_mass(
        self,
        *,
        fraction: Literal["lmf", "smf", "rmf"],
        xmin: float = 2.0,
        xmax: float = 7.0,
        dlog_x: float = 0.1,
    ) -> tuple[np.ndarray, np.ndarray]:
        log_bins = np.arange(xmin, xmax + dlog_x, dlog_x, dtype=float)
        log_mid = log_bins[:-1] + 0.5 * np.diff(log_bins)
        values = getattr(self, f"{fraction}_ts")
        result = np.full(log_mid.shape, np.nan, dtype=float)
        valid_time = self.t_ts >= self.t_mass_threshold_ts
        log_dm = np.log10(self.dm_tot_g_ts)
        for idx, (left, right) in enumerate(zip(log_bins[:-1], log_bins[1:], strict=True)):
            selector = valid_time & (log_dm > left) & (log_dm <= right)
            if np.any(selector):
                result[idx] = float(np.mean(values[selector]))
        return log_mid, result

    def root_depth_fraction(
        self,
        *,
        fraction: float,
        depth_axis: Literal["mid", "bottom"],
        cap_at_water_table: bool = False,
    ) -> np.ndarray:
        depth_reference = self.grid.z_mid if depth_axis == "mid" else self.grid.z_bttm
        root_profiles = self.c_r_by_layer_ts
        result = np.full(self.t_ts.shape, np.nan, dtype=float)
        for idx in range(root_profiles.shape[1]):
            profile = root_profiles[:, idx]
            total = float(np.sum(profile))
            if total <= 0:
                continue
            cumulative = np.cumsum(profile) / total
            upper_mask = cumulative >= fraction
            upper_value = float(np.min(cumulative[upper_mask]))
            upper_depth = float(np.min(depth_reference[cumulative == upper_value]))
            if cap_at_water_table:
                upper_depth = min(upper_depth, self.grid.z_wt)
            lower_mask = cumulative < fraction
            if np.any(lower_mask):
                lower_value = float(np.max(cumulative[lower_mask]))
                lower_depth = float(np.max(depth_reference[cumulative == lower_value]))
            else:
                lower_value = 0.0
                lower_depth = 0.0
            if upper_value == lower_value:
                result[idx] = upper_depth
            else:
                result[idx] = lower_depth + (upper_depth - lower_depth) * (fraction - lower_value) / (upper_value - lower_value)
        return result

    def four_week_mean(self, series: np.ndarray) -> np.ndarray:
        n_chunk = int(np.ceil((4 * 7 * 24 * 3600) / _default_dt_sav_data()))
        n_chunk = max(1, n_chunk)
        n_valid = n_chunk * (len(series) // n_chunk)
        if n_valid == 0:
            return np.asarray(series, dtype=float)
        return np.mean(np.reshape(series[:n_valid], (n_chunk, n_valid // n_chunk), order="F"), axis=0)


@lru_cache(maxsize=1)
def _default_bundle():
    return default_bundle_params()


def _default_dt_sav_data() -> float:
    return float(_default_bundle().richards.dt * np.ceil((7 * 24 * 3600.0) / _default_bundle().richards.dt))


def soil_grid_for_example(*, z_wt: float = 74.0, bc_bttm: str = "FreeDrainage") -> SoilGridView:
    bundle = _default_bundle()
    init = initial_soil_and_roots(
        params=bundle.soil_initialization.__class__(
            rho=bundle.soil_initialization.rho,
            g=bundle.soil_initialization.g,
            z_wt=float(z_wt),
            z_soil=bundle.soil_initialization.z_soil,
            n_soil=bundle.soil_initialization.n_soil,
            bc_bttm=bc_bttm,
            soil=bundle.soil_initialization.soil,
            vc_r=bundle.soil_initialization.vc_r,
            beta_r_h=bundle.soil_initialization.beta_r_h,
            beta_r_v=bundle.soil_initialization.beta_r_v,
        ),
        c_r_i=1.0,
        z_i=3.0,
    )
    return SoilGridView(
        dz=np.asarray(init.grid.dz, dtype=float),
        z_mid=np.asarray(init.grid.z_mid, dtype=float),
        z_bttm=np.asarray(init.grid.z_bttm, dtype=float),
        z_wt=float(z_wt),
    )


def load_legacy_scenario(
    *,
    mat_path: Path,
    scenario_id: str,
    z_wt: float = 74.0,
    bc_bttm: str = "FreeDrainage",
) -> ThorpLegacyScenario:
    mat = load_mat(mat_path)
    return ThorpLegacyScenario(
        scenario_id=scenario_id,
        mat_path=mat_path,
        grid=soil_grid_for_example(z_wt=z_wt, bc_bttm=bc_bttm),
        t_ts=_vec(mat, "t_stor"),
        c_l_ts=_vec(mat, "c_l_stor"),
        c_sw_ts=_vec(mat, "c_sw_stor"),
        c_hw_ts=_vec(mat, "c_hw_stor"),
        c_r_h_by_layer_ts=_mat(mat, "c_r_H_stor"),
        c_r_v_by_layer_ts=_mat(mat, "c_r_V_stor"),
        u_l_ts=_vec(mat, "u_l_stor"),
        u_sw_ts=_vec(mat, "u_sw_stor"),
        u_r_h_ts=_vec(mat, "u_r_H_stor"),
        u_r_v_ts=_vec(mat, "u_r_V_stor"),
        u_ts=_vec(mat, "U_stor"),
        h_ts=_vec(mat, "H_stor"),
        w_ts=_vec(mat, "W_stor"),
        d_ts=_vec(mat, "D_stor"),
        d_hw_ts=_vec(mat, "D_hw_stor"),
        psi_l_ts=_vec(mat, "P_x_l_stor"),
        psi_s_ts=_vec(mat, "P_x_s_stor"),
        psi_rc_ts=_vec(mat, "P_x_r_stor"),
        psi_rc0_ts=_vec(mat, "P_x_r0_stor"),
        psi_soil_by_layer_ts=_mat(mat, "P_soil_stor"),
        a_n_ts=_vec(mat, "A_n_stor"),
        e_ts=_vec(mat, "E_stor"),
    )


def load_main_text_scenario(
    scenario_id: str,
    *,
    legacy_dir: Path = DEFAULT_LEGACY_THORP_SUPPORT_DIR,
) -> ThorpLegacyScenario:
    filename = MAIN_TEXT_SCENARIOS[scenario_id]
    return load_legacy_scenario(
        mat_path=legacy_dir / filename,
        scenario_id=scenario_id,
    )


def load_gwt_sweep_scenario(
    depth_m: int,
    *,
    legacy_dir: Path = DEFAULT_LEGACY_THORP_SUPPORT_DIR,
) -> ThorpLegacyScenario:
    return load_legacy_scenario(
        mat_path=legacy_dir / f"THORP_data_0.50_Precip_GWT_{depth_m}_m.mat",
        scenario_id=f"gwt_{depth_m}m",
        z_wt=float(depth_m),
        bc_bttm="GroundwaterTable",
    )


def deep_uptake_fraction(
    scenario: ThorpLegacyScenario,
    *,
    h_min: float,
    h_max: float,
    depth_threshold_m: float = 2.0,
) -> float:
    bundle = _default_bundle()
    selector = (scenario.h_ts >= h_min) & (scenario.h_ts <= h_max)
    if not np.any(selector):
        return float("nan")
    z_bttm = scenario.grid.z_bttm
    deep_total = 0.0
    e_total = 0.0
    for idx in np.where(selector)[0]:
        res = e_from_soil_to_root_collar(
            params=bundle.root_uptake,
            psi_rc=float(scenario.psi_rc_ts[idx]),
            psi_soil_by_layer=np.asarray(scenario.psi_soil_by_layer_ts[:, idx], dtype=float),
            z_soil_mid=scenario.grid.z_mid,
            dz=scenario.grid.dz,
            la=float(scenario.la_ts[idx]),
            c_r_h=np.asarray(scenario.c_r_h_by_layer_ts[:, idx], dtype=float),
            c_r_v=np.asarray(scenario.c_r_v_by_layer_ts[:, idx], dtype=float),
        )
        e_soil = np.asarray(res.e_soil, dtype=float).copy()
        shallow_idx = np.where(z_bttm < depth_threshold_m)[0]
        if shallow_idx.size:
            e_soil[shallow_idx] = 0.0
        transition_idx = np.where(z_bttm >= depth_threshold_m)[0]
        if transition_idx.size:
            first_deep = int(transition_idx[0])
            if first_deep > 0:
                fraction = (z_bttm[first_deep] - depth_threshold_m) / scenario.grid.dz[first_deep]
                e_soil[first_deep] = e_soil[first_deep] * fraction
        deep_total += float(np.sum(e_soil))
        e_total += float(res.e)
    return float(deep_total / e_total) if e_total > 0 else float("nan")


def simulated_groundwater_depth(scenario: ThorpLegacyScenario) -> np.ndarray:
    bundle = _default_bundle()
    z_bttm = scenario.grid.z_bttm
    z_boundary = float(np.min(z_bttm[z_bttm >= scenario.grid.z_wt]))
    p_boundary = bundle.soil_initialization.rho * bundle.soil_initialization.g * (z_boundary - scenario.grid.z_wt) / 1e6
    gwtd = np.full(scenario.t_ts.shape, np.nan, dtype=float)
    for idx in range(scenario.t_ts.size):
        z_profile = scenario.grid.z_mid
        p_profile = np.asarray(scenario.psi_soil_by_layer_ts[:, idx], dtype=float)
        z_aug = np.concatenate([z_profile, [z_boundary]])
        p_aug = np.concatenate([p_profile, [p_boundary]])
        order = np.argsort(z_aug)
        z_aug = z_aug[order]
        p_aug = p_aug[order]
        if np.min(p_aug) > 0:
            gwtd[idx] = 0.0
        elif np.max(p_aug) <= 0:
            max_p = float(np.max(p_aug))
            gwtd[idx] = float(z_aug[p_aug == max_p][0] - max_p / bundle.soil_initialization.rho / bundle.soil_initialization.g * 1e6)
        else:
            upper = float(np.min(p_aug[p_aug > 0]))
            lower = float(np.max(p_aug[p_aug <= 0]))
            z_upper = float(z_aug[p_aug == upper][0])
            z_lower = float(z_aug[p_aug == lower][-1])
            gwtd[idx] = z_lower + (z_upper - z_lower) * (0.0 - lower) / (upper - lower)
    return gwtd
