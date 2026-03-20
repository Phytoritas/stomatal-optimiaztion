from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import hashlib
import json
from typing import Any


def build_exp_key(
    payload: Mapping[str, Any],
    *,
    prefix: str = "exp",
    digest_size: int = 10,
) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:digest_size]
    return f"{prefix}_{digest}"


@dataclass(frozen=True, slots=True)
class RunSchedule:
    max_steps: int | None
    default_dt_s: float


def schedule_from_config(config: Mapping[str, Any]) -> RunSchedule:
    forcing_raw = config.get("forcing", {})
    forcing = forcing_raw if isinstance(forcing_raw, Mapping) else {}

    max_steps_raw = forcing.get("max_steps")
    if max_steps_raw is None:
        max_steps: int | None = None
    else:
        max_steps = max(0, int(max_steps_raw))

    default_dt_s = float(forcing.get("default_dt_s", 6.0 * 3600.0))
    if default_dt_s <= 0:
        raise ValueError(f"default_dt_s must be > 0, got {default_dt_s!r}.")
    return RunSchedule(max_steps=max_steps, default_dt_s=default_dt_s)


__all__ = [
    "RunSchedule",
    "build_exp_key",
    "schedule_from_config",
]
