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

## Current KNU result

For the current harvest-family factorial and harvest-aware promotion gate outputs:

- `harvest_mass_balance_error = 0`
- `latent_fruit_residual_end = 0`
- `leaf_harvest_mass_balance_error = 0`

The current gate failure is therefore not a mass-balance failure; it is a biological / validation-guardrail failure driven mainly by canopy-collapse and lack of material holdout improvement.
