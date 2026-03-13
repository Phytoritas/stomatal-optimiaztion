# GOSM Control Example Parity Note

## Purpose

Record the first bounded example-parity evidence packet after the legacy example audit reopened workflow reproduction.

## Legacy Reference

- MATLAB script: `GOSM/example/Growth_Opt_Stomata_plot_example.m`
- control payload: `GOSM/example/Example_Growth_Opt__control.mat`
- control export: `GOSM/example/Figures/Example_Growth_Opt__P_soil=0.jpeg`

## Current Reproduction

- payload builder: `src/stomatal_optimiaztion/domains/gosm/examples/control_figure.py`
- repo-level renderer: `scripts/render_gosm_control_example.py`
- Plotkit-style spec: `configs/plotkit/gosm/control_example_figure.yaml`
- Plotkit-style tokens: `configs/plotkit/themes/nature_plants_like_tokens.yaml`
- output bundle:
  - `out/gosm/control_example/gosm_control_example_figure.png`
  - `out/gosm/control_example/gosm_control_example_figure.pdf`
  - `out/gosm/control_example/gosm_control_example_figure_data.csv`
  - `out/gosm/control_example/gosm_control_example_figure_spec.yaml`
  - `out/gosm/control_example/gosm_control_example_figure_resolved_spec.yaml`
  - `out/gosm/control_example/gosm_control_example_figure_tokens.yaml`
  - `out/gosm/control_example/gosm_control_example_figure_metadata.json`

## Parity Results

- legacy digest summary: all grouped control-series digests matched
- direct `.mat` comparison:
  - `g_c_vec` max absolute difference: `7.549516567451064e-15`
  - `panel_a_left` max absolute difference: `1.809041805245215e-11`
  - `panel_a_right` max absolute difference: `1.1287738743703812e-07`
  - `panel_b_left` max absolute difference: `5.861977570020827e-14`
  - `panel_c_left` max absolute difference: `5.684341886080802e-14`
  - `panel_c_right` max absolute difference: `6.661338147750939e-15`
  - `panel_d_left` max absolute difference: `5.964118088286341e-13`

## Interpretation

The current Python control-example workflow reproduces the legacy MATLAB control payload within negligible numerical error. The new figure is intentionally not pixel-identical because it uses Plotkit-style publication tokens, but the plotted series, panel contracts, axis contracts, and export bundle are parity-complete for the bounded control-example slice.
