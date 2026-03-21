# TOMICS KNU State Reconstruction

## Problem

The forcing record starts on `2024-06-13`, but the crop is already in progress. Promotion evidence is not fair without a shared hidden-state reconstruction layer.

## Supported modes

The reconstruction layer supports:

- `minimal_scalar_init`
- `cohort_aware_init`
- `buffer_aware_init`

## Chosen mode on current fair-validation run

The selected mode for shipped, current-selected, and promoted-selected was:

- `minimal_scalar_init`

Recovered common initial state:

- `LAI = 2.0`
- `W_lv = 90.9091`
- `W_st = 40.9091`
- `W_rt = 27.2727`
- `W_fr = 6.0`
- `W_fr_harvested = 0.0867429008404087`

## Output root

- `out/tomics_knu_state_reconstruction/`

## Current conclusion

The fair-validation run used the same reconstruction interface and the same hidden-state budget across shipped TOMICS, the current selected architecture, and the promoted selected architecture.
