# TOMICS Lane-Matrix Daily Increment Diagnostics

Issue: #308

## Executive Summary

The remaining `all_zero_model_daily_increment_series=true` rows in the A1-A4
multi-dataset lane matrix are not a recurrence of the broader harvested
writeback bug fixed in #307. The cumulative model harvest series is nonzero,
so `any_all_zero_harvest_series=false` is correct.

The residual daily-increment flag has two dataset-specific causes:

- `knu_actual`: the four-row sanitized smoke window seeds the first cumulative
  harvested value but does not generate a harvest event inside the scored
  window.
- `public_ai_competition__yield`: the fallback seeded cohort harvests on the
  first observed date, so the event is present in the mass-balance trace but
  invisible to a `.diff()`-based observed-row daily increment comparison.

`public_rda__yield` is not the blocker for this diagnostic pass.

## Scope

This diagnostic does not change the shipped `partition_policy: tomics`
behavior, does not promote A4, and does not alter production allocation logic.
Public derived-DW datasets remain review-only robustness lanes and are not
promotion evidence.

## Code Path Inspected

- `scripts/run_tomics_lane_matrix.py`
- `src/stomatal_optimiaztion/domains/tomato/tomics/alloc/validation/lane_matrix/matrix_runner.py`
- `src/stomatal_optimiaztion/domains/tomato/tomics/alloc/validation/lane_matrix/lane_scorecard.py`
- `src/stomatal_optimiaztion/domains/tomato/tomics/alloc/validation/harvest_family_eval.py`
- `src/stomatal_optimiaztion/domains/tomato/tomics/alloc/validation/harvest_operator.py`
- `src/stomatal_optimiaztion/domains/tomato/tomics/alloc/validation/init_search.py`
- `src/stomatal_optimiaztion/domains/tomato/tomics/alloc/validation/state_reconstruction.py`

The scorecard flag is computed from the validation overlay's
`model_daily_increment_floor_area` column. The model daily increment is derived
from daily-last cumulative `harvested_fruit_g_m2` using `.diff()`, and the
first observed row has no increment by construction.

## Artifact Evidence

Primary artifact root:

- `out/tomics_a1_a4_multidataset_lane_matrix/`

Representative incumbent lane:

- `scenarios/incumbent_current__incumbent_harvest_profile__knu_actual/`
- `scenarios/incumbent_current__incumbent_harvest_profile__public_ai_competition__yield/`

### KNU

Validation overlay:

| date | measured cumulative | measured increment | model cumulative | model increment |
| --- | ---: | ---: | ---: | ---: |
| 2024-08-08 | 2.4 | n/a | 2.4 | n/a |
| 2024-08-09 | 4.1 | 1.7 | 2.4 | 0.0 |
| 2024-08-10 | 6.9 | 2.8 | 2.4 | 0.0 |
| 2024-08-11 | 10.2 | 3.3 | 2.4 | 0.0 |

Harvest mass-balance evidence:

- `fruit_harvest_flux_g_m2_d=0.0` for all four scored days.
- `eligible_harvest_mass_g_m2=0.0` for all four scored days.
- `mature_onplant_mass_g_m2=0.0` for all four scored days.
- `family_state_mode=shared_tdvs_proxy`.
- `native_family_state_fraction=0.0`.

Diagnosis: the nonzero cumulative model series is the initial harvested seed,
not generated harvest during the four-day smoke window. The daily-zero flag is
therefore scientifically meaningful for KNU.

### Public AI Competition

Validation overlay:

| date | measured cumulative | measured increment | model cumulative | model increment |
| --- | ---: | ---: | ---: | ---: |
| 2024-01-19 | 7.1487 | n/a | 16.5282 | n/a |
| 2024-01-26 | 16.5282 | 9.3795 | 16.5282 | 0.0 |

Harvest mass-balance evidence:

- `fruit_harvest_flux_g_m2_d=9.3795` on 2024-01-19.
- `eligible_harvest_mass_g_m2=16.414125` on 2024-01-19.
- `mature_onplant_mass_g_m2=16.414125` on 2024-01-19.
- Later scored interval increment is 0.0.
- `family_state_mode=native_payload`.
- `native_family_state_fraction=1.0`.

Diagnosis: public AI does generate a model harvest event, but it lands on the
first observed date. Because daily increments are scored by differencing
observed-row cumulative values, the first-day event is not represented as a
finite increment, and the only finite observed-row model increment is 0.0.

## Decision

This is not a production allocator bug and not a scorecard false positive.
The scorecard is correctly reporting that the finite observed-row model daily
increment series is all zero.

The issue is a validation-surface mismatch:

- KNU needs either a longer/direct measured validation fixture window or a
  reconstruction objective that rejects seeded-only fits when measured
  increments are positive.
- Public AI needs either pre-roll alignment or a fallback seeding policy that
  prevents the only harvest event from landing on the first unscored increment
  row.

## Next Minimal Fix Candidate

Add a reconstruction/fallback guard in a follow-up patch: when the observed
finite daily increments contain positive values, penalize or reject
reconstruction candidates whose finite scored `model_daily_increment_floor_area`
series is all zero.

For short review-only public smoke lanes, keep the resulting warning explicit
instead of using the lane for promotion.

