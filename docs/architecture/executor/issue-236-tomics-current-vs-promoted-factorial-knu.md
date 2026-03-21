# Issue 236 Executor Record

## Title

[Validation + Architecture Promotion] Run current vs promoted TOMICS allocation factorial on actual KNU greenhouse data

## Scope

- verify the actual KNU forcing CSV and yield workbook
- add a greenhouse-soilless substrate proxy seam
- replay the merged current TOMICS architecture study on actual data
- add a promoted constrained-marginal allocator family
- compare current vs promoted side-by-side on floor-area basis
- write a promotion decision bundle without changing shipped `tomics`

## Output roots

- `out/knu_longrun/`
- `out/tomics_current_factorial_knu/`
- `out/tomics_promoted_factorial_knu/`
- `out/tomics_current_vs_promoted_knu/`

## Validation commands

1. targeted KNU loader / proxy / promoted allocator tests
2. current TOMICS regression tests
3. `poetry run python scripts/run_tomics_partition_compare.py --config configs/exp/tomics_partition_compare.yaml`
4. `poetry run python scripts/run_tomics_factorial.py --config configs/exp/tomics_factorial.yaml`
5. `poetry run python scripts/run_tomics_current_vs_promoted_factorial.py --config configs/exp/tomics_current_vs_promoted_factorial_knu.yaml --mode both`
6. `poetry run pytest`
7. `poetry run ruff check .`

## Decision

The promoted allocator remains research-only in this issue.

The shipped `partition_policy: tomics` path stays unchanged.

Follow-up note:

- issue `#239` / module `118` replaces the old implicit fruit-mass interpretation with an explicit harvested-yield observation operator and a fair promotion gate.
