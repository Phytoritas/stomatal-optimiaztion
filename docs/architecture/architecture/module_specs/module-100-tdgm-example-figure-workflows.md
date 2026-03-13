# Module Spec: Slice 100 TDGM Example Figure Workflows

## Goal

Close the remaining root `TDGM` supplementary example wave by reproducing both offline-analysis and THORP-G MATLAB figure workflows as Plotkit-style, spec-first figure bundles.

## Source

- `TDGM/example/Supplementary Code __ TDGM Offline Simulations/ANALYSIS_Turgor_driven_growth.m`
- `TDGM/example/Supplementary Code __ TDGM Offline Simulations/ANALYSIS_Max_height_for_soil.m`
- `TDGM/example/Supplementary Code __ TDGM Offline Simulations/ANALYSIS_Phloem_transport_04mtall.m`
- `TDGM/example/Supplementary Code __ TDGM Offline Simulations/ANALYSIS_Phloem_transport_44mtall.m`
- `TDGM/example/Supplementary Code __ TDGM Offline Simulations/PLOT_Poorter_SMF.m`
- `TDGM/example/Supplementary Code __THORP_code_v1.4/Simulations_and_code_to_plot/PLOT_source_vs_sink_G.m`
- `TDGM/example/Supplementary Code __THORP_code_v1.4/Simulations_and_code_to_plot/PLOT_G_versus_C.m`
- `TDGM/example/Supplementary Code __THORP_code_v1.4/Simulations_and_code_to_plot/PLOT_G_versus_C_versus_Precipitation.m`
- `TDGM/example/Supplementary Code __THORP_code_v1.4/Simulations_and_code_to_plot/PLOT_G_versus_C_versus_Soilmoisture.m`
- `TDGM/example/Supplementary Code __THORP_code_v1.4/Simulations_and_code_to_plot/PLOT_G_versus_C_versus_Soilmoisture_detrended.m`
- `TDGM/example/Supplementary Code __THORP_code_v1.4/Simulations_and_code_to_plot/PLOT_S_e_versus_C.m`
- `TDGM/example/Supplementary Code __THORP_code_v1.4/Simulations_and_code_to_plot/PLOT_H_versus_age_turgorthreshold.m`
- `TDGM/example/Supplementary Code __THORP_code_v1.4/Simulations_and_code_to_plot/PLOT_H_versus_age_waterstress.m`
- legacy `.mat` payloads under both example directories

## Target

- `src/stomatal_optimiaztion/domains/tdgm/examples/adapter.py`
- `src/stomatal_optimiaztion/domains/tdgm/examples/figure_workflows.py`
- `src/stomatal_optimiaztion/domains/tdgm/examples/__init__.py`
- `scripts/render_tdgm_example_figures.py`
- `configs/plotkit/tdgm/*.yaml`
- `tests/test_tdgm_example_figures.py`

## Requirements

1. read the real legacy `.mat` payloads and the literature/envelope tables embedded in the original MATLAB scripts directly from the legacy workspace
2. render every remaining root `TDGM` supplementary figure workflow as a Plotkit-style bundle with PNG, PDF, CSV, spec copy, resolved spec, tokens copy, and metadata
3. preserve panel count, panel order, axis-scale semantics, legend semantics, and literature/reference overlays from the MATLAB workflows
4. lock numeric parity with fixed frame digests so every bundle metadata file reports `passed=true`
5. visually spot-check representative THORP-G growth and height figures to confirm the rendered bundle shape matches the legacy script intent even though Plotkit styling replaces MATLAB defaults

## Non-Goals

- pixel-perfect reproduction of MATLAB fonts, marker sizes, or colormap defaults
- rerunning the original MATLAB simulations or regenerating legacy `.mat` payloads
- broadening `shared_plotkit.py` beyond the figure-bundle contract already justified by the multi-domain example wave

## Validation

1. keep `tests/test_tdgm_example_figures.py` green for frame coverage and suite rendering
2. render the complete TDGM example suite to `out/tdgm/example_figures`
3. verify fixed digest parity for every bundle in the emitted metadata
4. visually spot-check representative PNGs for:
   - THORP-G growth-versus-carbon panels
   - THORP-G height-versus-age figure(s)
   - THORP-G soil-moisture-versus-carbon regression panels
5. keep repo-wide `pytest` and `ruff` green
