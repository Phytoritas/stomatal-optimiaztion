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
- Gate C. Validation plan ready through slice 005
- Gate D. Bounded slices 001 through 005 approved for THORP

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
