## Why
- `slice 073` opened the root `GOSM` parameter-defaults seam, so the next smallest runtime kernel is `GOSM/src/gosm/model/radiation.py`.
- The radiation kernel is numerically small, equation-tagged (`Eq.S3.2`), and already isolated from the rest of the GOSM runtime except for scalar inputs, which makes it the safest first runtime port.
- This slice should stay bounded: migrate the radiation kernel and the minimal model package path only, then leave allometry, hydraulics, conductance-temperature, and pipeline orchestration for later slices.

## Affected model
- `gosm`
- `src/stomatal_optimiaztion/domains/gosm/model/`
- `tests/`
- architecture status docs

## Validation method
- `poetry run pytest`
- `poetry run ruff check .`
- add coverage for equation tagging, zenith-angle clamping, negative-radiation guardrails, and a representative baseline snapshot

## Comparison target
- legacy `GOSM/src/gosm/model/radiation.py`
- legacy `GOSM/src/gosm/model/__init__.py`
- current migrated `src/stomatal_optimiaztion/domains/gosm/params/defaults.py`
