## Summary
- migrate the legacy THORP stable `sim` wrapper into `src/stomatal_optimiaztion/domains/thorp/sim/`
- preserve `thorp.sim.run` passthrough behavior over the migrated simulation runtime
- move the next bounded THORP compatibility seam to `THORP/src/thorp/equation_registry.py`

## Validation
- `.\\.venv\\Scripts\\python.exe -m pytest`
- `.\\.venv\\Scripts\\ruff.exe check .`

Closes #121
