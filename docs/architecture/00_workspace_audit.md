# Workspace Audit

## Bound Context

- Bound repo root: `C:\Users\yhmoo\OneDrive\Phytoritas\projects\stomatal-optimiaztion`
- Legacy source root: `C:\Users\yhmoo\OneDrive\Phytoritas\00. Stomatal Optimization`
- Audit date: 2026-03-13

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
- Gate C. Validation plan ready through slice 050
- Gate D. Bounded slices 001 through 024 approved for THORP, slices 025 through 045 approved for TOMATO, and slices 046 through 050 approved for `load-cell-data`

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

Slice 022:
- source: `THORP/src/thorp/simulate.py` (`run`)
- target: `src/stomatal_optimiaztion/domains/thorp/simulation.py`
- scope: bounded THORP simulation orchestration across forcing, runtime seams, growth, and buffered storage
- excluded: CLI entrypoints and concrete MAT-file writer implementation

Slice 023:
- source: `THORP/src/thorp/matlab_io.py`
- target: `src/stomatal_optimiaztion/domains/thorp/matlab_io.py`
- scope: bounded MAT-file read/write helpers for legacy THORP payloads
- excluded: CLI entrypoints and simulation-runner orchestration

Slice 024:
- source: `THORP/src/thorp/simulate.py` (`if __name__ == "__main__"`)
- target: `src/stomatal_optimiaztion/domains/thorp/cli.py` and `src/stomatal_optimiaztion/domains/thorp/__main__.py`
- scope: bounded package-local CLI wrapper over migrated `run` and `save_mat` seams
- excluded: THORP numerical changes and broader workspace entrypoints

Slice 025:
- source: `TOMATO/tTHORP/src/tthorp/contracts.py`
- target: `src/stomatal_optimiaztion/domains/tomato/tthorp/`
- scope: bounded TOMATO forcing-step contracts, context protocol, and output coercion helpers
- excluded: pandas-backed interface surfaces, adapters, pipelines, and CLI entrypoints

Slice 026:
- source: `TOMATO/tTHORP/src/tthorp/interface.py`
- target: `src/stomatal_optimiaztion/domains/tomato/tthorp/interface.py`
- scope: bounded TOMATO pipeline interface, tabular simulation loop, and placeholder flux-step helper
- excluded: tomato legacy models, CSV forcing loaders, pipelines, and CLI entrypoints

Slice 027:
- source: `TOMATO/tTHORP/src/tthorp/models/tomato_legacy/forcing_csv.py`
- target: `src/stomatal_optimiaztion/domains/tomato/tthorp/models/tomato_legacy/forcing_csv.py`
- scope: bounded TOMATO CSV forcing ingestion, alias normalization, and canonical `EnvStep` reconstruction
- excluded: tomato legacy adapters, the full `TomatoModel`, pipelines, and CLI entrypoints

Slice 028:
- source: `TOMATO/tTHORP/src/tthorp/models/tomato_legacy/adapter.py`
- target: `src/stomatal_optimiaztion/domains/tomato/tthorp/models/tomato_legacy/adapter.py`
- scope: bounded TOMATO step-adapter bridge and pipeline module wiring over injected legacy-model protocols
- excluded: the full `TomatoModel`, partition-policy packages, pipelines, and CLI entrypoints

Slice 029:
- source: `TOMATO/tTHORP/src/tthorp/models/tomato_legacy/tomato_model.py`
- target: `src/stomatal_optimiaztion/domains/tomato/tthorp/models/tomato_legacy/tomato_model.py`
- scope: bounded TOMATO legacy-model surface covering reset-state defaults, forcing-row ingestion, output payload shape, density helpers, sample forcing generation, and default adapter execution
- excluded: the full age-structured growth kernels, partition-policy package migration, and legacy runner or CLI entrypoints

Slice 030:
- source: `TOMATO/tTHORP/src/tthorp/models/tomato_legacy/run.py`
- target: `src/stomatal_optimiaztion/domains/tomato/tthorp/models/tomato_legacy/run.py`
- scope: bounded TOMATO package-local runner over migrated forcing CSV, adapter, and tabular simulation seams
- excluded: TOMATO partition-policy package migration, broader package entrypoints, and other legacy subprojects

Slice 031:
- source: `TOMATO/tTHORP/src/tthorp/components/partitioning/{organ.py,fractions.py,policy.py,sink_based.py}`
- target: `src/stomatal_optimiaztion/domains/tomato/tthorp/components/partitioning/`
- scope: bounded TOMATO partitioning core covering organ enums, allocation-fraction validation, policy coercion, and default sink-based allocation
- excluded: `thorp_opt.py`, `thorp_policies.py`, and broader cross-domain policy sharing

