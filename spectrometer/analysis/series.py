import csv
from pathlib import Path

import numpy as np

COLUMNS = ["folder", "time", "current_mA", "voltage_V", "led", "sample", "lamp", "note", "peak", "peak_x", "area",
           "exposure", "gain"]


def add_row(series_csv, folder, saved, spectrum):
    x, values, mask = spectrum["x"], spectrum["values"], spectrum["mask"]
    row = dict(saved["annotations"], folder=Path(folder).as_posix(), time=saved["measured_at"],
               note=saved["note"] or "", exposure=saved["camera"].get("exposure"), gain=saved["camera"].get("gain"))
    if np.count_nonzero(mask) >= 2:
        i = int(np.argmax(np.where(mask, values, -np.inf)))
        row.update(peak=f"{values[i]:.10g}", peak_x=f"{x[i]:.10g}", area=f"{np.trapezoid(values[mask], x[mask]):.10g}")
    new = not Path(series_csv).exists()
    with open(series_csv, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        if new:
            writer.writeheader()
        writer.writerow({k: row.get(k, "") for k in COLUMNS})


def curve(series_csv):
    with open(series_csv, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    current = np.array([float(row["current_mA"]) if row["current_mA"] else np.nan for row in rows])
    area = np.array([float(row["area"]) if row["area"] else np.nan for row in rows])
    ok = (current > 0) & np.isfinite(area)
    current, area = current[ok], area[ok]
    xs = np.unique(current)
    groups = [np.sort(area[current == x]) for x in xs]
    return xs, np.array([g.mean() for g in groups])


def droop(xs, areas):
    eff = areas / xs
    return eff / np.nanmax(eff)
