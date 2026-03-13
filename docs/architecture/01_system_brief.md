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
- `src/stomatal_optimiaztion/domains/gosm`
- `src/stomatal_optimiaztion/domains/tdgm`
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

### GOSM
- standalone Python package for the growth-optimizing stomata model
- includes model-card assets, parameter defaults, runtime kernels, example adapters, and traceability tests
- should remain a root migrated domain instead of being conflated with TOMATO `tGOSM`

### TDGM
- standalone Python package for the turgor-driven growth model and THORP-G coupling
- includes model-card assets, PTM/TDGM kernels, coupling helpers, and THORP-backed regression tooling
- should remain a root migrated domain instead of being conflated with TOMATO `tTDGM`

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
- move `organ.py`, `fractions.py`, `policy.py`, and `sink_based.py` into the package-local TOMATO partitioning package
- preserve organ enums, allocation-fraction validation, policy coercion, and the default sink-based tomato partition rule
- replace inline default tomato allocation fallback inside `TomatoModel` with the migrated partitioning core
- leave `thorp_opt.py` and `thorp_policies.py` blocked as the next seam

## Slice 032: TOMATO tTHORP THORP-Derived Partition Policies

The thirty-second slice closes the remaining TOMATO partitioning seam:
- move `thorp_opt.py` and `thorp_policies.py` into the package-local TOMATO partitioning package
- preserve THORP-backed tomato allocation wrappers, policy invariants, and `thorp_veg` / `thorp_fruit_veg` alias wiring
- keep `TomatoModel` able to execute THORP-derived policies without breaking the bounded legacy surface
- leave `pipelines/tomato_legacy.py` blocked as the next seam

## Slice 033: TOMATO tTHORP Package-Level Legacy Pipeline

The thirty-third slice opens the next bounded TOMATO seam:
- move `TOMATO/tTHORP/src/tthorp/pipelines/tomato_legacy.py` into the staged `domains/tomato/tthorp` package
- preserve repo-root and forcing-path resolution, filtered config payloads, default model construction, pipeline execution, and metrics summary behavior
- keep the seam package-local instead of opening `core/io.py`, `core/scheduler.py`, or `pipelines/tomato_dayrun.py`
- leave `core/io.py` blocked as the next seam

## Slice 034: TOMATO tTHORP Shared IO

The thirty-fourth slice opens the next bounded TOMATO seam:
- move `TOMATO/tTHORP/src/tthorp/core/io.py` into the staged `domains/tomato/tthorp` package
- preserve directory creation, JSON metadata writing, YAML config parsing, recursive deep-merge behavior, and `extends`-chain loading
- declare `PyYAML` explicitly as a runtime dependency instead of relying on an undeclared local package
- leave `core/scheduler.py` blocked as the next seam

## Slice 035: TOMATO tTHORP Shared Scheduler

The thirty-fifth slice opens the next bounded TOMATO seam:
- move `TOMATO/tTHORP/src/tthorp/core/scheduler.py` into the staged `domains/tomato/tthorp` package
- preserve deterministic experiment-key hashing, `RunSchedule`, and forcing-derived schedule normalization
- keep the seam package-local instead of opening `pipelines/tomato_dayrun.py` or repo-level script entrypoints
- leave `pipelines/tomato_dayrun.py` blocked as the next seam

## Slice 036: TOMATO tTHORP Dayrun Pipeline

The thirty-sixth slice opens the next bounded TOMATO seam:
- move `TOMATO/tTHORP/src/tthorp/pipelines/tomato_dayrun.py` into the staged `domains/tomato/tthorp` package
- preserve config-driven execution, deterministic artifact writing, metadata JSON emission, and package-level from-config execution
- keep the seam package-local instead of opening repo-level `scripts/run_pipeline.py` or `scripts/make_features.py`
- leave `scripts/run_pipeline.py` blocked as the next seam

## Slice 037: TOMATO tTHORP Repo-Level Pipeline Script

