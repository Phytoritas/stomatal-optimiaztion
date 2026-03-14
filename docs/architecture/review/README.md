# Review Notes

Use this directory for architecture reviews, regression reviews, and change critiques.

Current notes:

- `python-rerun-parity-audit-note.md`: direct Python rerun vs legacy MATLAB payload audit for root `THORP`, `GOSM`, and `TDGM`
- `tdgm-full-series-control-drift-diagnosis-note.md`: bounded diagnosis summary for the first proven root `TDGM` long-horizon control-drift seam and its post-`791.5` handoff
- `tdgm-post-791d-stomata-sensitivity-diagnosis-note.md`: bounded diagnosis summary for the remaining post-`791.5` TDGM drift, including why the next seam is in the THORP-G sensitivity path rather than the mean-allocation filter
- `tdgm-root-sensitivity-zero-point-diagnosis-note.md`: bounded diagnosis summary showing that the remaining post-`791.5` TDGM drift is now narrowed to the root-specific zero-point sensitivity derivatives, with the vertical-root branch most inflated
- `matlab-source-parity-audit-note.md`: original MATLAB source coverage audit for root `THORP`, `GOSM`, and `TDGM`
- `legacy-example-parity-audit-note.md`: legacy example and figure workflow audit after the MATLAB-source parity wave
- `thorp-package-smoke-validation-note.md`: package-level THORP smoke validation summary
- `appendix-equation-coverage-audit-note.md`: paper-appendix coverage check for root `THORP`, `GOSM`, and `TDGM`
