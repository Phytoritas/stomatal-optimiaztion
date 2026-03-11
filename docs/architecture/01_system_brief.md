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

## Slice 003: THORP Weibull Vulnerability Curve

The third slice introduces the first numerical primitive that requires array semantics:
- port `WeibullVC` from `config.py` into its own THORP module
- preserve scalar and vectorized behavior from the legacy tests
- introduce `numpy` explicitly rather than hiding that dependency behind later seams
- keep the rest of `config.py` blocked until a larger hydraulic seam is selected

## Slice 004: THORP Soil Hydraulics

The fourth slice ports the next bounded hydraulic dataclass:
- move `SoilHydraulics` out of `config.py` into a dedicated THORP module
- preserve equation tags for `E_S2_4` through `E_S2_8`
- keep the implementation vectorized and numerically aligned with legacy snapshots
- leave `THORPParams` and `initial_soil_and_roots` blocked for the next seam

## Slice 005: THORP Soil Initialization

The fifth slice ports the first bounded soil-setup function:
- move `SoilGrid`, `InitialSoilAndRoots`, and `initial_soil_and_roots` from `soil.py`
- depend only on migrated primitives plus a minimal parameter dataclass
- validate soil-grid geometry and initialization outputs against legacy snapshots
- keep `richards_equation` and `soil_moisture` blocked for a later slice

## Slice 006: THORP Richards Equation

The sixth slice ports the next bounded soil-dynamics seam:
- move `richards_equation` from `soil.py` into a dedicated dynamics module
- reuse migrated `SoilGrid` and `SoilHydraulics`
- keep the interface bounded by a minimal `RichardsEquationParams` dataclass
- leave `soil_moisture` blocked as the next surface-coupling seam

## Slice 007: THORP Soil Moisture

The seventh slice ports the bounded soil surface-coupling seam:
- move `soil_moisture` from `soil.py` into the migrated soil-dynamics module
- reuse migrated `SoilGrid`, `SoilHydraulics`, and `richards_equation`
- keep the interface bounded by a minimal `SoilMoistureParams` dataclass
- leave `e_from_soil_to_root_collar` blocked as the next hydraulics seam

## Slice 008: THORP Root Uptake Hydraulics

The eighth slice ports the next bounded hydraulics seam:
- move `e_from_soil_to_root_collar` from `hydraulics.py` into a dedicated THORP hydraulics module
- reuse migrated `WeibullVC` and soil initialization outputs
- keep the interface bounded by a minimal `RootUptakeParams` dataclass
- leave `stomata` blocked as the next coupled hydraulics seam

## Immediate Deliverables

1. keep `poetry run pytest` green for the migrated model-card, radiation, hydraulic primitives, soil initialization, Richards-equation, soil-moisture, and root-uptake seams
2. keep `poetry run ruff check .` green as the minimum lint gate
3. prepare the next THORP source audit for `stomata` or another bounded coupled hydraulics seam
