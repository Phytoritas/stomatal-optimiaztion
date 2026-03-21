# Variable Glossary

Use one canonical name per concept across repositories.

## Core state and flux variables

| Concept | Canonical short name | Optional verbose alias | Typical unit | Notes |
|---|---|---|---|---|
| Net assimilation | `a_n` | `net_assimilation_rate` | µmol CO2 m^-2 s^-1 | Prefer lowercase `a_n`, not `A_n` |
| Transpiration | `e` | `transpiration_rate` | mmol H2O m^-2 s^-1 | Use `e_series` for time series, not `E_vect` |
| Stomatal conductance to CO2 | `g_sc` | `stomatal_conductance_co2` | mol CO2 m^-2 s^-1 | Avoid ambiguous `g_c` |
| Stomatal conductance to H2O | `g_sw` | `stomatal_conductance_h2o` | mol H2O m^-2 s^-1 | Distinguish from `g_sc` |
| Leaf water potential | `psi_l` | `leaf_water_potential` | MPa | Prefer `psi_l` over `P_leaf` |
| Stem water potential | `psi_s` | `stem_water_potential` | MPa | Prefer `psi_s` over `P_stem` |
| Root-collar water potential | `psi_rc` | `root_collar_water_potential` | MPa | Prefer `psi_rc` over `P_rc` |
| Soil water potential | `psi_soil` | `soil_water_potential` | MPa | Prefer `psi_soil` over `P_soil` |
| Soil volumetric water content | `theta_soil` | `soil_water_content` | m3 m^-3 | Distinguish from soil water potential |
| Marginal WUE parameter | `lambda_wue` | `marginal_wue` | model-specific | Avoid bare `lambda` |
| Non-structural carbon | `c_nsc` | `nonstructural_carbon` | g C m^-2 or equivalent | Avoid bare `NSC` |
| Turgor pressure | `p_turgor` | `turgor_pressure` | MPa | |
| Air temperature | `t_air` | `air_temperature` | °C | |
| Leaf temperature | `t_leaf` | `leaf_temperature` | °C | |
| Vapor pressure deficit | `vpd_air` | `air_vpd` | kPa | |
| Ambient CO2 | `c_a` | `ambient_co2` | ppm or µmol mol^-1 | |
| Absorbed PAR | `par_abs` | `absorbed_par` | µmol photons m^-2 s^-1 | |
| Gross primary productivity | `gpp` | `gross_primary_productivity` | g C m^-2 d^-1 or model-specific | |
| Net primary productivity | `npp` | `net_primary_productivity` | g C m^-2 d^-1 or model-specific | |
| Dark respiration | `r_dark` | `dark_respiration` | µmol CO2 m^-2 s^-1 | |
| Soil-to-plant hydraulic conductance | `k_sw` | `soil_to_plant_conductance` | model-specific | Avoid bare `k` |
| Root hydraulic conductance | `k_root` | `root_hydraulic_conductance` | model-specific | |
| Stem hydraulic conductance | `k_stem` | `stem_hydraulic_conductance` | model-specific | |
| Leaf hydraulic conductance | `k_leaf` | `leaf_hydraulic_conductance` | model-specific | |
| Xylem PLC | `plc_xylem` | `xylem_percent_loss_conductance` | % | |

## TOMICS tomato-facing naming

| Concept | Canonical name | Historical name | Notes |
|---|---|---|---|
| Tomato integrated framework | `TOMICS` | none | Umbrella tomato-facing framework label |
| Tomato flux surface | `TOMICS-Flux` | `tGOSM` | Canonical public/runtime name; retired runtime imports keep `tGOSM` only in provenance docs |
| Tomato allocation surface | `TOMICS-Alloc` | `tTHORP` | Canonical public/runtime name; retired runtime imports keep `tTHORP` only in provenance docs |
| Tomato growth surface | `TOMICS-Grow` | `tTDGM` | Canonical public/runtime name; retired runtime imports keep `tTDGM` only in provenance docs |

