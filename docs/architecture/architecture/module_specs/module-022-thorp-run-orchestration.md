# Module Spec 022: THORP Run Orchestration

## Purpose

Migrate the bounded `run` seam so the new package can execute the THORP simulation orchestration end to end by composing the already migrated forcing, hydraulics, allocation, growth, and storage seams.

## Source Inputs

- `THORP/src/thorp/simulate.py` (`run`)
- migrated `THORPParams`, forcing, runtime, and simulation-storage seams in `src/stomatal_optimiaztion/domains/thorp/`

## Target Outputs

- `src/stomatal_optimiaztion/domains/thorp/simulation.py`
- `tests/test_thorp_run.py`

## Responsibilities

1. preserve the legacy orchestration order across forcing, radiation, stomata, allocation, soil moisture, growth, and storage
2. adapt flat `THORPParams` into migrated dataclass seams without reintroducing legacy module coupling
3. keep MAT persistence behind an injected callback instead of pulling the writer into the runner

## Non-Goals

- port CLI entrypoints from `simulate.py`
- port a concrete MAT-file writer implementation
- retune or simplify THORP numerical behavior

## Validation

- `poetry run pytest`
- `poetry run ruff check .`

## Next Seam

- CLI entrypoints from `simulate.py`
