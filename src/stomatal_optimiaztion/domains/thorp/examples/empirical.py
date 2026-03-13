from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import re

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[5]
WORKSPACE_ROOT = REPO_ROOT.parents[1]
DEFAULT_LEGACY_THORP_EXAMPLE_DIR = WORKSPACE_ROOT / "00. Stomatal Optimization" / "THORP" / "example" / "THORP_code_forcing_outputs_plotting"
DEFAULT_LEGACY_THORP_SUPPORT_DIR = DEFAULT_LEGACY_THORP_EXAMPLE_DIR / "Simulations_and_additional_code_to_plot"
DEFAULT_MASS_FRACTION_SCRIPT_PATH = DEFAULT_LEGACY_THORP_SUPPORT_DIR / "PLOT_data_2_Mass_Fractions.m"
DEFAULT_ALLOCATION_SCRIPT_PATH = DEFAULT_LEGACY_THORP_SUPPORT_DIR / "PLOT_data_3_Allocation_Fractions.m"


def _parse_matlab_matrix(body: str) -> np.ndarray:
    cleaned = re.sub(r"%.*", "", body).replace("...", " ")
    parsed_rows = [np.fromstring(row.strip().replace(",", " "), sep=" ", dtype=float) for row in cleaned.split(";") if row.strip()]
    widths = [row.size for row in parsed_rows if row.size > 0]
    if not widths:
        return np.empty((0, 0), dtype=float)
    row_width = max(set(widths), key=widths.count)
    flattened: list[np.ndarray] = []
    for row in parsed_rows:
        if row.size == 0:
            continue
        if row.size % row_width != 0:
            raise ValueError(f"Unable to normalize MATLAB matrix row width {row.size} to {row_width}")
        for idx in range(0, row.size, row_width):
            flattened.append(row[idx : idx + row_width])
    return np.vstack(flattened)


