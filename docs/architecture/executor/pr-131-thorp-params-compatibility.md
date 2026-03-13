## Summary
- broaden `src/stomatal_optimiaztion/domains/thorp/params.py` to preserve the legacy THORP params compatibility surface
- re-export migrated primitive types and add flat `default_params()` coverage for legacy callers
- move the next bounded artifact to a THORP package-level smoke validation note

## Validation
- `.\\.venv\\Scripts\\python.exe -m pytest`
- `.\\.venv\\Scripts\\ruff.exe check .`

Closes #131
