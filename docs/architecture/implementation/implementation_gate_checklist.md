# Implementation Gate Checklist

Broad implementation is blocked until all required items are checked.

- [x] New scaffolded repo exists
- [x] `Phytoritas.md` exists
- [x] Initial workspace audit exists
- [x] Initial system brief exists
- [x] Starter ADR exists
- [x] Starter module spec exists
- [x] Target repo profile is finalized
- [x] First migration slice is chosen
- [x] Validation commands for the first slice are documented
- [x] Artifact retention and ignore policy are confirmed for migrated content

## Slice 001 Validation Commands

- `poetry run pytest`
- `poetry run ruff check .`

## Artifact Retention Rule

- keep THORP `model_card` JSON files in-package for traceability
- do not copy the source PDF, MATLAB outputs, caches, or generated plots into Git
