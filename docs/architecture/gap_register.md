# Gap Register

| ID | Gap | Impact | Required Artifact |
| --- | --- | --- | --- |

Current open gaps:
- `D-108`: root `TDGM` canonical full-series control rerun still reopens against the legacy MATLAB payload after day `791.5`; module `111` narrows the next likely culprit to the root-specific zero-point derivative branch inside the `THORP-G` sensitivity path, especially `d_psi_rc0_d_c_r_*` and `dk_canopy_max_d_c_r_*`

Last closed wave:
- slices `101-108` restored direct root Python rerun parity against legacy MATLAB outputs for `THORP`, `GOSM`, and `TDGM`, upgraded the live graph surface to rerun-only Plotkit bundles with explicit `python/legacy/diff` CSV exports, pruned the remaining legacy-only example plotting assets from the repository, and vectorized the THORP/TDGM root-uptake bottleneck so canonical full-series control rerenders complete in practical time
