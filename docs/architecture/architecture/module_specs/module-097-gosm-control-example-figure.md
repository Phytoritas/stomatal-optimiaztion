# Module Spec: Slice 097 GOSM Control Example Figure

## Goal

Reproduce the root `GOSM` control example workflow from the original MATLAB example directory with a Plotkit-style, spec-first publication figure bundle.

## Source

- `GOSM/example/Growth_Opt_Stomata_plot_example.m`
- `GOSM/example/Example_Growth_Opt__control.mat`
- `GOSM/example/Figures/Example_Growth_Opt__P_soil=0.jpeg`

## Target

- `src/stomatal_optimiaztion/domains/gosm/examples/control_figure.py`
- `scripts/render_gosm_control_example.py`
- `configs/plotkit/gosm/control_example_figure.yaml`
- `configs/plotkit/themes/Phytoritas_tokens.yaml`
- `tests/test_gosm_control_example_figure.py`

## Requirements

1. rebuild the control-example numeric payload from migrated `gosm` kernels rather than replaying legacy plot code
2. validate parity numerically against the legacy `Example_Growth_Opt__control.mat` payload
3. export PNG, PDF, long-form CSV, spec copy, resolved spec, tokens copy, and metadata in one bundle
4. keep the figure style aligned with the Plotkit publication-graph contract

## Non-Goals

- migrate the broader GOSM sensitivity/manuscript figure workflows
- recreate MATLAB typography or exact legacy colors
- widen into root `THORP` or `TDGM` example scripts

## Validation

1. compare regenerated grouped series digests against legacy control digests
2. optionally compare directly against the legacy `.mat` payload and record max absolute deltas
3. keep `pytest` and `ruff` green
