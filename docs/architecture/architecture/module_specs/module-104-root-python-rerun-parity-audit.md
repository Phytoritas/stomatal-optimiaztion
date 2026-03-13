# Module Spec: Slice 104 Root Python Rerun Parity Audit

## Goal

Record a repository-level audit that distinguishes figure/example parity from true rerun parity and confirms which root architectures now compare current Python reruns directly against legacy MATLAB outputs.

## Source

- root `THORP`, `GOSM`, and `TDGM` legacy MATLAB output payloads in `00. Stomatal Optimization`
- migrated runtime surfaces under `src/stomatal_optimiaztion/domains/`
- rerun parity tests added in slices `101-103`

## Target

- `docs/architecture/review/python-rerun-parity-audit-note.md`
- `docs/architecture/gap_register.md`
- `docs/architecture/Phytoritas.md`
- `docs/architecture/01_system_brief.md`
- `README.md`

## Requirements

1. record which root architectures now support direct Python rerun versus legacy MATLAB output comparison
2. record the exact bounded scope of the comparisons:
   - root `THORP` fast regression
   - root `GOSM` control and sensitivity reruns
   - root `TDGM` THORP-G fast regression
3. distinguish default fast validation from opt-in slow validation branches
4. leave the gap register at `none` once the rerun wave is closed

## Non-Goals

- claiming pixel-perfect figure parity
- claiming full-horizon rerun parity for every scenario
- reopening already closed model-kernel or figure-workflow waves

## Validation

1. targeted rerun parity tests must pass
2. repo-wide `pytest` and `ruff` must pass
3. architecture docs must return to monitor mode with no open gaps
