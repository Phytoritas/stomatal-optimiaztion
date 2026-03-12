from __future__ import annotations

import argparse
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

from stomatal_optimiaztion.domains.tomato.tthorp.interface import simulate
from stomatal_optimiaztion.domains.tomato.tthorp.models.tomato_legacy.adapter import (
    TomatoLegacyAdapter,
)
from stomatal_optimiaztion.domains.tomato.tthorp.models.tomato_legacy.forcing_csv import (
    iter_forcing_csv,
)


def _parse_datetime(raw: str) -> datetime:
    try:
        return datetime.fromisoformat(raw)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"Invalid datetime {raw!r}; expected ISO-8601 like '2025-01-01T00:00:00'."
        ) from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Tomato legacy adapter on forcing CSV.")
    parser.add_argument("--input", required=True, help="Input forcing CSV path.")
    parser.add_argument("--output", required=True, help="Output CSV path for model results.")
    parser.add_argument("--max-steps", type=int, default=None, help="Optional max number of forcing rows.")
    parser.add_argument("--fixed-lai", type=float, default=None, help="Optional fixed LAI for single-day runs.")
    parser.add_argument("--default-dt-s", type=float, default=6.0 * 3600.0, help="Fallback timestep seconds.")
    parser.add_argument("--default-co2-ppm", type=float, default=420.0, help="Default CO2 when column is absent.")
    parser.add_argument(
        "--default-n-fruits-per-truss",
        type=int,
        default=4,
        help="Default fruit count when column is absent.",
    )
    parser.add_argument(
        "--start-datetime",
        type=_parse_datetime,
        default=None,
        help="Fallback start datetime when forcing CSV has no datetime column.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)

    forcing = iter_forcing_csv(
        args.input,
        max_steps=args.max_steps,
        start_datetime=args.start_datetime,
        default_dt_s=args.default_dt_s,
        default_co2_ppm=args.default_co2_ppm,
        default_n_fruits_per_truss=args.default_n_fruits_per_truss,
    )
    adapter = TomatoLegacyAdapter(fixed_lai=args.fixed_lai)
    output = simulate(model=adapter, forcing=forcing, max_steps=args.max_steps)

    output_path = Path(args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(output_path, index=False)
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
