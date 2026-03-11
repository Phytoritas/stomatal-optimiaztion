# System Brief

## Problem Statement

The legacy "00. Stomatal Optimization" folder contains valuable model and pipeline work, but it is organized as an umbrella workspace rather than a single scaffold-aligned refactoring repository.

The new `stomatal-optimiaztion` repo exists to provide:
- a stable architecture workspace
- a migration-friendly documentation backbone
- a clean place to stage bounded refactor slices

## Finalized Target Shape

This repository will stay a single Python package with staged domain subpackages:
- `src/stomatal_optimiaztion/domains/thorp`
- `src/stomatal_optimiaztion/domains/tomato`
- `src/stomatal_optimiaztion/domains/load_cell`
- `configs/` for migration and experiment settings
- `docs/architecture/` for decisions, evidence, and slice planning

Shared helpers can be introduced later under `src/stomatal_optimiaztion/shared/`, but only after at least two domains need the same seam.

## Primary Source Domains

### THORP
- model-oriented Python package
- includes equations, forcing, hydraulics, growth, and simulation modules
- likely best first candidate for source mapping

### TOMATO
- nested package workspace with `tTHORP`, `tGOSM`, and `tTDGM`
- includes integration tests, configs, and output artifacts
- likely requires explicit interface and package boundary decisions

### load-cell-data
- preprocessing and analysis pipeline
- includes CLI and visualization-oriented outputs
- should likely remain separated from model-core packages through adapters or data contracts

## Architectural Principle

Refactor by boundary and evidence, not by bulk copying. The new repo should only absorb code after:
- module boundaries are named
- validation commands are defined
- artifact handling rules are explicit

## Slice 001: THORP Model-Card Traceability

The first bounded migration slice is intentionally small:
- copy THORP `model_card` JSON assets only
- do not copy the source PDF or any MATLAB outputs
- migrate stdlib-only traceability helpers before numerical kernels
- prove the seam with package-local tests before moving simulation code

## Slice 002: THORP Radiation Kernel

The second slice moves the first runtime kernel:
- port `radiation.py` as a standalone THORP runtime seam
- preserve equation tags from S.5
- validate with a legacy snapshot and an extreme-angle behavior test
- keep the seam stdlib-only to avoid dependency growth before larger numerical modules move

## Immediate Deliverables

1. keep `poetry run pytest` green for the migrated model-card and radiation seams
2. keep `poetry run ruff check .` green as the minimum lint gate
3. prepare the next THORP source audit for `WeibullVC` or another small runtime primitive
