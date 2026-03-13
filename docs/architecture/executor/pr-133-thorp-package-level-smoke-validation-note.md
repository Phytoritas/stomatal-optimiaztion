## Summary
- extend the repo smoke suite to cover the migrated THORP package import surface and restored compatibility wrappers
- add a review note that records the package-level smoke scope and its current limits
- move the next bounded artifact to the second-domain comparison note for shared utility justification

## Validation
- `.\\.venv\\Scripts\\python.exe -m pytest`
- `.\\.venv\\Scripts\\ruff.exe check .`

Closes #133