The thirty-seventh slice opens the next bounded TOMATO seam:
- move `TOMATO/tTHORP/scripts/run_pipeline.py` into the repo-local `scripts/` surface
- preserve CLI argument parsing, config loading, output-dir resolution, deterministic artifact naming, and printed JSON summaries
- keep the seam bounded to the pipeline-runner script instead of opening `scripts/make_features.py` or broader automation entrypoints
- leave `scripts/make_features.py` blocked as the next seam

## Slice 038: TOMATO tTHORP Feature-Builder Script

The thirty-eighth slice opens the next bounded TOMATO seam:
- move `TOMATO/tTHORP/scripts/make_features.py` into the repo-local `scripts/` surface
- port the shared `core.util_units` PAR conversion helper as a direct dependency instead of duplicating the conversion logic again
- preserve deterministic feature CSV naming, SW-to-PAR derivation, forcing defaults, and printed output-path behavior
- leave `models/thorp_ref/adapter.py` blocked as the next seam

## Slice 039: TOMATO tTHORP THORP Reference Adapter

The thirty-ninth slice opens the next bounded TOMATO seam:
- move `TOMATO/tTHORP/src/tthorp/models/thorp_ref/adapter.py` and its package export into the staged `domains/tomato/tthorp` package
- bind the adapter to the migrated `stomatal_optimiaztion.domains.thorp` runtime instead of requiring an external THORP source checkout
- preserve forcing-column normalization, default fallback values, and the legacy-shaped output DataFrame contract
- leave `scripts/plot_simulation_png.py` blocked as the next seam

## Slice 040: TOMATO tTHORP Simulation Plotting Script

The fortieth slice opens the next bounded TOMATO seam:
- move `TOMATO/tTHORP/scripts/plot_simulation_png.py` into the repo-local `scripts/` surface
- preserve CLI parsing, CSV subsampling, four-panel simulation-summary plotting, and printed output-path behavior
- keep `matplotlib` as an optional plotting dependency instead of widening the core package runtime
- leave `scripts/plot_allocation_compare_png.py` blocked as the next seam

## Slice 041: TOMATO tTHORP Allocation-Comparison Plotting Script

The forty-first slice opens the next bounded TOMATO seam:
- move `TOMATO/tTHORP/scripts/plot_allocation_compare_png.py` into the repo-local `scripts/` surface
- preserve allocation-column ingestion, datetime alignment, overlap filtering, subsampling, and four-panel comparison plotting behavior
- keep `matplotlib` as an optional plotting dependency instead of widening the core package runtime
- leave `TOMATO/tGOSM/src/tgosm/contracts.py` blocked as the next seam

## Slice 042: TOMATO tGOSM Contracts

The forty-second slice opens the next bounded TOMATO seam:
- move `TOMATO/tGOSM/src/tgosm/contracts.py` into a new staged `domains/tomato/tgosm` package
- preserve optimization request/result dataclasses, nonnegative clamping, and the package import identity `MODEL_NAME == "tGOSM"`
- keep the slice contract-first and avoid pulling in `interface.py` or wider optimizer behavior yet
- leave `TOMATO/tGOSM/src/tgosm/interface.py` blocked as the next seam

## Slice 043: TOMATO tGOSM Interface

The forty-third slice opens the next bounded TOMATO seam:
- move `TOMATO/tGOSM/src/tgosm/interface.py` into the staged `domains/tomato/tgosm` package
- preserve the placeholder optimizer behavior that maps request stress to a nonnegative conductance target and explicit WUE/objective placeholders
- keep the seam intentionally small and avoid wider optimizer dependencies beyond the migrated contracts
- leave `TOMATO/tTDGM/src/ttdgm/contracts.py` blocked as the next seam

## Slice 044: TOMATO tTDGM Contracts