def _split_gymnosperm_angiosperm_curve(xy: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    x = xy[:, 0]
    restart_idx = np.where(np.diff(x) == np.min(np.diff(x)))[0][0] + 1
    return xy[:restart_idx], xy[restart_idx:]


@lru_cache(maxsize=1)
def load_mass_fraction_reference_points(
    script_path: Path = DEFAULT_MASS_FRACTION_SCRIPT_PATH,
) -> dict[str, np.ndarray]:
    text = script_path.read_text(encoding="utf-8")
    blocks = re.findall(r"xy\s*=\s*\[(.*?)\];", text, flags=re.DOTALL)
    if len(blocks) < 3:
        raise ValueError(f"Could not extract all empirical xy blocks from {script_path}")
    names = ("rmf", "smf", "lmf")
    return {
        name: _parse_matlab_matrix(block)
        for name, block in zip(names, blocks[:3], strict=True)
    }


def mass_fraction_reference_curves(
    *,
    px: np.ndarray | None = None,
    script_path: Path = DEFAULT_MASS_FRACTION_SCRIPT_PATH,
) -> dict[str, np.ndarray]:
    px = np.asarray(px if px is not None else np.linspace(-2.6, 6.0, 1000), dtype=float)
    xy_blocks = load_mass_fraction_reference_points(script_path)
    outputs: dict[str, np.ndarray] = {"px": px}
    for metric_name, xy in xy_blocks.items():
        gym, ang = _split_gymnosperm_angiosperm_curve(xy)
        p_gym = np.polyfit(gym[:, 0], gym[:, 1], 6)
        p_ang = np.polyfit(ang[:, 0], ang[:, 1], 6)
        y_gym = np.polyval(p_gym, px)
        y_ang = np.polyval(p_ang, px)
        y_all = np.full(px.shape, np.nan, dtype=float)
        positive = (y_gym > 0) & (y_ang > 0)
        y_all[positive] = 10 ** ((np.log10(y_gym[positive]) + np.log10(y_ang[positive])) / 2)
        outputs[f"{metric_name}_gym"] = y_gym
        outputs[f"{metric_name}_ang"] = y_ang
        outputs[f"{metric_name}_all"] = y_all

    sd_log10_ldm = 0.374
    sd_log10_sdm = 0.394
    sd_log10_rdm = 0.0

    lmf_all = outputs["lmf_all"]
    smf_all = outputs["smf_all"]
    rmf_all = outputs["rmf_all"]

    d_lmf_dlog10_ldm = np.log(10) * lmf_all * (1 - lmf_all)
    d_smf_dlog10_sdm = np.log(10) * smf_all * (1 - smf_all)
    d_rmf_dlog10_rdm = np.log(10) * rmf_all * (1 - rmf_all)

    d_lmf_dlog10_rdm = -np.log(10) * lmf_all * rmf_all
    d_lmf_dlog10_sdm = -np.log(10) * lmf_all * smf_all
    d_rmf_dlog10_ldm = -np.log(10) * rmf_all * lmf_all
    d_rmf_dlog10_sdm = -np.log(10) * rmf_all * smf_all
    d_smf_dlog10_ldm = -np.log(10) * smf_all * lmf_all
    d_smf_dlog10_rdm = -np.log(10) * smf_all * rmf_all

    outputs["rmf_sd"] = np.real(
        (
            d_rmf_dlog10_ldm**2 * sd_log10_ldm**2
            + d_rmf_dlog10_sdm**2 * sd_log10_sdm**2
            + d_rmf_dlog10_rdm**2 * sd_log10_rdm**2
        )
        ** 0.5
    )
    outputs["lmf_sd"] = np.real(
        (
            d_lmf_dlog10_ldm**2 * sd_log10_ldm**2
            + d_lmf_dlog10_sdm**2 * sd_log10_sdm**2
            + d_lmf_dlog10_rdm**2 * sd_log10_rdm**2
        )
        ** 0.5
    )
    outputs["smf_sd"] = np.real(
        (
            d_smf_dlog10_ldm**2 * sd_log10_ldm**2
            + d_smf_dlog10_sdm**2 * sd_log10_sdm**2
            + d_smf_dlog10_rdm**2 * sd_log10_rdm**2
        )
        ** 0.5
    )
    return outputs


@lru_cache(maxsize=1)
def load_allocation_reference_data(
    script_path: Path = DEFAULT_ALLOCATION_SCRIPT_PATH,
) -> tuple[np.ndarray, np.ndarray]:
    text = script_path.read_text(encoding="utf-8")
    year_seed_match = re.search(r"year_seed_meas\s*=\s*\[(.*?)\];", text, flags=re.DOTALL)
    alloc_match = re.search(r"u_l_w_fr\s*=\s*\[(.*?)\]\s*/\s*100;", text, flags=re.DOTALL)
    if year_seed_match is None or alloc_match is None:
        raise ValueError(f"Could not extract Xia et al. reference data from {script_path}")
    year_seed_meas = _parse_matlab_matrix(year_seed_match.group(1))
    allocation = _parse_matlab_matrix(alloc_match.group(1)) / 100.0
    return year_seed_meas, allocation


def allocation_reference_curves(
    *,
    xmax: int = 150,
    n_bins: int = 8,
    script_path: Path = DEFAULT_ALLOCATION_SCRIPT_PATH,
) -> dict[str, np.ndarray]:
    year_seed_meas, allocation = load_allocation_reference_data(script_path)
    age = year_seed_meas[:, 1] - year_seed_meas[:, 0]
    u_l = allocation[:, 0]
    u_w = allocation[:, 1]
    u_fr = allocation[:, 2]

    age_bin = np.concatenate([[0.0], (xmax ** (1 / n_bins)) ** np.arange(1, n_bins + 1, dtype=float)])
    age_mid_bin = age_bin[:-1] + np.diff(age_bin)

    conf_leaf = np.full(n_bins, np.nan, dtype=float)
    conf_wood = np.full(n_bins, np.nan, dtype=float)
    conf_fine_root = np.full(n_bins, np.nan, dtype=float)

    for idx in range(n_bins):
        years_begin = age_bin[idx]
        years_end = age_bin[idx + 1]
        if idx == 0:
            selector = age <= years_end
        else:
            selector = (age > years_begin) & (age <= years_end)
        conf_leaf[idx] = np.std(u_l[selector]) / np.sqrt(np.count_nonzero(selector))
        conf_wood[idx] = np.std(u_w[selector]) / np.sqrt(np.count_nonzero(selector))
        conf_fine_root[idx] = np.std(u_fr[selector]) / np.sqrt(np.count_nonzero(selector))

    years = np.arange(1, 321, dtype=float)
    return {
        "years": years,
        "age_mid_bin": age_mid_bin,
        "leaf_combined": (-3.80 * np.log(age_mid_bin) + 38.60) / 100.0,
        "wood_combined": (-8.40 * np.log(age_mid_bin) + 82.28) / 100.0,
        "fine_root_combined": (12.20 * np.log(age_mid_bin) - 20.88) / 100.0,
        "leaf_conf": conf_leaf,
        "wood_conf": conf_wood,
        "fine_root_conf": conf_fine_root,
        "leaf_boreal": (-5.55 * np.log(years) + 44.00) / 100.0,
        "leaf_temperate": (-1.64 * np.log(years) + 32.97) / 100.0,
        "wood_boreal": (-8.08 * np.log(years) + 80.57) / 100.0,
        "wood_temperate": (-8.28 * np.log(years) + 82.10) / 100.0,
        "fine_root_boreal": (13.64 * np.log(years) - 25.56) / 100.0,
        "fine_root_temperate": (9.93 * np.log(years) - 15.07) / 100.0,
    }
