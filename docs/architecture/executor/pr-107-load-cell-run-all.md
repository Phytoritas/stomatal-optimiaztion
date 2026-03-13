## Summary
- migrate the `load-cell-data` end-to-end runner seam into `domains/load_cell/run_all.py`
- preserve package-local parser and orchestration across preprocessing, workflow, and sweep dispatch
- keep raw preprocessing as a lazy or injected dependency until `almemo_preprocess.py` migrates

## Validation
- `.\\.venv\\Scripts\\python.exe -m pytest`
- `.\\.venv\\Scripts\\ruff.exe check .`

Closes #107
