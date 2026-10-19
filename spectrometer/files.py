"""Sparar mätningar på disk och läser punktfiler och kända fördelningar. Filen räknar inte.

Används av main.py (save, calibrate och response build).
"""
import csv
import json
import math
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np



def save_measurement(parent, spectrum, image, settings):
    """Sparar en mätning som en mapp, returnerar mätmappen som Path och kan kasta OSError."""

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")

    folder = Path(parent) / stamp

    counter = 2
    while folder.exists():
        folder = Path(parent) / f"{stamp}-{counter}"
        counter += 1

    folder.mkdir(parents=True)

    with open(folder / "spectrum.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        x_col = "x_px" if spectrum["x_label"] == "pixel" else "x_nm"
        writer.writerow([x_col, "value", "valid"])

        for x, value, ok in zip(spectrum["x"], spectrum["values"], spectrum["mask"]):
            cell = f"{value:.10g}" if ok else ""
            writer.writerow([f"{x:.10g}", cell, "true" if ok else "false"])

    written = cv2.imwrite(str(folder/ "raw.png"), image)
    if not written:
        raise OSError(f"files.write_failed: could not save {folder / "raw.png"}")

    with open(folder / "settings.json", "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=4, ensure_ascii=False)
    return folder

def load_points(path):
    """
    Läser en punktfil med kolumnerna pixel, wavelength_nm och check.

    Parametrar: path: sökvägen till CSV-filen (str eller Path); check är 0 för anpassning och 1 för kontroll
    Returnerar: (pixels, wavelengths, is_check): pixlar i hela bilden (K,) float64, våglängder i nm (K,) float64 och is_check (K,) bool, True för en kontrollpunkt.
    Fel: ValueError med input.invalid_argument, filnamnet och radnumret vid fel rubrik, fel antal fält, ett fält som inte är ett tal, ett ogiltigt värde eller check som inte är 0 eller 1; OSError om filen saknas.
    """
    name = Path(path).name
    pixels = []
    wavelengths = []
    is_check = []
    with open(path, encoding="utf-8-sig", newline="") as f:
        for line_no, row in enumerate(csv.reader(f), start=1):
            if not row:
                continue  # tom rad, en sist i filen är vanlig
            if line_no == 1:
                if row != ["pixel", "wavelength_nm", "check"]:
                    raise ValueError(f"input.invalid_argument: {name} rad {line_no}: fel rubrik, väntade pixel,wavelength_nm,check")
                continue
            if len(row) != 3:
                raise ValueError(f"input.invalid_argument: {name} rad {line_no}: fel antal fält, väntade 3")
            try:
                pixel = float(row[0])
            except ValueError as err:
                raise ValueError(f"input.invalid_argument: {name} rad {line_no}: pixel är inte ett tal") from err
            try:
                wavelength = float(row[1])
            except ValueError as err:
                raise ValueError(f"input.invalid_argument: {name} rad {line_no}: wavelength_nm är inte ett tal") from err
            if not math.isfinite(pixel) or pixel < 0:
                raise ValueError(f"input.invalid_argument: {name} rad {line_no}: pixel har ett ogiltigt värde")
            if row[2] not in ("0", "1"):
                raise ValueError(f"input.invalid_argument: {name} rad {line_no}: check ska vara 0 eller 1")
            pixels.append(pixel)
            wavelengths.append(wavelength)
            is_check.append(row[2] == "1")
    pixels = np.array(pixels, dtype=np.float64)
    wavelengths = np.array(wavelengths, dtype=np.float64)
    is_check = np.array(is_check, dtype=bool)
    return pixels, wavelengths, is_check
def load_known(path):
    """Läser en känd fördelning med kolumnerna wavelength_nm och relative_power_per_nm.

    Parametrar: path: sökvägen till CSV-filen (str eller Path).
    Returnerar: (wavelengths, values): våglängder i stigande nm (K,) float64 och relativ effekt per nm (K,) float64.
    Fel: ValueError med input.invalid_argument, filnamnet och radnumret vid fel rubrik, fel antal fält, ett fält som
    inte är ett tal, ett ogiltigt värde, en våglängd som inte stiger eller färre än två datarader; OSError om filen saknas.
    """
    name = Path(path).name
    wavelengths = []
    values = []
    with open(path, encoding="utf-8-sig", newline="") as f:
        for line_no, row in enumerate(csv.reader(f), start=1):
            if not row:
                continue  # tom rad, en sist i filen är vanlig
            if line_no == 1:
                if row != ["wavelength_nm", "relative_power_per_nm"]:
                    raise ValueError(f"input.invalid_argument: {name} rad {line_no}: fel rubrik {row}")
                continue
            if len(row) != 2:
                raise ValueError(f"input.invalid_argument: {name}: fel antal fält, rad {line_no}")
            try:
                wavelength = float(row[0])
                power = float(row[1])
            except ValueError as err:
                raise ValueError(f"input.invalid_argument: {name}: fältet är inte ett tal, rad {line_no}") from err
            if not (math.isfinite(wavelength) and math.isfinite(power)) or power < 0:
                raise ValueError(f"input.invalid_argument: {name}: ogiltigt värde, rad {line_no}")
            if wavelengths and wavelength <= wavelengths[-1]:
                raise ValueError(f"input.invalid_argument: {name}: våglängden stiger inte, rad {line_no}")
            wavelengths.append(wavelength)
            values.append(power)
    if len(wavelengths) < 2:
        raise ValueError(f"input.invalid_argument: färre än två datarader i {name}")
    return np.array(wavelengths, dtype=np.float64), np.array(values, dtype=np.float64)