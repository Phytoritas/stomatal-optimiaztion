# Module Spec 032: TOMATO tTHORP THORP-Derived Partition Policies

## Purpose

Close the remaining TOMATO `tTHORP` partitioning seam by porting the THORP-backed tomato allocation adapter and policy layer that powers `thorp_veg` and `thorp_fruit_veg`.

## Source Inputs

- `TOMATO/tTHORP/src/tthorp/components/partitioning/thorp_opt.py`
- `TOMATO/tTHORP/src/tthorp/components/partitioning/thorp_policies.py`
- `TOMATO/tTHORP/tests/test_thorp_opt_partitioning.py`
- `TOMATO/tTHORP/tests/test_partition_policy_invariants.py`

## Target Outputs

- `src/stomatal_optimiaztion/domains/tomato/tomics/alloc/components/partitioning/`
- `tests/test_tomics_alloc_partitioning.py`

## Responsibilities

1. provide `ThorpObjectiveParams`, THORP allocation wrappers, and collapsed tomato partition outputs behind a TOMATO-local surface
2. reuse the migrated THORP allocation core while preserving the TOMATO adapter contract for ported versus external THORP backends
3. expose `ThorpVegetativePolicy` and `ThorpFruitVegPolicy` through `build_partition_policy()` alias wiring and keep `TomatoModel` policy execution finite

## Non-Goals

- migrate `TOMATO/tTHORP/src/tthorp/pipelines/tomato_legacy.py`
- migrate `TOMATO/tTHORP/src/tthorp/core/`
- broaden into shared cross-crop partition-policy abstractions

## Validation

- `poetry run pytest`
- `poetry run ruff check .`

## Next Seam

- `TOMATO/tTHORP/src/tthorp/pipelines/tomato_legacy.py`
