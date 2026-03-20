# Module Spec 030: TOMATO tTHORP Runner Seam

## Purpose

Open the next bounded TOMATO `tTHORP` seam by porting the legacy `models/tomato_legacy/run.py` runner so the migrated package can bind forcing CSV ingestion, default adapter construction, argument parsing, and CSV result writing into one package-local execution surface.

## Source Inputs

- `TOMATO/tTHORP/src/tthorp/models/tomato_legacy/run.py`

## Target Outputs

- `src/stomatal_optimiaztion/domains/tomato/tomics/alloc/models/tomato_legacy/run.py`
- `tests/test_tomics_alloc_run.py`

## Responsibilities

1. preserve CLI argument parsing for forcing input, output path, timestep defaults, and optional fixed LAI
2. preserve the bounded execution order across `iter_forcing_csv()`, `TomatoLegacyAdapter`, and `simulate()`
3. preserve output-path creation and module execution behavior without opening broader package entrypoints

## Non-Goals

- create a repo-wide TOMATO CLI entrypoint outside the legacy runner seam
- port TOMATO partition-policy packages as first-class modules
- broaden into `tGOSM`, `tTDGM`, or cross-domain execution surfaces

## Validation

- `poetry run pytest`
- `poetry run ruff check .`

## Next Seam

- `TOMATO/tTHORP/src/tthorp/components/partitioning/policy.py`
