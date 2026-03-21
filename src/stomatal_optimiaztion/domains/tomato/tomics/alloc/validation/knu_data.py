from __future__ import annotations

import json
import re
import zipfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

FORCING_REQUIRED_COLUMNS = (
    "datetime",
    "T_air_C",
    "PAR_umol",
    "CO2_ppm",
    "RH_percent",
    "wind_speed_ms",
)
PLANTS_PER_M2 = 1.836091
_XLSX_NS = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
_EXCEL_DATE_STYLE_IDS = {14, 15, 16, 17, 22, 27, 30, 36, 45, 46, 47, 50, 57}


@dataclass(frozen=True, slots=True)
class KnuValidationData:
    forcing_df: pd.DataFrame
    yield_df: pd.DataFrame
    forcing_summary: dict[str, Any]
    yield_summary: dict[str, Any]
    observation_unit_label: str
    measured_column: str
    estimated_column: str


def _finite_float_series(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").astype(float)


def read_knu_forcing_csv(path: str | Path) -> pd.DataFrame:
    forcing_path = Path(path)
    df = pd.read_csv(forcing_path)
    missing = [column for column in FORCING_REQUIRED_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError(f"KNU forcing CSV is missing required columns: {missing}")

    out = df.copy()
    out["datetime"] = pd.to_datetime(out["datetime"], errors="coerce")
    if out["datetime"].isna().any():
        raise ValueError("KNU forcing CSV contains unparsable datetime values.")
    out = out.sort_values("datetime").reset_index(drop=True)
    for column in FORCING_REQUIRED_COLUMNS[1:]:
        out[column] = _finite_float_series(out[column])
    return out


def _col_to_idx(ref: str) -> int:
    match = re.match(r"([A-Z]+)", ref)
    if match is None:
        raise ValueError(f"Unsupported Excel cell reference: {ref!r}")
    idx = 0
    for char in match.group(1):
        idx = idx * 26 + (ord(char) - 64)
    return idx - 1


def _excel_date_to_datetime(value: float) -> datetime:
    return datetime(1899, 12, 30) + timedelta(days=float(value))


def _xlsx_shared_strings(zf: zipfile.ZipFile) -> list[str]:
    try:
        root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
    except KeyError:
        return []
    values: list[str] = []
    for si in root.findall("x:si", _XLSX_NS):
        values.append("".join(node.text or "" for node in si.iterfind(".//x:t", _XLSX_NS)))
    return values


def _xlsx_num_format_lookup(zf: zipfile.ZipFile) -> tuple[dict[int, str], list[int]]:
    root = ET.fromstring(zf.read("xl/styles.xml"))
    num_formats: dict[int, str] = {}
    numfmts_node = root.find("x:numFmts", _XLSX_NS)
    if numfmts_node is not None:
        for fmt in numfmts_node.findall("x:numFmt", _XLSX_NS):
            num_formats[int(fmt.attrib["numFmtId"])] = fmt.attrib.get("formatCode", "")
    cell_xfs: list[int] = []
    cellxfs_node = root.find("x:cellXfs", _XLSX_NS)
    if cellxfs_node is not None:
        for xf in cellxfs_node.findall("x:xf", _XLSX_NS):
            cell_xfs.append(int(xf.attrib.get("numFmtId", "0")))
    return num_formats, cell_xfs


def _parse_xlsx_cell(
    cell: ET.Element,
    *,
    shared_strings: list[str],
    num_formats: dict[int, str],
    cell_xfs: list[int],
) -> Any:
    cell_type = cell.attrib.get("t")
    style_idx = int(cell.attrib.get("s", "0"))
    value_node = cell.find("x:v", _XLSX_NS)
    text = value_node.text if value_node is not None else None
    if text is None:
        inline = cell.find("x:is/x:t", _XLSX_NS)
        return inline.text if inline is not None else None
    if cell_type == "s":
        return shared_strings[int(text)]
    if cell_type == "b":
        return text == "1"
    if cell_type == "str":
        return text
    try:
        numeric = float(text)
    except ValueError:
        return text
    num_fmt_id = cell_xfs[style_idx] if style_idx < len(cell_xfs) else 0
    fmt = num_formats.get(num_fmt_id, "")
    if num_fmt_id in _EXCEL_DATE_STYLE_IDS or any(token in fmt.lower() for token in ("yy", "mm", "dd", "h", "s")):
        return _excel_date_to_datetime(numeric)
    if numeric.is_integer():
        return int(numeric)
    return numeric


def _first_sheet_rows_from_xlsx(path: Path) -> list[dict[int, Any]]:
    with zipfile.ZipFile(path) as zf:
        shared_strings = _xlsx_shared_strings(zf)
        num_formats, cell_xfs = _xlsx_num_format_lookup(zf)
        sheet = ET.fromstring(zf.read("xl/worksheets/sheet1.xml"))
        rows: list[dict[int, Any]] = []
        for row in sheet.findall(".//x:sheetData/x:row", _XLSX_NS):
            parsed_row: dict[int, Any] = {}
            for cell in row.findall("x:c", _XLSX_NS):
                col_idx = _col_to_idx(cell.attrib["r"])
                parsed_row[col_idx] = _parse_xlsx_cell(
                    cell,
                    shared_strings=shared_strings,
                    num_formats=num_formats,
                    cell_xfs=cell_xfs,
                )
            rows.append(parsed_row)
    return rows


def read_knu_yield_workbook(path: str | Path) -> tuple[pd.DataFrame, str, str, str]:
    workbook_path = Path(path)
    rows = _first_sheet_rows_from_xlsx(workbook_path)
    if not rows:
        raise ValueError("KNU yield workbook is empty.")

    header_map = rows[0]
    max_header_idx = max(header_map) if header_map else -1
    headers = [header_map.get(idx) for idx in range(max_header_idx + 1)]
    if len(headers) < 3:
        raise ValueError(f"KNU yield workbook has too few header columns: {headers!r}")

    date_col = str(headers[0])
    measured_col = str(headers[1])
    estimated_col = str(headers[2])

    records: list[dict[str, Any]] = []
    for raw_row in rows[1:]:
        date_value = raw_row.get(0)
        if not isinstance(date_value, datetime):
            continue
        records.append(
            {
                date_col: pd.Timestamp(date_value).normalize(),
                measured_col: raw_row.get(1),
                estimated_col: raw_row.get(2),
            }
        )

    if not records:
        raise ValueError("KNU yield workbook did not contain any daily observation rows.")

    df = pd.DataFrame.from_records(records)
    df[measured_col] = _finite_float_series(df[measured_col])
    df[estimated_col] = _finite_float_series(df[estimated_col])
    unit_label = measured_col[measured_col.find("(") + 1 : measured_col.rfind(")")] if "(" in measured_col and ")" in measured_col else measured_col
    return df, unit_label, measured_col, estimated_col


def forcing_summary(forcing_df: pd.DataFrame) -> dict[str, Any]:
    dt = forcing_df["datetime"].diff().dropna()
    resolution_s = float(dt.dt.total_seconds().mode().iloc[0]) if not dt.empty else 0.0
    return {
        "rows": int(forcing_df.shape[0]),
        "start": forcing_df["datetime"].min().isoformat(),
        "end": forcing_df["datetime"].max().isoformat(),
        "resolution_seconds_mode": resolution_s,
        "columns": list(forcing_df.columns),
    }


def yield_summary(yield_df: pd.DataFrame, *, measured_column: str, estimated_column: str) -> dict[str, Any]:
    return {
        "rows": int(yield_df.shape[0]),
        "start": pd.Timestamp(yield_df.iloc[0, 0]).isoformat(),
        "end": pd.Timestamp(yield_df.iloc[-1, 0]).isoformat(),
        "measured_start": float(yield_df[measured_column].iloc[0]),
        "measured_end": float(yield_df[measured_column].iloc[-1]),
        "estimated_start": float(yield_df[estimated_column].iloc[0]),
        "estimated_end": float(yield_df[estimated_column].iloc[-1]),
    }


def resample_forcing(
    forcing_df: pd.DataFrame,
    *,
    freq: str,
    extra_last_columns: list[str] | None = None,
) -> pd.DataFrame:
    work = forcing_df.copy()
    work = work.set_index("datetime")
    protected_last_columns = {"theta_substrate", "rootzone_multistress", "rootzone_saturation"}
    mean_columns = [
        column
        for column in work.columns
        if column not in protected_last_columns and pd.api.types.is_numeric_dtype(work[column])
    ]
    resampled = work[mean_columns].resample(freq).mean()
    for column in extra_last_columns or [
        "theta_substrate",
        "rootzone_multistress",
        "rootzone_saturation",
        "theta_proxy_mode",
        "theta_proxy_scenario",
        "irrigation_recharge_flag",
    ]:
        if column in work.columns:
            resampled[column] = work[column].resample(freq).last()
    resampled = resampled.dropna(subset=["T_air_C", "PAR_umol", "CO2_ppm", "RH_percent", "wind_speed_ms"], how="any")
    return resampled.reset_index()


def write_knu_manifest(
    *,
    output_root: Path,
    forcing_df: pd.DataFrame,
    yield_df: pd.DataFrame,
    measured_column: str,
    estimated_column: str,
    observation_unit_label: str,
    forcing_source_path: Path,
    yield_source_path: Path,
    resample_rule: str,
) -> dict[str, str]:
    output_root.mkdir(parents=True, exist_ok=True)
    forcing_summary_path = output_root / "forcing_summary.csv"
    yield_summary_path = output_root / "yield_summary.csv"
    manifest_path = output_root / "manifest.json"

    forcing_daily = forcing_df.copy()
    forcing_daily["date"] = pd.to_datetime(forcing_daily["datetime"]).dt.normalize()
    forcing_summary_df = (
        forcing_daily.groupby("date", as_index=False)
        .agg(
            T_air_C_mean=("T_air_C", "mean"),
            PAR_umol_mean=("PAR_umol", "mean"),
            CO2_ppm_mean=("CO2_ppm", "mean"),
            RH_percent_mean=("RH_percent", "mean"),
            wind_speed_ms_mean=("wind_speed_ms", "mean"),
        )
    )
    forcing_summary_df.to_csv(forcing_summary_path, index=False)
    yield_df.to_csv(yield_summary_path, index=False)

    manifest = {
        "forcing_source_path": str(forcing_source_path.resolve()),
        "yield_source_path": str(yield_source_path.resolve()),
        "resample_rule": resample_rule,
        "reporting_basis": "floor_area",
        "plants_per_m2": PLANTS_PER_M2,
        "observation_unit_label": observation_unit_label,
        "forcing_summary": forcing_summary(forcing_df),
        "yield_summary": yield_summary(
            yield_df,
            measured_column=measured_column,
            estimated_column=estimated_column,
        ),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return {
        "manifest_json": str(manifest_path),
        "forcing_summary_csv": str(forcing_summary_path),
        "yield_summary_csv": str(yield_summary_path),
    }


def load_knu_validation_data(
    *,
    forcing_path: str | Path,
    yield_path: str | Path,
) -> KnuValidationData:
    forcing_df = read_knu_forcing_csv(forcing_path)
    yield_df, observation_unit_label, measured_column, estimated_column = read_knu_yield_workbook(yield_path)
    return KnuValidationData(
        forcing_df=forcing_df,
        yield_df=yield_df,
        forcing_summary=forcing_summary(forcing_df),
        yield_summary=yield_summary(
            yield_df,
            measured_column=measured_column,
            estimated_column=estimated_column,
        ),
        observation_unit_label=observation_unit_label,
        measured_column=measured_column,
        estimated_column=estimated_column,
    )


__all__ = [
    "FORCING_REQUIRED_COLUMNS",
    "KnuValidationData",
    "PLANTS_PER_M2",
    "load_knu_validation_data",
    "read_knu_forcing_csv",
    "read_knu_yield_workbook",
    "resample_forcing",
    "write_knu_manifest",
]
