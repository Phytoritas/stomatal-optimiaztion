# TOMICS KNU Observation Operator

## Problem

The workbook target is cumulative **harvested** fruit dry weight. Model latent fruit mass is not the same variable.

## Observation definition

The public KNU observation operator now maps:

- model `harvested_fruit_g_m2`
- to cumulative harvested fruit dry weight on floor-area basis

The operator also keeps:

- on-plant fruit dry weight
- total latent fruit dry weight

as diagnostic series only.

## Evaluation series

The observation layer evaluates:

- raw cumulative harvested series
- offset-adjusted cumulative harvested series
- daily harvested increment reconstructed from the cumulative series

Workbook estimated yield remains a comparator only. It is never treated as ground truth.

## Current observation-fit summary

Output root:

- `out/tomics_knu_observation_eval/`

Measured-harvest fit on the current actual-data baseline:

- workbook estimated `rmse_cumulative_offset = 6.5609`
- shipped TOMICS `rmse_cumulative_offset = 19.0308`
- current selected `rmse_cumulative_offset = 54.2892`
- promoted selected `rmse_cumulative_offset = 39.5735`

The fair-validation pipeline therefore begins from harvested-yield semantics, not total latent fruit mass.
