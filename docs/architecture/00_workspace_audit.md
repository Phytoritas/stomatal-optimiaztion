# Workspace Audit

## Bound Context

- Bound repo root: `C:\Users\yhmoo\OneDrive\Phytoritas\projects\stomatal-optimiaztion`
- Legacy source root: `C:\Users\yhmoo\OneDrive\Phytoritas\00. Stomatal Optimization`
- Audit date: 2026-03-12

## Repo Profile Inference

Target repo profile:
- single Python package rooted at `src/stomatal_optimiaztion/`
- architecture-first migration repo with staged domain subpackages
- domain layout: `domains/thorp`, `domains/tomato`, `domains/load_cell`
- code migration rule: move one bounded seam at a time, keep each seam independently testable

Legacy source profile:
- umbrella folder containing multiple Python subprojects and generated artifacts
- not yet aligned to the workspace factory scaffold as one coherent repository

## Observed Legacy Top Level

- `THORP`: Python package repo with `src`, `tests`, `docs`, `scripts`, `data`, `example`, and `model_card`
- `TOMATO`: umbrella tree containing `tTHORP`, `tGOSM`, `tTDGM`, plus integration docs and output artifacts
- `load-cell-data`: separate pipeline-oriented Python project with preprocessing and visualization outputs
- `.venv`, `.pytest_cache`, `.codex-home`, and generated outputs exist inside the legacy workspace and should not be treated as migration sources

## Initial Structural Findings

1. The legacy source is already split into domain-oriented subprojects, but the umbrella folder mixes source, tooling, caches, and generated artifacts.
2. `THORP` appears closest to a modern single-package layout and can serve as the first reference domain for boundary design.
3. `TOMATO` contains nested packages and integration tests, which suggests future migration work needs explicit cross-package contracts.
4. `load-cell-data` behaves more like a pipeline project than a model-core package and may need its own adapter boundary.

## Early Risks

- generated outputs and caches may be copied into the new repo accidentally
- duplicated concepts across `THORP`, `TOMATO`, and `load-cell-data` may create naming drift
- nested package layouts inside `TOMATO` can blur migration boundaries
- validation commands for the umbrella folder are not yet normalized in this new repo

## Current Gate Status

- Gate A. Source audit complete for top-level legacy domains
- Gate B. Target architecture chosen
- Gate C. Validation plan ready through slice 021
- Gate D. Bounded slices 001 through 021 approved for THORP

## Migrated THORP Slices

Slice 001:
- source: `THORP/model_card/*.json`, `THORP/src/thorp/implements.py`, and traceability-facing patterns
- target: `src/stomatal_optimiaztion/domains/thorp/`
- scope: curated equation metadata, decorator-based traceability, and tests
- excluded: simulation runtime, MATLAB assets, and generated outputs

Slice 002:
- source: `THORP/src/thorp/radiation.py`
- target: `src/stomatal_optimiaztion/domains/thorp/radiation.py`
- scope: standalone canopy radiation kernel plus regression tests
- excluded: forcing, growth, and simulation orchestration

Slice 003:
- source: `THORP/src/thorp/config.py` (`WeibullVC`)
- target: `src/stomatal_optimiaztion/domains/thorp/vulnerability.py`
- scope: scalar and vectorized vulnerability-curve behavior
- excluded: `THORPParams`, `SoilHydraulics`, and the wider config bundle

Slice 004:
- source: `THORP/src/thorp/config.py` (`SoilHydraulics`)
- target: `src/stomatal_optimiaztion/domains/thorp/soil_hydraulics.py`
- scope: soil hydraulic relationships and equation-tagged methods
- excluded: `THORPParams` and `initial_soil_and_roots`

Slice 005:
- source: `THORP/src/thorp/soil.py` (`SoilGrid`, `InitialSoilAndRoots`, `initial_soil_and_roots`)
- target: `src/stomatal_optimiaztion/domains/thorp/soil_initialization.py`
- scope: bounded soil discretization and root initialization
- excluded: `richards_equation`, `soil_moisture`, and full soil time stepping

Slice 006:
- source: `THORP/src/thorp/soil.py` (`richards_equation`)
- target: `src/stomatal_optimiaztion/domains/thorp/soil_dynamics.py`
- scope: bounded Richards-equation solver with minimal parameter surface
- excluded: `soil_moisture` and full coupled surface flux logic

Slice 007:
- source: `THORP/src/thorp/soil.py` (`soil_moisture`)
- target: `src/stomatal_optimiaztion/domains/thorp/soil_dynamics.py`
- scope: bounded soil surface-coupling seam for evaporation, precipitation, and top-boundary updates
- excluded: `e_from_soil_to_root_collar`, stomatal optimization, and the wider hydraulics stack

