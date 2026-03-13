# Module Spec: Slice 106 Root Rerun Parity Graph Bundles

## Goal

Make root `THORP`, `GOSM`, and `TDGM` rerun parity directly inspectable through Plotkit-style publication graph bundles, not only through pytest assertions.

## Source

- root rerun parity slices `101-105`
- legacy MATLAB output payloads under `C:\Users\yhmoo\OneDrive\Phytoritas\00. Stomatal Optimization`
- existing Plotkit-style example renderer contracts already used by root `THORP`, `GOSM`, and `TDGM`

## Target

- `configs/plotkit/thorp/rerun_parity.yaml`
- `configs/plotkit/gosm/control_rerun_parity.yaml`
- `configs/plotkit/gosm/sensitivity_rerun_parity.yaml`
- `configs/plotkit/tdgm/rerun_parity_case.yaml`
- `src/stomatal_optimiaztion/domains/thorp/examples/rerun_parity.py`
- `src/stomatal_optimiaztion/domains/gosm/examples/rerun_parity.py`
- `src/stomatal_optimiaztion/domains/tdgm/examples/rerun_parity.py`
- `scripts/render_root_rerun_parity_figures.py`
- `tests/test_root_rerun_parity_figures.py`
- `docs/architecture/review/python-rerun-parity-audit-note.md`

## Requirements

1. render reproducible PNG comparison graphs with paired data CSV exports for each rerun parity case
2. overlay Python rerun outputs against the corresponding legacy MATLAB payload for each root architecture
3. keep the graph workflow compatible with the existing root rerun tests and bounded fast validation scope
4. expose one repo-level script that writes comparison outputs under `out/rerun_parity/`

## Non-Goals

- pixel-matching the original MATLAB figures
- rerunning MATLAB itself
- widening the closed root rerun wave into a new long-horizon benchmark program

## Validation

1. representative THORP, GOSM, and TDGM parity bundles must render in pytest
2. the repo-level graph-render script must run from a clean checkout
3. repo-wide `pytest` and `ruff` must pass
