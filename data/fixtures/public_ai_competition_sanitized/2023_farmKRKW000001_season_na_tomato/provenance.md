# competition measured-harvest preprocessing provenance

- dataset_id: `public_ai_competition__yield`
- slice_id: `2023_farmKRKW000001_season_na_tomato`
- year: `2023`
- farm: `KRKW000001`
- season: `NA`
- crop_name: `tomato`
- source_refs:
  - `70_공공데이터/스마트팜코리아_AI경진대회 데이터셋/2023년 개방데이터/23_환경정보.csv`
  - `70_공공데이터/스마트팜코리아_AI경진대회 데이터셋/2023년 개방데이터/23_생육정보.csv`
  - `70_공공데이터/스마트팜코리아_AI경진대회 데이터셋/2023_스마트팜코리아_데이터정의서.hwp`

## forcing_path

- output_file: `forcing_fixture.csv`
- source_description: `23_환경정보.csv` filtered to `farm_cde=KRKW000001`, `itemcode=80300`, `classcode=FG`
- timestamp_column: `mea_dat`
- sensor_mapping:
  - `T_air_C <- TI`
  - `RH_percent <- HI`
  - `CO2_ppm <- CI`
  - `PAR_umol <- SR * 2.02`
  - `wind_speed_ms <- 0.3`
- aggregation: raw timestamp sensor rows -> hour floor -> hourly mean by sensor code
- validation_overlap: forcing covers `2024-01-19 00:00:00` through `2024-01-26 23:00:00`
- forcing_caveat:
  - `SR` is treated as inside shortwave radiation and converted to PAR with `PAR_umol = SR * 2.02`
  - `wind_speed_ms` is not observed from an inside wind sensor in this clone; `0.3 m/s` is used as a greenhouse internal wind assumption

## observed_harvest_path

- output_file: `observed_harvest_fixture.csv`
- helper_file: `observed_harvest_candidate_g_per_plant.csv`
- source_description: `23_생육정보.csv` filtered to `farm_cde=KRKW000001`, `itemCode=80300`
- source_observed_quantity: measured fresh harvest mass-like `outtrn` values paired with `hvstCo`
- interpretation_basis:
  - `outtrn` is inferred as fresh harvested fruit mass in grams, not dry weight
  - inference rationale: positive `outtrn` rows co-occur with positive `hvstCo`, and the implied fruit mass scale is biologically plausible for tomato
- derivation: `fresh harvest mass * dry matter fraction`
- semantic_label: `derived_dw_from_measured_fresh_harvest_per_plant`
- is_direct_dry_weight: `false`
- uses_literature_dry_matter_fraction: `true`
- review_flag: `review_only_dry_matter_conversion`
- derivation_formula:
  - `daily_fresh_harvest_g_total = sum(max(outtrn_g, 0) by Date across sampled plants)`
  - `daily_dw_g_per_sampled_plant = (daily_fresh_harvest_g_total / 22 sampled plants) * 0.065`
  - `daily_dw_g_per_m2 = daily_dw_g_per_sampled_plant * 2.86 plants_per_m2`
  - `cumulative_dw_g_per_m2 = cumsum(daily_dw_g_per_m2)`
- observed_dates_used:
  - `2024-01-19`
  - `2024-01-26`
- negative_or_zero_outtrn_policy: non-positive `outtrn` rows are excluded from the cumulative harvest proxy

## reporting_basis

- reporting_basis: `g_per_m2`
- floor_area_m2: `not directly observed in clone`
- floor_area_basis_evidence:
  - this slice is normalized to area by multiplying the sampled-plant mean harvest mass by the user-provided planting density `2.86 plants_per_m2`
  - no direct competition raw field in this clone exposes `floor area`, `cultivation area`, or an equivalent denominator for `KRKW000001`
- plants_per_m2: `2.86`
- plants_per_m2_source: `user-provided density in chat on 2026-04-19`
- sampled_plants_count: `22`
- basis_status: `resolved_via_plant_density`

## validation_window

- validation_start: `2024-01-19`
- validation_end: `2024-01-26`

## registry-facing fields

- date_column: `Date`
- measured_cumulative_column: `Measured_Cumulative_Total_Fruit_DW (g/m^2)`
- column_semantic_caveat:
  - the compatibility header is kept in the current contract shape
  - the numeric values in this slice are now `g DW / m^2`, derived from sampled-plant mean fresh harvest mass times `plants_per_m2 = 2.86`
  - this remains review-only because dry weight is literature-ratio-derived and `outtrn` unit semantics are inferred from the raw competition CSV context rather than confirmed from a parsed definition document

## dry_matter_fraction

- dry_matter_fraction: `0.065`
- dry_matter_fraction_source: user-provided tomato fruit dry-matter synthesis dated `2026-03-21`

## provenance_tags

- `competition_candidate`
- `fresh_harvest_proxy`
- `derived_dw_proxy`
- `plant_density_assumed`
- `runnable_review_only`

## blocker_codes

- `none`