The forty-fourth slice opens the next bounded TOMATO seam:
- move `TOMATO/tTDGM/src/ttdgm/contracts.py` into a new staged `domains/tomato/ttdgm` package
- preserve growth-step dataclasses, allocation validation semantics, and the package import identity `MODEL_NAME == "tTDGM"`
- keep the slice contract-first and avoid pulling in `interface.py` or placeholder growth-step behavior yet
- leave `TOMATO/tTDGM/src/ttdgm/interface.py` blocked as the next seam

## Slice 045: TOMATO tTDGM Interface

The forty-fifth slice opens the next bounded TOMATO seam:
- move `TOMATO/tTDGM/src/ttdgm/interface.py` into the staged `domains/tomato/ttdgm` package
- preserve placeholder growth-step behavior that validates allocations and returns explicit zeroed leaf/stem/root/fruit growth channels
- keep the seam intentionally small and avoid wider physiology or shared abstractions beyond the migrated contracts
- leave `load-cell-data/loadcell_pipeline/config.py` blocked as the next seam

## Slice 046: load-cell-data Config

The forty-sixth slice opens the first bounded `load-cell-data` seam:
- move `load-cell-data/loadcell_pipeline/config.py` into a new staged `domains/load_cell` package
- preserve `PipelineConfig` defaults, `to_dict()` path serialization, YAML loading, and override precedence
- keep the slice config-first and avoid widening into ingestion, preprocessing, workflow, or CLI seams yet
- leave `load-cell-data/loadcell_pipeline/io.py` blocked as the next seam

## Slice 047: load-cell-data IO

The forty-seventh slice opens the next bounded `load-cell-data` seam:
- move `load-cell-data/loadcell_pipeline/io.py` into the staged `domains/load_cell` package
- preserve raw CSV ingestion, duplicate-timestamp handling, interpolation flags, and single/multi-resolution artifact writing behavior
- keep optional Excel export behavior explicit without widening into aggregation, preprocessing, workflow, or CLI seams
- leave `load-cell-data/loadcell_pipeline/aggregation.py` blocked as the next seam

## Slice 048: load-cell-data Aggregation

The forty-eighth slice opens the next bounded `load-cell-data` seam:
- move `load-cell-data/loadcell_pipeline/aggregation.py` into the staged `domains/load_cell` package
- preserve coarse-timescale flux aggregation, daily summary assembly, event counts, label-derived durations, and metadata passthrough
- keep the seam aggregation-bounded without widening into threshold detection, preprocessing, workflow, or CLI surfaces
- leave `load-cell-data/loadcell_pipeline/thresholds.py` blocked as the next seam

## Slice 049: load-cell-data Thresholds

The forty-ninth slice opens the next bounded `load-cell-data` seam:
- move `load-cell-data/loadcell_pipeline/thresholds.py` into the staged `domains/load_cell` package
- preserve robust derivative-distribution threshold detection, valid-mask fallback, and physical sign constraints
- keep the seam threshold-bounded without widening into preprocessing, workflow, or CLI surfaces
- leave `load-cell-data/loadcell_pipeline/preprocessing.py` blocked as the next seam

## Slice 050: load-cell-data Preprocessing

The fiftieth slice opens the next bounded `load-cell-data` seam:
- move `load-cell-data/loadcell_pipeline/preprocessing.py` into the staged `domains/load_cell` package
- preserve impulsive outlier detection/correction, moving-average and Savitzky-Golay smoothing, and derivative reconstruction behavior
- keep the seam preprocessing-bounded without widening into event detection, flux decomposition, workflow, or CLI surfaces
- leave `load-cell-data/loadcell_pipeline/events.py` blocked as the next seam

## Slice 051: load-cell-data Events

The fifty-first slice opens the next bounded `load-cell-data` seam:
- move `load-cell-data/loadcell_pipeline/events.py` into the staged `domains/load_cell` package
- preserve derivative-based labeling, hysteresis labeling, event grouping, short-event filtering, and close-event merge behavior
- keep the seam events-bounded without widening into flux decomposition, workflow, or CLI surfaces
- leave `load-cell-data/loadcell_pipeline/fluxes.py` blocked as the next seam

