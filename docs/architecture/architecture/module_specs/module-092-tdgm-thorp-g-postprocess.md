# Module Spec 092: TDGM THORP-G Postprocess

## Purpose

Restore the bounded root `TDGM/` postprocess bridge that derives coupling terms from stored THORP-G control outputs without re-running THORP.

## Source Inputs

- `TDGM/src/tdgm/thorp_g_postprocess.py`
- migrated `coupling.py`
- legacy THORP-G stored-output conventions (`*_stor`, forcing `data`)

## Target Outputs

- `src/stomatal_optimiaztion/domains/tdgm/thorp_g_postprocess.py`
- `tests/test_tdgm_thorp_g_postprocess.py`

## Responsibilities

1. preserve MATLAB-output loading, forcing-temperature alignment, and THORP-G postprocess dataclass surfaces
2. preserve the derived `g_rate_from_eq_ts == g_rate_ts` reconstruction contract over synthetic THORP-G outputs
3. keep the seam isolated from fresh THORP execution, external control datasets, and broader workflow tooling

## Non-Goals

- re-run THORP or TDGM dynamics
- migrate example control datasets into the repo
- widen the seam into viewer, CLI, or plotting layers

## Validation

- `poetry run pytest`
- `poetry run ruff check .`

## Next Seam

- none; close the current root `TDGM` migration wave and return to architecture audit
