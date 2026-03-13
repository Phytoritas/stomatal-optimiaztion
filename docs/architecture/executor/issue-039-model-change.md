## Why
- `slice 038` landed the TOMATO repo-level feature builder, so the next bounded TOMATO `tTHORP` seam is the THORP reference bridge at `models/thorp_ref/adapter.py`.
- The migrated repo still lacks the adapter that reshapes tabular forcing into THORP forcing arrays and exposes THORP outputs through the TOMATO `tTHORP` DataFrame contract.
- The current repository already contains a migrated `stomatal_optimiaztion.domains.thorp` runtime, so this seam should bind to that local surface instead of depending on an external THORP source checkout.

## Affected model
- `TOMATO tTHORP`
- `src/stomatal_optimiaztion/domains/tomato/tthorp/models/thorp_ref/`
- related TOMATO THORP reference-adapter tests and package exports

## Validation method
- `poetry run pytest`
- `poetry run ruff check .`
- add coverage for forcing-column normalization, default fallback values, migrated THORP runtime binding, and adapter output shape

## Comparison target
- legacy `TOMATO/tTHORP/src/tthorp/models/thorp_ref/adapter.py`
- legacy `TOMATO/tTHORP/src/tthorp/models/thorp_ref/__init__.py`
- current migrated `stomatal_optimiaztion.domains.thorp` runtime surface