Slice 008:
- source: `THORP/src/thorp/hydraulics.py` (`e_from_soil_to_root_collar`)
- target: `src/stomatal_optimiaztion/domains/thorp/hydraulics.py`
- scope: bounded root-uptake hydraulics and resistance bookkeeping
- excluded: `stomata`, canopy conductance coupling, and the wider optimization stack

Slice 009:
- source: `THORP/src/thorp/hydraulics.py` (`stomata`)
- target: `src/stomatal_optimiaztion/domains/thorp/hydraulics.py`
- scope: bounded stomatal closure, gas-exchange coupling, and derivative bookkeeping
- excluded: `allocation_fractions`, growth integration, and simulation orchestration

Slice 010:
- source: `THORP/src/thorp/allocation.py` (`allocation_fractions`)
- target: `src/stomatal_optimiaztion/domains/thorp/allocation.py`
- scope: bounded carbon-allocation scoring and fraction normalization
- excluded: `grow`, whole-plant growth-state updates, and simulation orchestration

Slice 011:
- source: `THORP/src/thorp/growth.py` (`GrowthState`, `grow`)
- target: `src/stomatal_optimiaztion/domains/thorp/growth.py`
- scope: bounded growth-state updates, senescence, and geometry reconstruction
- excluded: `biomass_fractions`, reporting helpers, and simulation orchestration

Slice 012:
- source: `THORP/src/thorp/metrics.py` (`BiomassFractions`, `biomass_fractions`)
- target: `src/stomatal_optimiaztion/domains/thorp/metrics.py`
- scope: bounded biomass-fraction reporting from carbon-pool time series
- excluded: `huber_value`, soil-grid helpers, rooting-depth reporting, and simulation orchestration

Slice 013:
- source: `THORP/src/thorp/metrics.py` (`huber_value`)
- target: `src/stomatal_optimiaztion/domains/thorp/metrics.py`
- scope: bounded sapwood-to-leaf area reporting from migrated growth time series
- excluded: `rooting_depth`, soil-grid reconstruction, and simulation orchestration

Slice 014:
- source: `THORP/src/thorp/metrics.py` (`rooting_depth`)
- target: `src/stomatal_optimiaztion/domains/thorp/metrics.py`
- scope: bounded rooting-depth reporting from migrated root time series and `SoilGrid`
- excluded: `soil_grid` reconstruction helper and simulation orchestration

Slice 015:
- source: `THORP/src/thorp/metrics.py` (`soil_grid`)
- target: `src/stomatal_optimiaztion/domains/thorp/metrics.py`
- scope: bounded grid-reconstruction helper using migrated soil-initialization params
- excluded: `default_params`, the legacy `THORPParams` bundle, and simulation orchestration

Slice 016:
- source: `THORP/src/thorp/config.py` (`default_params`)
- target: `src/stomatal_optimiaztion/domains/thorp/defaults.py`
- scope: bounded default-parameter bundle for already migrated THORP seams
- excluded: the legacy `THORPParams` dataclass, forcing-path setup, and simulation orchestration

Slice 017:
- source: `THORP/src/thorp/config.py` (`THORPParams`)
- target: `src/stomatal_optimiaztion/domains/thorp/params.py`
- scope: legacy-compatible flat parameter dataclass layered on top of migrated defaults
- excluded: `load_forcing`, `netCDF4`-backed forcing I/O, and simulation orchestration

Slice 018:
- source: `THORP/src/thorp/forcing.py` (`Forcing`, `load_forcing`)
- target: `src/stomatal_optimiaztion/domains/thorp/forcing.py`
- scope: bounded forcing netCDF ingestion, clipping, scaling, repetition, and solar-angle reconstruction
- excluded: `SimulationOutputs`, simulation orchestration, and MAT-file export

Slice 019:
- source: `THORP/src/thorp/simulate.py` (`SimulationOutputs`)
- target: `src/stomatal_optimiaztion/domains/thorp/simulation.py`
- scope: bounded simulation-result dataclass plus legacy MAT key mapping
- excluded: `_Store`, `simulate`, and MAT-file export

Slice 020:
- source: `THORP/src/thorp/simulate.py` (`_Store`)
- target: `src/stomatal_optimiaztion/domains/thorp/simulation.py`
- scope: bounded simulation-output buffering, cadence handling, and `SimulationOutputs` assembly
- excluded: `_initial_allometry`, `run`, and MAT-file export implementation

Slice 021:
- source: `THORP/src/thorp/simulate.py` (`_initial_allometry`)
- target: `src/stomatal_optimiaztion/domains/thorp/simulation.py`
- scope: bounded initial geometry and carbon-pool helper for THORP startup state
- excluded: `run`, CLI entrypoints, and simulation orchestration
