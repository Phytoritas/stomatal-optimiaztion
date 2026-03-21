#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation import (  # noqa: E402
    apply_theta_substrate_proxy,
    load_knu_validation_data,
    resample_forcing,
    theta_proxy_summary,
    write_knu_manifest,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prepare KNU long-run validation manifests and proxy forcing bundles.")
    parser.add_argument("--forcing-path", default=str(PROJECT_ROOT / "data" / "forcing" / "KNU_Tomato_Env.CSV"))
    parser.add_argument(
        "--yield-path",
        default=str(PROJECT_ROOT / "data" / "forcing" / "tomato_validation_data_yield_260321.xlsx"),
    )
    parser.add_argument("--output-root", default=str(PROJECT_ROOT / "out" / "knu_longrun"))
    parser.add_argument("--resample-rule", default="1h")
    parser.add_argument("--theta-mode", default="bucket_irrigated")
    parser.add_argument("--scenarios", nargs="+", default=["dry", "moderate", "wet"])
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    output_root = Path(args.output_root).resolve()
    prepared_dir = output_root / "prepared_forcing"
    prepared_dir.mkdir(parents=True, exist_ok=True)

    data = load_knu_validation_data(forcing_path=args.forcing_path, yield_path=args.yield_path)
    manifest_summary = write_knu_manifest(
        output_root=output_root,
        forcing_df=data.forcing_df,
        yield_df=data.yield_df,
        measured_column=data.measured_column,
        estimated_column=data.estimated_column,
        observation_unit_label=data.observation_unit_label,
        forcing_source_path=Path(args.forcing_path),
        yield_source_path=Path(args.yield_path),
        resample_rule=args.resample_rule,
    )

    proxy_paths: dict[str, str] = {}
    proxy_summaries: dict[str, dict[str, object]] = {}
    for scenario in args.scenarios:
        minute_proxy = apply_theta_substrate_proxy(
            data.forcing_df,
            mode=args.theta_mode,
            scenario=scenario,
        )
        hourly_proxy = resample_forcing(minute_proxy, freq=args.resample_rule)
        output_path = prepared_dir / f"knu_longrun_{args.theta_mode}_{scenario}_{args.resample_rule.replace('/', '_')}.csv"
        hourly_proxy.to_csv(output_path, index=False)
        proxy_paths[scenario] = str(output_path)
        proxy_summaries[scenario] = theta_proxy_summary(minute_proxy)

    summary = {
        **manifest_summary,
        "prepared_forcing": proxy_paths,
        "theta_proxy_summaries": proxy_summaries,
    }
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
