# TOMICS-HAF 2025-2C Cross-Dataset Gate

Goal 3C runs an explicit HAF cross-dataset gate. The current HAF measured dataset count is expected to be one: `haf_2025_2c`.

The cross-dataset gate records compatible measured datasets separately from diagnostic or proxy datasets. Legacy/public proxy datasets do not contribute to HAF promotion unless they are explicitly validated as compatible measured datasets.

Expected current outcome:

- `cross_dataset_gate_run = true`
- `cross_dataset_gate_passed = false`
- `cross_dataset_gate_status = blocked_insufficient_measured_datasets`
- `measured_dataset_count = 1`
- `required_measured_dataset_count = 2`

Primary command:

```powershell
poetry run python scripts/run_tomics_haf_cross_dataset_gate.py --config configs/exp/tomics_haf_2025_2c_cross_dataset_gate.yaml
```

Primary private outputs are written under:

```text
out/tomics/validation/multi-dataset/haf_2025_2c/
```
