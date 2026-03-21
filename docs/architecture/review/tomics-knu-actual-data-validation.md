# TOMICS KNU Actual-Data Validation Review

## Files verified

Exact local files used:

- `data/forcing/KNU_Tomato_Env.CSV`
- `data/forcing/tomato_validation_data_yield_260222.xlsx`

The loader verifies file structure programmatically before the factorial or fairness runners proceed.

## Parsed forcing summary

- required columns present:
  - `datetime`
  - `T_air_C`
  - `PAR_umol`
  - `CO2_ppm`
  - `RH_percent`
  - `wind_speed_ms`
- parsed row count: `116640`
- parsed start timestamp: `2024-06-13 00:00`
- parsed end timestamp: `2024-08-31 23:59`
- modal forcing interval: `60 s`

## Parsed observation summary

- parsed daily row count: `24`
- parsed start date: `2024-08-08`
- parsed end date: `2024-08-31`
- measured column: `Measured_Cumulative_Total_Fruit_DW (g/m^2)`
- estimated column: `Estimated_Cumulative_Total_Fruit_DW (g/m^2)`
- declared unit from workbook header: `g/m^2`

The measured series is treated as **cumulative harvested fruit dry weight on floor area basis**.

## Alignment and basis

- warmup: `2024-06-13` through `2024-08-07`
- validation: `2024-08-08` through `2024-08-31`
- baseline calibration slice: `2024-08-08` through `2024-08-19`
- baseline holdout slice: `2024-08-20` through `2024-08-31`
- reporting basis: `floor_area_g_m2`
- plant density: `1.836091 plants m^-2`

Offset-adjusted evaluation remains required because the observed cumulative harvested series begins above zero.

## Public actual-data baseline findings

Output roots:

- `out/tomics_current_factorial_knu/`
- `out/tomics_promoted_factorial_knu/`
- `out/tomics_current_vs_promoted_knu/`

Canonical selected current candidate:

- `kuijpers_hybrid_candidate`

Canonical selected promoted candidate:

- `constrained_full_plus_feedback__buffer_capacity_g_m2_12p0`

Baseline recommendation:

- keep both research candidates `research-only`

This baseline is now superseded by the fair-validation evidence in issue `#239` / module `118`.

## Fair-validation follow-up

The fair-validation bundle is now the promotion source of truth:

- `out/tomics_knu_observation_eval/`
- `out/tomics_knu_state_reconstruction/`
- `out/tomics_knu_rootzone_reconstruction/`
- `out/tomics_knu_calibration/`
- `out/tomics_knu_promotion_gate/`

Under that fair-validation pipeline:

- workbook estimated remains the best soft comparator
- shipped TOMICS stays the incumbent
- current selected and promoted selected can improve holdout RMSE, but both fail promotion guardrails because fruit-anchor drift and canopy-collapse pressure remain non-zero
