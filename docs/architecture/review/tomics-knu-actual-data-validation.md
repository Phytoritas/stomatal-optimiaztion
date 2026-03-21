# TOMICS KNU Actual-Data Validation Review

## Files verified

Exact local files used:

- `data/forcing/KNU_Tomato_Env.CSV`
- `data/forcing/tomato_validation_data_yield_260222.xlsx`

The loader verifies file structure programmatically before the factorial runners proceed.

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

## Parsed yield summary

- parsed daily row count: `24`
- parsed start date: `2024-08-08`
- parsed end date: `2024-08-31`
- measured column: `Measured_Cumulative_Total_Fruit_DW (g/m^2)`
- estimated column: `Estimated_Cumulative_Total_Fruit_DW (g/m^2)`
- declared unit from workbook header: `g/m^2`

The measured cumulative series begins above zero, so offset-adjusted evaluation is mandatory for fair comparison.

## Warmup and validation alignment

- warmup: `2024-06-13` through `2024-08-07`
- validation: `2024-08-08` through `2024-08-31`
- calibration slice: `2024-08-08` through `2024-08-19`
- holdout slice: `2024-08-20` through `2024-08-31`

The model always receives the full forcing history for state warmup before yield-fit metrics are computed on the measured window.

## Floor-area boundary

Canonical reporting boundary:

- `reporting_basis = floor_area_g_m2`

Conversion rule for any per-plant internal outputs:

- `value_floor_area = value_per_plant * 1.836091`

Observed workbook values already carry a floor-area unit label and are not reconverted.

## Greenhouse substrate proxy assumptions

The actual forcing record does not include measured substrate water content. For actual-data validation, the workflow adds a greenhouse-soilless proxy instead of using deep-soil or tree-style assumptions.

Default actual-data mode:

- `theta_proxy_mode = bucket_irrigated`

Actual-data scenarios:

- dry proxy around `0.50`
- moderate proxy around `0.65`
- wet proxy around `0.80`

Hard bounds:

- `0.40 <= theta_substrate <= 0.85`

Additional proxy outputs:

- `rootzone_multistress`
- `rootzone_saturation`
- `demand_index`
- `vpd_kpa`

These remain explicit proxy variables until measured KNU root-zone observations become available.

## Current actual-data findings

Current replay output root:

- `out/tomics_current_factorial_knu/`

Observed ranking result:

- selected current candidate: `kuijpers_hybrid_candidate`
- mean offset-adjusted RMSE remained materially worse than shipped TOMICS

## Promoted actual-data findings

Promoted replay output root:

- `out/tomics_promoted_factorial_knu/`

Observed ranking result:

- selected promoted candidate: `constrained_full_plus_feedback__lai_target_center_3p0`
- the promoted winner improved over the current kuijpers candidate
- the promoted winner did not improve over shipped TOMICS
- the promoted winner still incurred canopy-collapse pressure and fruit-anchor drift

## Side-by-side decision

Comparison output root:

- `out/tomics_current_vs_promoted_knu/`

Current decision:

- keep promoted allocator `research-only`
- keep shipped `partition_policy: tomics` unchanged