## Slice 052: load-cell-data Fluxes

The fifty-second slice opens the next bounded `load-cell-data` seam:
- move `load-cell-data/loadcell_pipeline/fluxes.py` into the staged `domains/load_cell` package
- preserve irrigation/drainage/transpiration decomposition, event-gap transpiration interpolation, cumulative sums, and water-balance scaling behavior
- keep the seam flux-bounded without widening into package-level pipeline orchestration, workflow, or batch-runner surfaces
- leave `load-cell-data/loadcell_pipeline/cli.py` blocked as the next seam

## Slice 053: load-cell-data CLI

The fifty-third slice opens the next bounded `load-cell-data` seam:
- move `load-cell-data/loadcell_pipeline/cli.py` into the staged `domains/load_cell` package
- preserve parser construction, CLI override mapping, package-level helper orchestration, event timing fields, and summary stats behavior
- keep the seam CLI-bounded without widening into batch workflow, sweep, or batch-runner surfaces
- leave `load-cell-data/loadcell_pipeline/workflow.py` blocked as the next seam

## Slice 054: load-cell-data Workflow

The fifty-fourth slice opens the next bounded `load-cell-data` seam:
- move `load-cell-data/loadcell_pipeline/workflow.py` into the staged `domains/load_cell` package
- preserve config signatures, filename matching, daily environment export, substrate joins, and per-variant/per-config batch orchestration behavior
- keep the seam workflow-bounded without widening into sweep, end-to-end batch runners, or raw preprocessing surfaces
- leave `load-cell-data/loadcell_pipeline/sweep.py` blocked as the next seam

## Slice 055: load-cell-data Sweep

The fifty-fifth slice opens the next bounded `load-cell-data` seam:
- move `load-cell-data/loadcell_pipeline/sweep.py` into the staged `domains/load_cell` package
- preserve grid parsing, generated config emission, workflow dispatch, run collection, and ranking behavior
- keep the seam sweep-bounded without widening into raw preprocessing or end-to-end runner surfaces
- leave `load-cell-data/loadcell_pipeline/run_all.py` blocked as the next seam

## Slice 056: load-cell-data End-to-End Runner

The fifty-sixth slice opens the next bounded `load-cell-data` seam:
- move `load-cell-data/loadcell_pipeline/run_all.py` into the staged `domains/load_cell` package
- preserve parser construction plus orchestration across raw preprocessing, workflow dispatch, and sweep dispatch
- keep raw preprocessing behind a lazy-or-injected dependency instead of widening into `almemo_preprocess.py` in the same slice
- leave `load-cell-data/loadcell_pipeline/almemo_preprocess.py` blocked as the next seam

## Slice 057: load-cell-data Raw ALMEMO Preprocessing

The fifty-seventh slice opens the next bounded `load-cell-data` seam:
- move `load-cell-data/loadcell_pipeline/almemo_preprocess.py` into the staged `domains/load_cell` package
- preserve raw ALMEMO CSV parsing, canonical channel mapping, duplicate-timestamp merge, optional 1-second interpolation, and precision-aware per-day CSV writing
- reconnect the migrated `run_all` seam to the concrete preprocessing implementation without widening into synthetic validation harnesses in the same slice
- leave `load-cell-data/loadcell_pipeline/synthetic_test.py` blocked as the next seam

## Slice 058: load-cell-data Synthetic Validation Harness

The fifty-eighth slice opens the next bounded `load-cell-data` seam:
- move `load-cell-data/loadcell_pipeline/synthetic_test.py` into the staged `domains/load_cell` package
- preserve deterministic synthetic dataset generation, truth totals, and end-to-end tolerance checks over the migrated `run_pipeline()` surface
- keep the seam validation-harness-bounded without widening into repo-level real-data benchmarks in the same slice
- leave `load-cell-data/real_data_benchmark.py` blocked as the next seam

## Slice 059: load-cell-data Real-Data Benchmark Harness

