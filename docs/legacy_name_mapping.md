# Legacy Name Mapping

Use this file when migrating from older codebases that used inconsistent naming.

| Legacy name | Canonical name | Why |
|---|---|---|
| `P_soil` | `psi_soil` | Water potential should use the `psi_*` family |
| `P_leaf` | `psi_l` | Keep leaf water potential consistent |
| `P_stem` | `psi_s` | Keep stem water potential consistent |
| `P_rc` | `psi_rc` | Keep root-collar water potential consistent |
| `A_n` | `a_n` | Canonical assimilation variable is lowercase |
| `E_vect` | `e_series` | Series should describe the series, not use `vect` |
| `E` | `e` | Canonical transpiration variable |
| `g_c` | `g_sc` or `g_sw` | Must disambiguate CO2 vs H2O basis |
| `lambda` | `lambda_wue` | Bare `lambda` is too ambiguous |
| `NSC` | `c_nsc` | Make the biological meaning explicit |
| `k` | `k_sw`, `k_root`, `k_stem`, or `k_leaf` | Do not use bare hydraulic conductance |
| `T_air` | `t_air` | Use lowercase snake_case |
| `T_leaf` | `t_leaf` | Use lowercase snake_case |

## Migration rule
When porting an old model:
1. map the legacy name to the canonical concept
2. rename once in a structured refactor
3. update docs and tests together
