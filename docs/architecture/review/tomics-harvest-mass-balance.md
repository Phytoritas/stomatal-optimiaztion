# TOMICS Harvest Mass Balance

## Enforced invariants

The harvest layer enforces these invariants per run:

- fruit harvest flux is nonnegative
- cumulative harvested fruit is monotonic nondecreasing
- already harvested fruit entities cannot be harvested twice
- on-plant fruit mass cannot fall below zero
- leaf mass cannot fall below zero after pruning
- latent fruit plus harvested fruit stays internally consistent at the family level

## Core metrics

- `harvest_mass_balance_error`
- `latent_fruit_residual_end`
- `leaf_harvest_mass_balance_error`
- `duplicate_harvest_flag`
- `negative_mass_flag`
- `post_writeback_dropped_nonharvested_mass_g_m2`
- `any_all_zero_harvest_series`

## Current KNU result

For the current harvest-family factorial and harvest-aware promotion gate outputs:

- `harvest_mass_balance_error = 0`
- `leaf_harvest_mass_balance_error = 0`
- `post_writeback_dropped_nonharvested_mass_g_m2 = 0`
- `any_all_zero_harvest_series = false`
- selected research-family factorial row `latent_fruit_residual_end = 2.25e-4 g/m^2`

The current gate failure is therefore not a mass-balance or writeback-audit failure; it is a biological / validation-guardrail failure driven mainly by canopy-collapse, low winner stability, and lack of material holdout improvement.