The fifty-ninth slice opens the next bounded `load-cell-data` seam:
- move `load-cell-data/real_data_benchmark.py` into the repo-local `scripts/` surface
- preserve batch summary/comparison/failure outputs over matched interpolated and raw daily CSV files
- keep the seam benchmark-harness-bounded without widening into preprocess-compare viewer/server tooling in the same slice
- leave `load-cell-data/src/preprocess_incremental.py` blocked as the next seam

## Slice 060: load-cell-data Incremental Preprocess Harness

The sixtieth slice opens the next bounded `load-cell-data` seam:
- move `load-cell-data/src/preprocess_incremental.py` into the repo-local `scripts/` surface
- preserve marker-backed raw skip logic, canonical parquet upsert, transpiration parquet emission, optional viewer cache refresh, and repo-level CLI defaults
- keep the seam incremental-tooling-bounded without widening into the preprocess-compare server or static viewer builder in the same slice
- leave `load-cell-data/src/preprocess_compare_server.py` blocked as the next seam

## Slice 061: load-cell-data Preprocess-Compare Local Server

The sixty-first slice opens the next bounded `load-cell-data` seam:
- move `load-cell-data/src/preprocess_compare_server.py` into the repo-local `scripts/` surface
- preserve local health/export/preprocess/cancel APIs, transpiration export computation, static viewer serving, and repo-level CLI defaults
- keep the seam server-bounded without widening into the static viewer builder or broader web-framework choices in the same slice
- leave `load-cell-data/src/build_preprocess_compare_viewer.py` blocked as the next seam

## Slice 062: load-cell-data Static Preprocess-Compare Viewer

The sixty-second slice closes the remaining bounded `load-cell-data/src` seam:
- move `load-cell-data/src/build_preprocess_compare_viewer.py` into the repo-local `scripts/` surface
- preserve canonical day discovery, transpiration parquet lookup plus canonical-derived 1-minute fallback, static asset writing, and per-day JSON generation
- keep the seam viewer-builder-bounded without widening into a new frontend architecture or a second server framework
- leave post-`load-cell-data` workspace re-audit blocked as the next step

## Slice 063: THORP Stable Sim Runner

The sixty-third slice opens the next bounded THORP compatibility seam:
- move `THORP/src/thorp/sim/runner.py` and `THORP/src/thorp/sim/__init__.py` into the staged `domains/thorp/sim/` package
- preserve the stable `thorp.sim.run` wrapper import surface over the already migrated simulation runtime
- keep the seam wrapper-bounded without widening into THORP numerical kernels or package-wide export redesign
- leave `THORP/src/thorp/equation_registry.py` blocked as the next seam

## Slice 064: THORP Equation Registry

The sixty-fourth slice opens the next bounded THORP compatibility seam:
- move `THORP/src/thorp/equation_registry.py` into the staged `domains/thorp/` package
- preserve module-bound annotated-callable discovery and one-call equation mapping over the migrated THORP runtime modules
- keep the seam compatibility-bounded without redesigning the existing traceability helper layer
- leave `THORP/src/thorp/utils/__init__.py` blocked as the next seam

## Slice 065: THORP Utilities Namespace

The sixty-fifth slice opens the next bounded THORP namespace-wrapper seam:
- move `THORP/src/thorp/utils/__init__.py` into the staged `domains/thorp/utils/` package
- preserve the grouped convenience imports for equation-registry, implements, and model-card helpers
- keep the seam wrapper-bounded without widening into new shared utility abstractions
- leave `THORP/src/thorp/io/__init__.py` blocked as the next seam

## Slice 066: THORP IO Namespace

The sixty-sixth slice opens the next bounded THORP namespace-wrapper seam:
- move `THORP/src/thorp/io/__init__.py` into the staged `domains/thorp/io/` package
- preserve the grouped convenience imports for forcing and MATLAB compatibility helpers
- keep the seam wrapper-bounded without widening into new I/O abstractions
- leave `THORP/src/thorp/model/__init__.py` blocked as the next seam

