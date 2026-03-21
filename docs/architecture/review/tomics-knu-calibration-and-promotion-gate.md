# TOMICS KNU Calibration and Promotion Gate

## Purpose

Issue `#239` / module `118` adds the fair promotion gate so shipped TOMICS, the current selected research architecture, and the promoted selected allocator are compared under the same observation model, hidden-state budget, root-zone treatment, and shared calibration budget.

## Calibration budget

Shared free parameters:

- `fruit_load_multiplier`
- `lai_target_center`

Hidden-state budget:

- `reconstruction_mode`
- shared initial-state overrides for `W_lv`, `W_st`, `W_rt`, `W_fr`, and `W_fr_harvested`

Architecture-specific knobs remain frozen during parity calibration.

## Splits

Current fair-validation splits:

- `blocked_holdout`: calibration `2024-08-05..2024-08-19`, holdout `2024-08-20..2024-08-31`
- `alternate_holdout`: calibration `2024-08-05..2024-08-15`, holdout `2024-08-16..2024-08-31`
- `rolling_origin_1`: calibration `2024-08-05..2024-08-18`, holdout `2024-08-19..2024-08-22`

## Holdout scorecard

Output roots:

- `out/tomics/validation/knu/fairness/calibration/`
- `out/tomics/validation/knu/fairness/promotion-gate/`

Mean holdout RMSE, offset-adjusted harvested yield:

- shipped TOMICS: `12.7982`
- current selected: `8.8529`
- promoted selected: `8.4690`

Guardrail outcomes:

- current selected fruit-anchor error: `0.0629`
- promoted selected fruit-anchor error: `0.1160`
- current selected canopy collapse days: `4`
- promoted selected canopy collapse days: `4`
- shipped TOMICS stays incumbent

## Final promotion decision

- recommendation: `keep shipped TOMICS incumbent`
- promotion allowed: `false`

No research allocator clears the full promotion gate yet.
