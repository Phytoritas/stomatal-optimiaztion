## Background
- `slice 028` left the default TOMATO adapter execution path blocked until a migrated `TomatoModel` surface existed inside the staged package.
- This PR lands `slice 029` as a bounded legacy-model surface and updates the architecture spine to point the next seam at `models/tomato_legacy/run.py`.

## Changes
- add a bounded `TomatoModel` compatibility surface with reset-state defaults, forcing-row ingestion, output payload helpers, density updates, and sample forcing generation
- export the migrated TOMATO model seam and update adapter coverage so the default `TomatoLegacyAdapter` path runs without an injected `model_factory`
- add module spec 029 and refresh README, Phytoritas, workspace-audit, system-brief, and gap-register records

## Validation
- `.venv\Scripts\python.exe -m pytest`
- `.venv\Scripts\ruff.exe check .`

## Impact
- default `TomatoLegacyAdapter` and `make_tomato_legacy_model()` execution now work inside the migrated package layout
- deeper partition-policy and runner seams remain explicitly blocked for later slices

## Linked issue
Closes #51
