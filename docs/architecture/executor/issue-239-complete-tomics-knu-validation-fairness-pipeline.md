# Issue 239 Executor Record

## Title

[Validation + Promotion Gate] Complete KNU harvest observation, hidden-state reconstruction, root-zone inversion, and calibration-parity pipeline for TOMICS

## Scope

- add a private-data contract and sanitized fixture path for KNU validation
- map observed yield to cumulative harvested fruit dry weight explicitly
- reconstruct shared hidden state before cross-architecture comparison
- reconstruct greenhouse root-zone proxy scenarios with uncertainty
- enforce equal-budget calibration and holdout evaluation
- run the KNU promotion gate without changing shipped `partition_policy: tomics`

## Output roots

- `out/knu_longrun/`
- `out/tomics_knu_observation_eval/`
- `out/tomics_knu_state_reconstruction/`
- `out/tomics_knu_rootzone_reconstruction/`
- `out/tomics_knu_calibration/`
- `out/tomics_knu_promotion_gate/`

## Decision

Shipped TOMICS remains the incumbent after the fair KNU promotion gate.

The current selected and promoted selected research candidates remain research-only.