Slice 032:
- source: `TOMATO/tTHORP/src/tthorp/components/partitioning/{thorp_opt.py,thorp_policies.py}`
- target: `src/stomatal_optimiaztion/domains/tomato/tthorp/components/partitioning/`
- scope: bounded TOMATO THORP-derived partitioning surface covering allocation wrappers, policy aliases, and `TomatoModel` THORP-policy execution
- excluded: `pipelines/tomato_legacy.py`, `core/`, and `models/thorp_ref/`

Slice 033:
- source: `TOMATO/tTHORP/src/tthorp/pipelines/tomato_legacy.py`
- target: `src/stomatal_optimiaztion/domains/tomato/tthorp/pipelines/` and `tests/test_tomato_tthorp_pipeline.py`
- scope: bounded TOMATO package-level legacy pipeline surface covering repo-root resolution, forcing-path resolution, filtered config payloads, default model construction, pipeline execution, and metrics summaries
- excluded: `core/io.py`, `core/scheduler.py`, `pipelines/tomato_dayrun.py`, and broader repo-level CLI entrypoints

Slice 034:
- source: `TOMATO/tTHORP/src/tthorp/core/io.py`
- target: `src/stomatal_optimiaztion/domains/tomato/tthorp/core/`, `tests/test_tomato_tthorp_core_io.py`, `pyproject.toml`, and `poetry.lock`
- scope: bounded TOMATO shared IO surface covering directory creation, JSON metadata writing, YAML config parsing, recursive config merge, and `extends`-chain loading
- excluded: `core/scheduler.py`, `pipelines/tomato_dayrun.py`, and repo-level script entrypoints

Slice 035:
- source: `TOMATO/tTHORP/src/tthorp/core/scheduler.py`
- target: `src/stomatal_optimiaztion/domains/tomato/tthorp/core/` and `tests/test_tomato_tthorp_core_scheduler.py`
- scope: bounded TOMATO shared scheduler surface covering deterministic experiment-key hashing, schedule dataclass construction, and forcing-derived run normalization
- excluded: `pipelines/tomato_dayrun.py` and repo-level script entrypoints

Slice 036:
- source: `TOMATO/tTHORP/src/tthorp/pipelines/tomato_dayrun.py`
- target: `src/stomatal_optimiaztion/domains/tomato/tthorp/pipelines/` and `tests/test_tomato_tthorp_dayrun.py`
- scope: bounded TOMATO dayrun orchestration surface covering config-driven execution, deterministic output artifact paths, metadata emission, and package-level from-config entrypoints
- excluded: repo-level `scripts/run_pipeline.py` and `scripts/make_features.py`

Slice 037:
- source: `TOMATO/tTHORP/scripts/run_pipeline.py`
- target: `scripts/run_pipeline.py` and `tests/test_tomato_tthorp_run_pipeline_script.py`
- scope: bounded TOMATO repo-level pipeline script surface covering CLI argument parsing, config loading, output-dir resolution, deterministic result artifact naming, and printed JSON summaries
- excluded: `scripts/make_features.py` and broader non-TOMATO entrypoints

Slice 038:
- source: `TOMATO/tTHORP/scripts/make_features.py` and `TOMATO/tTHORP/src/tthorp/core/util_units.py`
- target: `scripts/make_features.py`, `src/stomatal_optimiaztion/domains/tomato/tthorp/core/util_units.py`, and feature/unit-conversion tests
- scope: bounded TOMATO feature-building surface covering deterministic feature CSV output, SW-to-PAR derivation, forcing defaults, and shared PAR conversion helpers
- excluded: `models/thorp_ref/adapter.py`, plotting scripts, and broader non-TOMATO entrypoints

Slice 039:
- source: `TOMATO/tTHORP/src/tthorp/models/thorp_ref/{adapter.py,__init__.py}`
- target: `src/stomatal_optimiaztion/domains/tomato/tthorp/models/thorp_ref/`, package exports, and `tests/test_tomato_tthorp_thorp_ref_adapter.py`
- scope: bounded TOMATO THORP-reference bridge covering forcing-column normalization, migrated THORP runtime binding, and legacy-shaped DataFrame outputs
- excluded: repo-level plotting scripts, PNG summary generation, and broader non-TOMATO entrypoints

Slice 040:
- source: `TOMATO/tTHORP/scripts/plot_simulation_png.py`
- target: `scripts/plot_simulation_png.py` and `tests/test_tomato_tthorp_plot_simulation_png_script.py`
- scope: bounded TOMATO repo-level plotting surface covering CLI parsing, CSV subsampling, four-panel simulation-summary plotting, and optional matplotlib dependency behavior
- excluded: `scripts/plot_allocation_compare_png.py`, shared plotting packages, and broader non-TOMATO reporting entrypoints

Slice 041:
- source: `TOMATO/tTHORP/scripts/plot_allocation_compare_png.py`
- target: `scripts/plot_allocation_compare_png.py` and `tests/test_tomato_tthorp_plot_allocation_compare_png_script.py`
- scope: bounded TOMATO repo-level allocation-comparison plotting surface covering CSV alignment, allocation-column reshaping, overlap filtering, subsampling, and optional matplotlib dependency behavior
- excluded: `tGOSM`, `tTDGM`, shared plotting packages, and broader non-TOMATO reporting entrypoints

