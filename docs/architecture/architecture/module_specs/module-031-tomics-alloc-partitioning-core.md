# Module Spec 031: TOMATO tTHORP Partitioning Core

## Purpose

Open the next bounded TOMATO `tTHORP` seam by porting the partitioning core that owns organ enums, allocation-fraction validation, policy coercion, and the default sink-based tomato partition rule.

## Source Inputs

- `TOMATO/tTHORP/src/tthorp/components/partitioning/organ.py`
- `TOMATO/tTHORP/src/tthorp/components/partitioning/fractions.py`
- `TOMATO/tTHORP/src/tthorp/components/partitioning/policy.py`
- `TOMATO/tTHORP/src/tthorp/components/partitioning/sink_based.py`

## Target Outputs

- `src/stomatal_optimiaztion/domains/tomato/tomics/alloc/components/partitioning/`
- `src/stomatal_optimiaztion/domains/tomato/tomics/alloc/models/tomato_legacy/tomato_model.py`
- `tests/test_tomics_alloc_partitioning.py`

## Responsibilities

1. preserve `Organ` and `AllocationFractions` validation and scheme-conversion behavior
2. preserve `PartitionPolicy`/`coerce_partition_policy()` and the default sink-based policy aliases
3. replace inline default tomato allocation fallback with the migrated sink-based partitioning core

## Non-Goals

- port THORP-derived tomato partitioning helpers in `thorp_opt.py`
- port THORP-derived tomato policies in `thorp_policies.py`
- broaden into repo-wide shared utilities or non-TOMATO domains

## Validation

- `poetry run pytest`
- `poetry run ruff check .`

## Next Seam

- `TOMATO/tTHORP/src/tthorp/components/partitioning/thorp_opt.py`
