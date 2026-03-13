# Phytoritas

Canonical blueprint: [docs/architecture/Phytoritas.md](docs/architecture/Phytoritas.md)

This repository is the scaffold-first refactoring workspace for the legacy source tree at:

`C:\Users\yhmoo\OneDrive\Phytoritas\00. Stomatal Optimization`

Current status:
- Bootstrap complete
- Architecture scaffold seeded
- Target repo shape finalized as a staged single-package domain workspace
- Slices 001-024 migrated: THORP bounded runtime, reporting, config, IO, and CLI seams
- Slices 025-045 migrated: TOMATO `tTHORP` contracts, interface, forcing, adapters, `TomatoModel`, runner, partitioning-package, package-level legacy pipeline, shared IO, shared scheduler, dayrun pipeline, repo-level scripts, feature-builder script, THORP reference adapter, plotting seams, `tGOSM` contract/interface seams, and `tTDGM` contract/interface seams
- Slice 046 migrated: `load-cell-data` config seam
- Slice 047 migrated: `load-cell-data` IO seam
- Slice 048 migrated: `load-cell-data` aggregation seam
- Slice 049 migrated: `load-cell-data` threshold-detection seam
- Slice 050 migrated: `load-cell-data` preprocessing seam
- Slice 051 migrated: `load-cell-data` event-detection seam
- Slice 052 migrated: `load-cell-data` flux-decomposition seam
- Slice 053 migrated: `load-cell-data` pipeline CLI seam
- Slice 054 migrated: `load-cell-data` workflow seam
- Slice 055 migrated: `load-cell-data` sweep seam
- Slice 056 migrated: `load-cell-data` end-to-end runner seam
- Next blocked seam: `load-cell-data` raw preprocessing seam at `loadcell_pipeline/almemo_preprocess.py`