## Slice 067: THORP Model Namespace

The sixty-seventh slice opens the next bounded THORP namespace-wrapper seam:
- move `THORP/src/thorp/model/__init__.py` into the staged `domains/thorp/model/` package
- preserve the grouped convenience imports for allocation, growth, hydraulics, radiation, and soil helpers
- keep the seam wrapper-bounded without widening into new runtime abstractions
- leave `THORP/src/thorp/params/__init__.py` blocked as the next seam

## Slice 068: THORP Params Compatibility

The sixty-eighth slice closes the remaining bounded THORP namespace-wrapper gap:
- broaden `src/stomatal_optimiaztion/domains/thorp/params.py` so legacy callers recover the grouped `thorp.params` surface
- preserve grouped exports for `BottomBoundaryCondition`, `SoilHydraulics`, `THORPParams`, `WeibullVC`, and flat `default_params()`
- keep the seam compatibility-bounded without reintroducing the legacy `config.py` module layout
- leave package-level smoke validation as the next artifact

## Slice 069: THORP Package-Level Smoke Validation

The sixty-ninth slice closes the remaining THORP validation gap:
- extend the repo smoke suite so it exercises the migrated THORP root package and restored compatibility wrappers together
- record a review note that states the smoke-covered surface and the still out-of-scope numerical depth
- keep the slice validation-bounded without widening into new runtime abstractions
- leave the second-domain comparison note as the next artifact

## Slice 070: Second-Domain Utility Comparison

The seventieth slice closes the final open architecture gap:
- compare utility-like seams across THORP, TOMATO `tTHORP`, and `load_cell`
- record whether a shared utility layer is justified today
- keep `shared/` blocked because the current contracts, dependencies, and reuse pressure still diverge by domain
- leave the architecture in monitor mode until a new structural uncertainty appears

## Slice 071: Root GOSM Model-Card And Traceability Foundation

The seventy-first slice reopens the architecture after the false "all gaps closed" state:
- move the root `GOSM` model-card JSON assets into a staged `domains/gosm` package
- preserve packaged equation-id access and `@implements(...)` metadata helpers
- open a legacy-style `domains/gosm/utils/traceability.py` compatibility path so later numerical ports can land without import churn
- leave `GOSM/src/gosm/params/defaults.py` and the wider `model/` runtime blocked as later seams

## Slice 072: Root TDGM Model-Card And Traceability Foundation

The seventy-second slice opens the parallel root `TDGM` package foundation:
- move the root `TDGM` model-card JSON assets into a staged `domains/tdgm` package
- preserve packaged equation-id access and decorator-based traceability metadata helpers
- keep the seam package-foundation-bounded and leave PTM, turgor-growth, coupling, and THORP-G runtime imports blocked

## Slice 073: Root GOSM Parameter Defaults

The seventy-third slice opens the first bounded root `GOSM` numerical seam:
- move `GOSM/src/gosm/params/defaults.py` into a staged `domains/gosm/params/` package
- preserve `BaselineInputs.matlab_default()`, legacy alias properties, and bundled callable parameter functions
- keep the seam parameter-bounded and leave runtime kernels under `gosm.model` blocked

## Slice 074: Root GOSM Radiation Kernel

The seventy-fourth slice opens the first bounded root `GOSM` runtime kernel:
- move `GOSM/src/gosm/model/radiation.py` into the staged `domains/gosm/model/` package
- preserve `Eq.S3.2` tagging, zenith-angle clamping, and the negative-radiation guardrail
- keep the seam runtime-kernel-bounded and leave `allometry.py`, `hydraulics.py`, and higher-order orchestration blocked

## Slice 075: Root GOSM Allometry Helper

The seventy-fifth slice extends the bounded root `GOSM` runtime package with the next structural helper:
- move `GOSM/src/gosm/model/allometry.py` into the staged `domains/gosm/model/` package
- preserve `Eq.S3.LAI` tagging plus scalar and vector `leaf_area_index()` behavior
- keep the seam helper-bounded and leave `npp_gpp.py`, steady-state kernels, and pipeline orchestration blocked

