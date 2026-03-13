# Module Spec 090: TDGM Coupling

## Purpose

Restore the bounded root `TDGM/` coupling primitives that bridge PTM and turgor outputs into THORP-G growth terms.

## Source Inputs

- `TDGM/src/tdgm/coupling.py`
- `TDGM/src/tdgm/__init__.py`

## Target Outputs

- `src/stomatal_optimiaztion/domains/tdgm/`
- `tests/test_tdgm_coupling.py`

## Responsibilities

1. preserve the `Eq.S.3.*`-tagged THORP-G coupling helpers and the one-step dataclass wrapper
2. preserve allocation-history smoothing and scalar/vector Michaelis-Menten coupling behavior
3. keep the seam isolated from equation-registry assembly and THORP-G postprocess IO

## Non-Goals

- migrate `TDGM/src/tdgm/equation_registry.py`
- migrate `TDGM/src/tdgm/thorp_g_postprocess.py`
- widen the seam into external forcing or MATLAB output loaders

## Validation

- `poetry run pytest`
- `poetry run ruff check .`

## Next Seam

- `TDGM/src/tdgm/equation_registry.py`
