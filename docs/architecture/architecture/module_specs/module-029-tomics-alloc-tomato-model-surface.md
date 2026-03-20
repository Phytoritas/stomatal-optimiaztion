# Module Spec 029: TOMATO tTHORP TomatoModel Surface

## Purpose

Open the next bounded TOMATO `tTHORP` seam by porting the legacy `TomatoModel` public surface so the migrated package can construct a default model, ingest forcing rows, emit legacy-shaped outputs, and support model-state regression checks without opening the full partition-policy ecosystem or CLI yet.

## Source Inputs

- `TOMATO/tTHORP/src/tthorp/models/tomato_legacy/tomato_model.py`

## Target Outputs

- `src/stomatal_optimiaztion/domains/tomato/tomics/alloc/models/tomato_legacy/tomato_model.py`
- `src/stomatal_optimiaztion/domains/tomato/tomics/alloc/models/tomato_legacy/__init__.py`
- `src/stomatal_optimiaztion/domains/tomato/tomics/alloc/__init__.py`
- `tests/test_tomics_alloc_tomato_model.py`
- `tests/test_tomics_alloc_adapter.py`

## Responsibilities

1. preserve `TomatoModel` reset-state defaults, forcing-row ingestion, output payload shape, and density-helper behavior
2. preserve `run_simulation()` and `create_sample_input_csv()` as package-local compatibility surfaces for the migrated adapter path
3. make the default `TomatoLegacyAdapter` execution path work without an injected `model_factory`

## Non-Goals

- port the full age-structured growth, energy-balance, or harvest kernels from the legacy `tomato_model.py`
- port the TOMATO partition-policy package tree as first-class migrated modules
- port TOMATO runner or CLI entrypoints

## Validation

- `poetry run pytest`
- `poetry run ruff check .`

## Next Seam

- `TOMATO/tTHORP/src/tthorp/models/tomato_legacy/run.py`
