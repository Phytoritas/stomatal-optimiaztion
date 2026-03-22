# Issue 255 Executor Record

## Title

[Experiment Run] Re-run KNU harvest-aware factorial and promotion gate after harvest-runtime completion

## Prerequisite

- PR `#254` is merged into `main` at commit `f3bfe385d9a55c1bfcf65daccdaab8304ccdf81d`.
- This lane starts from latest `main`, not from PR `#252`.

## Scope

- verify that runtime-complete harvest fields populate in the KNU actual-data lane
- run the harvest-aware factorial and promotion gate on runtime-complete `main`
- surface results into artifacts and the minimal result-facing docs
- preserve shipped `partition_policy: tomics` unless a runtime-complete rerun clears every guardrail

## Pre-Rerun Sanity Probe

- `matured_at`
- `days_since_maturity`
- `sink_active_flag`
- `mature_pool_residence_days`
- `final_stage_residence_days`
- `partial_outflow_flag`
- `family_state_mode`
- `proxy_mode_used`
- `model_cumulative_harvested_fruit_dry_weight_floor_area`
- common-structure `h1` and `h2` step harvest fluxes

## Canonical Commands

1. `poetry run python scripts/run_tomics_knu_observation_eval.py --config configs/exp/tomics_knu_observation_eval.yaml`
2. `poetry run python scripts/run_tomics_knu_state_reconstruction.py --config configs/exp/tomics_knu_state_reconstruction.yaml`
3. `poetry run python scripts/run_tomics_knu_rootzone_reconstruction.py --config configs/exp/tomics_knu_rootzone_reconstruction.yaml`
4. `poetry run python scripts/run_tomics_knu_calibration.py --config configs/exp/tomics_knu_calibration.yaml`
5. `poetry run python scripts/run_tomics_knu_harvest_family_factorial.py --config configs/exp/tomics_knu_harvest_family_factorial.yaml`
6. `poetry run python scripts/run_tomics_knu_harvest_promotion_gate.py --config configs/exp/tomics_knu_harvest_promotion_gate.yaml`

## Output Roots

- `out/tomics_knu_harvest_runtime_probe/`
- `out/tomics_knu_harvest_family_factorial/`
- `out/tomics_knu_harvest_promotion_gate/`

## Runtime-complete probe result

- probe status: passed with no blocker
- populated runtime fields observed: `matured_at`, `days_since_maturity`, `sink_active_flag`
- step-flux check: common-structure harvest step flux matches baseline-adjusted daily harvested-cumulative diffs
- proxy/native boundary: sampled `tomsim_truss` hits `native_payload` as well as `shared_tdvs_proxy`, but sampled research families still report `shared_tdvs_proxy` with `proxy_mode_used = true`
- partial outflow: diagnostic column round-trips, but no partial-outflow event appears in the current KNU window
- mass-balance audit: `offplant_with_positive_mass_flag = false`, `post_writeback_dropped_nonharvested_mass_g_m2 = 0`

## Rerun outcome

- determine whether runtime-complete rerun still keeps shipped TOMICS plus incumbent TOMSIM harvest as the incumbent baseline
- report whether the winner remains partly proxy-dependent or is interpretable as runtime-complete family behavior on the current KNU window

Result:

- selected research harvest family: `dekoning_fds + vegetative_unit_pruning + dekoning_fds`
- shipped/current/promoted holdout RMSE offset: all `33.3229`
- shipped/current/promoted holdout RMSE daily increment: all `4.9743`
- canopy collapse days: shipped `47`, current `11`, promoted `11`
- winner stability score: current `1.00`, promoted `0.00`
- final recommendation: `Keep shipped TOMICS + incumbent TOMSIM harvest as the incumbent baseline.`
- interpretation: runtime-complete rerun is now valid, but the current KNU window still shows weak family discrimination and a proxy-heavy research-family state surface
