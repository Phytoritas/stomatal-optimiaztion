# TOMICS Current vs Promoted Factorial on KNU Data

## Purpose

This document records the public KNU actual-data baseline introduced in issue `#236` / module `117` and refreshed in issue `#239` / module `118`.

The workflow keeps shipped `partition_policy: tomics` unchanged, replays the current research architecture family on actual KNU greenhouse forcing, and compares it against the promoted constrained-marginal allocator family on a floor-area boundary.

The measured validation target is **cumulative harvested fruit dry weight**, not latent on-plant fruit mass.

## Actual data inputs

- forcing CSV: `data/forcing/KNU_Tomato_Env.CSV`
- yield workbook: `data/forcing/tomato_validation_data_yield_260222.xlsx`
- plants per square meter: `1.836091`

Parsed coverage:

- forcing start: `2024-06-13 00:00`
- forcing end: `2024-08-31 23:59`
- forcing nominal resolution: `1 min`
- observed harvest start: `2024-08-08`
- observed harvest end: `2024-08-31`
- workbook unit declaration: `g/m^2`

## Reporting basis

All public validation outputs remain on floor-area basis.

- reporting basis: `floor_area_g_m2`
- per-plant internal quantities are converted only at the reporting boundary
- workbook observations already on `g/m^2` are preserved and never reconverted

## Time alignment

- warmup period: `2024-06-13` through `2024-08-07`
- validation period: `2024-08-08` through `2024-08-31`
- baseline calibration slice: `2024-08-08` through `2024-08-19`
- baseline holdout slice: `2024-08-20` through `2024-08-31`

Offset-adjusted cumulative metrics remain the preferred baseline because the measured cumulative harvested series starts above zero.

## Greenhouse substrate proxy

The actual KNU forcing file does not contain measured substrate water content. The public baseline therefore uses a greenhouse-soilless proxy family:

- `flat_constant`
- `bucket_irrigated`
- `bucket_irrigated_hysteretic`

Default actual-data mode:

- `theta_proxy_mode = bucket_irrigated`

Operational scenarios:

- dry around `0.50`
- moderate around `0.65`
- wet around `0.80`

Hard clamps:

- `theta_min_hard = 0.40`
- `theta_max_hard = 0.85`

These remain explicit proxy assumptions until measured root-zone variables are supplied.

## Current factorial replay

Output root:

- `out/tomics_current_factorial_knu/`

Design counts:

- Stage 1: `18`
- Stage 2: `31`
- Stage 3: `24`
- Total: `73`

Canonical selected current architecture:

- `kuijpers_hybrid_candidate`

## Promoted constrained-marginal factorial

Output root:

- `out/tomics_promoted_factorial_knu/`

Design counts:

- P0 controls: `5`
- P1 structural screening: `30`
- P2 reduced parameter screening: `39`
- P3 confirmation matrix: `24`
- Total: `98`

Canonical selected promoted architecture:

- `constrained_full_plus_feedback__buffer_capacity_g_m2_12p0`

The promoted family remains research-only and preserves the legacy fruit gate as the fruit anchor.

## Baseline decision

Comparison root:

- `out/tomics_current_vs_promoted_knu/`

Current-vs-promoted baseline recommendation:

- `research-only`

This baseline is now subordinate to the fair-validation promotion gate in issue `#239` / module `118`. The fair gate keeps shipped TOMICS incumbent even though the research candidates can beat it on RMSE alone, because the research candidates still violate tomato-first guardrails.
