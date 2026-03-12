# Phytoritas

Canonical blueprint: [docs/architecture/Phytoritas.md](docs/architecture/Phytoritas.md)

This repository is the scaffold-first refactoring workspace for the legacy source tree at:

`C:\Users\yhmoo\OneDrive\Phytoritas\00. Stomatal Optimization`

Current status:
- Bootstrap complete
- Architecture scaffold seeded
- Target repo shape finalized as a staged single-package domain workspace
- Slices 001-024 migrated: THORP bounded runtime, reporting, config, IO, and CLI seams
- Slices 025-035 migrated: TOMATO `tTHORP` contracts, interface, forcing, adapter, `TomatoModel`, runner, partitioning-package, package-level legacy pipeline, shared IO, and shared scheduler seams
- Next blocked seam: TOMATO `tTHORP` dayrun pipeline at `pipelines/tomato_dayrun.py`
