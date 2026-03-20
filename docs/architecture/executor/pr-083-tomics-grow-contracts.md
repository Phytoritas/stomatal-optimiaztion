## Summary
- migrate the bounded TOMATO `tTDGM` contracts seam into the staged repo package
- expose `MODEL_NAME == "tTDGM"` and contract dataclasses through the package import surface
- add seam-level regression tests and update architecture records for slice 044

## Validation
- poetry run pytest
- poetry run ruff check .

## Next Seam
- `TOMATO/tTDGM/src/ttdgm/interface.py`

Closes #83
