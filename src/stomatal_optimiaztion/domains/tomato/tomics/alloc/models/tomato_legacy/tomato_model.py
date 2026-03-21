from __future__ import annotations

import logging
import math
from collections.abc import Mapping
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import fsolve

from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.partitioning import (
    PartitionPolicy,
    coerce_partition_policy,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.partitioning.common_structure import (
    build_common_structure_snapshot,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.partitioning.fruit_feedback import (
    apply_fruit_feedback_proxy,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.partitioning.research_modes import (
    TomicsResearchArchitecture,
    coerce_tomics_research_architecture,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.partitioning.promoted_modes import (
    PromotedAllocatorConfig,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.partitioning.reserve_buffer import (
    resolve_realized_growth_with_buffer,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.contracts import (
    EnvStep,
    water_supply_stress_from_theta,
)

PHOTON_UMOL_TO_MJ = 0.218e-6
LOGGER = logging.getLogger(__name__)


def check_and_clip_value(value: object, min_val: float, max_val: float, default_val: float = 0.0) -> float:
    """Coerce non-finite values to a default, then clip to a bounded range."""

    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return float(default_val)

    if not math.isfinite(numeric):
        return float(default_val)
    return float(min(max(numeric, min_val), max_val))


def _finite_float(raw: object, *, default: float) -> float:
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return float(default)
    if not math.isfinite(value):
        return float(default)
    return float(value)


def _resolve_partition_key(raw: object) -> str:
    key = getattr(raw, "value", raw)
    return str(key).strip().lower()


def esat_Pa_from_T_C(t_c: float) -> float:
    """Tetens saturation vapor pressure from air temperature in Celsius."""

    return float(610.78 * math.exp((17.2694 * t_c) / (t_c + 237.29)))


def slope_esat_Pa_per_K(t_c: float) -> float:
    saturation_vapor_pressure_pa = esat_Pa_from_T_C(t_c)
    return float(saturation_vapor_pressure_pa * (17.2694 * 237.29) / ((t_c + 237.29) ** 2))


def psychrometric_constant_Pa_per_K(
    P_Pa: float = 101325.0,
    cp: float = 1004.0,
    lambda_v: float = 2.45e6,
    eps: float = 0.622,
) -> float:
    return float(cp * P_Pa / (eps * lambda_v))


def penman_monteith_LE_Wm2(
    Rn_Wm2: float,
    Ta_K: float,
    VPD_Pa: float,
    ra_s_m: float,
    rc_s_m: float,
    rho: float = 1.225,
    cp: float = 1004.0,
    gamma_PaK: float | None = None,
    allow_negative: bool = False,
) -> float:
    """Ground-area Penman-Monteith latent heat flux in W/m2."""

    ta_c = float(Ta_K) - 273.15
    slope = slope_esat_Pa_per_K(ta_c)
    gamma = psychrometric_constant_Pa_per_K() if gamma_PaK is None else float(gamma_PaK)
    aerodynamic_resistance = max(1e-6, float(ra_s_m))
    canopy_resistance = max(0.0, float(rc_s_m))
    denominator = slope + gamma * (1.0 + canopy_resistance / aerodynamic_resistance)
    if denominator <= 1e-12:
        return 0.0

    numerator = slope * float(Rn_Wm2) + float(rho) * (float(cp) * (float(VPD_Pa) / aerodynamic_resistance))
    latent_heat_flux = numerator / denominator
    if (not allow_negative) and latent_heat_flux < 0.0:
        latent_heat_flux = 0.0
    return float(latent_heat_flux)


class TomatoModel:
    """TOMICS-compatible tomato legacy model updated from model-foundry tomato_v1_2."""

    def __init__(
        self,
        fixed_lai: float | None = None,
        partition_policy: PartitionPolicy | str | None = None,
        allocation_scheme: str = "4pool",
        partition_policy_params: Mapping[str, object] | None = None,
    ) -> None:
        self.fixed_lai = fixed_lai
        self.partition_policy = coerce_partition_policy(partition_policy)
        self.allocation_scheme = str(allocation_scheme)
        self.partition_policy_params = (
            {str(key): value for key, value in partition_policy_params.items()}
            if isinstance(partition_policy_params, Mapping)
            else {}
        )

        self.photosyn_mode = "fvcb_canopy"
        self.use_age_structured_sink = True

        self.rho_a = 1.225
        self.c_p = 1004.0
        self.sigma = 5.67e-8
        self.lambda_v = 2.45e6
        self.alpha_c = 0.15
        self.emissivity_c = 0.98
        self.emissivity_cover = 0.84
        self.W_TO_UMOL_CONVERSION = 4.6
        self.PAR_FRACTION_OF_SW = 0.45
        self.P_air = 101325.0
        self.eps_air = 0.622
        self.gamma = psychrometric_constant_Pa_per_K(
            self.P_air,
            self.c_p,
            self.lambda_v,
            self.eps_air,
        )
        self.allow_condensation = True
        self.leaf_dimension = 0.15
        self.k_ext = 0.72

        self.fcvb_params = {
            "V_Ha": 91185.0,
            "R": 8.314,
            "V_S": 650.0,
            "V_Hd": 202900.0,
            "J_Ha": 79500.0,
            "J_S": 650.0,
            "J_Hd": 201000.0,
            "O": 210.0,
            "a": 0.3,
            "default_theta": 0.7,
        }
        self.joubert_params = {
            "Vcmax": 99.25,
            "Jmax": 190.68,
            "Rd": 1.0,
            "theta_J": 0.41,
            "gamma_J": 0.9,
            "c1": 19.02,
            "dHa1_kJ": 37.83,
            "c2": 12.3772,
            "dHa2_kJ": 23.72,
            "c3": 37.96,
            "dHa3_kJ": 79.43,
            "R1_kJ": 0.008314,
            "O_i_kPa": 21.0,
        }

        self.MAINT_25C = {"lv": 0.03, "st": 0.015, "rt": 0.01, "fr": 0.01}
        self.ASR = {"lv": 1.39, "st": 1.45, "rt": 1.39, "fr": 1.37}
        self.Q10_maint = 2.0
        self.f_Rm_RGR = 33.0

        self.harvest_truss_dm_g = 80.0
        self.root_frac_of_total_veg = 0.15 / 1.15
        self.veg_sink_g_d_per_shoot = 2.8
        self.pgr_params = {"a": 0.138, "b": 4.34, "c": 0.278, "d": 1.31}
        self.tdvs_min = 0.0
        self.tdvs_max = 1.0
        self.LAI_max = 3.0
        self.fr_T_min_valid = 18.0
        self.fr_T_max_valid = 23.0
        self.fr_clamp_to_valid = False

        self.plants_per_m2 = 1.836091
        self.shoots_per_plant = 1.0
        self.shoots_per_m2 = self.plants_per_m2 * self.shoots_per_plant

        self.theta_substrate = 0.33
        self.moisture_response_fn = lambda theta: theta / 0.4

        self.reset_state()

    def reset_state(self) -> None:
        """Reset model pools and diagnostics to legacy-compatible defaults."""

        self.start_date = datetime(2021, 2, 23)
        self.last_calc_time: datetime | None = None
        self.current_date: date = self.start_date.date()

        self.W_lv = 50.0
        self.W_st = 20.0
        self.W_rt = 10.0
        self.W_fr = 0.0
        self.W_fr_harvested = 0.0
        self.reserve_ch2o_g = 0.0

        init_doy = self.start_date.timetuple().tm_yday
        sla_cm2_per_g = 266.0 + 88.0 * math.sin(2.0 * math.pi * (init_doy + 68) / 365.0)
        self.SLA = max(0.0001, sla_cm2_per_g / 10000.0)
        self.LAI = float(self.fixed_lai) if self.fixed_lai is not None else self.W_lv * self.SLA

        self.T_c = 293.15
        self.T_a = 293.15
        self.SW_in_Wm2 = 0.0
        self.T_rad_K = self.T_a
        self.H = 0.0
        self.LE = 0.0
        self.LE_raw = 0.0
        self.LE_evap = 0.0
        self.LE_cond = 0.0
        self.r_ah = 50.0
        self.r_b = 50.0
        self.f_c = 0.1
        self.convergence_status_Tc = False
        self.co2_flux_g_m2_s = 0.0
        self.dt_seconds = 0.0
        self.water_supply_stress = self._resolve_water_supply_stress()
        self.rootzone_multistress = 0.0
        self.rootzone_saturation = 0.0
        self.VPD = 0.0

        self.daily_temp_accumulator: list[tuple[float, float]] = []
        self.daily_gross_ch2o_g = 0.0
        self.daily_par_umol_in_sum = 0.0
        self.daily_par_umol_int_sum = 0.0
        self.daily_dW_total = 0.0
        self.last_daily_dW_total = 0.0
        self.last_daily_epsilon = 0.0
        self.recent_total_dm_history: list[float] = []
        self.last_RGR = 0.03

        self.daily_transpiration_g = 0.0
        self.last_daily_transpiration_g = 0.0
        self.last_gsw_canopy = 0.0

        self.truss_count = 0
        self._truss_fraction_acc = 0.0
        self.truss_cohorts: list[dict[str, object]] = []
        self.pending_n_fruits: list[int] = []

        self.n_f = 2
        self.u_PAR = 0.0
        self.u_CO2 = 400.0
        self.RH = 0.7
        self.u = 0.1
        self.Ci = self.u_CO2 * 0.7

        self.part_fruit = math.nan
        self.part_leaf = math.nan
        self.part_stem = math.nan
        self.part_root = math.nan
        self.part_shoot = math.nan
        self.part_veg = math.nan
        self.vegetative_dw = self.W_lv + self.W_st + self.W_rt
        self.fruit_dw = self.W_fr

        self.buffer_pool_g = 0.0
        self.fruit_abort_fraction = 0.0
        self.fruit_set_feedback_events = 0
        self.maintenance_respiration_share = 0.0
        self.mean_stage_residence_time_d = 0.0
        self.promoted_leaf_canopy_return_proxy = 0.0
        self.promoted_stem_support_signal = 0.0
        self.promoted_root_gate_activation = 0.0
        self.promoted_supply_demand_ratio = 1.0
        self.promoted_low_sink_penalty = 0.0
        self.common_structure_snapshot = build_common_structure_snapshot(
            assimilate_buffer_g=self.reserve_ch2o_g,
            leaf_biomass_g=self.W_lv,
            stem_root_biomass_g=self.W_st + self.W_rt,
            fruit_biomass_g=self.W_fr,
            photosynthesis_g=0.0,
            growth_respiration_g=0.0,
            growth_g=0.0,
            maintenance_g=0.0,
            fruit_harvest_g=self.W_fr_harvested,
            leaf_harvest_g=0.0,
        )
        self._tomics_research_prev_root_fraction = None
        self._tomics_research_prev_root_target = None

        self._last_row_cols: set[str] = set()
        self._last_row_used_T_rad = False
        self.eps_eff_last = 0.0
        self.T_env_last_K = self.T_a
        self.r_lw_net_last = 0.0

    def to_floor_from_plant(self, x_per_plant: float) -> float:
        return float(x_per_plant) * float(self.plants_per_m2)

    def to_floor_from_shoot(self, x_per_shoot: float) -> float:
        return float(x_per_shoot) * float(self.shoots_per_m2)

    def to_plant_from_floor(self, x_per_floor: float) -> float:
        if self.plants_per_m2 <= 0:
            raise ValueError("plants_per_m2 must be > 0 to convert per-floor to per-plant.")
        return float(x_per_floor) / float(self.plants_per_m2)

    def to_shoot_from_floor(self, x_per_floor: float) -> float:
        if self.shoots_per_m2 <= 0:
            raise ValueError("shoots_per_m2 must be > 0 to convert per-floor to per-shoot.")
        return float(x_per_floor) / float(self.shoots_per_m2)

    def load_input_data(self, csv_file_path: str | Path) -> pd.DataFrame:
        """Load CSV forcing with the same required-column contract as the legacy model."""

        input_path = Path(csv_file_path)
        df = pd.read_csv(input_path)
        df["datetime"] = pd.to_datetime(df["datetime"])

        required_columns = [
            "datetime",
            "T_air_C",
            "PAR_umol",
            "CO2_ppm",
            "RH_percent",
            "wind_speed_ms",
        ]
        missing_columns = [column for column in required_columns if column not in df.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")

        if "n_fruits_per_truss" not in df.columns:
            df["n_fruits_per_truss"] = 4
        return df

    def run_simulation(self, input_df: pd.DataFrame, output_csv_path: str | Path | None = None) -> pd.DataFrame:
        """Run a bounded simulation loop over forcing rows and return a tabular output."""

        self.reset_state()
        forcing = input_df.sort_values("datetime").reset_index(drop=True)

        if forcing.shape[0] >= 2:
            dt0 = (forcing.loc[1, "datetime"] - forcing.loc[0, "datetime"]).total_seconds()
            dt_default = float(min(max(dt0, 1.0), 6.0 * 3600.0))
        else:
            dt_default = 3600.0

        results: list[dict[str, object]] = []
        if not forcing.empty:
            self.start_date = pd.Timestamp(forcing.iloc[0]["datetime"]).to_pydatetime()
            self.current_date = self.start_date.date()
            self.last_calc_time = self.start_date

        for index, row in forcing.iterrows():
            current_time = pd.Timestamp(row["datetime"]).to_pydatetime()
            try:
                if index == 0 or self.last_calc_time is None:
                    dt_seconds = dt_default
                else:
                    dt_seconds = max(1.0, (current_time - self.last_calc_time).total_seconds())

                self.update_inputs_from_row(row)
                self.run_timestep_calculations(dt_seconds, current_time)
                results.append(self.get_current_outputs(current_time))
                self.last_calc_time = current_time
            except Exception:
                LOGGER.exception("TomatoModel.run_simulation failed at step %s.", index)
                results.append(self.get_error_outputs(current_time))

        out = pd.DataFrame(results)
        if output_csv_path is not None:
            output_path = Path(output_csv_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            out.to_csv(output_path, index=False)
        return out

    def update_inputs_from_row(self, row: Mapping[str, object] | pd.Series) -> None:
        """Update model environment fields from a forcing row."""

        if hasattr(row, "index"):
            self._last_row_cols = {str(name) for name in row.index}
        else:
            self._last_row_cols = {str(name) for name in row.keys()}

        t_rad_candidate = row.get("T_rad_C", math.nan)
        self._last_row_used_T_rad = ("T_rad_C" in self._last_row_cols) and math.isfinite(
            _finite_float(t_rad_candidate, default=math.nan)
        )

        self.T_a = check_and_clip_value(row["T_air_C"], -50.0, 100.0, 20.0) + 273.15
        self.u_PAR = check_and_clip_value(row["PAR_umol"], 0.0, 3000.0, 0.0)
        self.u_CO2 = check_and_clip_value(row["CO2_ppm"], 300.0, 2000.0, 400.0)
        self.RH = check_and_clip_value(row["RH_percent"], 0.0, 100.0, 70.0) / 100.0
        self.u = check_and_clip_value(row["wind_speed_ms"], 0.01, 10.0, 0.1)
        if "theta_substrate" in self._last_row_cols:
            self.theta_substrate = _finite_float(row.get("theta_substrate", self.theta_substrate), default=self.theta_substrate)
        if "rootzone_multistress" in self._last_row_cols:
            self.rootzone_multistress = _finite_float(
                row.get("rootzone_multistress", self.rootzone_multistress),
                default=self.rootzone_multistress,
            )
        if "rootzone_saturation" in self._last_row_cols:
            self.rootzone_saturation = _finite_float(
                row.get("rootzone_saturation", self.rootzone_saturation),
                default=self.rootzone_saturation,
            )
        fruit_load_multiplier = _finite_float(
            getattr(self, "partition_policy_params", {}).get("fruit_load_multiplier", 1.0),
            default=1.0,
        )
        try:
            research_arch = self._current_research_architecture()
        except Exception:
            research_arch = None
        if research_arch is not None:
            fruit_load_multiplier = max(float(research_arch.fruit_load_multiplier), 0.25)

        base_n_f = check_and_clip_value(row["n_fruits_per_truss"], 1.0, 12.0, 4.0)
        self.n_f = int(round(check_and_clip_value(base_n_f * fruit_load_multiplier, 1.0, 12.0, 4.0)))
        self.Ci = self.u_CO2 * 0.7
        self.VPD = max(esat_Pa_from_T_C(self.T_a - 273.15) * (1.0 - self.RH) / 1000.0, 0.0)

        sw_in_candidate = row.get("SW_in_Wm2", math.nan)
        sw_in_value = _finite_float(sw_in_candidate, default=math.nan)
        if ("SW_in_Wm2" in self._last_row_cols) and math.isfinite(sw_in_value):
            self.SW_in_Wm2 = check_and_clip_value(sw_in_value, 0.0, 2000.0, 0.0)
        else:
            par_wm2 = self.u_PAR / self.W_TO_UMOL_CONVERSION
            frac = max(1e-6, float(self.PAR_FRACTION_OF_SW))
            self.SW_in_Wm2 = par_wm2 / frac

        if self._last_row_used_T_rad:
            self.T_rad_K = check_and_clip_value(t_rad_candidate, -50.0, 100.0, self.T_a - 273.15) + 273.15
        else:
            self.T_rad_K = self.T_a

    def get_current_outputs(self, current_time: datetime) -> dict[str, object]:
        """Return the bounded legacy output payload for the current timestep."""

        transp_rate_evap_g_s_m2 = (self.LE_evap / self.lambda_v * 1000.0) if self.lambda_v > 0 else 0.0
        transpiration_amount_g_m2 = transp_rate_evap_g_s_m2 * self.dt_seconds
        cond_rate_g_s_m2 = (self.LE_cond / self.lambda_v * 1000.0) if self.lambda_v > 0 else 0.0
        cond_amount_g_m2 = cond_rate_g_s_m2 * self.dt_seconds

        return {
            "datetime": current_time,
            "LAI": check_and_clip_value(self.LAI, 0.0, 100.0, 0.1),
            "T_canopy_C": check_and_clip_value(self.T_c - 273.15, -50.0, 100.0, 20.0),
            "total_dry_weight_g_m2": check_and_clip_value(self.W_lv + self.W_st + self.W_rt + self.W_fr, 0.0, 1e6, 0.0),
            "sensible_heat_W_m2": check_and_clip_value(self.H, -2000.0, 2000.0, 0.0),
            "latent_heat_W_m2": check_and_clip_value(self.LE, -2000.0, 2000.0, 0.0),
            "LE_W_m2_raw": check_and_clip_value(self.LE_raw, -2000.0, 2000.0, 0.0),
            "evaporation_W_m2": check_and_clip_value(self.LE_evap, 0.0, 2000.0, 0.0),
            "condensation_W_m2": check_and_clip_value(self.LE_cond, 0.0, 2000.0, 0.0),
            "transpiration_g_m2": check_and_clip_value(transpiration_amount_g_m2, 0.0, 1e6, 0.0),
            "condensation_g_m2": check_and_clip_value(cond_amount_g_m2, 0.0, 1e6, 0.0),
            "energy_balance_converged": float(self.convergence_status_Tc),
            "n_fruits_per_truss": float(self.n_f),
            "leaf_dry_weight_g_m2": check_and_clip_value(self.W_lv, 0.0, 1e6, 0.0),
            "fruit_dry_weight_g_m2": check_and_clip_value(self.W_fr, 0.0, 1e6, 0.0),
            "stem_dry_weight_g_m2": check_and_clip_value(self.W_st, 0.0, 1e6, 0.0),
            "root_dry_weight_g_m2": check_and_clip_value(self.W_rt, 0.0, 1e6, 0.0),
            "co2_flux_g_m2_s": check_and_clip_value(self.co2_flux_g_m2_s, -1.0, 1.0, 0.0),
            "crop_efficiency": check_and_clip_value(self._calculate_current_epsilon(), 0.0, 10.0, 0.0),
            "truss_count": float(self.truss_count),
            "transpiration_rate_g_s_m2": check_and_clip_value(transp_rate_evap_g_s_m2, 0.0, 1e6, 0.0),
            "daily_transpiration_mm": check_and_clip_value(self.last_daily_transpiration_g / 1000.0, 0.0, 1e6, 0.0),
            "current_transpiration_mm": check_and_clip_value(self.daily_transpiration_g / 1000.0, 0.0, 1e6, 0.0),
            "harvested_fruit_g_m2": check_and_clip_value(self.W_fr_harvested, 0.0, 1e7, 0.0),
            "fractional_cover": check_and_clip_value(self.f_c, 0.0, 1.0, 0.1),
            "SLA_m2_g": self.SLA,
            "active_trusses": float(self._count_active_trusses()),
            "alloc_frac_fruit": check_and_clip_value(self.part_fruit, 0.0, 1.0, math.nan),
            "alloc_frac_leaf": check_and_clip_value(self.part_leaf, 0.0, 1.0, math.nan),
            "alloc_frac_stem": check_and_clip_value(self.part_stem, 0.0, 1.0, math.nan),
            "alloc_frac_root": check_and_clip_value(self.part_root, 0.0, 1.0, math.nan),
            "alloc_frac_shoot": check_and_clip_value(self.part_shoot, 0.0, 1.0, math.nan),
            "reserve_pool_g_m2": check_and_clip_value(self.reserve_ch2o_g, 0.0, 1e6, 0.0),
            "buffer_pool_g_m2": check_and_clip_value(self.buffer_pool_g, 0.0, 1e6, 0.0),
            "fruit_abort_fraction": check_and_clip_value(self.fruit_abort_fraction, 0.0, 1.0, 0.0),
            "fruit_set_feedback_events": check_and_clip_value(self.fruit_set_feedback_events, 0.0, 1e6, 0.0),
            "maintenance_respiration_share": check_and_clip_value(
                self.maintenance_respiration_share,
                0.0,
                1.0,
                0.0,
            ),
            "mean_stage_residence_time_d": check_and_clip_value(
                self.mean_stage_residence_time_d,
                0.0,
                1e4,
                0.0,
            ),
            "rootzone_multistress": check_and_clip_value(self.rootzone_multistress, 0.0, 1.0, 0.0),
            "rootzone_saturation": check_and_clip_value(self.rootzone_saturation, 0.0, 1.0, 0.0),
            "VPD_kPa": check_and_clip_value(self.VPD, 0.0, 10.0, 0.0),
            "promoted_leaf_canopy_return_proxy": check_and_clip_value(
                self.promoted_leaf_canopy_return_proxy,
                -2.0,
                2.0,
                0.0,
            ),
            "promoted_stem_support_signal": check_and_clip_value(
                self.promoted_stem_support_signal,
                0.0,
                5.0,
                0.0,
            ),
            "promoted_root_gate_activation": check_and_clip_value(
                self.promoted_root_gate_activation,
                0.0,
                5.0,
                0.0,
            ),
            "promoted_supply_demand_ratio": check_and_clip_value(
                self.promoted_supply_demand_ratio,
                0.0,
                5.0,
                1.0,
            ),
            "promoted_low_sink_penalty": check_and_clip_value(
                self.promoted_low_sink_penalty,
                0.0,
                5.0,
                0.0,
            ),
        }

    def get_error_outputs(self, current_time: datetime) -> dict[str, object]:
        return {
            "datetime": current_time,
            "LAI": np.nan,
            "T_canopy_C": np.nan,
            "total_dry_weight_g_m2": np.nan,
            "sensible_heat_W_m2": np.nan,
            "latent_heat_W_m2": np.nan,
            "LE_W_m2_raw": np.nan,
            "evaporation_W_m2": np.nan,
            "condensation_W_m2": np.nan,
            "transpiration_g_m2": np.nan,
            "condensation_g_m2": np.nan,
            "energy_balance_converged": 0.0,
            "n_fruits_per_truss": np.nan,
            "leaf_dry_weight_g_m2": np.nan,
            "fruit_dry_weight_g_m2": np.nan,
            "stem_dry_weight_g_m2": np.nan,
            "root_dry_weight_g_m2": np.nan,
            "co2_flux_g_m2_s": np.nan,
            "crop_efficiency": np.nan,
            "truss_count": np.nan,
            "transpiration_rate_g_s_m2": np.nan,
            "daily_transpiration_mm": np.nan,
            "current_transpiration_mm": np.nan,
            "harvested_fruit_g_m2": np.nan,
            "fractional_cover": np.nan,
            "SLA_m2_g": np.nan,
            "active_trusses": np.nan,
            "alloc_frac_fruit": np.nan,
            "alloc_frac_leaf": np.nan,
            "alloc_frac_stem": np.nan,
            "alloc_frac_root": np.nan,
            "alloc_frac_shoot": np.nan,
            "reserve_pool_g_m2": np.nan,
            "buffer_pool_g_m2": np.nan,
            "fruit_abort_fraction": np.nan,
            "fruit_set_feedback_events": np.nan,
            "maintenance_respiration_share": np.nan,
            "mean_stage_residence_time_d": np.nan,
            "rootzone_multistress": np.nan,
            "rootzone_saturation": np.nan,
            "VPD_kPa": np.nan,
            "promoted_leaf_canopy_return_proxy": np.nan,
            "promoted_stem_support_signal": np.nan,
            "promoted_root_gate_activation": np.nan,
            "promoted_supply_demand_ratio": np.nan,
            "promoted_low_sink_penalty": np.nan,
        }

    def _current_research_architecture(self) -> TomicsResearchArchitecture | PromotedAllocatorConfig | None:
        policy_name = str(getattr(getattr(self, "partition_policy", None), "name", "")).strip().lower()
        if policy_name in {"tomics_alloc_research", "tomics_architecture_research"}:
            return coerce_tomics_research_architecture(self.partition_policy_params)
        if policy_name in {"tomics_promoted_research", "tomics_alloc_promoted_research"}:
            return PromotedAllocatorConfig.from_params(self.partition_policy_params)
        return None

    def _maintenance_efficiency_factor(
        self,
        *,
        architecture: TomicsResearchArchitecture | None,
        reserve_pool_g: float,
        buffer_pool_g: float,
    ) -> float:
        if architecture is None or architecture.maintenance_mode == "rgr_adjusted":
            rgr_used = getattr(self, "last_RGR", 0.03)
            return 1.0 - math.exp(-self.f_Rm_RGR * max(0.0, rgr_used))
        if architecture.maintenance_mode == "fixed":
            return 1.0
        if architecture.maintenance_mode == "buffer_linked":
            pool = max(float(reserve_pool_g), float(buffer_pool_g))
            capacity = max(
                architecture.buffer_capacity_g_ch2o_m2,
                architecture.storage_capacity_g_ch2o_m2,
                1e-9,
            )
            return 0.5 + 0.5 * min(max(pool / capacity, 0.0), 1.0)
        raise ValueError(f"Unsupported maintenance_mode {architecture.maintenance_mode!r}.")

    def _estimate_mean_stage_residence_time(self) -> float:
        active_tdvs = [
            float(cohort.get("tdvs", 0.0))
            for cohort in self.truss_cohorts
            if cohort.get("active", True)
        ]
        if not active_tdvs:
            return 0.0
        return float(sum(active_tdvs) / len(active_tdvs) * 30.0)

    def run_timestep_calculations(self, dt_seconds: float, current_time: datetime) -> None:
        """Advance one timestep using the updated v1_2 canopy and sink logic."""

        dt = float(dt_seconds)
        if dt <= 0:
            raise ValueError(f"dt_seconds must be > 0, got {dt_seconds!r}.")

        sim_date = current_time.date()
        if sim_date > self.current_date:
            self.update_daily_boundary(sim_date)
            self.current_date = sim_date

        self.dt_seconds = dt
        self.LAI = self.calculate_current_lai()
        self.f_c = self.calculate_vegetation_cover()
        self.water_supply_stress = self._resolve_water_supply_stress()
        research_architecture = self._current_research_architecture()

        self.solve_coupled_energy_balance()

        total_gross_photosynthesis_rate_umol, _, _ = self.calculate_canopy_photosynthesis(self.T_c)
        instantaneous_rm_g_ch2o = self.calculate_instantaneous_respiration(self.T_c)

        p_gross_g_co2 = total_gross_photosynthesis_rate_umol * 1e-6 * 44.01
        r_g_co2 = instantaneous_rm_g_ch2o * (44.01 / 30.03)
        self.co2_flux_g_m2_s = p_gross_g_co2 - r_g_co2

        self.daily_temp_accumulator.append((self.T_a, dt))
        gross_ch2o_prod_g = (total_gross_photosynthesis_rate_umol * 1e-6 * 30.03) * dt
        self.daily_gross_ch2o_g += max(0.0, gross_ch2o_prod_g)
        self.daily_par_umol_in_sum += max(0.0, self.u_PAR) * dt
        intercepted_par_umol_s = max(0.0, self.u_PAR * (1.0 - math.exp(-self.k_ext * max(0.0, self.LAI))))
        self.daily_par_umol_int_sum += intercepted_par_umol_s * dt

        transp_rate_evap_g_s_m2 = (self.LE_evap / self.lambda_v * 1000.0) if self.lambda_v > 0 else 0.0
        self.daily_transpiration_g += transp_rate_evap_g_s_m2 * dt

        rm_base_g_s = self.calculate_instantaneous_respiration(self.T_c)
        rm_eff_factor = self._maintenance_efficiency_factor(
            architecture=research_architecture,
            reserve_pool_g=self.reserve_ch2o_g,
            buffer_pool_g=self.buffer_pool_g,
        )
        rm_eff_g_s = rm_base_g_s * rm_eff_factor
        net_ch2o_step_g = max(0.0, gross_ch2o_prod_g - rm_eff_g_s * dt)
        self.maintenance_respiration_share = 0.0
        if gross_ch2o_prod_g > 1e-12:
            self.maintenance_respiration_share = max(
                0.0,
                min((rm_eff_g_s * dt) / gross_ch2o_prod_g, 1.0),
            )

        t_air_c = self.T_a - 273.15
        for cohort in self.truss_cohorts:
            if not cohort.get("active", True):
                continue
            cohort["tdvs"] = self._advance_tdvs_with_fdvr(float(cohort.get("tdvs", 0.0)), t_air_c, dt)
            if float(cohort["tdvs"]) >= self.tdvs_max:
                cohort["active"] = False

        sinks, per_truss_sinks = self._compute_sink_state()
        active_trusses = self._count_active_trusses()
        self.fruit_abort_fraction = 0.0
        self.fruit_set_feedback_events = 0
        if research_architecture is not None:
            supply_dm_equivalent_g_d = 0.0
            if dt > 0.0:
                supply_dm_equivalent_g_d = (net_ch2o_step_g / dt) * 86400.0
            sinks, self.fruit_abort_fraction, self.fruit_set_feedback_events = apply_fruit_feedback_proxy(
                mode=research_architecture.fruit_feedback_mode,
                sinks=sinks,
                supply_dm_equivalent_g_d=supply_dm_equivalent_g_d,
                active_trusses=active_trusses,
                threshold=research_architecture.fruit_feedback_threshold,
                slope=research_architecture.fruit_feedback_slope,
            )
        alloc = self._resolve_allocation_fractions(current_time=current_time, sinks=sinks)

        self.part_fruit = alloc["fruit"]
        self.part_leaf = alloc["leaf"]
        self.part_stem = alloc["stem"]
        self.part_root = alloc["root"]
        self.part_shoot = alloc["leaf"] + alloc["stem"]
        self.part_veg = self.part_shoot + self.part_root

        denom_cf = (
            self.ASR["lv"] * self.part_leaf
            + self.ASR["st"] * self.part_stem
            + self.ASR["rt"] * self.part_root
            + self.ASR["fr"] * self.part_fruit
        )
        c_f = 1.0 / denom_cf if denom_cf > 1e-12 else 0.0

        s_total_dm_d = max(0.0, float(sinks["S_fr_g_d"]) + float(sinks["S_veg_g_d"]))
        cap_dm_step = s_total_dm_d * (dt / 86400.0)
        reserve_mode = "off"
        if research_architecture is not None:
            reserve_mode = research_architecture.reserve_buffer_mode
        dW_total_step, self.reserve_ch2o_g, self.buffer_pool_g = resolve_realized_growth_with_buffer(
            mode=reserve_mode,
            net_ch2o_step_g=net_ch2o_step_g,
            c_f=c_f,
            cap_dm_step=cap_dm_step,
            reserve_pool_g=self.reserve_ch2o_g,
            buffer_pool_g=self.buffer_pool_g,
            storage_capacity_g=(
                self.reserve_ch2o_g + cap_dm_step + 1.0
                if research_architecture is None
                else research_architecture.storage_capacity_g_ch2o_m2
            ),
            storage_carryover_fraction=(
                1.0 if research_architecture is None else research_architecture.storage_carryover_fraction
            ),
            buffer_capacity_g=(0.0 if research_architecture is None else research_architecture.buffer_capacity_g_ch2o_m2),
            buffer_min_fraction=(0.0 if research_architecture is None else research_architecture.buffer_min_fraction),
        )

        if dW_total_step > 0.0:
            self.W_lv = max(0.0, self.W_lv + dW_total_step * self.part_leaf)
            self.W_st = max(0.0, self.W_st + dW_total_step * self.part_stem)
            self.W_rt = max(0.0, self.W_rt + dW_total_step * self.part_root)

            dW_fr_total_step = dW_total_step * self.part_fruit
            if dW_fr_total_step > 0.0 and float(sinks["S_fr_g_d"]) > 1e-9 and self.use_age_structured_sink:
                total_sink = max(sum(per_truss_sinks), 1e-12)
                for idx, cohort in enumerate(self.truss_cohorts):
                    if not cohort.get("active", True):
                        continue
                    if idx >= len(per_truss_sinks):
                        continue
                    truss_sink_share = max(0.0, per_truss_sinks[idx]) / total_sink
                    cohort["w_fr_cohort"] = float(cohort.get("w_fr_cohort", 0.0)) + dW_fr_total_step * truss_sink_share
            elif dW_fr_total_step > 0.0:
                self.W_fr += dW_fr_total_step

            if self.use_age_structured_sink and float(sinks["S_fr_g_d"]) > 1e-9:
                self.W_fr = sum(max(0.0, float(cohort.get("w_fr_cohort", 0.0))) for cohort in self.truss_cohorts)

            if self.fixed_lai is None:
                self.LAI = self.W_lv * self.SLA
                if self.LAI > self.LAI_max and self.SLA > 1e-9:
                    excess_lai = self.LAI - self.LAI_max
                    excess_w_lv = excess_lai / self.SLA
                    self.W_lv = max(0.0, self.W_lv - excess_w_lv)
                    self.LAI = self.LAI_max

            self.daily_dW_total += dW_total_step

        self._harvest_matured_cohorts()
        self.vegetative_dw = self.W_lv + self.W_st + self.W_rt
        self.fruit_dw = self.W_fr
        self.mean_stage_residence_time_d = self._estimate_mean_stage_residence_time()
        self.common_structure_snapshot = build_common_structure_snapshot(
            assimilate_buffer_g=max(self.reserve_ch2o_g, self.buffer_pool_g),
            leaf_biomass_g=self.W_lv,
            stem_root_biomass_g=self.W_st + self.W_rt,
            fruit_biomass_g=self.W_fr,
            photosynthesis_g=max(0.0, gross_ch2o_prod_g),
            growth_respiration_g=max(0.0, dW_total_step / max(c_f, 1e-9) - dW_total_step),
            growth_g=max(0.0, dW_total_step),
            maintenance_g=max(0.0, rm_eff_g_s * dt),
            fruit_harvest_g=self.W_fr_harvested,
            leaf_harvest_g=0.0,
        )

    def calculate_current_lai(self) -> float:
        if self.fixed_lai is not None:
            return float(self.fixed_lai)
        return max(0.0, self.W_lv * self.SLA)

    def calculate_vegetation_cover(self) -> float:
        lai = float(getattr(self, "LAI", 0.0))
        if (not math.isfinite(lai)) or lai <= 1e-6:
            return 0.0
        return float(min(max(1.0 - math.exp(-self.k_ext * lai), 0.0), 1.0))

    def solve_coupled_energy_balance(self) -> None:
        initial_guess = np.asarray([self.T_a], dtype=float)
        try:
            solution, _, ier, message = fsolve(
                self._energy_balance_residual,
                initial_guess,
                full_output=True,
            )
            if ier == 1:
                self.T_c = float(solution[0])
                self.convergence_status_Tc = True
            else:
                LOGGER.warning("Energy balance solver failed: %s. Falling back to T_c = T_a.", message)
                self.T_c = float(self.T_a)
                self.convergence_status_Tc = False
        except Exception:
            LOGGER.exception("Error during energy balance solving; falling back to air temperature.")
            self.T_c = float(self.T_a)
            self.convergence_status_Tc = False

        self.H = self.calculate_sensible_heat(self.T_c)
        rn = self.calculate_net_radiation(self.T_c)
        self.LE = self.calculate_canopy_latent_heat(self.T_c, Rn_Wm2=rn)

    def _energy_balance_residual(self, t_c_k_guess: object) -> float:
        t_c_k = float(np.atleast_1d(np.asarray(t_c_k_guess, dtype=float))[0])
        self.r_b = 70.0 / math.sqrt(max(self.u, 1e-6))
        self.r_ah = 50.0 * math.sqrt(self.leaf_dimension / max(self.u, 1e-6))

        rn = self.calculate_net_radiation(t_c_k)
        h = self.calculate_sensible_heat(t_c_k)
        le = self.calculate_canopy_latent_heat(t_c_k, Rn_Wm2=rn)
        return float(rn - h - le)

    def calculate_net_radiation(self, t_c_k: float) -> float:
        sw_in = max(0.0, float(getattr(self, "SW_in_Wm2", 0.0)))
        r_sw_abs = sw_in * (1.0 - self.alpha_c) * self.f_c

        t_env = float(self.T_a)
        if bool(getattr(self, "_last_row_used_T_rad", False)):
            t_env = float(getattr(self, "T_rad_K", self.T_a))

        eps_cover = min(max(float(getattr(self, "emissivity_cover", 0.84)), 1e-6), 1.0)
        eps_leaf = min(max(float(self.emissivity_c), 1e-6), 1.0)
        denom = (1.0 / eps_cover + 1.0 / eps_leaf - 1.0)
        eps_eff = min(max(1.0 / max(1e-6, denom), 0.0), 1.0)
        r_lw_net = eps_eff * self.sigma * (t_env**4 - float(t_c_k) ** 4) * self.f_c

        self.eps_eff_last = eps_eff
        self.T_env_last_K = t_env
        self.r_lw_net_last = r_lw_net
        return float(r_sw_abs + r_lw_net)

    def calculate_sensible_heat(self, t_c_k: float) -> float:
        if self.r_ah <= 1e-9:
            return 0.0
        return float(self.rho_a * self.c_p * (float(t_c_k) - self.T_a) / self.r_ah)

    def calculate_canopy_latent_heat(self, t_c_k: float, Rn_Wm2: float | None = None) -> float:
        if Rn_Wm2 is None:
            Rn_Wm2 = self.calculate_net_radiation(t_c_k)

        ta_c = self.T_a - 273.15
        es_ta = esat_Pa_from_T_C(ta_c)
        ea = es_ta * min(max(float(self.RH), 0.0), 1.0)

        tc_c = float(t_c_k) - 273.15
        es_tc = esat_Pa_from_T_C(tc_c)
        vpd = es_tc - ea

        _, _, gsw_canopy = self.calculate_canopy_photosynthesis(t_c_k)
        gsw_canopy = max(float(gsw_canopy), 1e-9)
        rc = 1.0 / gsw_canopy

        le = penman_monteith_LE_Wm2(
            Rn_Wm2=float(Rn_Wm2),
            Ta_K=float(self.T_a),
            VPD_Pa=float(vpd),
            ra_s_m=float(self.r_ah),
            rc_s_m=float(rc),
            rho=float(self.rho_a),
            cp=float(self.c_p),
            gamma_PaK=float(self.gamma),
            allow_negative=bool(getattr(self, "allow_condensation", True)),
        )

        self.LE_raw = float(le)
        self.LE_evap = float(max(0.0, le))
        self.LE_cond = float(max(0.0, -le))
        return float(le)

    def calculate_canopy_photosynthesis(self, t_c_k: float) -> tuple[float, float, float]:
        if self.LAI <= 1e-9:
            return 0.0, 0.0, 0.0

        stress = self._resolve_water_supply_stress()
        if self.photosyn_mode == "tomsim_canopy":
            alpha = 0.02
            pgc_max = 40.0
            pg = pgc_max * (1.0 - math.exp(-alpha * max(0.0, self.u_PAR))) * stress
            _, _, gsw = self.calculate_leaf_fvcb(t_c_k, self.u_PAR, self.Ci)
            return float(pg), 0.0, float(gsw)

        total_gross_a = 0.0
        total_gsw = 0.0
        lai_above = 0.0
        n_layers = 10
        lai_layer = self.LAI / n_layers
        par_total_wm2 = self.u_PAR / self.W_TO_UMOL_CONVERSION

        for _ in range(n_layers):
            par_layer_wm2 = par_total_wm2 * math.exp(-self.k_ext * (lai_above + 0.5 * lai_layer))
            par_layer_umol = par_layer_wm2 * self.W_TO_UMOL_CONVERSION
            a, r_d, gsw = self.calculate_leaf_fvcb(t_c_k, par_layer_umol, self.Ci)
            gross_a = max(0.0, a)
            total_gross_a += gross_a * lai_layer
            total_gsw += gsw * lai_layer
            lai_above += lai_layer

        self.last_gsw_canopy = total_gsw
        return float(total_gross_a), 0.0, float(total_gsw)

    def calculate_leaf_fvcb(self, T_K: float, PARi: float, Ci_initial: float) -> tuple[float, float, float]:
        jp = self.joubert_params
        Vcmax = float(jp["Vcmax"])
        Jmax = float(jp["Jmax"])
        Rd = float(jp["Rd"])
        theta_J = float(jp["theta_J"])
        c1 = float(jp["c1"])
        dHa1 = float(jp["dHa1_kJ"])
        c2 = float(jp["c2"])
        dHa2 = float(jp["dHa2_kJ"])
        c3 = float(jp["c3"])
        dHa3 = float(jp["dHa3_kJ"])
        R1 = float(jp["R1_kJ"])
        Oi_kPa = float(jp["O_i_kPa"])

        gamma_star = math.exp(c1 - (dHa1 / (R1 * T_K)))
        Ko = math.exp(c2 - (dHa2 / (R1 * T_K)))
        Kc = math.exp(c3 - (dHa3 / (R1 * T_K)))

        alpha = float(self.fcvb_params.get("a", 0.3))
        if theta_J <= 1e-12:
            J = 0.0
        else:
            disc = (alpha * PARi + Jmax) ** 2 - 4.0 * theta_J * alpha * PARi * Jmax
            J = (alpha * PARi + Jmax - math.sqrt(max(0.0, disc))) / (2.0 * theta_J)

        Ci = max(1e-6, float(Ci_initial))
        A = 0.0
        gsw_mol = 0.019
        for _ in range(100):
            Ac = Vcmax * (Ci - gamma_star) / (Ci + Kc * (1.0 + Oi_kPa / max(1e-9, Ko))) - Rd
            Aj = J * (Ci - gamma_star) / (4.0 * Ci + 8.0 * gamma_star) - Rd
            A = max(0.0, min(Ac, Aj))

            h_frac = min(max(float(self.RH), 0.0), 1.0)
            gsw_mol = (((A * 26.85 * h_frac) / self.u_CO2) + 0.019) if self.u_CO2 > 0 else 0.019
            gsw_mol = max(1e-9, gsw_mol)
            gsc_mol = gsw_mol / 1.6
            Ci_new = self.u_CO2 - A / gsc_mol if gsc_mol > 1e-9 else Ci
            Ci_new = min(max(float(Ci_new), 1.0), self.u_CO2)
            if abs(Ci_new - Ci) < 0.001:
                Ci = Ci_new
                break
            Ci = Ci_new

        water_stress = self._resolve_water_supply_stress()
        A *= water_stress
        gsw_ms = gsw_mol * (float(self.fcvb_params["R"]) * T_K / 101325.0) * water_stress
        return float(A), float(Rd), float(gsw_ms)

    def calculate_instantaneous_respiration(self, t_c_k: float) -> float:
        t_c_c = float(t_c_k) - 273.15
        q10 = self.Q10_maint ** ((t_c_c - 25.0) / 10.0)
        rm_day = (
            self.W_lv * self.MAINT_25C["lv"] * q10
            + self.W_st * self.MAINT_25C["st"] * q10
            + self.W_rt * self.MAINT_25C["rt"] * q10
            + self.W_fr * self.MAINT_25C["fr"] * q10
        )
        return float(rm_day / (24.0 * 3600.0))

    def get_current_sim_time(self, time_step_hours: float) -> datetime:
        return self.start_date + timedelta(hours=float(time_step_hours))

    def set_plant_density(
        self,
        plants_per_m2: float | None = None,
        shoots_per_plant: float | None = None,
        shoots_per_m2: float | None = None,
    ) -> None:
        old_shoots_per_m2 = float(getattr(self, "shoots_per_m2", 0.0))
        if shoots_per_m2 is not None:
            self.shoots_per_m2 = float(shoots_per_m2)
            if shoots_per_plant is not None:
                self.shoots_per_plant = float(shoots_per_plant)
                self.plants_per_m2 = self.shoots_per_m2 / self.shoots_per_plant if self.shoots_per_plant > 0 else 0.0
            elif plants_per_m2 is not None:
                self.plants_per_m2 = float(plants_per_m2)
                self.shoots_per_plant = self.shoots_per_m2 / self.plants_per_m2 if self.plants_per_m2 > 0 else 0.0
            else:
                self.plants_per_m2 = self.shoots_per_m2 / self.shoots_per_plant if self.shoots_per_plant > 0 else 0.0
        else:
            if plants_per_m2 is not None:
                self.plants_per_m2 = float(plants_per_m2)
            if shoots_per_plant is not None:
                self.shoots_per_plant = float(shoots_per_plant)
            self.shoots_per_m2 = self.plants_per_m2 * self.shoots_per_plant

        for cohort in self.truss_cohorts:
            cohort["mult"] = self.shoots_per_m2

        if old_shoots_per_m2 > 0 and self.shoots_per_m2 <= 0:
            LOGGER.warning("shoots_per_m2 is now <= 0; per-shoot conversions will be invalid.")

    def update_daily_boundary(self, sim_date: date) -> None:
        """Update daily state, SLA, RGR, FR(T)-based truss appearance, and diagnostics."""

        total_duration = sum(duration for _, duration in self.daily_temp_accumulator)
        if total_duration > 0:
            weighted_temp_sum = sum(temp_k * duration for temp_k, duration in self.daily_temp_accumulator)
            avg_temp_k = weighted_temp_sum / total_duration
        else:
            avg_temp_k = self.T_a
        avg_temp_c = avg_temp_k - 273.15
        self.daily_temp_accumulator = []

        doy = sim_date.timetuple().tm_yday
        research_architecture = self._current_research_architecture()
        sla_cm2_per_g = 266.0 + 88.0 * math.sin(2.0 * math.pi * (doy + 68) / 365.0)
        if research_architecture is not None and research_architecture.sla_mode == "tomgro_independent_driver":
            par_mol_m2_d = self.daily_par_umol_in_sum * 1e-6
            temp_scalar = max(0.55, min(1.35, 1.0 - 0.015 * (avg_temp_c - 23.0)))
            co2_scalar = max(0.75, min(1.20, 1.0 - 0.00035 * (self.u_CO2 - 350.0)))
            par_scalar = max(0.55, min(1.30, 1.15 - 0.04 * min(par_mol_m2_d, 12.0)))
            sla_cm2_per_g = max(120.0, min(450.0, 320.0 * temp_scalar * co2_scalar * par_scalar))
        self.SLA = max(0.0001, sla_cm2_per_g / 10000.0)
        if self.fixed_lai is None:
            self.LAI = self.W_lv * self.SLA

        current_total_dm = self.W_lv + self.W_st + self.W_rt + self.W_fr
        self.recent_total_dm_history.append(current_total_dm)
        if len(self.recent_total_dm_history) > 8:
            self.recent_total_dm_history = self.recent_total_dm_history[-8:]

        if len(self.recent_total_dm_history) >= 6 and self.recent_total_dm_history[-6] > 0:
            RGR = math.log(self.recent_total_dm_history[-1] / self.recent_total_dm_history[-6]) / 5.0
        elif len(self.recent_total_dm_history) >= 2 and self.recent_total_dm_history[-2] > 0:
            RGR = math.log(self.recent_total_dm_history[-1] / self.recent_total_dm_history[-2])
        else:
            RGR = 0.03
        self.last_RGR = max(0.0, float(RGR))

        t_for_fr = max(1.0, avg_temp_c)
        if self.fr_clamp_to_valid:
            t_for_fr = min(max(t_for_fr, self.fr_T_min_valid), self.fr_T_max_valid)
        fr = max(0.0, -0.2903 + 0.1454 * math.log(max(1.0, t_for_fr)))
        self._truss_fraction_acc += fr

        while self._truss_fraction_acc >= 1.0:
            self.truss_count += 1
            self._truss_fraction_acc -= 1.0
            if self.pending_n_fruits:
                try:
                    nfr = int(max(0, self.pending_n_fruits.pop(0)))
                except Exception:
                    nfr = int(self.n_f)
            else:
                nfr = int(self.n_f)
            self.truss_cohorts.append(
                {
                    "tdvs": 0.0,
                    "n_fruits": nfr,
                    "w_fr_cohort": 0.0,
                    "active": True,
                    "mult": self.shoots_per_m2,
                }
            )

        self._harvest_matured_cohorts()

        intercepted_par_mj = self.daily_par_umol_int_sum * PHOTON_UMOL_TO_MJ
        self.last_daily_dW_total = self.daily_dW_total
        self.last_daily_epsilon = 0.0 if intercepted_par_mj <= 1e-9 else (self.daily_dW_total / intercepted_par_mj)
        self.last_daily_transpiration_g = self.daily_transpiration_g

        self.daily_gross_ch2o_g = 0.0
        self.daily_par_umol_in_sum = 0.0
        self.daily_par_umol_int_sum = 0.0
        self.daily_dW_total = 0.0
        self.daily_transpiration_g = 0.0

    def _roll_daily_state(self, sim_date: date) -> None:
        """Compatibility wrapper around the v1_2 daily boundary update."""

        self.update_daily_boundary(sim_date)

    def _compute_sink_state(self) -> tuple[dict[str, float], list[float]]:
        research_architecture = self._current_research_architecture()
        if self.use_age_structured_sink:
            per_truss_sinks = self._compute_per_truss_sinks_gd(research_architecture)
            s_fr_g_d = sum(per_truss_sinks)
        else:
            active_trusses = self._count_active_trusses()
            nominal_singlefruit_pgr = 1.0
            s_fr_g_d = active_trusses * self.n_f * nominal_singlefruit_pgr
            per_truss_sinks = []

        s_veg_g_d = max(1e-9, float(self.to_floor_from_shoot(self.veg_sink_g_d_per_shoot)))
        if research_architecture is not None:
            if research_architecture.vegetative_demand_mode == "dekoning_vegetative_unit":
                s_veg_g_d *= 1.0 + 0.08 * min(self._count_active_trusses(), 6)
            elif research_architecture.vegetative_demand_mode == "tomgro_dynamic_age":
                lai_gap = max(research_architecture.lai_target_center - max(self.LAI, 0.1), 0.0)
                s_veg_g_d *= 1.0 + min(lai_gap / max(research_architecture.lai_target_center, 1e-6), 0.25)
        return {
            "S_fr_g_d": max(0.0, float(s_fr_g_d)),
            "S_veg_g_d": s_veg_g_d,
        }, per_truss_sinks

    def _default_sink_proxy(self) -> dict[str, float]:
        sinks, _ = self._compute_sink_state()
        return sinks

    def _resolve_allocation_fractions(self, *, current_time: datetime, sinks: dict[str, float]) -> dict[str, float]:
        env = EnvStep(
            t=current_time,
            dt_s=self.dt_seconds,
            T_air_C=self.T_a - 273.15,
            PAR_umol=self.u_PAR,
            CO2_ppm=self.u_CO2,
            RH_percent=self.RH * 100.0,
            wind_speed_ms=self.u,
            SW_in_Wm2=self.SW_in_Wm2,
            T_rad_C=self.T_rad_K - 273.15,
            n_fruits_per_truss=self.n_f,
        )

        alloc = self._allocation_from_policy(env=env, sinks=sinks)
        if alloc is None:
            s_fr_g_d = max(float(sinks["S_fr_g_d"]), 0.0)
            s_veg_g_d = max(float(sinks["S_veg_g_d"]), 1e-9)
            total = max(s_fr_g_d + s_veg_g_d, 1e-9)
            f_fr_total = s_fr_g_d / total
            f_veg_total = 1.0 - f_fr_total
            f_rt = f_veg_total * self.root_frac_of_total_veg
            f_shoot = f_veg_total - f_rt
            alloc = {
                "fruit": f_fr_total,
                "leaf": f_shoot * 0.7,
                "stem": f_shoot * 0.3,
                "root": f_rt,
            }

        return self._normalize_allocation(alloc)

    def _allocation_from_policy(self, *, env: EnvStep, sinks: dict[str, float]) -> dict[str, float] | None:
        compute = getattr(self.partition_policy, "compute", None)
        if not callable(compute):
            return None

        try:
            raw = compute(
                env=env,
                state=self,
                sinks=sinks,
                scheme=self.allocation_scheme,
                params=self.partition_policy_params,
            )
        except Exception:
            LOGGER.exception("Custom partition_policy.compute failed; falling back to sink-based split.")
            return None

        values = getattr(raw, "values", raw)
        if not isinstance(values, Mapping):
            return None

        normalized = {_resolve_partition_key(key): _finite_float(value, default=0.0) for key, value in values.items()}
        if "fruit" not in normalized or "root" not in normalized:
            return None

        if "shoot" in normalized:
            shoot = max(normalized["shoot"], 0.0)
            return {
                "fruit": max(normalized["fruit"], 0.0),
                "leaf": shoot * 0.7,
                "stem": shoot * 0.3,
                "root": max(normalized["root"], 0.0),
            }

        if {"leaf", "stem"} <= normalized.keys():
            return {
                "fruit": max(normalized["fruit"], 0.0),
                "leaf": max(normalized["leaf"], 0.0),
                "stem": max(normalized["stem"], 0.0),
                "root": max(normalized["root"], 0.0),
            }
        return None

    def _normalize_allocation(self, alloc: Mapping[str, object]) -> dict[str, float]:
        cleaned = {
            "fruit": max(_finite_float(alloc.get("fruit", 0.0), default=0.0), 0.0),
            "leaf": max(_finite_float(alloc.get("leaf", 0.0), default=0.0), 0.0),
            "stem": max(_finite_float(alloc.get("stem", 0.0), default=0.0), 0.0),
            "root": max(_finite_float(alloc.get("root", 0.0), default=0.0), 0.0),
        }
        total = sum(cleaned.values())
        if total <= 1e-12:
            return {"fruit": 0.0, "leaf": 0.7, "stem": 0.3, "root": 0.0}
        return {key: value / total for key, value in cleaned.items()}

    def _calculate_current_epsilon(self) -> float:
        intercepted_par_mj = self.daily_par_umol_int_sum * PHOTON_UMOL_TO_MJ
        if intercepted_par_mj <= 1e-9:
            return float(self.last_daily_epsilon)
        return float(max(self.daily_dW_total, 0.0) / intercepted_par_mj)

    def _compute_generative_sink_absolute_gd(self) -> float:
        total_g_d = 0.0
        for cohort in self.truss_cohorts:
            if not cohort.get("active", True):
                continue
            tdvs = float(cohort.get("tdvs", 0.0))
            if tdvs <= float(self.pgr_params["c"]):
                continue
            pgr_singlefruit = self._pgr_richards_raw(tdvs)
            if pgr_singlefruit <= 0.0:
                continue
            mult = float(cohort.get("mult", 1.0))
            total_g_d += mult * float(cohort.get("n_fruits", self.n_f)) * pgr_singlefruit
        return max(0.0, total_g_d)

    def _compute_per_truss_sinks_gd(
        self,
        research_architecture: TomicsResearchArchitecture | None = None,
    ) -> list[float]:
        sinks: list[float] = []
        n_classes = 3
        if research_architecture is not None and research_architecture.fruit_structure_mode == "vanthoor_fixed_boxcar":
            n_classes = 5
        for cohort in self.truss_cohorts:
            if not cohort.get("active", True):
                sinks.append(0.0)
                continue
            tdvs = float(cohort.get("tdvs", 0.0))
            if tdvs <= float(self.pgr_params["c"]):
                sinks.append(0.0)
                continue
            effective_tdvs = tdvs
            if research_architecture is not None:
                if research_architecture.fruit_structure_mode == "tomgro_age_class":
                    class_idx = min(max(int(tdvs * n_classes), 0), n_classes - 1)
                    effective_tdvs = (class_idx + 0.5) / n_classes
                elif research_architecture.fruit_structure_mode == "vanthoor_fixed_boxcar":
                    class_idx = min(max(int(tdvs * n_classes), 0), n_classes - 1)
                    effective_tdvs = (class_idx + 0.5) / n_classes
            pgr_singlefruit = self._pgr_richards_raw(effective_tdvs)
            if pgr_singlefruit <= 0.0:
                sinks.append(0.0)
                continue
            mult = float(cohort.get("mult", 1.0))
            truss_sink = mult * float(cohort.get("n_fruits", self.n_f)) * pgr_singlefruit
            sinks.append(truss_sink)
        return sinks

    def _pgr_richards_raw(self, tdvs: float) -> float:
        a = float(self.pgr_params.get("a", 0.138))
        b = float(self.pgr_params.get("b", 4.34))
        c = float(self.pgr_params.get("c", 0.278))
        d = float(self.pgr_params.get("d", 1.31))

        if d == 1.0:
            return 0.0

        z = b * (float(tdvs) - c)
        try:
            e_z = math.exp(z)
        except OverflowError:
            e_z = float("inf")
        e_neg_z = float("inf") if e_z == 0.0 else 1.0 / e_z

        base = 1.0 + e_neg_z
        exponent = 1.0 / (1.0 - d)
        numerator = a * b * (base**exponent)
        denominator = (d - 1.0) * (e_z + 1.0)
        if denominator == 0.0:
            return 0.0

        return max(0.0, float(numerator / denominator))

    def set_truss_n_f(self, idx: int, n_fruits: int) -> None:
        if 0 <= idx < len(self.truss_cohorts):
            self.truss_cohorts[idx]["n_fruits"] = int(max(0, n_fruits))

    def bulk_set_truss_n_f(self, values: list[int], order: str = "oldest") -> None:
        if not values:
            return
        idxs = range(len(self.truss_cohorts)) if order == "oldest" else reversed(range(len(self.truss_cohorts)))
        for idx, value in zip(idxs, values):
            self.truss_cohorts[idx]["n_fruits"] = int(max(0, value))

    def queue_truss_n_f(self, values: list[int]) -> None:
        if values:
            self.pending_n_fruits.extend(int(max(0, value)) for value in values)

    def _count_active_trusses(self) -> int:
        return sum(1 for cohort in self.truss_cohorts if cohort.get("active", True))

    def _advance_tdvs_with_fdvr(self, tdvs: float, T_C: float, dt_s: float) -> float:
        t_ratio = max(float(T_C), 0.1) / 20.0
        ln_term = math.log(t_ratio)
        fdvr = 0.0181 + ln_term * (
            0.0392 - 0.213 * tdvs + 0.451 * tdvs * tdvs - 0.240 * tdvs * tdvs * tdvs
        )
        tdvs_next = float(tdvs) + fdvr * (float(dt_s) / 86400.0)
        if tdvs_next < self.tdvs_min:
            tdvs_next = self.tdvs_min
        if tdvs_next > self.tdvs_max:
            tdvs_next = self.tdvs_max
        return float(tdvs_next)

    def _resolve_water_supply_stress(self) -> float:
        theta = min(max(_finite_float(getattr(self, "theta_substrate", 0.33), default=0.33), 0.0), 1.0)
        moisture_response_fn = getattr(self, "moisture_response_fn", None)
        if callable(moisture_response_fn):
            try:
                return float(water_supply_stress_from_theta(theta, moisture_response_fn))
            except Exception:
                LOGGER.exception("moisture_response_fn failed; falling back to no stress.")
        return 1.0

    def _harvest_matured_cohorts(self) -> None:
        matured_indices: list[int] = []
        harvested_now = 0.0
        for idx, cohort in enumerate(self.truss_cohorts):
            tdvs = float(cohort.get("tdvs", 0.0))
            is_active = bool(cohort.get("active", True))
            truss_dm = max(0.0, float(cohort.get("w_fr_cohort", 0.0)))
            if truss_dm >= self.harvest_truss_dm_g:
                cohort["active"] = False
                is_active = False
            if (not is_active) or tdvs >= self.tdvs_max:
                harvested_now += truss_dm
                matured_indices.append(idx)

        if matured_indices:
            for idx in reversed(matured_indices):
                del self.truss_cohorts[idx]
            self.W_fr_harvested += harvested_now
            self.W_fr = sum(max(0.0, float(cohort.get("w_fr_cohort", 0.0))) for cohort in self.truss_cohorts)


def create_sample_input_csv(filename: str | Path = "sample_tomato_input.csv", days: int = 90) -> str:
    """Create a deterministic sample forcing CSV matching the legacy utility contract."""

    output_path = Path(filename)
    start_date = datetime(2021, 2, 23)
    dates = [start_date + timedelta(hours=index) for index in range(days * 24)]
    rng = np.random.default_rng(0)

    data: list[dict[str, object]] = []
    for dt in dates:
        hour = dt.hour
        day_of_year = dt.timetuple().tm_yday

        t_air = 24.0 + 6.0 * math.sin(2.0 * math.pi * (hour - 6) / 24.0) + 3.0 * math.sin(
            2.0 * math.pi * day_of_year / 365.0
        )
        if 6 <= hour <= 18:
            par = 1000.0 + 500.0 * math.sin(math.pi * (hour - 6) / 12.0) * math.sin(
                2.0 * math.pi * day_of_year / 365.0 + math.pi / 2.0
            )
        else:
            par = 0.0

        co2 = 400.0 + 100.0 * math.sin(2.0 * math.pi * hour / 24.0)
        rh = 65.0 + 25.0 * math.sin(2.0 * math.pi * (hour - 12) / 24.0)
        wind_speed = 0.3 + 0.4 * float(rng.random())
        data.append(
            {
                "datetime": dt.strftime("%Y-%m-%d %H:%M:%S"),
                "T_air_C": round(t_air, 1),
                "PAR_umol": round(max(0.0, par), 0),
                "CO2_ppm": round(co2, 1),
                "RH_percent": round(min(max(rh, 30.0), 95.0), 1),
                "wind_speed_ms": round(wind_speed, 2),
                "n_fruits_per_truss": 4,
            }
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(data).to_csv(output_path, index=False)
    return str(output_path)


__all__ = ["TomatoModel", "check_and_clip_value", "create_sample_input_csv"]
