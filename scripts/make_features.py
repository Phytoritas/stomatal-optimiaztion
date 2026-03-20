#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from stomatal_optimiaztion.domains.tomato.tomics.alloc.core import (  # noqa: E402
    build_exp_key,
    ensure_dir,
    load_config,
    w_m2_to_par_umol,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.pipelines import (  # noqa: E402
    config_payload_for_exp_key,
    resolve_forcing_path,
    resolve_repo_root,
)


def _as_dict(raw: object) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    return {}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build deterministic TOMICS-Alloc forcing features from YAML config.")
    parser.add_argument(
        "--config",
        default="configs/exp/tomics_partition_compare.yaml",
        help="Path to experiment YAML config.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output feature CSV path (default from config and deterministic exp_key).",
    )
    return parser.parse_args()


def _find_sw_column(df: pd.DataFrame) -> str | None:
    for name in ("SW_in_Wm2", "r_incom_w_m2", "r_incom"):
        if name in df.columns:
            return name
    return None


def _resolve_default_output(config: dict[str, Any], repo_root: Path, exp_key: str) -> Path:
    paths_cfg = _as_dict(config.get("paths"))
    features_dir_raw = Path(str(paths_cfg.get("features_dir", "artifacts/tomics_alloc_features")))
    features_dir = (
        features_dir_raw if features_dir_raw.is_absolute() else (repo_root / features_dir_raw).resolve()
    )
    return features_dir / f"{exp_key}.features.csv"


def main() -> int:
    args = _parse_args()

    config_path = Path(args.config).resolve()
    config = load_config(config_path)
    repo_root = resolve_repo_root(config, config_path=config_path)
    forcing_path = resolve_forcing_path(config, repo_root=repo_root, config_path=config_path)
    forcing_cfg = _as_dict(config.get("forcing"))

    df = pd.read_csv(forcing_path)
    max_steps_raw = forcing_cfg.get("max_steps")
    if max_steps_raw is not None:
        df = df.head(max(0, int(max_steps_raw))).copy()
    else:
        df = df.copy()

    sw_col = _find_sw_column(df)
    if "PAR_umol" not in df.columns:
        if sw_col is None:
            df["PAR_umol"] = 0.0
        else:
            sw_series = df[sw_col].astype(float).clip(lower=0.0)
            df["PAR_umol"] = sw_series.map(lambda value: w_m2_to_par_umol(float(value)))

    if "CO2_ppm" not in df.columns:
        df["CO2_ppm"] = float(forcing_cfg.get("default_co2_ppm", 420.0))
    if "n_fruits_per_truss" not in df.columns:
        df["n_fruits_per_truss"] = int(forcing_cfg.get("default_n_fruits_per_truss", 4))

    exp_name = str(_as_dict(config.get("exp")).get("name", "exp"))
    exp_key = build_exp_key(config_payload_for_exp_key(config), prefix=exp_name)
    output_path = Path(args.output) if args.output else _resolve_default_output(config, repo_root, exp_key)
    if not output_path.is_absolute():
        output_path = (repo_root / output_path).resolve()
    ensure_dir(output_path.parent)
    df.to_csv(output_path, index=False)
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