## Slice 076: Root GOSM NPP GPP Helper

The seventy-sixth slice extends the bounded root `GOSM` runtime package with the next metabolic helpers:
- move `GOSM/src/gosm/model/npp_gpp.py` into the staged `domains/gosm/model/` package
- preserve `Eq.S8.1` and `Eq.S8.2` tagging plus scalar and vector steady-state NPP/GPP ratio behavior
- keep the seam helper-bounded and leave `optimal_control.py`, carbon-dynamics kernels, and pipeline orchestration blocked

## Slice 077: Root GOSM Optimal Control Helpers

The seventy-seventh slice extends the bounded root `GOSM` runtime package with the next objective-layer helpers:
- move `GOSM/src/gosm/model/optimal_control.py` into the staged `domains/gosm/model/` package
- preserve `Eq.S2.1` through `Eq.S2.6` tagging plus vectorized objective, eta, chi, theta, and eta-dot behavior
- keep the seam helper-bounded and leave `carbon_dynamics.py`, conductance-temperature kernels, and pipeline orchestration blocked

## Slice 078: Root GOSM Carbon Dynamics Helpers

The seventy-eighth slice extends the bounded root `GOSM` runtime package with the next carbon-balance helpers:
- move `GOSM/src/gosm/model/carbon_dynamics.py` into the staged `domains/gosm/model/` package
- preserve `Eq.S1.1` through `Eq.S1.9` tagging plus NSC limitation, respiration, growth, and compact/full NSC-rate behavior
- keep the seam helper-bounded and leave `conductance_temperature.py`, hydraulics kernels, and pipeline orchestration blocked

## Slice 079: Root GOSM Conductance Temperature Kernel

The seventy-ninth slice opens the first coupled root `GOSM` runtime kernel:
- move `GOSM/src/gosm/model/conductance_temperature.py` into the staged `domains/gosm/model/` package
- preserve `Eq.S3.1` and `Eq.S3.3` through `Eq.S3.10` tagging plus the leaf-temperature Newton solve, conductance outputs, latent heat, and derivative propagation
- keep the seam kernel-bounded and leave `carbon_assimilation.py`, hydraulics kernels, and pipeline orchestration blocked

## Slice 080: Root GOSM Carbon Assimilation Kernel

The eightieth slice extends the coupled root `GOSM` runtime with the next biochemical kernel:
- move `GOSM/src/gosm/model/carbon_assimilation.py` into the staged `domains/gosm/model/` package
- preserve `Eq.S4.1` through `Eq.S4.18` tagging plus the bounded assimilation solve, respiratory terms, and marginal-WUE calculation
- keep the seam kernel-bounded and leave `hydraulics.py`, full pipeline orchestration, and root `TDGM` runtime seams blocked

## Slice 081: Root GOSM Math Helper

The eighty-first slice repairs the small utility dependency required before hydraulics can land:
- move `GOSM/src/gosm/utils/math.py` into the staged `domains/gosm/utils/` package
- preserve `polylog2()` scalar and vector behavior and export it from `gosm.utils`
- keep the seam utility-bounded and leave `hydraulics.py` as the next coupled runtime kernel

## Slice 082: Root GOSM Hydraulics Kernel

The eighty-second slice opens the next coupled root `GOSM` runtime kernel:
- move `GOSM/src/gosm/model/hydraulics.py` into the staged `domains/gosm/model/` package
- preserve `Eq.S5.1` through `Eq.S6.15` tagging plus hydraulic state outputs, turgor-growth outputs, and derivative propagation
- keep the seam kernel-bounded and leave `pipeline.py` as the next fully wired runtime seam

## Slice 083: Root GOSM Runtime Pipeline

