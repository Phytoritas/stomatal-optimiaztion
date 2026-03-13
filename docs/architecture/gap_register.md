# Gap Register

| ID | Gap | Impact | Required Artifact |
| --- | --- | --- | --- |

Current open gaps:
- `D-108`: root `TDGM` canonical full-series control rerun still drifts from the legacy MATLAB payload over the full stored horizon even though the fast bounded parity tests pass

Last closed wave:
- slices `101-108` restored direct root Python rerun parity against legacy MATLAB outputs for `THORP`, `GOSM`, and `TDGM`, upgraded the live graph surface to rerun-only Plotkit bundles with explicit `python/legacy/diff` CSV exports, pruned the remaining legacy-only example plotting assets from the repository, and vectorized the THORP/TDGM root-uptake bottleneck so canonical full-series control rerenders complete in practical time
