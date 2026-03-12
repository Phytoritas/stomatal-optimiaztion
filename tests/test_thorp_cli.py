from __future__ import annotations

import runpy

import numpy as np
import pytest

import stomatal_optimiaztion.domains.thorp.cli as cli
from stomatal_optimiaztion.domains.thorp.simulation import SimulationOutputs


def _outputs(t_ts: np.ndarray) -> SimulationOutputs:
    t_ts = np.asarray(t_ts, dtype=float)
    n = t_ts.size
    zeros = np.zeros(n, dtype=float)
    zeros_by_layer = np.zeros((1, n), dtype=float)
    return SimulationOutputs(
        t_ts=t_ts,
        c_nsc_ts=zeros,
        c_l_ts=zeros,
        c_sw_ts=zeros,
        c_hw_ts=zeros,
        c_r_h_by_layer_ts=zeros_by_layer,
        c_r_v_by_layer_ts=zeros_by_layer,
        u_l_ts=zeros,
        u_sw_ts=zeros,
        u_r_h_ts=zeros,
        u_r_v_ts=zeros,
        d_ts=zeros,
        d_hw_ts=zeros,
        h_ts=zeros,
        w_ts=zeros,
        psi_l_ts=zeros,
        psi_s_ts=zeros,
        psi_rc_ts=zeros,
        psi_rc0_ts=zeros,
        psi_soil_by_layer_ts=zeros_by_layer,
        r_abs_ts=zeros,
        e_ts=zeros,
        evap_ts=zeros,
        g_w_ts=zeros,
        a_n_ts=zeros,
        r_d_ts=zeros,
        r_m_ts=zeros,
        u_ts=zeros,
    )


def test_cli_main_dispatches_run_and_prints_summary(monkeypatch, capsys) -> None:
    captures: dict[str, object] = {}

    def fake_run(*, max_steps, save_mat_path, save_mat_callback):
        captures["max_steps"] = max_steps
        captures["save_mat_path"] = save_mat_path
        captures["save_mat_callback"] = save_mat_callback
        return _outputs(np.array([0.0, 6.0], dtype=float))

    monkeypatch.setattr(cli, "run", fake_run)

    result = cli.main(["--max-steps", "7"])

    assert result == 0
    assert captures["max_steps"] == 7
    assert captures["save_mat_path"] is None
    assert captures["save_mat_callback"] is None
    assert "Stored 2 points (last t=6.0 s)." in capsys.readouterr().out


def test_cli_main_wires_full_run_and_mat_save(monkeypatch) -> None:
    captures: dict[str, object] = {}

    def fake_run(*, max_steps, save_mat_path, save_mat_callback):
        captures["max_steps"] = max_steps
        captures["save_mat_path"] = save_mat_path
        captures["save_mat_callback"] = save_mat_callback
        return _outputs(np.array([0.0], dtype=float))

    monkeypatch.setattr(cli, "run", fake_run)

    result = cli.main(["--full", "--save-mat", "result.mat"])

    assert result == 0
    assert captures["max_steps"] is None
    assert captures["save_mat_path"] == "result.mat"
    assert captures["save_mat_callback"] is cli.save_mat


def test_package_main_delegates_to_cli_main(monkeypatch) -> None:
    def fake_main() -> int:
        return 9

    monkeypatch.setattr(cli, "main", fake_main)

    with pytest.raises(SystemExit) as exc_info:
        runpy.run_module("stomatal_optimiaztion.domains.thorp.__main__", run_name="__main__")

    assert exc_info.value.code == 9
