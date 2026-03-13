# Module Spec: Slice 096 Legacy Example Parity Audit

## Goal

Reopen the architecture program for legacy MATLAB example and figure workflows after the root model-kernel parity wave closed.

## Source

- `THORP/example/THORP_code_forcing_outputs_plotting/`
- `GOSM/example/`
- `TDGM/example/Supplementary Code __ TDGM Offline Simulations/`
- `TDGM/example/Supplementary Code __THORP_code_v1.4/`

## Target

- `docs/architecture/review/legacy-example-parity-audit-note.md`
- `docs/architecture/gap_register.md`
- `docs/architecture/Phytoritas.md`
- `README.md`

## Requirements

1. separate closed model-kernel parity from still-open example and manuscript figure workflows
2. define a parity rule that allows Plotkit-style publication rendering without requiring MATLAB pixel identity
3. identify the next bounded example gaps for root `GOSM`, `THORP`, and `TDGM`

## Non-Goals

- implement a new figure workflow in this slice
- reopen any already-closed model-kernel helper or runtime gap
- widen into non-example workspace domains

## Validation

1. confirm the legacy example inventory directly against `00. Stomatal Optimization`
2. update the gap register so the next bounded example slice is explicit
3. keep the repository ready for the next code slice that will actually reproduce a legacy figure workflow
