import csv
import json
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np


def cell(number):
    if isinstance(number, np.bool_):
        return "true" if number else "false"
    return f"{number:.10g}" if np.isfinite(number) else ""


def save_measurement(parent, spectrum, image, settings):
    moment = datetime.fromisoformat(settings["measured_at"]) if "measured_at" in settings else datetime.now()
    stem = moment.strftime("%Y%m%d-%H%M%S")
    folder = Path(parent) / stem
    counter = 2
    while folder.exists():
        folder = Path(parent) / f"{stem}-{counter}"
        counter += 1
    folder.mkdir(parents=True)
    x_name = "x_px" if spectrum["x_label"] == "pixel" else "x_nm"
    mask, values = spectrum["mask"], spectrum["values"]
    columns = {x_name: spectrum["x"], "value": np.where(mask, values, np.nan), "valid": mask}
    if settings.get("mode") == "transmission":
        positive = mask & (values > 0)
        columns["absorbance"] = np.where(positive, -np.log10(np.where(positive, values, 1.0)), np.nan)
    if "raw" in spectrum:
        columns["raw_counts"] = spectrum["raw"]
        if "stddev" in spectrum:
            columns["stddev"] = np.where(np.isfinite(spectrum["raw"]), spectrum["stddev"], np.nan)
    if "px" in spectrum and x_name == "x_nm":
        columns["x_px"] = spectrum["px"]
    with open(folder / "spectrum.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(columns)
        for row in zip(*columns.values()):
            writer.writerow([cell(number) for number in row])
    cv2.imencode(".png", image)[1].tofile(folder / "raw.png")
    with open(folder / "settings.json", "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)
    return folder


def save_excel(folder):
    path = Path(folder) / "spectrum_sv.csv"
    with open(Path(folder) / "spectrum.csv", newline="", encoding="utf-8") as f:
        text = f.read()
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        f.write(text.replace(",", ";").replace(".", ","))
    return path


def read_table(path, header):
    with open(path, encoding="utf-8-sig") as f:
        lines = [line for line in f if line.strip() and not line.startswith("#")]
    if not lines or lines[0].strip().split(",") != header:
        raise ValueError(f"{Path(path).name}: wrong header, expected {','.join(header)}")
    name = Path(path).name
    if len(lines) < 2:
        raise ValueError(f"{name}: no data rows")
    try:
        table = np.loadtxt(lines[1:], delimiter=",", ndmin=2)
    except ValueError:
        raise ValueError(f"{name}: a value is not a number") from None
    if table.shape[1] != len(header):
        raise ValueError(f"{name}: needs {len(header)} columns")
    return table


def load_points(path):
    pixels, wavelengths, is_check = read_table(path, ["pixel", "wavelength_nm", "check"]).T
    if not np.all((is_check == 0) | (is_check == 1)):
        raise ValueError(f"{Path(path).name}: check must be 0 or 1")
    return pixels, wavelengths, is_check == 1


def load_known(path):
    wavelengths, values = read_table(path, ["wavelength_nm", "relative_power_per_nm"]).T
    if wavelengths.size < 2:
        raise ValueError(f"{Path(path).name}: needs at least 2 rows")
    if np.any(np.diff(wavelengths) <= 0):
        raise ValueError(f"{Path(path).name}: the wavelength must increase")
    return wavelengths, values


def load_lines(path):
    lines = read_table(path, ["wavelength_nm"])[:, 0]
    if lines.size < 2:
        raise ValueError(f"{Path(path).name}: needs at least 2 rows")
    return np.sort(lines)


def load_measurement(folder):
    folder = Path(folder)
    if not (folder / "spectrum.csv").is_file() or not (folder / "settings.json").is_file():
        raise ValueError(f"{folder.as_posix()} is not a measurement folder")
    with open(folder / "spectrum.csv", newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise ValueError(f"{(folder / 'spectrum.csv').as_posix()} has no rows")
    for name in ("value", "valid", "raw_counts", "stddev"):
        if name not in rows[0]:
            raise ValueError(f"{(folder / 'spectrum.csv').as_posix()} has no column {name}")
    x_col = "x_nm" if "x_nm" in rows[0] else "x_px"

    def column(name):
        return np.array([float(row[name]) if row[name] else np.nan for row in rows])

    settings = json.loads((folder / "settings.json").read_text(encoding="utf-8"))
    y_label = "signal (counts)"
    if settings.get("mode") == "transmission":
        y_label = "transmission (ratio)"
    elif settings.get("use_response"):
        y_label = "corrected signal (relative)"
    spectrum = {
        "x": column(x_col),
        "values": column("value"),
        "mask": np.array([row["valid"] == "true" for row in rows]),
        "x_label": "pixel" if x_col == "x_px" else "wavelength (nm)",
        "y_label": y_label,
        "settings": settings,
        "folder": folder.as_posix(),
        "raw": column("raw_counts"),
        "stddev": column("stddev"),
        "frames": settings.get("frames"),
    }
    if x_col == "x_nm" and "x_px" in rows[0]:
        spectrum["px"] = column("x_px")
    return spectrum
