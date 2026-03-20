# Module Spec 114: TOMICS Tomato Partitioning And Naming

## Purpose

Land one bounded tomato-facing slice that adds the canonical TOMICS naming layer, introduces a greenhouse-aware `tomics` hybrid partition policy on top of the existing tomato legacy pipeline, and ships deterministic comparison plus factorial runner workflows.

## Source Inputs

- `src/stomatal_optimiaztion/domains/tomato/tomics/alloc/components/partitioning/`
- `src/stomatal_optimiaztion/domains/tomato/tomics/alloc/models/tomato_legacy/`
- `src/stomatal_optimiaztion/domains/tomato/tomics/alloc/pipelines/`
- `src/stomatal_optimiaztion/domains/tomato/__init__.py` for the canonical TOMICS-only tomato namespace after physical `tthorp/tgosm/ttdgm` folder removal
- existing tomato-facing docs, scripts, tests, and public namespace exports

## Target Outputs

- `src/stomatal_optimiaztion/domains/tomato/tomics/`
- `src/stomatal_optimiaztion/domains/tomato/tomics/alloc/components/partitioning/tomics_policy.py`
- tomato-facing docs, configs, scripts, and tests updated with TOMICS mapping notes and retired runtime imports
- deterministic audit and comparison artifacts under `out/`

## Responsibilities

1. add `TOMICS`, `TOMICS-Alloc`, `TOMICS-Flux`, and `TOMICS-Grow` as the canonical tomato-facing naming layer while preserving legacy `tTHORP`, `tGOSM`, and `tTDGM` only in provenance records
2. keep `partition_policy` injection on the existing tomato legacy pipeline path and add a bounded `tomics` hybrid policy rather than a new model type
3. preserve the legacy sink law for fruit allocation, apply THORP-derived information only as a bounded vegetative/root correction, and guard leaf/stem allocation against canopy collapse
4. add deterministic comparison and screening runners plus tests and docs that make the new policy auditable

## Non-Goals

- rename root-domain `THORP`, `GOSM`, or `TDGM` provenance and generic packages into TOMICS
- erase historical `TOMATO/tTHORP`, `TOMATO/tGOSM`, or `TOMATO/tTDGM` wording from archive-style architecture records
- introduce a new tomato runtime model type outside the current `tomato_legacy` pipeline path

## Validation

- `poetry run pytest`
- `poetry run ruff check .`

## Next Seam

- re-open only if TOMICS naming or policy integration reveals a new bounded validation gap after the deterministic comparison/factorial workflows land
