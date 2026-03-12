# Module Spec 023: THORP MATLAB IO

## Purpose

Migrate the bounded `matlab_io` seam so the new package can read and write legacy THORP `.mat` payloads without calling back into the legacy repository.

## Source Inputs

- `THORP/src/thorp/matlab_io.py`
- migrated THORP simulation outputs and callback-based runner seam

## Target Outputs

- `src/stomatal_optimiaztion/domains/thorp/matlab_io.py`
- `tests/test_thorp_matlab_io.py`

## Responsibilities

1. preserve legacy `loadmat(..., squeeze_me=True, struct_as_record=False)` behavior
2. preserve legacy compressed `savemat(...)` behavior and parent-directory creation
3. keep file IO isolated from the simulation runner so CLI and export adapters can opt in explicitly

## Non-Goals

- port the remaining CLI entrypoint from `simulate.py`
- fold MAT writing back into `run`
- change MAT payload keys or shapes

## Validation

- `poetry run pytest`
- `poetry run ruff check .`

## Next Seam

- CLI entrypoints from `simulate.py`
