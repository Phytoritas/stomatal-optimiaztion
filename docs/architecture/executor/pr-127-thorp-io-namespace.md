## Summary
- migrate the legacy THORP `io` namespace wrapper into `src/stomatal_optimiaztion/domains/thorp/io/__init__.py`
- preserve grouped imports for forcing and MATLAB I/O helpers without redefining them
- move the next bounded THORP namespace-wrapper seam to `THORP/src/thorp/model/__init__.py`

## Validation
- `.\\.venv\\Scripts\\python.exe -m pytest`
- `.\\.venv\\Scripts\\ruff.exe check .`

Closes #127
