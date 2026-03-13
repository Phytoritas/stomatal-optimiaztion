"""Configuration helpers for the load-cell processing pipeline."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping

try:
    import yaml
except ImportError:  # pragma: no cover - yaml should exist but guard anyway
    yaml = None


@dataclass(slots=True)
class PipelineConfig:
    """Container for configurable parameters of the load-cell pipeline."""

    input_path: Path | None = None
    output_path: Path | None = None
    timestamp_column: str = "timestamp"
    weight_column: str = "weight_kg"

    smooth_method: str = "savgol"
    smooth_window_sec: int = 31
    poly_order: int = 2
    k_outlier: float = 10.0
    max_spike_width_sec: int = 2
    derivative_method: str = "central"

    use_auto_thresholds: bool = True
    irrigation_step_threshold_kg: float | None = None
    drainage_step_threshold_kg: float | None = None
    min_pos_events: int = 5
    min_neg_events: int = 5
    k_tail: float = 4.0
    min_factor: float = 3.0
    exclude_interpolated_from_thresholds: bool = True

    use_hysteresis_labels: bool = False
    hysteresis_ratio: float = 0.5

    min_event_duration_sec: int = 2
    merge_irrigation_gap_sec: int | None = None

    interpolate_transpiration_during_events: bool = True
    fix_water_balance: bool = True
    water_balance_scale_min: float = 0.0
    water_balance_scale_max: float | None = 3.0

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON/YAML-friendly dictionary representation."""

        data = asdict(self)
        for key in ("input_path", "output_path"):
            value = data.get(key)
            if isinstance(value, Path):
                data[key] = str(value)
        return data


def load_config(
    path: Path | str | None = None,
    overrides: Mapping[str, Any] | None = None,
) -> PipelineConfig:
    """Load YAML configuration or return defaults when no path is provided."""

    config_data: dict[str, Any] = {}
    if path is not None:
        config_path = Path(path)
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")
        if yaml is None:
            raise RuntimeError(
                "PyYAML is required to load configuration files but is not installed.",
            )
        with config_path.open("r", encoding="utf-8") as handle:
            loaded = yaml.safe_load(handle) or {}
        if not isinstance(loaded, Mapping):
            raise ValueError("Config YAML must define a mapping at the root.")
        config_data.update(loaded)

    if overrides:
        config_data.update(overrides)

    def _coerce_path(value: Any) -> Path | None:
        if value in (None, ""):
            return None
        return Path(value)

    if "input_path" in config_data:
        config_data["input_path"] = _coerce_path(config_data["input_path"])
    if "output_path" in config_data:
        config_data["output_path"] = _coerce_path(config_data["output_path"])

    return PipelineConfig(**config_data)
