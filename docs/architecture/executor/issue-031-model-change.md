## Why
- `slice 030` landed the TOMATO runner seam, so the next smallest unresolved architecture gap is the partitioning core that should own organ enums, allocation-fraction validation, policy coercion, and the default sink-based partition rule.
- The migrated `TomatoModel` currently falls back to inline allocation logic; this should be replaced by a bounded package-local partitioning seam before any THORP-derived tomato policies are considered.

## Affected model
- `TOMATO tTHORP`
- `src/stomatal_optimiaztion/domains/tomato/tthorp/components/partitioning/`
- related TOMATO `TomatoModel` and adapter integration tests

## Validation method
- `poetry run pytest`
- `poetry run ruff check .`
- add partition-scheme conversion, sink-based invariant, and default policy wiring tests

## Comparison target
- legacy `TOMATO/tTHORP/src/tthorp/components/partitioning/{organ.py,fractions.py,policy.py,sink_based.py}`
- current migrated `TomatoModel` fallback allocation behavior