The eighty-third slice closes the first fully wired root `GOSM` runtime path:
- move `GOSM/src/gosm/model/pipeline.py` into the staged `domains/gosm/model/` package
- preserve the S3 through S6 stage tagging plus the canonical radiation, hydraulics, conductance-temperature, and carbon-assimilation orchestration order
- keep the seam runtime-pipeline-bounded and leave `future_work.py` as the next small helper seam

## Slice 084: Root GOSM Future-Work Helpers

The eighty-fourth slice restores the small paper-alternative helper layer:
- move `GOSM/src/gosm/model/future_work.py` into the staged `domains/gosm/model/` package
- preserve `Eq.S10.1` and `Eq.S10.2` tagging plus the growth-integral helper, legacy `Gamma` alias, and augmented-Lagrangian helper behavior
- keep the seam helper-bounded and leave `stomata_models.py` as the next analysis seam

## Slice 085: Root GOSM Stomatal-Model Comparison

The eighty-fifth slice restores the bounded alternative-stomatal optimization layer:
- move `GOSM/src/gosm/model/stomata_models.py` into the staged `domains/gosm/model/` package
- preserve the `Eq.S7.*` tagging, shared interpolation logic, `HC_vec` legacy alias, and no-crossing `NaN` contracts
- keep the seam analysis-bounded and leave `instantaneous.py` as the next control seam

## Slice 086: Root GOSM Instantaneous Optimum

The eighty-sixth slice restores the fixed-eta, fixed-NSC operating-point helper:
- move `GOSM/src/gosm/model/instantaneous.py` into the staged `domains/gosm/model/` package
- preserve `Eq.S2.4a` and `Eq.S2.4b` tagging plus the zero-crossing interpolation branch, all-negative-conductance branch, and lambda-zero bisection fallback
- keep the seam control-bounded and leave `steady_state.py` as the next analysis seam

## Slice 087: Root GOSM Steady-State Helper

The eighty-seventh slice closes the remaining root `GOSM` control-analysis helper layer:
- move `GOSM/src/gosm/model/steady_state.py` into the staged `domains/gosm/model/` package
- preserve `Eq.S1.9` and `Eq.S2.4b` tagging plus the vectorized Newton branch, quadratic NSC shortcut, and no-crossing/no-anchor contracts
- keep the seam analysis-bounded and leave root `TDGM` `turgor_growth.py` as the next runtime seam

## Slice 088: Root TDGM Turgor-Driven Growth

The eighty-eighth slice opens the first numerical root `TDGM` runtime seam:
- move `TDGM/src/tdgm/turgor_growth.py` into the staged `domains/tdgm/` package
- preserve `Eq_S2.12` and `Eq_S2.16` tagging plus scalar/vector whole-tree growth-rate behavior
- keep the seam kernel-bounded and leave `ptm.py` as the next runtime seam

## Slice 089: Root TDGM Phloem Transport

The eighty-ninth slice restores the bounded root `TDGM` PTM kernel:
- move `TDGM/src/tdgm/ptm.py` into the staged `domains/tdgm/` package
- preserve the `Eq_S1.*` tagging, sucrose-viscosity helper, apex-concentration behavior, and physiological NaN guard branch
- keep the seam kernel-bounded and leave `coupling.py` as the next runtime seam

## Slice 090: Root TDGM Coupling

The ninetieth slice restores the bounded root `TDGM` THORP-G coupling layer:
- move `TDGM/src/tdgm/coupling.py` into the staged `domains/tdgm/` package
- preserve the `Eq.S.3.*` tagging, one-step THORP-G wrapper, and allocation-history smoothing behavior
- keep the seam kernel-bounded and leave `equation_registry.py` as the next traceability seam

## Immediate Deliverables

1. keep `poetry run pytest` green for the migrated THORP seams, the root `GOSM` and `TDGM` foundation seams plus the first GOSM runtime seams, the first twenty-one TOMATO bounded seams, and the first sixteen `load-cell-data` bounded seams
2. keep `poetry run ruff check .` green as the minimum lint gate
3. migrate `TDGM/src/tdgm/equation_registry.py` as the next bounded root TDGM traceability seam
