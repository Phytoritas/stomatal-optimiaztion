from __future__ import annotations

from pathlib import Path

import stomatal_optimiaztion.domains.thorp.sim as sim_pkg
import stomatal_optimiaztion.domains.thorp.sim.runner as runner


def test_runner_run_delegates_to_simulation_run(monkeypatch) -> None:
    captures: dict[str, object] = {}
    sentinel = object()

    def fake_run(*, params, forcing, max_steps, save_mat_path):
        captures["params"] = params
        captures["forcing"] = forcing
        captures["max_steps"] = max_steps
        captures["save_mat_path"] = save_mat_path
        return sentinel

    monkeypatch.setattr(runner, "_baseline_run", fake_run)

    params = object()
    forcing = object()
    result = runner.run(
        params=params,  # type: ignore[arg-type]
        forcing=forcing,  # type: ignore[arg-type]
        max_steps=7,
        save_mat_path=Path("out.mat"),
    )

    assert result is sentinel
    assert captures == {
        "params": params,
        "forcing": forcing,
        "max_steps": 7,
        "save_mat_path": Path("out.mat"),
    }


def test_sim_package_reexports_runner_run() -> None:
    assert sim_pkg.run is runner.run