## TOMICS policy controls

| Concept | Canonical short name | Optional verbose alias | Typical unit | Notes |
|---|---|---|---|---|
| Substrate water content | `theta_substrate` | `substrate_water_content` | m3 m^-3 | Greenhouse/rootzone moisture proxy for tomato surfaces |
| Water-supply stress | `water_supply_stress` | `tomato_water_supply_stress` | 0-1 | Bounded stress scalar used by TOMICS-Alloc |
| Wet-condition root cap | `wet_root_cap` | `tomics_wet_root_cap` | fraction of total allocation | Default near 0.10 |
| Dry-condition root cap | `dry_root_cap` | `tomics_dry_root_cap` | fraction of total allocation | Default near 0.18 |
| LAI target center | `lai_target_center` | `tomics_lai_target_center` | LAI | Default near 2.75 |
| Shoot leaf base share | `leaf_fraction_of_shoot_base` | `tomics_leaf_fraction_of_shoot_base` | fraction of shoot allocation | Default 0.70 |
| Shoot stem base share | `stem_fraction_of_shoot_base` | `tomics_stem_fraction_of_shoot_base` | fraction of shoot allocation | Default 0.30 |

## Tomato legacy model state

| Concept | Canonical short name | Optional verbose alias | Typical unit | Notes |
|---|---|---|---|---|
| Truss development stage | `tdvs` | `truss_development_stage` | 0-1 | Cohort state advanced by FDVR in the v1.2-aligned tomato legacy model |
| Vegetative sink strength per shoot | `veg_sink_g_d_per_shoot` | `vegetative_sink_strength_per_shoot` | g DW shoot^-1 d^-1 | Converted to per-floor sink with `shoots_per_m2` |
| Carbohydrate reserve pool | `reserve_ch2o_g` | `carbohydrate_reserve_pool` | g CH2O m^-2 | Temporary buffer used by sink-limited tomato growth updates |

## TOMICS allocation architecture study terms

| Concept | Canonical short name | Optional verbose alias | Typical unit | Notes |
|---|---|---|---|---|
| Research architecture id | `architecture_id` | `tomics_architecture_id` | string | Stable identifier for one opt-in research architecture candidate |
| Fruit structure mode | `fruit_structure_mode` | `tomics_fruit_structure_mode` | enum | `tomsim_truss_cohort`, `tomgro_age_class`, or `vanthoor_fixed_boxcar` |
| Vegetative demand mode | `vegetative_demand_mode` | `tomics_vegetative_demand_mode` | enum | `tomsim_constant_wholecrop`, `dekoning_vegetative_unit`, or `tomgro_dynamic_age` |
| Reserve / buffer mode | `reserve_buffer_mode` | `tomics_reserve_buffer_mode` | enum | `off`, `tomsim_storage_pool`, or `vanthoor_carbohydrate_buffer` |
| Fruit feedback mode | `fruit_feedback_mode` | `tomics_fruit_feedback_mode` | enum | Research-only fruit abortion or source-demand feedback switch |
| Maintenance mode | `maintenance_mode` | `tomics_maintenance_mode` | enum | `rgr_adjusted`, `fixed`, or `buffer_linked` in the current research seam |
| SLA mode | `sla_mode` | `tomics_sla_mode` | enum | `derived_not_driver` is preferred for tomato-first defaults |
| THORP root correction mode | `thorp_root_correction_mode` | `tomics_thorp_root_correction_mode` | enum | THORP remains a bounded greenhouse root correction only |
| Temporal coupling mode | `temporal_coupling_mode` | `tomics_temporal_coupling_mode` | enum | `daily_alloc`, `hourly_source_daily_alloc`, or `buffered_daily` |
| Research reserve pool output | `reserve_pool_g_m2` | `research_reserve_pool` | g CH2O m^-2 | Output column for storage-pool carryover in research runs |
| Research carbohydrate buffer output | `buffer_pool_g_m2` | `research_buffer_pool` | g CH2O m^-2 | Output column for Vanthoor-like buffer accounting in research runs |
| Fruit abort fraction | `fruit_abort_fraction` | `research_fruit_abort_fraction` | 0-1 | Output proxy, research-only, never part of shipped default `tomics` semantics |
| Fruit-set feedback events | `fruit_set_feedback_events` | `research_fruit_feedback_events` | count | Research-only event counter |
| Maintenance respiration share | `maintenance_respiration_share` | `maintenance_respiration_fraction` | 0-1 | Share of gross CH2O production consumed by maintenance in the current step |
| Mean stage residence time | `mean_stage_residence_time_d` | `fruit_stage_residence_time_days` | d | Diagnostic proxy for age-class or boxcar fruit structure modes |
| Common-structure assimilate buffer | `xA_assimilate_buffer_g_m2` | `kuijpers_assimilate_buffer_state` | g CH2O m^-2 | Kuijpers-normalized diagnostic state; scaffold only, not a standalone tomato law |
| Canopy collapse days | `canopy_collapse_days` | `days_with_canopy_collapse` | d | In the architecture study, days with active fruiting and either LAI below the configured floor or leaf allocation below the configured floor |

