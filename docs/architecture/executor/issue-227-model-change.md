## Why
- The migrated tomato surface still exposes `tTHORP`, `tGOSM`, and `tTDGM` as the primary tomato-facing names, even though the repository now needs one canonical umbrella naming layer for tomato-integrated workflows.
- The current tomato partition-policy surface only offers the legacy sink law and raw THORP-derived variants; it lacks a greenhouse-aware hybrid policy that preserves legacy fruit allocation while bounding root corrections and canopy risk.
- Reproducible side-by-side comparison and small screening workflows are missing, so the repository cannot yet validate legacy versus raw THORP versus TOMICS tomato allocation behavior in one deterministic path.

## Affected model
- `TOMICS`
- `TOMICS-Alloc (legacy: tTHORP)`
- `TOMICS-Flux (legacy: tGOSM)`
- `TOMICS-Grow (legacy: tTDGM)`
- tomato-facing docs, scripts, configs, tests, and compatibility aliases

## Validation method
- targeted TOMICS policy, naming migration, comparison runner, and factorial runner tests
- `poetry run pytest`
- `poetry run ruff check .`
- deterministic artifacts under `out/tomics_partition_compare/`, `out/tomics_factorial/`, and `out/tomics_naming_audit/`

## Comparison target
- legacy sink-based tomato partitioning
- raw `thorp_fruit_veg`
- bounded hybrid `tomics`
- historical TOMATO `tTHORP` / `tGOSM` / `tTDGM` provenance records that must remain annotated rather than erased
