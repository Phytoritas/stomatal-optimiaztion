# Module Spec 044: TOMATO tTDGM Contracts

## Purpose

Open the next bounded TOMATO seam by porting the `tTDGM` contract surface that defines growth-step payloads, allocation fractions, and package import identity.

## Source Inputs

- `TOMATO/tTDGM/src/ttdgm/contracts.py`
- `TOMATO/tTDGM/tests/test_ttdgm_contracts.py`
- `TOMATO/tTDGM/tests/test_ttdgm_import.py`

## Target Outputs

- `src/stomatal_optimiaztion/domains/tomato/tomics/grow/contracts.py`
- `src/stomatal_optimiaztion/domains/tomato/tomics/grow/__init__.py`
- `src/stomatal_optimiaztion/domains/tomato/__init__.py`
- `tests/test_tomics_grow_contracts.py`

## Responsibilities

1. preserve frozen contract dataclasses for organ pools, growth drivers, allocation fractions, and growth-step outputs
2. preserve allocation validation semantics that require a positive unity sum
3. expose the package import identity `MODEL_NAME == "tTDGM"` so the later interface seam can land on a canonical package surface

## Non-Goals

- migrate `TOMATO/tTDGM/src/ttdgm/interface.py`
- introduce growth-step behavior beyond the contract dataclasses
- widen into `load-cell-data` or cross-model shared abstractions

## Validation

- `poetry run pytest`
- `poetry run ruff check .`

## Next Seam

- `TOMATO/tTDGM/src/ttdgm/interface.py`
