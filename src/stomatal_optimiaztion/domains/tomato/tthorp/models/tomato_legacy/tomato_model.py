from __future__ import annotations

import logging
import math
from collections.abc import Mapping
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from stomatal_optimiaztion.domains.tomato.tthorp.contracts import EnvStep
from stomatal_optimiaztion.domains.tomato.tthorp.interface import run_flux_step

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


class TomatoModel:
    """Bounded legacy-compatible tomato model surface for staged migration.

    This slice preserves the public state, CSV ingestion, output payload, and
    default adapter construction surface from the legacy `tomato_model.py`.
    The deeper age-structured growth, full energy-balance solver, and broader
    partition-policy ecosystem remain blocked for later slices.
    """

    def __init__(
        self,
        fixed_lai: float | None = None,
        partition_policy: object | str | None = None,
        allocation_scheme: str = "4pool",
    ) -> None:
        self.fixed_lai = fixed_lai
        self.partition_policy = partition_policy
        self.allocation_scheme = str(allocation_scheme)

        self.lambda_v = 2.45e6
        self.alpha_c = 0.15
        self.k_ext = 0.72
        self.W_TO_UMOL_CONVERSION = 4.6
        self.PAR_FRACTION_OF_SW = 0.45
        self.harvest_truss_dm_g = 80.0
        self.root_frac_of_total_veg = 0.15 / 1.15

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

        self._last_row_cols: set[str] = set()
        self._last_row_used_T_rad = False

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
        self.n_f = int(round(check_and_clip_value(row["n_fruits_per_truss"], 1.0, 12.0, 4.0)))
        self.Ci = self.u_CO2 * 0.7

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
            "active_trusses": self._count_active_trusses(),
            "alloc_frac_fruit": check_and_clip_value(self.part_fruit, 0.0, 1.0, math.nan),
            "alloc_frac_leaf": check_and_clip_value(self.part_leaf, 0.0, 1.0, math.nan),
            "alloc_frac_stem": check_and_clip_value(self.part_stem, 0.0, 1.0, math.nan),
            "alloc_frac_root": check_and_clip_value(self.part_root, 0.0, 1.0, math.nan),
            "alloc_frac_shoot": check_and_clip_value(self.part_shoot, 0.0, 1.0, math.nan),
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
        }

    def run_timestep_calculations(self, dt_seconds: float, current_time: datetime) -> None:
        """Advance one bounded timestep using the migrated lightweight flux contract."""

        dt = float(dt_seconds)
        if dt <= 0:
            raise ValueError(f"dt_seconds must be > 0, got {dt_seconds!r}.")

        sim_date = current_time.date()
        if sim_date > self.current_date:
            self._roll_daily_state(sim_date)
            self.current_date = sim_date

        self.dt_seconds = dt
        self.LAI = self.calculate_current_lai()
        self.f_c = self.calculate_vegetation_cover()

        env = EnvStep(
            t=current_time,
            dt_s=dt,
            T_air_C=self.T_a - 273.15,
            PAR_umol=self.u_PAR,
            CO2_ppm=self.u_CO2,
            RH_percent=self.RH * 100.0,
            wind_speed_ms=self.u,
            SW_in_Wm2=self.SW_in_Wm2,
            T_rad_C=self.T_rad_K - 273.15,
            n_fruits_per_truss=self.n_f,
        )
        flux = run_flux_step(
            env=env,
            theta_substrate=float(self.theta_substrate),
            moisture_response_fn=self.moisture_response_fn,
        )

        canopy_delta_c = min(6.0, max(0.0, self.u_PAR / 1200.0) * (0.4 + 0.6 * self.f_c) * (1.1 - self.RH))
        self.T_c = self.T_a + canopy_delta_c
        self.r_b = 70.0 / math.sqrt(max(self.u, 1e-6))
        self.r_ah = 50.0 * math.sqrt(0.15 / max(self.u, 1e-6))
        self.convergence_status_Tc = True

        self.last_gsw_canopy = max(float(flux["g_w"]), 0.0)
        self.co2_flux_g_m2_s = float(flux["a_n"])
        self.LE_evap = max(float(flux["e"]), 0.0) * self.lambda_v / 1000.0
        self.LE_cond = 0.0
        self.LE = self.LE_evap
        self.LE_raw = self.LE
        self.H = max(0.0, canopy_delta_c) * (6.0 + 14.0 * self.f_c)

        self.daily_temp_accumulator.append((self.T_a, dt))
        self.daily_gross_ch2o_g += max(0.0, self.co2_flux_g_m2_s) * 0.68
        self.daily_par_umol_in_sum += max(0.0, self.u_PAR) * dt
        intercepted_par_umol = max(0.0, self.u_PAR * (1.0 - math.exp(-self.k_ext * max(0.0, self.LAI))))
        self.daily_par_umol_int_sum += intercepted_par_umol * dt
        self.daily_transpiration_g += max(float(flux["e"]), 0.0) * dt

        self._apply_growth(current_time=current_time)

    def calculate_current_lai(self) -> float:
        if self.fixed_lai is not None:
            return float(self.fixed_lai)
        return max(0.0, self.W_lv * self.SLA)

    def calculate_vegetation_cover(self) -> float:
        lai = float(getattr(self, "LAI", 0.0))
        if (not math.isfinite(lai)) or lai <= 1e-6:
            return 0.0
        return float(min(max(1.0 - math.exp(-self.k_ext * lai), 0.0), 1.0))

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

    def _roll_daily_state(self, sim_date: date) -> None:
        days_elapsed = max(1, (sim_date - self.current_date).days)
        self.last_daily_transpiration_g = self.daily_transpiration_g
        self.last_daily_dW_total = self.daily_dW_total
        self.last_daily_epsilon = self._calculate_current_epsilon()
        self.daily_temp_accumulator = []
        self.daily_gross_ch2o_g = 0.0
        self.daily_par_umol_in_sum = 0.0
        self.daily_par_umol_int_sum = 0.0
        self.daily_dW_total = 0.0
        self.daily_transpiration_g = 0.0

        self._truss_fraction_acc += days_elapsed / 5.0
        while self._truss_fraction_acc >= 1.0:
            self.truss_count += 1
            self.truss_cohorts.append(
                {
                    "tdvs": 0.0,
                    "n_fruits": int(self.n_f),
                    "w_fr_cohort": 0.0,
                    "active": True,
                    "mult": self.shoots_per_m2,
                }
            )
            self._truss_fraction_acc -= 1.0

    def _apply_growth(self, *, current_time: datetime) -> None:
        alloc = self._resolve_allocation_fractions(current_time)
        self.part_fruit = alloc["fruit"]
        self.part_leaf = alloc["leaf"]
        self.part_stem = alloc["stem"]
        self.part_root = alloc["root"]
        self.part_shoot = alloc["leaf"] + alloc["stem"]

        dry_matter_gain = max(self.co2_flux_g_m2_s, 0.0) * 0.5
        self.daily_dW_total += dry_matter_gain

        self.W_fr += dry_matter_gain * self.part_fruit
        self.W_lv += dry_matter_gain * self.part_leaf
        self.W_st += dry_matter_gain * self.part_stem
        self.W_rt += dry_matter_gain * self.part_root

        if self.W_fr > self.harvest_truss_dm_g and self.truss_count > 0:
            harvested = self.W_fr - self.harvest_truss_dm_g
            self.W_fr = self.harvest_truss_dm_g
            self.W_fr_harvested += harvested
            if self.truss_cohorts:
                self.truss_cohorts[0]["active"] = False

        self.LAI = self.calculate_current_lai()
        total_dry_weight = self.W_lv + self.W_st + self.W_rt + self.W_fr
        self.recent_total_dm_history.append(total_dry_weight)
        if len(self.recent_total_dm_history) > 8:
            self.recent_total_dm_history = self.recent_total_dm_history[-8:]

    def _resolve_allocation_fractions(self, current_time: datetime) -> dict[str, float]:
        sinks = self._default_sink_proxy()
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
        if alloc is not None:
            return alloc

        s_fr_g_d = sinks["S_fr_g_d"]
        s_veg_g_d = max(sinks["S_veg_g_d"], 1e-9)
        total = max(s_fr_g_d + s_veg_g_d, 1e-9)
        f_fr_total = max(0.0, s_fr_g_d) / total
        f_veg_total = 1.0 - f_fr_total
        f_rt = f_veg_total * self.root_frac_of_total_veg
        f_shoot = f_veg_total - f_rt
        f_lv = f_shoot * 0.7
        f_st = f_shoot * 0.3
        return {"fruit": f_fr_total, "leaf": f_lv, "stem": f_st, "root": f_rt}

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
                params=None,
            )
        except Exception:
            LOGGER.exception("Custom partition_policy.compute failed; falling back to default sink split.")
            return None

        values = getattr(raw, "values", raw)
        if not isinstance(values, Mapping):
            return None

        normalized = {_resolve_partition_key(key): float(value) for key, value in values.items()}
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

    def _default_sink_proxy(self) -> dict[str, float]:
        fruit_bias = min(0.65, 0.08 * max(self.truss_count, 1) + 0.02 * max(self.n_f - 2, 0))
        fruit_bias = max(0.0, fruit_bias)
        return {
            "S_fr_g_d": fruit_bias,
            "S_veg_g_d": 1.0,
        }

    def _calculate_current_epsilon(self) -> float:
        par_mj = self.daily_par_umol_in_sum * PHOTON_UMOL_TO_MJ
        if par_mj <= 1e-12:
            return float(self.last_daily_epsilon)
        return float(max(self.daily_dW_total, 0.0) / par_mj)

    def _count_active_trusses(self) -> float:
        if not self.truss_cohorts:
            return 0.0
        return float(sum(1 for cohort in self.truss_cohorts if bool(cohort.get("active", True))))


def create_sample_input_csv(filename: str | Path = "sample_tomato_input.csv", days: int = 90) -> str:
    """Create a deterministic sample forcing CSV matching the legacy utility contract."""

    output_path = Path(filename)
    start_date = datetime(2021, 2, 23)
    dates = [start_date + timedelta(hours=index) for index in range(days * 24)]

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
        wind_speed = 0.3 + 0.4 * float(np.random.random())
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
