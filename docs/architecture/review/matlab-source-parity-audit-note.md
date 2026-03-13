# MATLAB Source Parity Audit Note

## Purpose

Re-check the migrated root `THORP`, `GOSM`, and `TDGM` packages against the original MATLAB source in `00. Stomatal Optimization`, not just against the already-porting legacy Python seams.

## Scope

- original MATLAB source under:
  - `THORP/example/THORP_code_forcing_outputs_plotting/`
  - `GOSM/example/`
  - `TDGM/example/Supplementary Code __ TDGM Offline Simulations/`
  - `TDGM/example/Supplementary Code __THORP_code_v1.4/`
- current migrated Python surfaces under:
  - `src/stomatal_optimiaztion/domains/thorp/`
  - `src/stomatal_optimiaztion/domains/gosm/`
  - `src/stomatal_optimiaztion/domains/tdgm/`

Out of scope for this audit:
- figure-only `PLOT_*.m` scripts
- manuscript-only sensitivity scripts that do not introduce new model kernels
- generated example data files

## THORP

### Covered runtime and IO surface

| MATLAB source | Current Python surface | Status |
| --- | --- | --- |
| `THORP.m` | `domains/thorp/simulation.py::run` and package CLI | covered |
| `FUNCTION_Radiation.m` | `domains/thorp/radiation.py::radiation` | covered |
| `FUNCTION_E_from_Soil_to_Root_Collar.m` | `domains/thorp/hydraulics.py::e_from_soil_to_root_collar` | covered |
| `FUNCTION_Stomata.m` | `domains/thorp/hydraulics.py::stomata` | covered |
| `FUNCTION_Allocation_Fractions.m` | `domains/thorp/allocation.py::allocation_fractions` | covered |
| `FUNCTION_Growth.m` | `domains/thorp/growth.py::grow` | covered |
| `FUNCTION_Initial_Soil_and_Roots.m` | `domains/thorp/soil_initialization.py::initial_soil_and_roots` | covered |
| `FUNCTION_Richards_Equation.m` | `domains/thorp/soil_dynamics.py::richards_equation` | covered |
| `FUNCTION_Soil_Moisture.m` | `domains/thorp/soil_dynamics.py::soil_moisture` | covered |
| `INPUTS_0_Constants.m` | `domains/thorp/defaults.py`, `domains/thorp/params.py` | covered |
| `INPUTS_1_Initial_Allometry.m` | `domains/thorp/simulation.py::_initial_allometry` | covered |
| `INPUTS_2_Environmental_Conditions.m` + `FUNCTION_Environmental_Conditions.m` | `domains/thorp/forcing.py::load_forcing` | replaced by pre-expanded forcing dataclass |
| `STORE_data.m` + `LOAD_data.m` | `domains/thorp/simulation.py::_Store`, `domains/thorp/matlab_io.py` | covered |

### Example-only scripts left outside the package surface

- `generate_disturbance_file.m`
- `PLOT_data.m`
- `Simulations_and_additional_code_to_plot/PLOT_data_*.m`

### Audit result

No core `THORP` runtime gap was found relative to the original MATLAB source. Remaining MATLAB files are example plotting or data-prep utilities, not missing model kernels.

## GOSM

### Covered runtime surface

| MATLAB source | Current Python surface | Status |
| --- | --- | --- |
| `FUNCTION_Radiation.m` | `domains/gosm/model/radiation.py` | covered |
| `FUNCTION_Hydraulics.m` | `domains/gosm/model/hydraulics.py` | covered |
| `FUNCTION_Conductances_and_Temperature.m` | `domains/gosm/model/conductance_temperature.py` | covered |
| `FUNCTION_CarbonAssimilation.m` | `domains/gosm/model/carbon_assimilation.py` | covered |
| `FUNCTION_Rad_Hydr_Grow_Temp_CAssimilation.m` | `domains/gosm/model/pipeline.py` | covered |
| `FUNCTION_Update_CarbonAssimilation_Growth.m` | `domains/gosm/model/instantaneous.py::update_carbon_assimilation_growth` | covered |
| `FUNCTION_Steadystate_NSC_and_CUE.m` | `domains/gosm/model/steady_state.py::steady_state_nsc_and_cue` | covered |
| `FUNCTION_Stomata_*.m` | `domains/gosm/model/stomata_models.py` | covered |

### Gap found during audit

| MATLAB source | Current Python surface | Status |
| --- | --- | --- |
| `FUNCTION_Solve_mult_phi_given_assumed_NSC.m` | none at audit time | closed later by slice 094 |

### Example-only scripts left outside the package surface

- `Growth_Opt_Stomata.m`
- `Growth_Opt_Stomata_plot_example.m`
- `Growth_Opt_Stomata__test_*.m`
- `PLOT_sensitivity_analyses.m`
- `PLOT_true_vs_imag_conductance_loss.m`
- `Inkscape_figure_plots.m`

### Audit result

The core `GOSM` runtime is almost complete against the original MATLAB source, but one bounded helper seam is still missing: `FUNCTION_Solve_mult_phi_given_assumed_NSC.m`.

## TDGM

### Covered runtime surface

| MATLAB source | Current Python surface | Status |
| --- | --- | --- |
| `FUNCTION_Turgor_driven_growth.m` | `domains/tdgm/turgor_growth.py` | covered |
| `FUNCTION_Phloem_transport.m` + `mu_sucrose.m` | `domains/tdgm/ptm.py` | covered |
| `src/tdgm/coupling.py` | `domains/tdgm/coupling.py` | covered |
| `src/tdgm/equation_registry.py` | `domains/tdgm/equation_registry.py` | covered |
| `src/tdgm/thorp_g_postprocess.py` | `domains/tdgm/thorp_g_postprocess.py` | covered |
| `FUNCTION_Turgor_driven_growth_THORP.m` | `domains/tdgm/turgor_growth.py` + `domains/tdgm/thorp_g_postprocess.py` helpers | replaced by decomposed helpers |
| `FUNCTION_Mean_Allocation_Fractions.m` | `domains/tdgm/coupling.py::allocation_fraction_derivative` and `allocation_fraction_from_history` | replaced by explicit ODE/discrete filter helpers |

### Gap found during audit

| MATLAB source | Current Python surface | Status |
| --- | --- | --- |
| `FUNCTION_Initial_Mean_Allocation_Fractions.m` | none at audit time | closed later by slice 095 |

### Example-only scripts left outside the package surface

- `ANALYSIS_*.m`
- `PLOT_*.m`
- supplementary THORP example plotting scripts under `Simulations_and_code_to_plot/`

### Audit result

The current `TDGM` package covers the model kernels and postprocess bridge, but one small compatibility helper is still missing if exact supplementary THORP-G allocation-memory initialization is required.

## Findings

1. `THORP` core runtime parity is complete; no new bounded code slice is required there.
2. `GOSM` initially lacked `FUNCTION_Solve_mult_phi_given_assumed_NSC.m`, which was a real model helper rather than a plotting script; this was closed by slice 094.
3. `TDGM` initially lacked `FUNCTION_Initial_Mean_Allocation_Fractions.m`, a small initialization helper for the supplementary THORP-G allocation-memory path; this was closed by slice 095.

## Next Actions

1. keep the remaining MATLAB plotting and manuscript scripts explicitly out of scope unless full figure/workflow reproduction becomes a project goal
2. treat the current root `THORP`, `GOSM`, and `TDGM` model-kernel wave as parity-complete
