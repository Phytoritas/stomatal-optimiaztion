# Module Spec 028: TOMATO tTHORP Adapter

## Purpose

Open the next bounded TOMATO `tTHORP` seam by porting the adapter bridge that maps migrated `EnvStep` forcing into the legacy tomato step-model contract without importing the full `tomato_model.py` implementation yet.

## Source Inputs

- `TOMATO/tTHORP/src/tthorp/models/tomato_legacy/adapter.py`

## Target Outputs

- `src/stomatal_optimiaztion/domains/tomato/tthorp/models/tomato_legacy/adapter.py`
- `src/stomatal_optimiaztion/domains/tomato/tthorp/models/tomato_legacy/__init__.py`
- `tests/test_tomato_tthorp_adapter.py`

## Responsibilities

1. preserve legacy row mapping, timestep forwarding, and numeric-output extraction through `TomatoLegacyAdapter`
2. preserve `TomatoLegacyModule` stress bookkeeping and pipeline wiring while using an injected tomato-model protocol to keep the seam bounded
3. fail clearly when no migrated `tomato_model` or explicit `model_factory` is available yet

## Non-Goals

- port `models/tomato_legacy/tomato_model.py`
- port partition-policy packages beyond pass-through adapter wiring
- port TOMATO pipelines or CLI entrypoints

## Validation

- `poetry run pytest`
- `poetry run ruff check .`

## Next Seam

- `TOMATO/tTHORP/src/tthorp/models/tomato_legacy/tomato_model.py`
