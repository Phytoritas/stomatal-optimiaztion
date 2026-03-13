#!/usr/bin/env python3
"""
Build a static HTML viewer to compare preprocessing choices.

The viewer is designed for the pipeline discussed in this repo:
- Weight is stored in kg and visualized in g.
- Transpiration is derived from negative weight changes only.
- Comparison methods (per loadcell):
  1) raw 1s diff (very noisy)
  2) trailing moving-average diff (window configurable; default 60s)
  3) 60s diff at 1-minute resolution (uses existing transpiration_1m outputs if present)
  4) rolling linear-regression slope (window configurable; default 300s)

Outputs:
- <output-dir>/index.html
- <output-dir>/app.js
- <output-dir>/style.css
- <output-dir>/data/dates.json
- <output-dir>/data/YYYY-MM-DD.json (one per selected date)

Note: The viewer loads JSON via fetch(), so open it via a local web server:
  python -m http.server 8000 --directory artifacts/preprocess_compare
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd


DATE_RE = re.compile(r"^(?P<date>\d{4}-\d{2}-\d{2})_canonical_1s\.parquet$")
LC_COLS = [f"loadcell_{i}_kg" for i in range(1, 7)]


@dataclass(frozen=True)
class DayPaths:
    date: str
    canonical_1s: Path
    transpiration_1m: Optional[Path]


def _list_canonical_days(canonical_dir: Path) -> list[DayPaths]:
    out: list[DayPaths] = []
    for p in canonical_dir.glob("*_canonical_1s.parquet"):
        m = DATE_RE.match(p.name)
        if not m:
            continue
        out.append(DayPaths(date=m.group("date"), canonical_1s=p, transpiration_1m=None))
    out.sort(key=lambda d: d.date)
    return out


def _select_days(
    days: list[DayPaths],
    *,
    dates: Optional[list[str]],
    start_date: Optional[str],
    end_date: Optional[str],
    max_days: Optional[int],
    all_days: bool,
) -> list[DayPaths]:
    if dates:
        wanted = set(dates)
        picked = [d for d in days if d.date in wanted]
        missing = sorted(wanted - {d.date for d in picked})
        if missing:
            raise FileNotFoundError(f"Dates not found in canonical-dir: {missing}")
        return picked

    picked = days
    if start_date:
        picked = [d for d in picked if d.date >= start_date]
    if end_date:
        picked = [d for d in picked if d.date <= end_date]

    if all_days:
        return picked
    if max_days is None or max_days <= 0:
        return picked
    return picked[-max_days:]


def _find_transpiration_1m_path(transpiration_1m_dir: Path, date: str) -> Optional[Path]:
    if not transpiration_1m_dir.exists():
        return None
    matches = sorted(transpiration_1m_dir.glob(f"{date}__transpiration_1m__diff60__g_min_per_plant__p*.parquet"))
    return matches[0] if matches else None


def _load_weights_dg(canonical_path: Path) -> tuple[str, int, list[list[int]]]:
    df = pd.read_parquet(canonical_path, columns=["timestamp", *LC_COLS])
    if df.empty:
        raise ValueError(f"Empty canonical file: {canonical_path}")

    ts0 = pd.Timestamp(df["timestamp"].iloc[0]).to_pydatetime()
    t0_iso = ts0.strftime("%Y-%m-%dT%H:%M:%S")
    n = int(len(df))

    # kg -> g -> deci-grams (0.1g). Store as ints to keep JSON smaller.
    w_kg = df[LC_COLS].to_numpy(dtype=np.float64)
    w_dg = np.rint(w_kg * 1000.0 * 10.0).astype(np.int32)

    weights_by_lc: list[list[int]] = []
    for i in range(6):
        weights_by_lc.append(w_dg[:, i].tolist())
    return t0_iso, n, weights_by_lc


def _compute_transpiration_1m_from_canonical(
    canonical_path: Path,
    *,
    plants_per_loadcell: int,
) -> tuple[str, int, int, list[list[int]]]:
    df = pd.read_parquet(canonical_path, columns=["timestamp", *LC_COLS])
    if df.empty:
        raise ValueError(f"Empty canonical file: {canonical_path}")
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.set_index("timestamp", drop=True)

    w_end = df[LC_COLS].resample("1min", label="right", closed="right").last()
    delta_kg = w_end.diff()
    transp_g_min_per_plant = (-delta_kg).clip(lower=0.0).fillna(0.0) * 1000.0 / float(plants_per_loadcell)

    ts0 = pd.Timestamp(transp_g_min_per_plant.index[0]).to_pydatetime()
    t0_iso = ts0.strftime("%Y-%m-%dT%H:%M:%S")
    n = int(len(transp_g_min_per_plant))
    dt_sec = 60

    # g/min -> mg/min to store as ints.
    arr_mg = np.rint(transp_g_min_per_plant.to_numpy(dtype=np.float64) * 1000.0).astype(np.int32)
    by_lc: list[list[int]] = []
    for i in range(6):
        by_lc.append(arr_mg[:, i].tolist())
    return t0_iso, n, dt_sec, by_lc


def _load_transpiration_1m_mg(
    transpiration_1m_path: Path,
) -> tuple[str, int, int, list[list[int]]]:
    df = pd.read_parquet(transpiration_1m_path)
    if df.empty:
        raise ValueError(f"Empty transpiration file: {transpiration_1m_path}")

    cols = [f"loadcell_{i}_transpiration_g_min_per_plant" for i in range(1, 7)]
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise KeyError(f"Missing columns in {transpiration_1m_path}: {missing}")

    ts0 = pd.Timestamp(df["timestamp"].iloc[0]).to_pydatetime()
    t0_iso = ts0.strftime("%Y-%m-%dT%H:%M:%S")
    n = int(len(df))
    dt_sec = 60

    arr_mg = np.rint(df[cols].to_numpy(dtype=np.float64) * 1000.0).astype(np.int32)
    by_lc: list[list[int]] = []
    for i in range(6):
        by_lc.append(arr_mg[:, i].tolist())
    return t0_iso, n, dt_sec, by_lc


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, separators=(",", ":")), encoding="utf-8")


def _write_static_files(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "data").mkdir(parents=True, exist_ok=True)

    index_html = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Preprocess Compare</title>
    <link rel="stylesheet" href="./style.css" />
    <script src="https://cdn.plot.ly/plotly-2.30.0.min.js"></script>
  </head>
  <body>
    <div class="bg"></div>
    <header class="top">
      <div class="brand">
        <div class="kicker">Load-cell preprocessing</div>
        <h1>Preprocess Compare</h1>
        <div class="sub">Weight (g) on top, transpiration (g/min/plant) on bottom.</div>
      </div>
      <div class="nav">
        <button id="prevDay" class="btn" title="Left arrow">Prev</button>
        <select id="dateSelect" class="select"></select>
        <button id="nextDay" class="btn" title="Right arrow">Next</button>
      </div>
    </header>

    <main class="grid">
      <section class="panel">
        <div class="panelTitle">Summary</div>
        <div id="summary" class="summary"></div>

        <div class="tabs" role="tablist" aria-label="Panel">
          <button id="tabControls" class="tabBtn active" data-tab="controls" role="tab" aria-selected="true">Controls</button>
          <button id="tabExport" class="tabBtn" data-tab="export" role="tab" aria-selected="false">Export</button>
          <button id="tabPreprocess" class="tabBtn" data-tab="preprocess" role="tab" aria-selected="false">Preprocess</button>
          <button id="tabHelp" class="tabBtn" data-tab="help" role="tab" aria-selected="false">Help</button>
        </div>

        <div id="pageControls" class="tabPage active" data-tabpage="controls" role="tabpanel">
          <div class="panelTitle">Controls</div>

          <div class="row">
            <label class="label" for="loadcellSelect">Loadcell</label>
            <select id="loadcellSelect" class="select">
              <option value="0">Loadcell 1</option>
              <option value="1">Loadcell 2</option>
              <option value="2">Loadcell 3</option>
              <option value="3">Loadcell 4</option>
              <option value="4">Loadcell 5</option>
              <option value="5">Loadcell 6</option>
            </select>
          </div>

          <div class="row">
            <label class="label" for="maWindow">Trailing MA window</label>
            <div class="sliderWrap">
              <input id="maWindow" type="range" min="5" max="300" step="5" value="60" />
              <div class="sliderValue"><span id="maWindowVal">60</span>s</div>
            </div>
          </div>

          <div class="row">
            <label class="label" for="regWindow">Rolling regression window</label>
            <div class="sliderWrap">
              <input id="regWindow" type="range" min="60" max="900" step="60" value="300" />
              <div class="sliderValue"><span id="regWindowVal">300</span>s</div>
            </div>
          </div>

          <div class="row">
            <div class="label">Weight traces</div>
            <div class="checks">
              <label class="check"><input id="showWeightRaw" type="checkbox" checked /> 1s grid (filled)</label>
              <label class="check"><input id="showWeightMA" type="checkbox" checked /> MA (past+current)</label>
            </div>
          </div>

          <div class="row">
            <div class="label">Transpiration traces</div>
            <div class="checks">
              <label class="check"><input id="showTRaw" type="checkbox" checked /> Diff (1s)</label>
              <label class="check"><input id="showTMA" type="checkbox" checked /> MA diff (1s)</label>
              <label class="check"><input id="showTReg" type="checkbox" checked /> Rolling reg (5m)</label>
              <label class="check"><input id="showT1m" type="checkbox" checked /> Diff60 (1m)</label>
            </div>
          </div>

          <div class="row">
            <label class="label" for="capInput">Cap (g/min/plant, optional)</label>
            <input id="capInput" class="input" type="number" min="0" step="0.1" placeholder="off" />
          </div>
        </div>

        <div id="pageExport" class="tabPage" data-tabpage="export" role="tabpanel">
          <div class="panelTitle">Export</div>
          <div id="exportNotice" class="hint"></div>

          <div class="row">
            <label class="label" for="methodSelect">Method</label>
            <select id="methodSelect" class="select">
              <option value="diff_1s">diff (1s)</option>
              <option value="ma_diff_1s">MA diff (1s)</option>
              <option value="reg_1s">rolling reg (1s)</option>
              <option value="diff60_1m" selected>diff60 (1m)</option>
            </select>
          </div>

          <div class="row">
            <label class="label" for="resolutionSelect">Output resolution</label>
            <select id="resolutionSelect" class="select">
              <option value="1m" selected>1m</option>
              <option value="1s">1s</option>
            </select>
          </div>

          <div class="row">
            <label class="label" for="finalDir">Final folder</label>
            <input id="finalDir" class="input" type="text" value="data/final" />
          </div>

          <div class="row">
            <button id="saveBtn" class="btn btnPrimary">Save current date</button>
          </div>

          <div class="row">
            <label class="label" for="rangeStart">Date range</label>
            <div class="rangeRow">
              <select id="rangeStart" class="select selectFull"></select>
              <span class="rangeDash">to</span>
              <select id="rangeEnd" class="select selectFull"></select>
            </div>
          </div>

          <div class="row">
            <div class="rangeBtns">
              <button id="saveRangeBtn" class="btn">Save range</button>
              <button id="saveAllBtn" class="btn">Save all loaded</button>
              <button id="cancelSaveBtn" class="btn btnDanger" disabled>Cancel</button>
            </div>
          </div>

          <div id="exportStatus" class="hint"></div>
        </div>

        <div id="pagePreprocess" class="tabPage" data-tabpage="preprocess" role="tabpanel">
          <div class="panelTitle">Preprocess</div>
          <div id="preprocessNotice" class="hint"></div>

          <div class="row">
            <label class="label" for="rawDir">Raw folder</label>
            <input id="rawDir" class="input" type="text" value="data/raw" />
          </div>

          <div class="row">
            <label class="label" for="rawPattern">File pattern</label>
            <input id="rawPattern" class="input" type="text" value="ALMEMO500~*.csv" />
          </div>

          <div class="row">
            <div class="rangeBtns">
              <button id="preprocessBtn" class="btn btnPrimary">Preprocess new raw files</button>
              <button id="refreshDatesBtn" class="btn">Refresh dates</button>
              <button id="cancelPreprocessBtn" class="btn btnDanger" disabled>Cancel</button>
            </div>
          </div>

          <div id="preprocessStatus" class="summary logBox"></div>
        </div>

        <div id="pageHelp" class="tabPage" data-tabpage="help" role="tabpanel">
          <div class="panelTitle">How To Open</div>
          <pre class="code"># view-only
python -m http.server 8000 --directory artifacts/preprocess_compare

# view + export (Save button)
python scripts/preprocess_compare_server.py --port 8000 --bind 0.0.0.0</pre>
          <div class="hint">Open via <span class="mono">http://127.0.0.1:8000</span> (or WSL IP) in your browser.</div>
        </div>
      </section>

      <section class="plots">
        <div id="weightPlot" class="plot"></div>
        <div id="transpPlot" class="plot"></div>
      </section>
    </main>

    <script src="./app.js"></script>
  </body>
</html>
"""

    style_css = """:root{
  --bg0:#0b1020;
  --bg1:#0e1b2f;
  --card:rgba(255,255,255,0.06);
  --card2:rgba(255,255,255,0.08);
  --line:rgba(255,255,255,0.14);
  --control: rgba(0,0,0,0.32);
  --control2: rgba(0,0,0,0.42);
  --text:#e9eefc;
  --muted:rgba(233,238,252,0.68);
  --accent:#7cf2c2;
  --accent2:#ffb86b;
  --danger:#ff6b6b;
  --shadow: 0 12px 40px rgba(0,0,0,0.35);
  --radius:18px;
  --mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
  --sans: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, "Apple Color Emoji", "Segoe UI Emoji";
}
*{box-sizing:border-box}
html,body{height:100%}
body{
  margin:0;
  font-family:var(--sans);
  color:var(--text);
  color-scheme: dark;
  background: radial-gradient(1200px 600px at 15% 10%, rgba(124,242,194,0.20), transparent 60%),
              radial-gradient(900px 700px at 85% 30%, rgba(255,184,107,0.18), transparent 60%),
              linear-gradient(180deg, var(--bg0), var(--bg1));
}
.bg{
  position:fixed; inset:0;
  background-image:
    linear-gradient(rgba(255,255,255,0.06) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255,255,255,0.06) 1px, transparent 1px);
  background-size: 44px 44px;
  opacity:0.12;
  pointer-events:none;
}
.top{
  position:sticky; top:0; z-index:10;
  display:flex; gap:18px; align-items:flex-end; justify-content:space-between;
  padding:18px 22px;
  backdrop-filter: blur(10px);
  background: linear-gradient(180deg, rgba(11,16,32,0.72), rgba(11,16,32,0.35));
  border-bottom:1px solid var(--line);
}
.brand h1{margin:2px 0 4px; font-size:22px; letter-spacing:0.2px}
.kicker{font-size:12px; letter-spacing:0.14em; text-transform:uppercase; color:var(--muted)}
.sub{font-size:12px; color:var(--muted)}
.nav{display:flex; gap:10px; align-items:center}
.btn{
  border:1px solid var(--line);
  background:rgba(255,255,255,0.05);
  color:var(--text);
  padding:10px 12px;
  border-radius:12px;
  cursor:pointer;
  box-shadow: var(--shadow);
}
.btn:hover{border-color:rgba(255,255,255,0.28)}
.btnPrimary{
  border-color: rgba(124,242,194,0.45);
  background: rgba(124,242,194,0.10);
}
.btnPrimary:hover{border-color: rgba(124,242,194,0.75)}
.btnDanger{
  border-color: rgba(255,107,107,0.55);
  background: rgba(255,107,107,0.10);
}
.btnDanger:hover{border-color: rgba(255,107,107,0.85)}
.select{
  border:1px solid var(--line);
  background: var(--control);
  color:var(--text);
  padding:10px 12px;
  border-radius:12px;
  min-width: 220px;
}
.select:focus{
  outline: none;
  border-color: rgba(124,242,194,0.55);
  box-shadow: 0 0 0 3px rgba(124,242,194,0.14);
}
.select option{
  background: #0b1020;
  color: var(--text);
}
.selectFull{min-width:0; width:100%}
.grid{
  display:grid;
  grid-template-columns: 360px 1fr;
  gap:16px;
  padding:16px;
}
.panel{
  border:1px solid var(--line);
  background: var(--card);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  padding:14px;
  align-self:start;
}
.panelTitle{
  margin:10px 0 8px;
  font-size:12px;
  letter-spacing:0.14em;
  text-transform:uppercase;
  color:var(--muted);
}
.tabs{
  display:grid;
  grid-template-columns: 1fr 1fr;
  gap:8px;
  margin: 12px 0 10px;
}
.tabBtn{
  border:1px solid var(--line);
  background: rgba(0,0,0,0.18);
  color: rgba(233,238,252,0.78);
  padding:10px 10px;
  border-radius:999px;
  cursor:pointer;
  font-weight:600;
  letter-spacing:0.02em;
}
.tabBtn:hover{border-color:rgba(255,255,255,0.28)}
.tabBtn:focus{
  outline:none;
  border-color: rgba(124,242,194,0.55);
  box-shadow: 0 0 0 3px rgba(124,242,194,0.14);
}
.tabBtn.active{
  border-color: rgba(124,242,194,0.65);
  background: rgba(124,242,194,0.12);
  color: var(--text);
}
.tabPage{display:none}
.tabPage.active{display:block; animation: tabFade 140ms ease-out}
@keyframes tabFade{
  from{opacity:0; transform: translateY(2px)}
  to{opacity:1; transform: none}
}
.row{margin:10px 0}
.label{display:block; font-size:12px; color:var(--muted); margin-bottom:6px}
.sliderWrap{display:flex; gap:10px; align-items:center}
input[type="range"]{width:100%}
.sliderValue{
  font-family:var(--mono);
  font-size:12px;
  padding:6px 8px;
  border:1px solid var(--line);
  border-radius:12px;
  background:rgba(255,255,255,0.04);
  min-width:68px;
  text-align:center;
}
.input{
  width:100%;
  border:1px solid var(--line);
  background: var(--control);
  color:var(--text);
  padding:10px 12px;
  border-radius:12px;
}
.input:focus{
  outline: none;
  border-color: rgba(124,242,194,0.55);
  box-shadow: 0 0 0 3px rgba(124,242,194,0.14);
}
.checks{display:flex; gap:8px; flex-wrap:wrap}
.check{
  font-size:12px;
  color:var(--text);
  padding:8px 10px;
  border:1px solid var(--line);
  border-radius:999px;
  background:rgba(255,255,255,0.04);
}
.summary{
  font-family:var(--mono);
  font-size:12px;
  padding:10px 10px;
  border:1px solid var(--line);
  border-radius:14px;
  background:rgba(0,0,0,0.18);
  white-space:pre-wrap;
  line-height:1.45;
}
.code{
  font-family:var(--mono);
  font-size:12px;
  margin:0;
  padding:10px 10px;
  border:1px solid var(--line);
  border-radius:14px;
  background:rgba(0,0,0,0.25);
  overflow:auto;
}
.hint{font-size:12px; color:var(--muted); margin-top:8px}
.mono{font-family:var(--mono)}
.rangeRow{
  display:grid;
  grid-template-columns: 1fr;
  gap:8px;
  align-items:center;
}
.rangeDash{font-size:12px; color:var(--muted); text-align:center}
.rangeBtns{display:flex; gap:10px; flex-wrap:wrap}
.logBox{max-height: 180px; overflow:auto}
.plots{
  display:flex;
  flex-direction:column;
  gap:14px;
}
.plot{
  border:1px solid var(--line);
  border-radius: var(--radius);
  background: var(--card2);
  box-shadow: var(--shadow);
  min-height: 360px;
}
@media (max-width: 980px){
  .grid{grid-template-columns:1fr}
  .select{min-width: 140px}
}
"""

    app_js = """/* global Plotly */
function $(id){ return document.getElementById(id); }

const state = {
  dates: [],
  dateIdx: 0,
  day: null,
  loadcell: 0,
  plantsPerLoadcell: 3,
  maWindowSec: 60,
  regWindowSec: 300,
  capGMinPerPlant: null,
  exportEnabled: false,
  preprocessEnabled: false,
  activeTab: "controls",
  preprocessBusy: false,
  exportCancelRequested: false,
  exportBusy: false,
  cache: {
    ma: new Map(),
    regSlope: new Map(),
  },
  plotsReady: false,
};

function clamp(v, lo, hi){ return Math.max(lo, Math.min(hi, v)); }
function fmt(x, digits=2){
  if (!Number.isFinite(x)) return "NA";
  return x.toFixed(digits);
}

function trailingMA(y, window){
  const n = y.length;
  const out = new Array(n);
  const w = Math.max(1, Math.floor(window));
  let sum = 0;
  for (let i=0;i<n;i++){
    sum += y[i];
    if (i >= w) sum -= y[i-w];
    const denom = (i+1 < w) ? (i+1) : w;
    out[i] = sum / denom;
  }
  return out;
}

function transpFromDiff1s(weightsG, plantsPerLoadcell){
  const n = weightsG.length;
  const out = new Array(n);
  out[0] = 0;
  const denom = Math.max(1, plantsPerLoadcell);
  for (let i=1;i<n;i++){
    const d = weightsG[i] - weightsG[i-1]; // g per second
    const t = (d < 0) ? (-d) : 0; // g/s/loadcell
    out[i] = (t / denom) * 60.0; // g/min/plant
  }
  return out;
}

function rollingSlopeTrailing(weightsG, window){
  const n = weightsG.length;
  const out = new Array(n).fill(NaN);
  const N = Math.floor(window);
  if (N < 2 || n < N) return out;

  const S = new Float64Array(n);
  const SI = new Float64Array(n);
  let sum = 0;
  let sumI = 0;
  for (let i=0;i<n;i++){
    const y = weightsG[i];
    sum += y;
    sumI += i * y;
    S[i] = sum;
    SI[i] = sumI;
  }

  const sumX = (N * (N - 1)) / 2.0;
  const varX = (N * (N * N - 1)) / 12.0;
  for (let b=N-1;b<n;b++){
    const a = b - N + 1;
    const sumY = S[b] - (a > 0 ? S[a-1] : 0);
    const sumIY = SI[b] - (a > 0 ? SI[a-1] : 0);
    const sumXY = sumIY - a * sumY; // sum((k-a)*y_k)
    const numer = sumXY - (sumX * sumY) / N;
    out[b] = numer / varX; // g/s
  }
  return out;
}

function transpFromSlope(weightsSlopeGPerS, plantsPerLoadcell){
  const n = weightsSlopeGPerS.length;
  const out = new Array(n);
  const denom = Math.max(1, plantsPerLoadcell);
  for (let i=0;i<n;i++){
    const s = weightsSlopeGPerS[i];
    if (!Number.isFinite(s)) { out[i] = 0; continue; }
    const t = (s < 0) ? (-s) : 0; // g/s/loadcell
    out[i] = (t / denom) * 60.0; // g/min/plant
  }
  return out;
}

function capSeries(arr, cap){
  if (!Number.isFinite(cap) || cap <= 0) return arr;
  const n = arr.length;
  const out = new Array(n);
  for (let i=0;i<n;i++){
    const v = arr[i];
    out[i] = (v > cap) ? cap : v;
  }
  return out;
}

function dayTitle(){
  if (!state.day) return "";
  return `${state.day.date} | plants/loadcell=${state.day.plants_per_loadcell}`;
}

function setSummary(text){
  $("summary").textContent = text;
}

function setExportNotice(text){
  $("exportNotice").textContent = text;
}

function setExportStatus(text){
  $("exportStatus").textContent = text;
}

function setExportBusy(isBusy){
  state.exportBusy = isBusy;
  $("saveBtn").disabled = isBusy;
  $("saveRangeBtn").disabled = isBusy;
  $("saveAllBtn").disabled = isBusy;
  $("cancelSaveBtn").disabled = !isBusy;
  $("prevDay").disabled = isBusy;
  $("nextDay").disabled = isBusy;
  $("dateSelect").disabled = isBusy;
}

function setPreprocessNotice(text){
  $("preprocessNotice").textContent = text;
}

function setPreprocessStatus(text){
  $("preprocessStatus").textContent = text;
}

function setPreprocessBusy(isBusy){
  state.preprocessBusy = isBusy;
  $("preprocessBtn").disabled = isBusy;
  $("refreshDatesBtn").disabled = isBusy;
  $("cancelPreprocessBtn").disabled = !isBusy;
}

function setTab(tab){
  const tabs = ["controls","export","preprocess","help"];
  const btnIds = { controls: "tabControls", export: "tabExport", preprocess: "tabPreprocess", help: "tabHelp" };
  const pageIds = { controls: "pageControls", export: "pageExport", preprocess: "pagePreprocess", help: "pageHelp" };
  const next = tabs.includes(tab) ? tab : "controls";
  state.activeTab = next;
  for (const t of tabs){
    const isActive = (t === next);
    const btn = $(btnIds[t]);
    const page = $(pageIds[t]);
    if (btn){
      btn.classList.toggle("active", isActive);
      btn.setAttribute("aria-selected", isActive ? "true" : "false");
    }
    if (page){
      page.classList.toggle("active", isActive);
    }
  }
  try{ localStorage.setItem("pp_tab", next); } catch (_e){ /* ignore */ }
}

function initTab(){
  let tab = "controls";
  try{
    const saved = localStorage.getItem("pp_tab");
    if (saved) tab = saved;
  } catch (_e){ /* ignore */ }
  setTab(tab);
}

function buildSummary(weightsRawG, tRaw, tMA, tReg, t1m){
  const n = weightsRawG.length;
  const tStart = state.day.t0_1s.replace("T"," ");
  const tEnd = new Date(Date.parse(state.day.t0_1s) + (n-1)*1000).toISOString().replace("T"," ").slice(0,19);
  const sum1s = (arr)=> arr.reduce((a,b)=>a+b,0) / 60.0; // g/plant
  const sum1m = (arr)=> arr.reduce((a,b)=>a+b,0); // g/plant (each entry is g in that minute)
  const capLine = Number.isFinite(state.capGMinPerPlant) ? `cap: ${fmt(state.capGMinPerPlant,2)} g/min/plant` : "cap: off";

  const lines = [
    dayTitle(),
    `time: ${tStart}  ->  ${tEnd}`,
    capLine,
    "",
    "Total transpiration (g/plant)",
    `raw diff (1s):        ${fmt(sum1s(tRaw),2)}`,
    `MA diff (1s):         ${fmt(sum1s(tMA),2)}`,
    `rolling reg (1s):     ${fmt(sum1s(tReg),2)}`,
    `diff60 (1m):          ${fmt(sum1m(t1m),2)}`,
  ];
  return lines.join("\\n");
}

function getLoadcellWeightsG(loadcellIdx){
  const dg = state.day.weights_dg[loadcellIdx];
  const n = dg.length;
  const out = new Array(n);
  for (let i=0;i<n;i++) out[i] = dg[i] / 10.0;
  return out;
}

function getTransp1mGMinPerPlant(loadcellIdx){
  const t1m = state.day.transp1m_mg_min_per_plant;
  if (!t1m) return null;
  const mg = t1m.values[loadcellIdx];
  const n = mg.length;
  const out = new Array(n);
  for (let i=0;i<n;i++) out[i] = mg[i] / 1000.0;
  return out;
}

function computeSeries(){
  const lc = state.loadcell;
  const weightsRawG = getLoadcellWeightsG(lc);

  const maKey = `${state.day.date}|lc=${lc}|ma=${state.maWindowSec}`;
  let weightsMAG = state.cache.ma.get(maKey);
  if (!weightsMAG){
    weightsMAG = trailingMA(weightsRawG, state.maWindowSec);
    state.cache.ma.set(maKey, weightsMAG);
  }

  const cap = state.capGMinPerPlant;
  const tRaw = capSeries(transpFromDiff1s(weightsRawG, state.day.plants_per_loadcell), cap);
  const tMA = capSeries(transpFromDiff1s(weightsMAG, state.day.plants_per_loadcell), cap);

  const regKey = `${state.day.date}|lc=${lc}|reg=${state.regWindowSec}`;
  let slope = state.cache.regSlope.get(regKey);
  if (!slope){
    slope = rollingSlopeTrailing(weightsRawG, state.regWindowSec);
    state.cache.regSlope.set(regKey, slope);
  }
  const tReg = capSeries(transpFromSlope(slope, state.day.plants_per_loadcell), cap);

  const t1mBase = getTransp1mGMinPerPlant(lc) || [];
  const t1m = capSeries(t1mBase, cap);
  return { weightsRawG, weightsMAG, tRaw, tMA, tReg, t1m };
}

function weightLayout(){
  const fontColor = "rgba(233,238,252,0.92)";
  return {
    font: { color: fontColor },
    title: { text: `Weight (g) | ${dayTitle()}`, font: { size: 14, color: fontColor } },
    margin: { l: 58, r: 22, t: 52, b: 38 },
    paper_bgcolor: "rgba(0,0,0,0)",
    plot_bgcolor: "rgba(0,0,0,0)",
    hoverlabel: { bgcolor: "rgba(0,0,0,0.82)", bordercolor: "rgba(255,255,255,0.18)", font: { color: fontColor } },
    xaxis: {
      type: "date",
      gridcolor: "rgba(255,255,255,0.10)",
      zeroline: false,
      color: "rgba(233,238,252,0.86)",
    },
    yaxis: {
      title: { text: "Weight (g)", font: { color: "rgba(233,238,252,0.92)" } },
      gridcolor: "rgba(255,255,255,0.10)",
      zeroline: false,
      color: "rgba(233,238,252,0.86)",
    },
    legend: { orientation: "h", y: 1.02, x: 0, font: { size: 12, color: "rgba(233,238,252,0.92)" } },
  };
}

function transpLayout(){
  const fontColor = "rgba(233,238,252,0.92)";
  return {
    font: { color: fontColor },
    title: { text: `Transpiration (g/min/plant) | ${dayTitle()}`, font: { size: 14, color: fontColor } },
    margin: { l: 58, r: 22, t: 52, b: 38 },
    paper_bgcolor: "rgba(0,0,0,0)",
    plot_bgcolor: "rgba(0,0,0,0)",
    hoverlabel: { bgcolor: "rgba(0,0,0,0.82)", bordercolor: "rgba(255,255,255,0.18)", font: { color: fontColor } },
    xaxis: {
      type: "date",
      gridcolor: "rgba(255,255,255,0.10)",
      zeroline: false,
      color: "rgba(233,238,252,0.86)",
    },
    yaxis: {
      title: { text: "g/min/plant", font: { color: "rgba(233,238,252,0.92)" } },
      gridcolor: "rgba(255,255,255,0.10)",
      zeroline: false,
      rangemode: "tozero",
      color: "rgba(233,238,252,0.86)",
    },
    legend: { orientation: "h", y: 1.02, x: 0, font: { size: 12, color: "rgba(233,238,252,0.92)" } },
  };
}

function buildWeightTraces(series){
  const showRaw = $("showWeightRaw").checked;
  const showMA = $("showWeightMA").checked;
  return [
    {
      type: "scattergl",
      mode: "lines",
      name: "weight 1s (grid+fill)",
      y: series.weightsRawG,
      x0: state.day.t0_1s,
      dx: 1000,
      line: { color: "#7cf2c2", width: 1.4 },
      visible: showRaw ? true : "legendonly",
    },
    {
      type: "scattergl",
      mode: "lines",
      name: `weight MA (past+current, ${state.maWindowSec}s)`,
      y: series.weightsMAG,
      x0: state.day.t0_1s,
      dx: 1000,
      line: { color: "#ffb86b", width: 1.4 },
      visible: showMA ? true : "legendonly",
    },
  ];
}

function buildTranspTraces(series){
  const showTRaw = $("showTRaw").checked;
  const showTMA = $("showTMA").checked;
  const showTReg = $("showTReg").checked;
  const showT1m = $("showT1m").checked;

  const traces = [
    {
      type: "scattergl",
      mode: "lines",
      name: "diff (1s)",
      y: series.tRaw,
      x0: state.day.t0_1s,
      dx: 1000,
      line: { color: "rgba(124,242,194,0.85)", width: 1.1 },
      visible: showTRaw ? true : "legendonly",
    },
    {
      type: "scattergl",
      mode: "lines",
      name: `MA diff (1s, ${state.maWindowSec}s)`,
      y: series.tMA,
      x0: state.day.t0_1s,
      dx: 1000,
      line: { color: "rgba(255,184,107,0.9)", width: 1.2 },
      visible: showTMA ? true : "legendonly",
    },
    {
      type: "scattergl",
      mode: "lines",
      name: `rolling reg (1s, ${state.regWindowSec}s)`,
      y: series.tReg,
      x0: state.day.t0_1s,
      dx: 1000,
      line: { color: "rgba(255,107,107,0.9)", width: 1.2 },
      visible: showTReg ? true : "legendonly",
    },
  ];

  if (state.day.transp1m_mg_min_per_plant){
    traces.push({
      type: "scatter",
      mode: "lines",
      name: "diff60 (1m)",
      y: series.t1m,
      x0: state.day.transp1m_mg_min_per_plant.t0_1m,
      dx: state.day.transp1m_mg_min_per_plant.dt_sec * 1000,
      line: { color: "rgba(120,170,255,0.95)", width: 2.0, shape: "hv" },
      visible: showT1m ? true : "legendonly",
    });
  }
  return traces;
}

function syncXAxes(){
  const w = $("weightPlot");
  const t = $("transpPlot");

  w.on("plotly_relayout", (ev)=>{
    if (ev["xaxis.range[0]"] && ev["xaxis.range[1]"]){
      Plotly.relayout(t, { "xaxis.range": [ev["xaxis.range[0]"], ev["xaxis.range[1]"]] });
    }
  });
  t.on("plotly_relayout", (ev)=>{
    if (ev["xaxis.range[0]"] && ev["xaxis.range[1]"]){
      Plotly.relayout(w, { "xaxis.range": [ev["xaxis.range[0]"], ev["xaxis.range[1]"]] });
    }
  });
}

function renderPlots(){
  if (!state.day) return;

  const series = computeSeries();
  setSummary(buildSummary(series.weightsRawG, series.tRaw, series.tMA, series.tReg, series.t1m));

  const weightTraces = buildWeightTraces(series);
  const transpTraces = buildTranspTraces(series);

  const config = { responsive: true, displaylogo: false };
  if (!state.plotsReady){
    Plotly.newPlot("weightPlot", weightTraces, weightLayout(), config);
    Plotly.newPlot("transpPlot", transpTraces, transpLayout(), config);
    syncXAxes();
    state.plotsReady = true;
  } else {
    Plotly.react("weightPlot", weightTraces, weightLayout(), config);
    Plotly.react("transpPlot", transpTraces, transpLayout(), config);
  }
}

function setDateIdx(idx){
  if (!state.dates || state.dates.length === 0){
    setSummary("No dates loaded.");
    return;
  }
  state.dateIdx = clamp(idx, 0, state.dates.length - 1);
  const d = state.dates[state.dateIdx];
  if (!d){
    setSummary("No date selected.");
    return;
  }
  $("dateSelect").value = d;
  loadDay(d);
}

async function loadDay(dateStr){
  if (!dateStr){
    setSummary("No date selected.");
    return;
  }
  const resp = await fetch(`./data/${dateStr}.json`);
  if (!resp.ok){
    setSummary(`Failed to load data/${dateStr}.json`);
    return;
  }
  state.day = await resp.json();
  state.cache.ma.clear();
  state.cache.regSlope.clear();
  renderPlots();
}

function wire(){
  $("tabControls").addEventListener("click", ()=> setTab("controls"));
  $("tabExport").addEventListener("click", ()=> setTab("export"));
  $("tabPreprocess").addEventListener("click", ()=> setTab("preprocess"));
  $("tabHelp").addEventListener("click", ()=> setTab("help"));

  $("prevDay").addEventListener("click", ()=> setDateIdx(state.dateIdx - 1));
  $("nextDay").addEventListener("click", ()=> setDateIdx(state.dateIdx + 1));
  $("dateSelect").addEventListener("change", (e)=>{
    const dateStr = e.target.value;
    const idx = state.dates.indexOf(dateStr);
    if (idx >= 0) setDateIdx(idx);
  });
  $("loadcellSelect").addEventListener("change", (e)=>{
    state.loadcell = parseInt(e.target.value, 10);
    renderPlots();
  });

  const onSlider = (key, el, valEl)=>{
    const v = parseInt(el.value, 10);
    state[key] = v;
    valEl.textContent = String(v);
  };
  $("maWindow").addEventListener("input", ()=>{
    onSlider("maWindowSec", $("maWindow"), $("maWindowVal"));
  });
  $("maWindow").addEventListener("change", renderPlots);

  $("regWindow").addEventListener("input", ()=>{
    onSlider("regWindowSec", $("regWindow"), $("regWindowVal"));
  });
  $("regWindow").addEventListener("change", renderPlots);

  const rerenderOnClick = ["showWeightRaw","showWeightMA","showTRaw","showTMA","showTReg","showT1m"];
  for (const id of rerenderOnClick){
    $(id).addEventListener("change", renderPlots);
  }

  const updateCap = ()=>{
    const raw = String($("capInput").value || "").trim();
    if (!raw){
      state.capGMinPerPlant = null;
    } else {
      const v = parseFloat(raw);
      state.capGMinPerPlant = (Number.isFinite(v) && v > 0) ? v : null;
    }
    renderPlots();
  };
  $("capInput").addEventListener("change", updateCap);

  const onMethodChange = ()=>{
    const method = $("methodSelect").value;
    const res = $("resolutionSelect");
    if (method === "diff60_1m"){
      res.value = "1m";
      res.disabled = true;
    } else {
      res.disabled = false;
    }
  };
  $("methodSelect").addEventListener("change", onMethodChange);
  $("resolutionSelect").addEventListener("change", ()=>{ /* noop; used by export */ });
  onMethodChange();

  const buildExportPayload = (dateStr)=>({
    date: dateStr,
    method: $("methodSelect").value,
    resolution: $("resolutionSelect").value,
    ma_window_sec: state.maWindowSec,
    reg_window_sec: state.regWindowSec,
    cap_g_min_per_plant: state.capGMinPerPlant,
    plants_per_loadcell: state.day ? state.day.plants_per_loadcell : 3,
    final_dir: String($("finalDir").value || "").trim() || "data/final",
  });

  const postExport = async (payload)=>{
    const resp = await fetch("./api/export", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const txt = await resp.text();
    let obj = null;
    try{ obj = JSON.parse(txt); } catch(_e){ obj = null; }
    if (!resp.ok){
      const errMsg = (obj && obj.error) ? obj.error : txt;
      throw new Error(errMsg);
    }
    if (obj && obj.ok === false){
      throw new Error(obj.error || "export failed");
    }
    return obj || { ok: true, message: txt };
  };

  const saveCurrent = async ()=>{
    if (!state.exportEnabled){
      setExportStatus("Export disabled: run the API server (see docs).");
      return;
    }
    if (!state.day){
      setExportStatus("No day loaded.");
      return;
    }
    setExportBusy(true);
    state.exportCancelRequested = false;
    setExportStatus("Saving current date...");
    const payload = buildExportPayload(state.day.date);
    try{
      const obj = await postExport(payload);
      setExportStatus(obj.path ? `Saved: ${obj.path}` : "Saved.");
    } catch (err){
      setExportStatus(`Save error: ${String(err)}`);
    } finally {
      setExportBusy(false);
    }
  };
  $("saveBtn").addEventListener("click", ()=>{ void saveCurrent(); });

  const saveDates = async (dates)=>{
    if (!state.exportEnabled){
      setExportStatus("Export disabled: run the API server (see docs).");
      return;
    }
    if (!dates || dates.length === 0){
      setExportStatus("No dates selected.");
      return;
    }
    setExportBusy(true);
    state.exportCancelRequested = false;
    let ok = 0;
    let failed = 0;
    for (let i=0;i<dates.length;i++){
      if (state.exportCancelRequested){
        setExportStatus(`Canceled. ok=${ok} failed=${failed}`);
        break;
      }
      const d = dates[i];
      setExportStatus(`Saving ${d}... (${i+1}/${dates.length})`);
      try{
        await postExport(buildExportPayload(d));
        ok += 1;
      } catch (err){
        failed += 1;
        setExportStatus(`Failed ${d}: ${String(err)}  (${i+1}/${dates.length})`);
      }
    }
    if (!state.exportCancelRequested){
      setExportStatus(`Done. ok=${ok} failed=${failed}`);
    }
    setExportBusy(false);
  };

  const datesInRange = (start, end)=>{
    const a = state.dates.indexOf(start);
    const b = state.dates.indexOf(end);
    if (a < 0 || b < 0) return [];
    const lo = Math.min(a,b);
    const hi = Math.max(a,b);
    return state.dates.slice(lo, hi+1);
  };

  const saveRange = async ()=>{
    const start = $("rangeStart").value;
    const end = $("rangeEnd").value;
    const dates = datesInRange(start, end);
    await saveDates(dates);
  };
  $("saveRangeBtn").addEventListener("click", ()=>{ void saveRange(); });

  $("saveAllBtn").addEventListener("click", ()=>{ void saveDates(state.dates.slice()); });

  $("cancelSaveBtn").addEventListener("click", ()=>{
    state.exportCancelRequested = true;
  });

  const postJson = async (url, payload)=>{
    const resp = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload || {}),
    });
    const txt = await resp.text();
    let obj = null;
    try{ obj = JSON.parse(txt); } catch(_e){ obj = null; }
    if (!resp.ok){
      const errMsg = (obj && obj.error) ? obj.error : txt;
      throw new Error(errMsg);
    }
    if (obj && obj.ok === false){
      throw new Error(obj.error || "request failed");
    }
    return obj || { ok: true, message: txt };
  };

  let preprocessPollTimer = null;

  const pollPreprocess = async ()=>{
    try{
      const resp = await fetch("./api/preprocess/status");
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const obj = await resp.json();
      const st = (obj && obj.state) ? obj.state : null;
      if (!st){
        setPreprocessStatus("No status.");
        return;
      }
      const tail = Array.isArray(st.log_tail) ? st.log_tail : [];
      setPreprocessStatus(tail.join("\\n"));
      if (!st.running){
        if (preprocessPollTimer){
          clearInterval(preprocessPollTimer);
          preprocessPollTimer = null;
        }
        setPreprocessBusy(false);
        await reloadDates(true);
      }
    } catch (err){
      setPreprocessStatus(`Status error: ${String(err)}`);
    }
  };

  const startPreprocess = async ()=>{
    if (!state.preprocessEnabled){
      setPreprocessStatus("Preprocess disabled: run the API server.");
      return;
    }
    setPreprocessBusy(true);
    setPreprocessStatus("Starting preprocess job...");
    const payload = {
      raw_dir: String($("rawDir").value || "").trim() || "data/raw",
      pattern: String($("rawPattern").value || "").trim() || "ALMEMO500~*.csv",
      plants_per_loadcell: state.day ? state.day.plants_per_loadcell : 3,
    };
    try{
      const obj = await postJson("./api/preprocess", payload);
      if (obj && obj.started === false){
        setPreprocessStatus("Already running.");
      }
      if (preprocessPollTimer){
        clearInterval(preprocessPollTimer);
      }
      preprocessPollTimer = setInterval(()=>{ void pollPreprocess(); }, 1000);
      await pollPreprocess();
    } catch (err){
      setPreprocessBusy(false);
      setPreprocessStatus(`Start error: ${String(err)}`);
    }
  };
  $("preprocessBtn").addEventListener("click", ()=>{ void startPreprocess(); });

  $("cancelPreprocessBtn").addEventListener("click", async ()=>{
    try{
      await postJson("./api/preprocess/cancel", {});
      setPreprocessStatus("Cancel requested...");
    } catch (err){
      setPreprocessStatus(`Cancel error: ${String(err)}`);
    }
  });

  $("refreshDatesBtn").addEventListener("click", ()=>{ void reloadDates(true); });

  document.addEventListener("keydown", (e)=>{
    if (state.exportBusy || state.preprocessBusy) return;
    if (e.key === "ArrowLeft") setDateIdx(state.dateIdx - 1);
    if (e.key === "ArrowRight") setDateIdx(state.dateIdx + 1);
  });
}

async function reloadDates(keepCurrent){
  const prev = (keepCurrent && state.day) ? state.day.date : null;
  const resp = await fetch("./data/dates.json", { cache: "no-store" });
  if (!resp.ok){
    setSummary("Failed to load data/dates.json");
    return;
  }
  const parsed = await resp.json();
  state.dates = Array.isArray(parsed) ? parsed : [];

  if (state.dates.length === 0){
    $("prevDay").disabled = true;
    $("nextDay").disabled = true;
    $("dateSelect").disabled = true;
    setSummary("No dates found. Preprocess first (Preprocess tab) or rebuild viewer JSON.");
    return;
  }
  $("prevDay").disabled = false;
  $("nextDay").disabled = false;
  $("dateSelect").disabled = false;

  const sel = $("dateSelect");
  sel.innerHTML = "";
  for (const d of state.dates){
    const opt = document.createElement("option");
    opt.value = d;
    opt.textContent = d;
    sel.appendChild(opt);
  }

  const r0 = $("rangeStart");
  const r1 = $("rangeEnd");
  r0.innerHTML = "";
  r1.innerHTML = "";
  for (const d of state.dates){
    const o0 = document.createElement("option");
    o0.value = d;
    o0.textContent = d;
    r0.appendChild(o0);

    const o1 = document.createElement("option");
    o1.value = d;
    o1.textContent = d;
    r1.appendChild(o1);
  }
  if (state.dates.length > 0){
    r0.value = state.dates[0];
    r1.value = state.dates[state.dates.length - 1];
  }

  if (prev && state.dates.includes(prev)){
    setDateIdx(state.dates.indexOf(prev));
  } else if (state.dates.length > 0){
    setDateIdx(state.dates.length - 1);
  }
}

async function checkExportApi(){
  try{
    const resp = await fetch("./api/health");
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const obj = await resp.json();
    if (obj && obj.ok){
      state.exportEnabled = true;
      state.preprocessEnabled = true;
      setExportNotice("Export enabled (API server connected).");
      setExportStatus("");
      setPreprocessNotice("Preprocess enabled (API server connected).");
      setPreprocessStatus("");
      return;
    }
  } catch (_e){
    // ignore
  }
  state.exportEnabled = false;
  state.preprocessEnabled = false;
  setExportNotice("Export disabled. Run: python scripts/preprocess_compare_server.py --port 8000 --bind 0.0.0.0");
  setExportStatus("");
  setPreprocessNotice("Preprocess disabled. Run the API server (same as Export).");
  setPreprocessStatus("");
}

async function main(){
  wire();
  initTab();
  await checkExportApi();
  await reloadDates(false);
}

main().catch((err)=>{ setSummary(String(err)); });
"""

    (output_dir / "index.html").write_text(index_html, encoding="utf-8")
    (output_dir / "style.css").write_text(style_css, encoding="utf-8")
    (output_dir / "app.js").write_text(app_js, encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Build HTML viewer to compare preprocessing methods.")
    p.add_argument(
        "--canonical-dir",
        type=Path,
        default=Path("data/processed/canonical_1s"),
        help="Directory with YYYY-MM-DD_canonical_1s.parquet files.",
    )
    p.add_argument(
        "--transpiration-1m-dir",
        type=Path,
        default=Path("data/processed/transpiration_1m"),
        help="Directory with transpiration 1m parquet outputs (optional).",
    )
    p.add_argument(
        "--output-dir",
        type=Path,
        default=Path("artifacts/preprocess_compare"),
        help="Output directory for static viewer.",
    )
    p.add_argument("--plants-per-loadcell", type=int, default=3, help="Plants per loadcell (used if 1m file missing).")

    group = p.add_mutually_exclusive_group()
    group.add_argument(
        "--all",
        dest="all_days",
        action="store_true",
        help="Generate JSON for all available dates (can be large).",
    )
    group.add_argument(
        "--max-days",
        type=int,
        default=31,
        help="Generate JSON for only the latest N dates (default: 31). Ignored with --all.",
    )

    p.add_argument(
        "--dates",
        type=str,
        default=None,
        help="Comma-separated explicit date list (e.g. 2025-06-17,2025-06-18).",
    )
    p.add_argument("--start-date", type=str, default=None, help="Start date YYYY-MM-DD (inclusive).")
    p.add_argument("--end-date", type=str, default=None, help="End date YYYY-MM-DD (inclusive).")
    return p


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)

    canonical_dir = Path(args.canonical_dir)
    if not canonical_dir.exists():
        raise FileNotFoundError(f"canonical-dir not found: {canonical_dir}")

    out_dir = Path(args.output_dir)
    _write_static_files(out_dir)

    all_days = _list_canonical_days(canonical_dir)
    if not all_days:
        raise FileNotFoundError(f"No canonical files found in: {canonical_dir}")

    dates: Optional[list[str]] = None
    if args.dates:
        dates = [d.strip() for d in str(args.dates).split(",") if d.strip()]

    selected = _select_days(
        all_days,
        dates=dates,
        start_date=args.start_date,
        end_date=args.end_date,
        max_days=None if bool(args.all_days) else int(args.max_days),
        all_days=bool(args.all_days),
    )

    plants_per_loadcell = int(args.plants_per_loadcell)
    if plants_per_loadcell < 1:
        raise ValueError("--plants-per-loadcell must be >= 1")

    transp_1m_dir = Path(args.transpiration_1m_dir)
    for day in selected:
        t0_1s, n_1s, weights_dg = _load_weights_dg(day.canonical_1s)

        transp_path = _find_transpiration_1m_path(transp_1m_dir, day.date)
        if transp_path is not None:
            t0_1m, n_1m, dt_sec, transp1m_mg = _load_transpiration_1m_mg(transp_path)
            transp_payload = {"t0_1m": t0_1m, "n": n_1m, "dt_sec": dt_sec, "values": transp1m_mg}
        else:
            t0_1m, n_1m, dt_sec, transp1m_mg = _compute_transpiration_1m_from_canonical(
                day.canonical_1s, plants_per_loadcell=plants_per_loadcell
            )
            transp_payload = {"t0_1m": t0_1m, "n": n_1m, "dt_sec": dt_sec, "values": transp1m_mg}

        payload = {
            "date": day.date,
            "plants_per_loadcell": plants_per_loadcell,
            "t0_1s": t0_1s,
            "n_1s": n_1s,
            "weights_dg": weights_dg,
            "transp1m_mg_min_per_plant": transp_payload,
        }
        _write_json(out_dir / "data" / f"{day.date}.json", payload)

    # dates.json should reflect *what's actually present* under output_dir/data.
    # This avoids accidentally hiding dates written by the API preprocess job.
    present_dates: list[str] = []
    for p in (out_dir / "data").glob("*.json"):
        if p.name == "dates.json":
            continue
        if re.match(r"^\d{4}-\d{2}-\d{2}\.json$", p.name):
            present_dates.append(p.stem)
    present_dates = sorted(set(present_dates))
    _write_json(out_dir / "data" / "dates.json", present_dates)

    print(f"[ok] wrote viewer: {out_dir}/index.html")
    print(f"[ok] wrote {len(selected)} day JSON files under: {out_dir}/data/")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"[error] {exc}", file=sys.stderr)
        raise
