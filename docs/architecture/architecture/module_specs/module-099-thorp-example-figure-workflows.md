# Module Spec: Slice 099 THORP Example Figure Workflows

## Goal

Reproduce the remaining root `THORP` main-text example figure workflows from the original MATLAB example directory with Plotkit-style, spec-first figure bundles.

## Source

- `THORP/example/THORP_code_forcing_outputs_plotting/PLOT_data.m`
- `THORP/example/THORP_code_forcing_outputs_plotting/Simulations_and_additional_code_to_plot/PLOT_data_2_Mass_Fractions.m`
- `THORP/example/THORP_code_forcing_outputs_plotting/Simulations_and_additional_code_to_plot/PLOT_data_3_Allocation_Fractions.m`
- `THORP/example/THORP_code_forcing_outputs_plotting/Simulations_and_additional_code_to_plot/PLOT_data_5_H_Z_LAI_Hv.m`
- `THORP/example/THORP_code_forcing_outputs_plotting/Simulations_and_additional_code_to_plot/PLOT_data_7_Z_and_GWT.m`
- `THORP/example/THORP_code_forcing_outputs_plotting/Simulations_and_additional_code_to_plot/PLOT_data_8_eCO2_and_light.m`
- `THORP/example/THORP_code_forcing_outputs_plotting/Figures/Main Text Figs/FIGURE_2_Control_(H_Z_LAI_etc).jpg`
- `THORP/example/THORP_code_forcing_outputs_plotting/Figures/Main Text Figs/FIGURE_3_Control_and_reduced_Precip_(MF).jpg`
- `THORP/example/THORP_code_forcing_outputs_plotting/Figures/Main Text Figs/FIGURE_4_Control_and_reduced_Precip_(allocation_fractions).jpg`
- `THORP/example/THORP_code_forcing_outputs_plotting/Figures/Main Text Figs/FIGURE_5_GW_(Z_RMF_fraction_E_from_below_2_m).jpg`
- `THORP/example/THORP_code_forcing_outputs_plotting/Figures/Main Text Figs/FIGURE_6_Control_and_eCO2_and_Light_limited_(MF).jpg`

## Target

- `src/stomatal_optimiaztion/domains/thorp/examples/adapter.py`
- `src/stomatal_optimiaztion/domains/thorp/examples/empirical.py`
- `src/stomatal_optimiaztion/domains/thorp/examples/figure_workflows.py`
- `src/stomatal_optimiaztion/domains/thorp/examples/__init__.py`
- `src/stomatal_optimiaztion/shared_plotkit.py`
- `scripts/render_thorp_example_figures.py`
- `configs/plotkit/thorp/mass_fractions.yaml`
- `configs/plotkit/thorp/allocation_fractions.yaml`
- `configs/plotkit/thorp/structural_traits.yaml`
- `configs/plotkit/thorp/groundwater_sweep.yaml`
- `configs/plotkit/thorp/eco2_light_limited_mass_fractions.yaml`
- `tests/test_thorp_example_figures.py`

## Requirements

1. read the real legacy `.mat` example payloads and empirical reference tables directly from the original THORP example directory
2. re-render the five main-text THORP figures as Plotkit-style publication bundles with PNG, PDF, CSV, spec copy, resolved spec, tokens copy, and metadata
3. preserve panel count, panel order, axis-limit semantics, scenario overlays, and empirical/reference overlays from the MATLAB workflows
4. lock numeric parity with fixed frame digests so the metadata can report `passed=true` against the real legacy-derived long-form data
5. allow the second example domain to reuse the same figure-bundle helper contract without reopening a broad generic shared-utility layer

## Non-Goals

- pixel-perfect reproduction of MATLAB fonts, line colors, or renderer defaults
- rebuilding the underlying THORP `.mat` example payloads from the migrated runtime
- moving into root `TDGM` supplementary example workflows in the same slice

## Validation

1. compare each THORP figure frame against fixed digests computed from the real legacy `.mat` payloads and empirical tables
2. render the five real bundles to disk and verify the metadata parity flags plus legacy reference-image links
3. visually spot-check at least the mass-fraction and groundwater-sweep PNGs against the legacy exports
4. keep `pytest` and `ruff` green
