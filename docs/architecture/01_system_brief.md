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

## Slice 009: THORP Stomata

The ninth slice ports the next coupled hydraulics and gas-exchange seam:
- move `stomata` from `hydraulics.py` into the migrated THORP hydraulics module
- reuse migrated root-uptake, vulnerability, and traceable photosynthesis primitives
- keep the interface bounded by a minimal `StomataParams` dataclass
- leave `allocation_fractions` blocked as the next plant-growth seam

## Slice 010: THORP Allocation Fractions

The tenth slice ports the next bounded plant-growth seam:
- move `allocation_fractions` from `allocation.py` into a dedicated THORP allocation module
- reuse migrated stomatal derivative outputs without pulling in full growth state integration
- keep the interface bounded by a minimal `AllocationParams` dataclass
- leave `grow` blocked as the next growth-state seam

## Slice 011: THORP Grow

The eleventh slice ports the next bounded growth-state seam:
- move `grow` from `growth.py` into a dedicated THORP growth module
- reuse migrated allocation outputs without pulling in the full simulation loop
- keep the interface bounded by a minimal `GrowthParams` dataclass
- leave `biomass_fractions` blocked as the next reporting seam

## Slice 012: THORP Biomass Fractions

The twelfth slice ports the next bounded reporting seam:
- move `biomass_fractions` from `metrics.py` into a dedicated THORP metrics module
- reuse migrated growth time-series names without pulling in the legacy `SimulationOutputs` container
- keep the interface bounded by a minimal `BiomassFractionSeries` dataclass
- leave `huber_value` blocked as the next reporting seam

## Slice 013: THORP Huber Value

The thirteenth slice ports the next bounded reporting seam:
- move `huber_value` from `metrics.py` into the migrated THORP metrics module
- reuse migrated growth geometry time-series names without pulling in the legacy `SimulationOutputs` container
- keep the interface bounded by minimal `HuberValueSeries` and `HuberValueParams` dataclasses
- leave `rooting_depth` blocked as the next reporting seam

## Slice 014: THORP Rooting Depth

The fourteenth slice ports the next bounded reporting seam:
- move `rooting_depth` from `metrics.py` into the migrated THORP metrics module
- reuse migrated root time-series names and `SoilGrid` without pulling in the legacy `SimulationOutputs` container
- keep the interface bounded by a minimal `RootingDepthSeries` dataclass plus migrated `SoilGrid`
- leave `soil_grid` blocked as the next helper seam

## Slice 015: THORP Soil Grid Helper

The fifteenth slice ports the final bounded `metrics.py` helper seam:
- move `soil_grid` from `metrics.py` into the migrated THORP metrics module
- reuse migrated `SoilInitializationParams` and `initial_soil_and_roots`
- keep the helper bounded to grid reconstruction instead of porting the legacy `THORPParams` bundle
- leave `default_params` blocked as the next config seam

## Slice 016: THORP Default Params Bundle

The sixteenth slice ports the next bounded config seam:
- move the legacy `default_params` logic into a migrated defaults bundle for already ported THORP seams
- expose canonical defaults for `soil_initialization`, `richards`, `soil_moisture`, `root_uptake`, `stomata`, `allocation`, `growth`, and `huber_value`
- keep the implementation bounded to migrated parameter dataclasses instead of reintroducing the full legacy `THORPParams` bundle
- leave `THORPParams` blocked as the next config seam

## Slice 017: THORP Params Compatibility

The seventeenth slice ports the next bounded config seam:
- move the legacy `THORPParams` dataclass into a dedicated compatibility module
- reuse the migrated defaults bundle to expose a flat parameter surface for remaining adapters
- keep forcing metadata passive instead of porting `load_forcing` or adding a new runtime dependency
- leave `load_forcing` blocked as the next forcing seam

## Slice 018: THORP Load Forcing

The eighteenth slice ports the next bounded forcing seam:
- move `Forcing` and `load_forcing` from `forcing.py` into a dedicated THORP forcing module
- reuse migrated `THORPParams` compatibility metadata for file paths, scaling, and repeat controls
- keep the `netCDF4` dependency isolated to this boundary and validate with temporary fixtures instead of workspace-global assets
- leave `SimulationOutputs` blocked as the next simulation seam

## Slice 019: THORP Simulation Outputs

The nineteenth slice ports the next bounded simulation seam:
- move `SimulationOutputs` from `simulate.py` into a dedicated THORP simulation module
- preserve the legacy `as_mat_dict()` MAT key mapping without pulling in file export or time-stepping logic
- keep the boundary limited to result storage so reporting and export adapters can target one canonical output surface
- leave `_Store` blocked as the next simulation seam

## Slice 020: THORP Simulation Store

The twentieth slice ports the next bounded simulation seam:
- move `_Store` from `simulate.py` into the migrated THORP simulation module
- preserve legacy buffering cadence and `SimulationOutputs` assembly behavior
- keep MAT export behind an injected callback instead of pulling the writer into the storage seam
- leave `_initial_allometry` blocked as the next simulation seam

## Slice 021: THORP Initial Allometry

The twenty-first slice ports the next bounded simulation seam:
- move `_initial_allometry` from `simulate.py` into the migrated THORP simulation module
- preserve the legacy initial geometry and carbon-pool formulas
- expose one explicit output structure so the later `run` seam can consume the helper without anonymous tuples
- leave `run` blocked as the next simulation seam

