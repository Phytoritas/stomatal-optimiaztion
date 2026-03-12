# Module Spec 021: THORP Initial Allometry

## Purpose

Migrate the bounded `_initial_allometry` seam so the new package can reconstruct THORP initial geometry and carbon pools before porting the full simulation runner.

## Source Inputs

- `THORP/src/thorp/simulate.py` (`_initial_allometry`)
- migrated `THORPParams` compatibility bundle in `src/stomatal_optimiaztion/domains/thorp/params.py`

## Target Outputs

- `src/stomatal_optimiaztion/domains/thorp/simulation.py`
- `tests/test_thorp_initial_allometry.py`

## Responsibilities

1. preserve the legacy initial geometry and carbon-pool formulas
2. expose one explicit output structure for later simulation orchestration
3. keep the helper isolated from `_Store` and `run`

## Non-Goals

- port `run` from `simulate.py`
- port CLI entrypoints
- change the legacy constants baked into the helper

## Validation

- `poetry run pytest`
- `poetry run ruff check .`

## Next Seam

- `run` from `simulate.py`
