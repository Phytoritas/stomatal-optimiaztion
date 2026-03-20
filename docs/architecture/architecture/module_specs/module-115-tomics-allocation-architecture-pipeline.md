# Module Spec 115: TOMICS Allocation Architecture Pipeline

## Purpose

Land the next bounded TOMICS-Alloc slice by adding source-traceable research seams, a staged architecture factorial runner, and architecture review records while keeping the shipped `tomics` default stable.

## Source Inputs

- `docs/references/source_papers/`
- `docs/architecture/review/equation_manifest.md`
- `docs/architecture/review/source_manifest.csv`
- `docs/architecture/review/source_traceability.md`
- live TOMICS allocation code under `src/stomatal_optimiaztion/domains/tomato/tomics/alloc/`

## Target Outputs

- research-only allocation helper modules under `src/stomatal_optimiaztion/domains/tomato/tomics/alloc/components/partitioning/`
- `scripts/run_tomics_allocation_factorial.py`
- `configs/exp/tomics_allocation_factorial.yaml`
- architecture review docs and study outputs under `docs/architecture/` and `out/tomics_allocation_factorial/`

## Responsibilities

1. preserve shipped `partition_policy: tomics` semantics
2. add opt-in architecture variants only behind research policy keys
3. trace every screened mechanism to a local source equation or explicit algorithm reference
4. use Kuijpers common structure as the study scaffold
5. rank research candidates without forcing a destructive refactor

## Non-Goals

- redoing the TOMICS naming migration
- reintroducing old tomato runtime imports
- promoting THORP into a master tomato allocator
- silently changing the shipped default path

## Validation

- targeted architecture-study tests
- current TOMICS regressions
- compare runner replay
- existing TOMICS factorial replay
- new architecture factorial run
- `poetry run pytest`
- `poetry run ruff check .`

## Next Seam

- only reopen after architecture-study review if one research candidate is ready for calibration-grade promotion into the shipped default
