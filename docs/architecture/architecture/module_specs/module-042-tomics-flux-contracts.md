# Module Spec 042: TOMATO tGOSM Contracts

## Purpose

Open the next bounded TOMATO seam by porting the `tGOSM` contract surface that defines optimizer request/result payloads and the minimal nonnegative helper.

## Source Inputs

- `TOMATO/tGOSM/src/tgosm/contracts.py`
- `TOMATO/tGOSM/tests/test_tgosm_contracts.py`
- `TOMATO/tGOSM/tests/test_tgosm_import.py`

## Target Outputs

- `src/stomatal_optimiaztion/domains/tomato/tomics/flux/contracts.py`
- `src/stomatal_optimiaztion/domains/tomato/tomics/flux/__init__.py`
- `src/stomatal_optimiaztion/domains/tomato/__init__.py`
- `tests/test_tomics_flux_contracts.py`

## Responsibilities

1. preserve optimization request/result dataclasses and the nonnegative clamp helper
2. expose the package import identity `MODEL_NAME == "tGOSM"`
3. keep the seam contract-first so later `tGOSM` interface work can build on one canonical package surface

## Non-Goals

- migrate `TOMATO/tGOSM/src/tgosm/interface.py`
- introduce optimizer behavior beyond the contract dataclasses
- widen into `tTDGM` or cross-model shared abstractions

## Validation

- `poetry run pytest`
- `poetry run ruff check .`

## Next Seam

- `TOMATO/tGOSM/src/tgosm/interface.py`