Slice 042:
- source: `TOMATO/tGOSM/src/tgosm/contracts.py` and `TOMATO/tGOSM/tests/{test_tgosm_contracts.py,test_tgosm_import.py}`
- target: `src/stomatal_optimiaztion/domains/tomato/tgosm/`, root TOMATO exports, and `tests/test_tomato_tgosm_contracts.py`
- scope: bounded TOMATO `tGOSM` contract surface covering optimization request/result dataclasses, nonnegative clamping, and package import identity
- excluded: `src/tgosm/interface.py`, optimizer implementation details, `tTDGM`, and broader non-TOMATO entrypoints

Slice 043:
- source: `TOMATO/tGOSM/src/tgosm/interface.py`
- target: `src/stomatal_optimiaztion/domains/tomato/tgosm/interface.py`, package exports, and `tests/test_tomato_tgosm_interface.py`
- scope: bounded TOMATO `tGOSM` interface surface covering placeholder optimizer behavior, conductance target clamping, and explicit WUE/objective placeholders
- excluded: `tTDGM`, non-placeholder optimizer dependencies, and broader non-TOMATO entrypoints

Slice 044:
- source: `TOMATO/tTDGM/src/ttdgm/contracts.py` and `TOMATO/tTDGM/tests/{test_ttdgm_contracts.py,test_ttdgm_import.py}`
- target: `src/stomatal_optimiaztion/domains/tomato/ttdgm/`, root TOMATO exports, and `tests/test_tomato_ttdgm_contracts.py`
- scope: bounded TOMATO `tTDGM` contract surface covering growth-step dataclasses, allocation validation, and package import identity
- excluded: `src/ttdgm/interface.py`, placeholder growth-step behavior, `load-cell-data`, and broader non-TOMATO entrypoints

Slice 045:
- source: `TOMATO/tTDGM/src/ttdgm/interface.py`
- target: `src/stomatal_optimiaztion/domains/tomato/ttdgm/interface.py`, package exports, and `tests/test_tomato_ttdgm_interface.py`
- scope: bounded TOMATO `tTDGM` interface surface covering placeholder growth-step behavior, allocation validation, and explicit four-organ growth outputs
- excluded: `load-cell-data`, non-placeholder growth dynamics, and broader cross-domain abstractions

Slice 046:
- source: `load-cell-data/loadcell_pipeline/config.py`
- target: `src/stomatal_optimiaztion/domains/load_cell/`, root domain exports, and `tests/test_load_cell_config.py`
- scope: bounded `load-cell-data` config surface covering pipeline defaults, path serialization, YAML loading, and override precedence
- excluded: `loadcell_pipeline/io.py`, preprocessing, workflow, CLI, and dashboard entrypoints

Slice 047:
- source: `load-cell-data/loadcell_pipeline/io.py`
- target: `src/stomatal_optimiaztion/domains/load_cell/io.py`, package exports, and `tests/test_load_cell_io.py`
- scope: bounded `load-cell-data` IO surface covering raw CSV ingestion, interpolation flags, duplicate-timestamp handling, and single/multi-resolution artifact writing
- excluded: `loadcell_pipeline/aggregation.py`, preprocessing, workflow, CLI, and dashboard entrypoints

Slice 048:
- source: `load-cell-data/loadcell_pipeline/aggregation.py`
- target: `src/stomatal_optimiaztion/domains/load_cell/aggregation.py`, package exports, and `tests/test_load_cell_aggregation.py`
- scope: bounded `load-cell-data` aggregation surface covering flux resampling, daily summaries, event counts, label-derived durations, and metadata passthrough
- excluded: `loadcell_pipeline/thresholds.py`, preprocessing, workflow, CLI, and dashboard entrypoints

Slice 049:
- source: `load-cell-data/loadcell_pipeline/thresholds.py`
- target: `src/stomatal_optimiaztion/domains/load_cell/thresholds.py`, package exports, and `tests/test_load_cell_thresholds.py`
- scope: bounded `load-cell-data` threshold surface covering robust sigma estimation, valid-mask fallback, and irrigation/drainage threshold constraints
- excluded: `loadcell_pipeline/preprocessing.py`, workflow, CLI, and dashboard entrypoints

Slice 050:
- source: `load-cell-data/loadcell_pipeline/preprocessing.py`
- target: `src/stomatal_optimiaztion/domains/load_cell/preprocessing.py`, package exports, and `tests/test_load_cell_preprocessing.py`
- scope: bounded `load-cell-data` preprocessing surface covering impulsive outlier correction, moving-average and Savitzky-Golay smoothing, and derivative reconstruction
- excluded: `loadcell_pipeline/events.py`, flux decomposition, workflow, CLI, and dashboard entrypoints
