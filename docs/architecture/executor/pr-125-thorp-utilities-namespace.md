## Summary
- migrate the legacy THORP `utils` namespace wrapper into `src/stomatal_optimiaztion/domains/thorp/utils/__init__.py`
- preserve grouped imports for equation-registry, implements, and model-card helpers without redefining them
- move the next bounded THORP namespace-wrapper seam to `THORP/src/thorp/io/__init__.py`

## Validation
- `.\\.venv\\Scripts\\python.exe -m pytest`
- `.\\.venv\\Scripts\\ruff.exe check .`

Closes #125
