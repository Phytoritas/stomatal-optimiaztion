## Why
- The earlier migration wave compared the staged Python repo mainly against the already-porting legacy Python seams.
- The original source of truth for `THORP`, `GOSM`, and `TDGM` is the MATLAB code under `00. Stomatal Optimization`, so architecture completeness now depends on a direct MATLAB-to-Python parity audit.
- The audit should identify which MATLAB files are already covered, which were intentionally replaced by stronger staged surfaces, and which bounded helpers are still missing.

## Scope
- audit original MATLAB source for root `THORP`, `GOSM`, and `TDGM`
- write a review note with per-domain parity findings
- reopen the gap register only for core/runtime helpers that are still missing

## Validation
- verify the audited mapping against current migrated module names and tests
- keep `poetry run pytest` and `poetry run ruff check .` as the repo-level green gate after any follow-on slices

## Comparison target
- `C:\\Users\\yhmoo\\OneDrive\\Phytoritas\\00. Stomatal Optimization\\THORP`
- `C:\\Users\\yhmoo\\OneDrive\\Phytoritas\\00. Stomatal Optimization\\GOSM`
- `C:\\Users\\yhmoo\\OneDrive\\Phytoritas\\00. Stomatal Optimization\\TDGM`
