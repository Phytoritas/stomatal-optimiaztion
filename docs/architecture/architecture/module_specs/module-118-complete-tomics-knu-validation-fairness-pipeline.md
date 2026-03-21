# Module 118: Complete TOMICS KNU Validation Fairness Pipeline

## Problem

The KNU actual-data baseline from module `117` still needed a fair observation operator, shared hidden-state reconstruction, explicit root-zone uncertainty, and parity-controlled calibration before any promotion decision could be considered credible.

## Inputs

- `data/forcing/KNU_Tomato_Env.CSV`
- `data/forcing/tomato_validation_data_yield_260222.xlsx`
- current selected baseline artifact under `out/tomics/validation/knu/architecture/current-factorial/`
- promoted selected baseline artifact under `out/tomics/validation/knu/architecture/promoted-factorial/`

## New seams

- `src/stomatal_optimiaztion/domains/tomato/tomics/alloc/validation/data_contract.py`
- `src/stomatal_optimiaztion/domains/tomato/tomics/alloc/validation/harvest_operator.py`
- `src/stomatal_optimiaztion/domains/tomato/tomics/alloc/validation/observation_model.py`
- `src/stomatal_optimiaztion/domains/tomato/tomics/alloc/validation/state_reconstruction.py`
- `src/stomatal_optimiaztion/domains/tomato/tomics/alloc/validation/rootzone_inversion.py`
- `src/stomatal_optimiaztion/domains/tomato/tomics/alloc/validation/calibration.py`
- `src/stomatal_optimiaztion/domains/tomato/tomics/alloc/validation/identifiability.py`
- `src/stomatal_optimiaztion/domains/tomato/tomics/alloc/validation/promotion_gate.py`

## Contracts

### Observation semantics

- measured target is cumulative harvested fruit dry weight on floor-area basis
- workbook estimated yield is comparator only
- daily harvested increment is evaluated alongside cumulative fit

### Calibration parity

- same shared free-parameter budget across shipped, current-selected, and promoted-selected
- same hidden-state reconstruction budget across those architectures
- architecture-specific knobs remain frozen

### Promotion gate

- no promotion if fruit-anchor drift exceeds `0.03`
- no promotion if canopy collapse days are non-zero
- no promotion if holdout improvement depends on unfair flexibility rather than architecture

## Current decision

Module `118` keeps shipped TOMICS incumbent and keeps both research candidates research-only.
