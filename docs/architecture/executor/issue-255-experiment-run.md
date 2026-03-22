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

- `out/tomics_knu_harvest_family_factorial/`
- `out/tomics_knu_harvest_promotion_gate/`

## Decision Target

- determine whether runtime-complete rerun still keeps shipped TOMICS plus incumbent TOMSIM harvest as the incumbent baseline
- report whether the winner remains partly proxy-dependent or is interpretable as runtime-complete family behavior on the current KNU window
