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

## Rules
- Use lowercase snake_case.
- Reuse the same name for the same concept in every repository.
- If you need both scalar and series forms, keep the canonical base name and add a meaningful suffix such as `_series`, `_profile`, `_daily`, or `_hourly`.
- Do not encode implementation details such as `vect`, `tmp`, `new`, or `final` into the biological variable name.
