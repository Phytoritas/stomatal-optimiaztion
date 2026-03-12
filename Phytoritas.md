# Phytoritas

Canonical blueprint: [docs/architecture/Phytoritas.md](docs/architecture/Phytoritas.md)

This repository is the scaffold-first refactoring workspace for the legacy source tree at:

`C:\Users\yhmoo\OneDrive\Phytoritas\00. Stomatal Optimization`

Current status:
- Bootstrap complete
- Architecture scaffold seeded
- Target repo shape finalized as a staged single-package domain workspace
- Slices 001-024 migrated: THORP bounded runtime, reporting, config, IO, and CLI seams
- Slices 025-033 migrated: TOMATO `tTHORP` contracts, interface, forcing, adapter, `TomatoModel`, runner, partitioning-package, and package-level legacy pipeline seams
- Next blocked seam: TOMATO `tTHORP` shared IO helpers at `core/io.py`
