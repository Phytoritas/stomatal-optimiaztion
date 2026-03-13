# Module Spec 063: THORP Stable Sim Runner

## Purpose

Open the next bounded THORP compatibility seam by porting the stable `thorp.sim.run` wrapper surface over the already migrated simulation runtime.

## Source Inputs

- `THORP/src/thorp/sim/runner.py`
- `THORP/src/thorp/sim/__init__.py`

## Target Outputs

- `src/stomatal_optimiaztion/domains/thorp/sim/runner.py`
- `src/stomatal_optimiaztion/domains/thorp/sim/__init__.py`
- `tests/test_thorp_sim_runner.py`

## Responsibilities

1. preserve the package-local `thorp.sim.run` import surface
2. preserve passthrough delegation to the migrated simulation runtime without changing behavior
3. keep the seam wrapper-bounded instead of reopening THORP numerical kernels or package-wide export redesign

## Non-Goals

- redesign `domains.thorp.simulation.run()`
- widen the THORP package export surface in the same slice
- migrate `THORP/src/thorp/equation_registry.py` in the same slice

## Validation

- `poetry run pytest`
- `poetry run ruff check .`

## Next Seam

- `THORP/src/thorp/equation_registry.py`
