# Module Spec 024: THORP CLI Entrypoint

## Purpose

Migrate the remaining THORP `simulate.py` CLI entrypoint seam so the new package exposes a package-local execution surface over the migrated `run` and `save_mat` seams.

## Source Inputs

- `THORP/src/thorp/simulate.py` (`if __name__ == "__main__"`)
- migrated THORP `run` seam in `simulation.py`
- migrated THORP `save_mat` seam in `matlab_io.py`

## Target Outputs

- `src/stomatal_optimiaztion/domains/thorp/cli.py`
- `src/stomatal_optimiaztion/domains/thorp/__main__.py`
- `tests/test_thorp_cli.py`

## Responsibilities

1. preserve the legacy `--max-steps`, `--full`, and `--save-mat` flags
2. dispatch into the migrated `run` seam with the correct `save_mat` callback wiring
3. expose one package-local module execution surface without reaching back into the legacy repository

## Non-Goals

- retune THORP runtime numerics
- create workspace-wide entrypoints for other domains
- broaden into end-to-end smoke validation beyond the wrapper boundary

## Validation

- `poetry run pytest`
- `poetry run ruff check .`

## Next Seam

- representative package-local THORP CLI smoke validation
