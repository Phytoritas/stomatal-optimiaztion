# Gap Register

| ID | Gap | Impact | Required Artifact |
| --- | --- | --- | --- |

Current open gaps:
- none

Last closed wave:
- slices `101-108` restored direct root Python rerun parity against legacy MATLAB outputs for `THORP`, `GOSM`, and `TDGM`, upgraded the live graph surface to rerun-only Plotkit bundles with explicit `python/legacy/diff` CSV exports, pruned the remaining legacy-only example plotting assets from the repository, and vectorized the THORP/TDGM root-uptake bottleneck so canonical full-series control rerenders complete in practical time
- `D-108` is closed by `docs/architecture/review/tdgm-reference-payload-resume-provenance-note.md`: continuous root `TDGM` parity remains exact through day `784.5`, and the shipped post-day-`791.5` control reopening is explained by a one-off MATLAB resume from the last weekly checkpoint after the day-`787` file save
