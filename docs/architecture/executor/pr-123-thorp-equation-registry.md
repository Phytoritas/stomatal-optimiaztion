## Summary
- migrate the legacy THORP `equation_registry` module into `src/stomatal_optimiaztion/domains/thorp/equation_registry.py`
- preserve module-bound annotated-callable discovery and equation mapping over migrated THORP runtime modules
- move the next bounded THORP compatibility seam to `THORP/src/thorp/utils/__init__.py`

## Validation
- `.\\.venv\\Scripts\\python.exe -m pytest`
- `.\\.venv\\Scripts\\ruff.exe check .`

Closes #123
