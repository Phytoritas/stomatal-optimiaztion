"""Synthetic validation harness for the load-cell processing pipeline."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .cli import run_pipeline
from .config import PipelineConfig


def generate_synthetic_dataset(
    duration_hours: float = 6.0,
    base_weight_kg: float = 100.0,
    transpiration_rate_kg_s: float = 1e-4,
    noise_std: float = 0.01,
) -> tuple[pd.DataFrame, dict[str, float]]:
    """Create a synthetic 1-second weight series with irrigation and drainage pulses."""

    total_seconds = int(duration_hours * 3600)
    time_index = pd.date_range("2024-07-01 06:00:00", periods=total_seconds, freq="1s")
    flux = np.full(total_seconds, -transpiration_rate_kg_s, dtype=float)

    irrigation_pulses = [
        (900, 5, 0.12),
        (3600, 6, 0.15),
        (5400, 5, 0.12),
    ]
    drainage_pulses = [
        (900 + 120, 120, 0.01),
        (3600 + 180, 150, 0.012),
        (5400 + 150, 120, 0.011),
    ]

    total_irrigation = 0.0
    total_drainage = 0.0
    for start, duration, rate in irrigation_pulses:
        flux[start : start + duration] += rate
        total_irrigation += rate * duration
    for start, duration, rate in drainage_pulses:
        flux[start : start + duration] -= rate
        total_drainage += rate * duration

    weight = np.empty(total_seconds)
    weight[0] = base_weight_kg
    for idx in range(1, total_seconds):
        weight[idx] = weight[idx - 1] + flux[idx - 1]

    rng = np.random.default_rng(42)
    noisy_weight = weight + rng.normal(0.0, noise_std, size=total_seconds)

    df = pd.DataFrame({"timestamp": time_index, "weight_kg": noisy_weight})
    truth = {
        "irrigation_kg": total_irrigation,
        "drainage_kg": total_drainage,
        "transpiration_kg": transpiration_rate_kg_s * (total_seconds - 1),
    }
    return df, truth


def run_synthetic_pipeline(tmp_path: Path) -> dict[str, dict[str, float]]:
    """Execute the full pipeline on synthetic data for validation."""

    tmp_path = Path(tmp_path)
    tmp_path.mkdir(parents=True, exist_ok=True)

    data, truth = generate_synthetic_dataset()
    input_path = tmp_path / "synthetic_loadcell.csv"
    data.to_csv(input_path, index=False)

    cfg = PipelineConfig(
        input_path=input_path,
        output_path=tmp_path / "synthetic_results.csv",
        smooth_method="ma",
        smooth_window_sec=14,
        poly_order=2,
        merge_irrigation_gap_sec=60,
    )

    processed_df, _events_df, metadata = run_pipeline(
        cfg,
        include_excel=False,
        write_output=False,
    )

    estimates = {
        "irrigation_kg": float(processed_df["cum_irrigation_kg"].iloc[-1]),
        "drainage_kg": float(processed_df["cum_drainage_kg"].iloc[-1]),
        "transpiration_kg": float(processed_df["cum_transpiration_kg"].iloc[-1]),
    }
    errors = {key: estimates[key] - truth[key] for key in truth}

    tolerances = {
        "irrigation_kg": 0.05,
        "drainage_kg": 0.05,
        "transpiration_kg": 0.02,
    }
    for key, tolerance in tolerances.items():
        if abs(errors[key]) > tolerance:
            raise AssertionError(
                f"{key} estimate deviates by {errors[key]:.4f} kg "
                f"(tolerance {tolerance} kg)."
            )

    final_balance = metadata["stats"]["final_balance_error_kg"]
    if abs(final_balance) > 0.05:
        raise AssertionError(f"Water balance bias too high: {final_balance:.4f} kg")

    print("Synthetic test passed.")
    print("Truth:", truth)
    print("Estimates:", estimates)
    print("Errors:", errors)

    return {
        "truth": truth,
        "estimates": estimates,
        "errors": errors,
    }


def main(output_dir: Path | str = Path("./synthetic_output")) -> int:
    """Run the synthetic validation harness with the legacy default output dir."""

    run_synthetic_pipeline(Path(output_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
