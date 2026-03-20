# Module Spec 027: TOMATO tTHORP Forcing CSV

## Purpose

Open the next bounded TOMATO `tTHORP` seam by porting the CSV forcing loader that normalizes legacy column aliases and emits canonical `EnvStep` rows for the migrated interface.

## Source Inputs

- `TOMATO/tTHORP/src/tthorp/models/tomato_legacy/forcing_csv.py`

## Target Outputs

- `src/stomatal_optimiaztion/domains/tomato/tomics/alloc/models/tomato_legacy/forcing_csv.py`
- `src/stomatal_optimiaztion/domains/tomato/tomics/alloc/models/tomato_legacy/__init__.py`
- `tests/test_tomics_alloc_forcing_csv.py`

## Responsibilities

1. preserve legacy datetime sorting, timestep reconstruction, and required-column validation when yielding `EnvStep`
2. preserve alias-column handling plus `SW_in_Wm2 -> PAR_umol` reconstruction without pulling in wider tomato legacy model code
3. keep the seam bounded to forcing ingestion and package exports, leaving adapters and the full `TomatoModel` surface blocked

## Non-Goals

- port `models/tomato_legacy/adapter.py`
- port `models/tomato_legacy/tomato_model.py`
- port TOMATO pipelines or CLI entrypoints

## Validation

- `poetry run pytest`
- `poetry run ruff check .`

## Next Seam

- `TOMATO/tTHORP/src/tthorp/models/tomato_legacy/adapter.py`
