# Gap Register

| ID | Gap | Impact | Required Artifact |
| --- | --- | --- | --- |
| G-094 | Root GOSM steady-state inversion helper from the original MATLAB source is still missing | Prevents the staged repo from matching the last remaining core GOSM helper `FUNCTION_Solve_mult_phi_given_assumed_NSC.m` | `docs/architecture/architecture/module_specs/module-094-gosm-steady-state-inversion-helper.md` |
| G-095 | Root TDGM initial mean-allocation helper from the supplementary MATLAB THORP-G code is still missing | Prevents exact reproduction of the THORP-G allocation-memory initialization helper `FUNCTION_Initial_Mean_Allocation_Fractions.m` | `docs/architecture/architecture/module_specs/module-095-tdgm-initial-mean-allocation-helper.md` |

Current open gaps: G-094, G-095.
