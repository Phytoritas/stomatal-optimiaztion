## Why
- `load-cell-data` source wave closed at `slice 062`, so the next smallest remaining legacy runtime surface sits in `THORP/src/thorp/sim/runner.py`.
- The migrated repo already exposes `domains.thorp.simulation.run`, but it does not yet preserve the refactor-friendly stable wrapper import path `domains.thorp.sim.run`.
- This slice should stay wrapper-bounded: package-local `sim` namespace, stable `runner.run()` delegation, and import-compatibility regression coverage only.

## Affected model
- `thorp`
- `src/stomatal_optimiaztion/domains/thorp/sim/`
- THORP wrapper/import compatibility tests
- architecture docs for the next THORP compatibility seam

## Validation method
- `poetry run pytest`
- `poetry run ruff check .`
- add coverage for `thorp.sim.run` delegation, passthrough arguments, and package import surface stability

## Comparison target
- legacy `THORP/src/thorp/sim/runner.py`
- legacy `THORP/src/thorp/sim/__init__.py`
- current migrated `src/stomatal_optimiaztion/domains/thorp/simulation.py`
