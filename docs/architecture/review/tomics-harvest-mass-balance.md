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
- `offplant_with_positive_mass_flag`
- `partial_outflow_flag`

## Current KNU result

For the current harvest-family factorial and harvest-aware promotion gate outputs:

- `harvest_mass_balance_error = 0`
- `leaf_harvest_mass_balance_error = 0`
- `post_writeback_dropped_nonharvested_mass_g_m2 = 0`
- `offplant_with_positive_mass_flag = false`
- `any_all_zero_harvest_series = false`
- `partial_outflow_flag` is available end-to-end, but the current KNU rerun window does not trigger it

`latent_fruit_residual_end` can remain positive for the selected research-family runs because mature on-plant residual mass is allowed to stay in the system after the runtime-complete writeback; that is not itself a conservation failure.

The current gate failure is therefore not a mass-balance failure; it is a biological / validation-guardrail failure driven mainly by canopy-collapse and lack of material holdout improvement.