## KNU actual-data validation terms

| Concept | Canonical short name | Optional verbose alias | Typical unit | Notes |
|---|---|---|---|---|
| Theta proxy mode | `theta_proxy_mode` | `substrate_moisture_proxy_mode` | enum | `flat_constant`, `bucket_irrigated`, or `bucket_irrigated_hysteretic` |
| Theta proxy scenario | `theta_proxy_scenario` | `substrate_proxy_scenario` | enum | `dry`, `moderate`, or `wet` for actual KNU runs |
| Root-zone multistress proxy | `rootzone_multistress` | `greenhouse_rootzone_multistress_proxy` | 0-1 | Bounded greenhouse proxy derived from demand and root-zone assumptions |
| Root-zone saturation proxy | `rootzone_saturation` | `greenhouse_rootzone_saturation_proxy` | 0-1 | Saturation penalty proxy for greenhouse substrate runs |
| Offset-adjusted yield RMSE | `yield_rmse_offset_adjusted` | `offset_adjusted_yield_rmse` | declared observation unit | Preferred cumulative-yield fit metric when the observed series starts with a non-zero offset |
| Offset-adjusted yield R2 | `yield_r2_offset_adjusted` | `offset_adjusted_yield_r2` | 0-1 | Reported alongside full-window and split-window KNU validation |
| Final total dry weight on floor area | `final_total_dry_weight_floor_area` | `final_total_dry_weight_g_m2_floor_area` | g m^-2 floor | Canonical actual-data reporting boundary |
| Final fruit dry weight on floor area | `final_fruit_dry_weight_floor_area` | `final_cumulative_fruit_dry_weight_floor_area` | g m^-2 floor | In KNU validation, reported on the same floor-area basis as the observation workbook |
| Promoted optimizer mode | `optimizer_mode` | `promoted_allocator_optimizer_mode` | enum | `bounded_static_current`, `prior_weighted_softmax`, or `prior_weighted_softmax_plus_lowpass` |
| Promoted softmax sharpness | `beta` | `promoted_softmax_beta` | dimensionless | Prior-weighted softmax sharpness parameter |
| Allocation-memory timescale | `tau_alloc_days` | `allocation_lowpass_tau_days` | d | Low-pass memory constant for promoted allocation research runs |

## Rules
- Use lowercase snake_case.
- Reuse the same name for the same concept in every repository.
- If you need both scalar and series forms, keep the canonical base name and add a meaningful suffix such as `_series`, `_profile`, `_daily`, or `_hourly`.
- Do not encode implementation details such as `vect`, `tmp`, `new`, or `final` into the biological variable name.
