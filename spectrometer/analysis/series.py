"""Mätserier: en rad per mätning i serie.csv, och analysen uteffekt mot ström (Krav 18) och droop (Krav 21)."""

import csv
from pathlib import Path

import numpy as np

COLUMNS = ["folder", "time", "current_mA", "voltage_V", "led", "sample", "lamp", "note", "peak", "peak_x", "area",
           "exposure", "gain"]


def append(series_csv, row):
    """Lägger en rad i serie.csv (skapar med rubrik). row: dict med nycklar ur COLUMNS; tomt för saknade."""
    path = Path(series_csv)
    new = not path.exists()
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        if new:
            w.writeheader()
        w.writerow({k: row.get(k, "") for k in COLUMNS})


def load(series_csv):
    """Läser serie.csv till en lista av dict med tal som float där det går."""
    rows = []
    with open(series_csv, newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            for k in ("current_mA", "voltage_V", "peak", "peak_x", "area", "exposure", "gain"):
                try:
                    r[k] = float(r[k])
                except (ValueError, TypeError):
                    r[k] = float("nan")
            rows.append(r)
    return rows


def table(rows, x="current_mA"):
    """(x, area, area/x) sorterat på x, utan rader som saknar x eller area."""
    pts = [(r[x], r["area"]) for r in rows if np.isfinite(r[x]) and np.isfinite(r["area"]) and r[x] > 0]
    pts.sort()
    xs = np.array([p[0] for p in pts])
    areas = np.array([p[1] for p in pts])
    return xs, areas, areas / xs


def droop(xs, areas):
    """Relativ effektivitet area/I normerad till sitt max: 1,0 där dioden är som effektivast. Aldrig absolut."""
    eff = areas / xs
    return eff / np.nanmax(eff) if np.any(np.isfinite(eff)) else eff


def add_row(series_csv, folder, saved, spectrum):
    """Lägger mätningen i folder som en rad i serie.csv: tid, series note, note, topp, area och exponering. Ger antalet rader.

    area är trapetsytan under kurvan där masken är sann: relativ uteffekt (counts·nm eller counts·pixel), aldrig watt.
    exposure och gain är vad drivrutinen sa under mätningen (tomt för en bildfil).
    """
    x, values, mask = spectrum["x"], spectrum["values"], spectrum["mask"]
    row = dict(saved.get("annotations") or {}, folder=Path(folder).as_posix(), time=saved.get("measured_at", ""),
               note=saved.get("note") or "")
    if np.count_nonzero(mask) >= 2:
        i = int(np.argmax(np.where(mask, values, -np.inf)))
        row.update(peak=f"{values[i]:.10g}", peak_x=f"{x[i]:.10g}", area=f"{np.trapezoid(values[mask], x[mask]):.10g}")
    camera = saved.get("camera") or {}
    row.update(exposure=camera.get("exposure"), gain=camera.get("gain"))
    append(series_csv, row)
    return len(load(series_csv))


def repeats(xs, areas):
    """Mätningar vid samma x slås ihop: (x, medel, spridning, antal), x stigande. 1.2.14.

    Spridningen är stickprovets (ddof=1) mellan de upprepade mätningarna, NaN där x bara mättes en gång (RAP-14:
    osäkerheten är spridningen mellan upprepade mätningar; total osäkerhet är inte kvantifierad).
    """
    xs, areas = np.asarray(xs, dtype=np.float64), np.asarray(areas, dtype=np.float64)
    unique = np.unique(xs)
    groups = [areas[xs == value] for value in unique]
    means = np.array([group.mean() for group in groups])
    spreads = np.array([group.std(ddof=1) if group.size > 1 else np.nan for group in groups])
    return unique, means, spreads, np.array([group.size for group in groups])
