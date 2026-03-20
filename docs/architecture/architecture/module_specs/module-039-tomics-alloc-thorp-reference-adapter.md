# Module Spec 039: TOMATO tTHORP THORP Reference Adapter

## Purpose

Open the next bounded TOMATO `tTHORP` seam by porting the THORP reference adapter that reshapes tabular forcing into THORP runtime inputs and exposes legacy-shaped summary outputs.

## Source Inputs

- `TOMATO/tTHORP/src/tthorp/models/thorp_ref/adapter.py`
- `TOMATO/tTHORP/src/tthorp/models/thorp_ref/__init__.py`

## Target Outputs

- `src/stomatal_optimiaztion/domains/tomato/tomics/alloc/models/thorp_ref/adapter.py`
- `src/stomatal_optimiaztion/domains/tomato/tomics/alloc/models/thorp_ref/__init__.py`
- `tests/test_tomics_alloc_thorp_ref_adapter.py`

## Responsibilities

1. preserve forcing-column normalization, datetime reconstruction, and fallback defaults for THORP reference runs
2. bind the adapter to the migrated `stomatal_optimiaztion.domains.thorp` runtime instead of an external THORP checkout
3. preserve the legacy-shaped output DataFrame with `theta_substrate`, `water_supply_stress`, `e`, `g_w`, `a_n`, and `r_d`

## Non-Goals

- migrate `TOMATO/tTHORP/scripts/plot_simulation_png.py`
- migrate `TOMATO/tTHORP/scripts/plot_allocation_compare_png.py`
- broaden into non-TOMATO reporting or visualization entrypoints

## Validation

- `poetry run pytest`
- `poetry run ruff check .`

## Next Seam

- `TOMATO/tTHORP/scripts/plot_simulation_png.py`
