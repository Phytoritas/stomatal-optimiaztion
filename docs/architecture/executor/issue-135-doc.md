## Why
- `slice 069` closed the THORP package-level smoke validation gap, leaving `GAP-007` as the final open architecture gap.
- The repo still needs an explicit second-domain comparison note before anyone introduces `src/stomatal_optimiaztion/shared/` or another cross-domain utility layer.
- This slice should stay documentation-bounded: compare migrated utilities across domains, decide whether sharing is justified, and update architecture status only.

## Affected scope
- `docs/architecture/system/`
- architecture status docs
- gap register closure

## Validation method
- `poetry run pytest`
- `poetry run ruff check .`
- confirm the comparison note names at least two migrated domains and produces a concrete keep-blocked or proceed decision

## Comparison target
- `domains/thorp` utility-like surfaces such as `forcing.py`, `matlab_io.py`, and `params.py`
- `domains/tomato/tthorp/core/` utility-like surfaces such as `io.py` and `util_units.py`
- `domains/load_cell` utility-like surfaces such as `config.py` and `io.py`
