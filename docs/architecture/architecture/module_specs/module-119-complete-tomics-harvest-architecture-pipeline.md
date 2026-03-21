# Module 119: Complete TOMICS Harvest Architecture Pipeline

## Problem

The public KNU fair-validation pipeline already distinguished allocator families and observation semantics, but harvest was still acting mostly as a validation-side helper instead of a first-class architecture family.

## Inputs

- KNU forcing contract and yield workbook from the public fair-validation baseline
- current selected allocator `kuijpers_hybrid_candidate`
- promoted selected allocator `constrained_full_plus_feedback__buffer_capacity_g_m2_12p0`
- local literature corpus for Heuvelink, Jones, De Koning, Vanthoor, and Kuijpers

## New seams

- `src/stomatal_optimiaztion/domains/tomato/tomics/alloc/components/harvest/`
- `src/stomatal_optimiaztion/domains/tomato/tomics/alloc/validation/harvest_family_eval.py`
- `src/stomatal_optimiaztion/domains/tomato/tomics/alloc/validation/harvest_factorial.py`
- `src/stomatal_optimiaztion/domains/tomato/tomics/alloc/validation/harvest_promotion_gate.py`

## Contracts

- incumbent baseline remains shipped TOMICS + incumbent TOMSIM harvest
- research harvest families remain opt-in only
- cumulative harvested fruit dry weight stays the measured target on floor-area basis
- allocator freedom and harvest-family freedom must remain parity-controlled before promotion

## Current decision

Module `119` keeps shipped TOMICS plus incumbent TOMSIM harvest as the incumbent baseline.

No harvest-aware research candidate clears the KNU promotion gate yet.
