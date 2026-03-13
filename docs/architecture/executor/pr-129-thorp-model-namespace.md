## Summary
- migrate the legacy THORP `model` namespace wrapper into `src/stomatal_optimiaztion/domains/thorp/model/__init__.py`
- preserve grouped imports for allocation, growth, hydraulics, radiation, and soil helpers without redefining them
- move the next bounded THORP compatibility seam to `THORP/src/thorp/params/__init__.py`

## Validation
- `.\\.venv\\Scripts\\python.exe -m pytest`
- `.\\.venv\\Scripts\\ruff.exe check .`

Closes #129