## Slice 022: THORP Run Orchestration

The twenty-second slice ports the next bounded simulation seam:
- move `run` from `simulate.py` into the migrated THORP simulation module
- preserve the legacy orchestration order across forcing, radiation, stomata, allocation, soil-moisture, growth, and storage seams
- adapt flat `THORPParams` into the migrated dataclass seams without reintroducing legacy coupling
- leave CLI entrypoints blocked as the next seam

## Slice 023: THORP MATLAB IO

The twenty-third slice ports the next bounded IO seam:
- move `matlab_io.py` into the migrated THORP package
- preserve legacy MAT read/write behavior, including parent-directory creation and scipy options
- keep MAT persistence isolated from `run` so the remaining CLI seam can opt into the writer explicitly
- leave CLI entrypoints blocked as the next seam

## Slice 024: THORP CLI Entrypoint

The twenty-fourth slice ports the remaining bounded THORP execution seam:
- move the legacy `if __name__ == "__main__"` wrapper into package-local CLI modules
- preserve the legacy flags `--max-steps`, `--full`, and `--save-mat`
- wire the migrated `run` seam to the migrated `save_mat` callback without reintroducing legacy imports
- leave representative end-to-end CLI smoke validation as the next hardening step

## Slice 025: TOMATO tTHORP Contracts

The twenty-fifth slice opens the first bounded TOMATO seam:
- move `TOMATO/tTHORP/src/tthorp/contracts.py` into the staged `domains/tomato/tthorp` package
- preserve `EnvStep`, `Context`, `Module`, and output-coercion behavior
- keep the first TOMATO slice stdlib-only so nested-workspace boundaries are explicit before interface and pipeline migration
- leave `tTHORP/interface.py` blocked as the next seam

## Slice 026: TOMATO tTHORP Interface

The twenty-sixth slice opens the next bounded TOMATO seam:
- move `TOMATO/tTHORP/src/tthorp/interface.py` into the staged `domains/tomato/tthorp` package
- preserve `PipelineModel.step`, `simulate()`, and `run_flux_step()` behavior over the migrated contracts
- isolate the new `pandas` dependency to the tabular interface instead of pulling in tomato legacy models or pipelines
- leave `models/tomato_legacy/forcing_csv.py` blocked as the next seam

## Slice 027: TOMATO tTHORP Forcing CSV

The twenty-seventh slice opens the next bounded TOMATO seam:
- move `TOMATO/tTHORP/src/tthorp/models/tomato_legacy/forcing_csv.py` into the staged `domains/tomato/tthorp` package
- preserve alias-column normalization, timestep reconstruction, and `EnvStep` emission behavior
- keep the radiation-to-PAR conversion helper local to the seam instead of opening the broader TOMATO core utility layer
- leave `models/tomato_legacy/adapter.py` blocked as the next seam

## Slice 028: TOMATO tTHORP Adapter

The twenty-eighth slice opens the next bounded TOMATO seam:
- move `TOMATO/tTHORP/src/tthorp/models/tomato_legacy/adapter.py` into the staged `domains/tomato/tthorp` package
- preserve `TomatoLegacyAdapter`, `TomatoLegacyModule`, and `make_tomato_legacy_model()` behavior over the migrated `interface` and `forcing_csv` seams
- use an injected tomato-model protocol so the adapter bridge lands today without forcing the full `tomato_model.py` import surface
- leave `models/tomato_legacy/tomato_model.py` blocked as the next seam

## Slice 029: TOMATO tTHORP TomatoModel Surface

The twenty-ninth slice opens the next bounded TOMATO seam:
- move `TOMATO/tTHORP/src/tthorp/models/tomato_legacy/tomato_model.py` into the staged `domains/tomato/tthorp` package as a bounded public model surface
- preserve `TomatoModel` reset-state defaults, forcing-row ingestion, output payload shape, `set_plant_density()`, and `create_sample_input_csv()` compatibility
- wire the seam over the migrated `run_flux_step()` placeholder so default adapter execution works without opening the full partition-policy ecosystem or CLI yet
- leave `models/tomato_legacy/run.py` blocked as the next seam

## Slice 030: TOMATO tTHORP Runner Seam

The thirtieth slice opens the next bounded TOMATO seam:
- move `TOMATO/tTHORP/src/tthorp/models/tomato_legacy/run.py` into the staged `domains/tomato/tthorp` package
- preserve bounded argument parsing, forcing iteration, default adapter construction, and CSV result writing
- keep the runner package-local instead of opening a repo-wide TOMATO CLI entrypoint yet
- leave `components/partitioning/policy.py` blocked as the next seam

## Slice 031: TOMATO tTHORP Partitioning Core

The thirty-first slice opens the next bounded TOMATO seam:
- move `organ.py`, `fractions.py`, `policy.py`, and `sink_based.py` into a package-local TOMATO partitioning core
- preserve allocation-fraction validation, scheme conversion, policy coercion, and default sink-based aliases
- wire `TomatoModel` to the migrated sink-based policy instead of keeping default partitioning inline
- leave `components/partitioning/thorp_opt.py` blocked as the next seam

## Immediate Deliverables

1. keep `poetry run pytest` green for the migrated THORP seams plus the first seven TOMATO `tTHORP` seams
2. keep `poetry run ruff check .` green as the minimum lint gate
3. prepare the next TOMATO source audit for `components/partitioning/thorp_opt.py`
