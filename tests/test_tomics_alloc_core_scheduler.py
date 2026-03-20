from __future__ import annotations

import pytest

from stomatal_optimiaztion.domains.tomato.tomics.alloc.core import (
    RunSchedule,
    build_exp_key,
    schedule_from_config,
)


def test_build_exp_key_is_order_insensitive_and_deterministic() -> None:
    payload_a = {
        "pipeline": {"model": "tomato_legacy"},
        "forcing": {"max_steps": 20},
        "exp": {"name": "tomato_dayrun"},
    }
    payload_b = {
        "exp": {"name": "tomato_dayrun"},
        "forcing": {"max_steps": 20},
        "pipeline": {"model": "tomato_legacy"},
    }

    assert build_exp_key(payload_a) == "exp_be493124a1"
    assert build_exp_key(payload_a) == build_exp_key(payload_b)


def test_build_exp_key_respects_prefix_and_digest_size() -> None:
    payload = {"exp": {"name": "demo"}, "forcing": {"max_steps": 3}}

    assert build_exp_key(payload, prefix="run", digest_size=6) == "run_5f28c9"


def test_build_exp_key_supports_non_json_scalars_via_default_str() -> None:
    payload = {"exp": {"name": "demo"}, "path": pytest}

    exp_key = build_exp_key(payload)

    assert exp_key.startswith("exp_")
    assert len(exp_key) == 14


def test_schedule_from_config_returns_defaults_when_forcing_missing() -> None:
    schedule = schedule_from_config({"exp": {"name": "demo"}})

    assert schedule == RunSchedule(max_steps=None, default_dt_s=21600.0)


def test_schedule_from_config_normalizes_mapping_values() -> None:
    schedule = schedule_from_config({"forcing": {"max_steps": "-4", "default_dt_s": "3600"}})

    assert schedule == RunSchedule(max_steps=0, default_dt_s=3600.0)


def test_schedule_from_config_ignores_non_mapping_forcing() -> None:
    schedule = schedule_from_config({"forcing": ["unexpected"]})

    assert schedule == RunSchedule(max_steps=None, default_dt_s=21600.0)


def test_schedule_from_config_rejects_non_positive_default_dt_s() -> None:
    with pytest.raises(ValueError, match="default_dt_s must be > 0"):
        schedule_from_config({"forcing": {"default_dt_s": 0}})
