# TOMICS-HAF 2025-2C Methods Outline

## Data Sources

- Dataset1 environmental radiation and loadcell-linked observer features.
- Dataset2/harvest-family generated validation outputs where available through the HAF pipeline.
- Dataset3 bridge outputs for growth and phenology context.

## Radiation-Defined Day/Night

Day/night phases were defined from Dataset1 `env_inside_radiation_wm2`, not from a fixed clock primary. Fixed-clock windows are compatibility references only.

## Event-Bridged Loadcell ET

Loadcell water-flux summaries were bridged into radiation-defined daily windows. These outputs support observer ET summaries and do not directly validate allocation.

## Root-Zone Stress Index

Root-zone RZI was computed as an observer feature for stress-aware interpretation and latent allocation inputs.

## DMC 0.056 Observation Operator

For 2025-2C, DMC is fixed at `0.056`. Dry yield derived from fresh yield using DMC `0.056` is an estimated dry-yield basis, not direct destructive dry-mass measurement.

## Latent Allocation Inference

Latent allocation was inferred from observer-supported state, bounded priors, diagnostics, identifiability checks, and guardrails. It remains observer-supported inference, not direct allocation validation.

## Harvest-Family Factorial

The harvest-family factorial separated allocator family, harvest family, and observation operator. Candidate ranking is interpreted as bounded architecture discrimination for 2025-2C.

## Budget Parity

Budget parity is knob-count and hidden-calibration-budget parity. It is not wall-clock compute-budget parity.

## Promotion And Cross-Dataset Gate

Promotion and cross-dataset gates were executed as safeguards. Promotion requires at least two compatible measured datasets and a passing cross-dataset gate.

## Claim Register

The claim register freezes allowed, forbidden, and safe-rewrite statements for manuscript and thesis use.
