# TOMICS Current vs Promoted Factorial on KNU Data

## Purpose

This document records the actual-data validation workflow added in issue `#236` / module `117`.

The workflow keeps the shipped `partition_policy: tomics` path unchanged, replays the current research architecture family on actual KNU greenhouse forcing, and compares it against a new promoted constrained-marginal allocator family under the same floor-area validation boundary.

## Actual data inputs

- Forcing CSV: `data/forcing/KNU_Tomato_Env.CSV`
- Yield workbook: `data/forcing/tomato_validation_data_yield_260222.xlsx`

Parsed characteristics:

- forcing start: `2024-06-13 00:00`
- forcing end: `2024-08-31 23:59`
- forcing nominal resolution: `1 min`
- observed yield start: `2024-08-08`
- observed yield end: `2024-08-31`
- observation unit declared in workbook header: `g/m^2`

The measured cumulative fruit dry-weight column is the primary target. The workbook estimated cumulative fruit dry-weight column is retained as a comparator only.

## Reporting basis

All validation outputs are reported on floor-area basis.

- planting density: `1.836091 plants m^-2`
- if an internal quantity is per plant, the reporting boundary converts it to floor area
- if a source file is already on floor-area basis, it is preserved as-is

Observed workbook values are already labeled on floor-area basis and are not reconverted.

## Time alignment

- warmup period: forcing start through `2024-08-07`
- validation period: `2024-08-08` through `2024-08-31`
- calibration slice: `2024-08-08` through `2024-08-19`
- holdout slice: `2024-08-20` through `2024-08-31`

Validation metrics are reported for raw cumulative series and offset-adjusted cumulative series. Offset-adjusted metrics are preferred because the measured cumulative series starts above zero.

## Greenhouse substrate proxy

The KNU forcing file does not contain measured substrate water content. The actual-data workflow therefore adds a greenhouse-soilless substrate proxy family:

- `flat_constant`
- `bucket_irrigated`
- `bucket_irrigated_hysteretic`

The default actual-data mode is `bucket_irrigated`.

Operational proxy scenarios:

- dry: center near `0.50`
- moderate: center near `0.65`
- wet: center near `0.80`

Hard clamps:

- `theta_min_hard = 0.40`
- `theta_max_hard = 0.85`

These are explicit proxy assumptions, not measured root-zone observations.

## Current factorial replay

The current architecture replay preserves the merged issue `#231` design logic and applies it to actual KNU forcing.

Actual-data design:

- Stage 1: `18` runs
- Stage 2: `31` runs
- Stage 3: `24` runs
- Total: `73` runs

Outputs:

- `out/tomics_current_factorial_knu/`

## Promoted constrained-marginal factorial

The promoted family remains research-only.

Core promoted architecture features:

- legacy fruit gate retained as the fruit anchor
- prior-weighted softmax over vegetative marginals
- canopy-first leaf marginal
- support/transport stem marginal
- greenhouse multistress root gate
- optional low-pass allocation memory
- optional reserve/buffer and fruit-feedback seams
- THORP still bounded to subordinate root correction only

Actual-data design:

- P0 controls: `5` runs
- P1 structural screening: `30` runs
- P2 reduced parameter screening: `39` runs
- P3 confirmation matrix: `24` runs
- Total: `98` runs

Outputs:

- `out/tomics_promoted_factorial_knu/`

## Promotion decision

The current vs promoted side-by-side bundle is written under:

- `out/tomics_current_vs_promoted_knu/`

Decision status for this issue:

- promoted allocator remains `research-only`

Observed reason:

- shipped TOMICS still fits measured yield better on the offset-adjusted KNU target
- the promoted winner loses the legacy fruit anchor too strongly
- the promoted winner still shows non-zero canopy-collapse pressure in the confirmation slice

This means the promoted allocator is not ready for silent default promotion.
