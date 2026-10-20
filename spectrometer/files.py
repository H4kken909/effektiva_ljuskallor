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
    """Sparar en mätning som en mapp med spectrum.csv, raw.png och settings.json.

    Parametrar: parent: föräldramappen (str eller Path); spectrum: ordboken från measure med x, values, mask,
    x_label och y_label; image: råbilden, (H, W, 3) uint8; settings: inställningarna (bara tal, text, tuple,
    listor, bool och None).
    Returnerar: mätmappen som Path, till exempel data/20261016-153012 eller data/20261016-153012-2.
    Fel: OSError om något inte går att skriva, med files.write_failed om raw.png inte sparas.
    """
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    folder = Path(parent) / stamp
    counter = 2
    while folder.exists():
        folder = Path(parent) / f"{stamp}-{counter}"
        counter += 1
    folder.mkdir(parents=True)
    transmission = (
        settings.get("mode") == "transmission"
    )  # valfritt (0.9.3): kolumnen absorbance
    with open(folder / "spectrum.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        x_col = "x_px" if spectrum["x_label"] == "pixel" else "x_nm"
        header = [x_col, "value", "valid"]
        if transmission:
            header.append("absorbance")
        writer.writerow(header)
        for x, value, ok in zip(spectrum["x"], spectrum["values"], spectrum["mask"]):
            cell = f"{value:.10g}" if ok else ""
            row = [f"{x:.10g}", cell, "true" if ok else "false"]
            if transmission:
                # Absorbans A = -log10(T), tom där T saknas eller är 0 eller mindre. Se rev7, Krav 22.
                row.append(f"{-math.log10(value):.10g}" if ok and value > 0 else "")
            writer.writerow(row)
    raw_path = folder / "raw.png"
    try:
        written, encoded = cv2.imencode(".png", image)  # imencode och tofile, inte imwrite: klarar åäö i Windows
        if written:
            encoded.tofile(raw_path)
    except OSError:
        written = False
    if not written:
        raise OSError(f"files.write_failed: raw.png kunde inte sparas: {raw_path}")
    with open(folder / "settings.json", "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)
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
                    raise ValueError(
                        f"input.invalid_argument: {name} rad {line_no}: fel rubrik, väntade pixel,wavelength_nm,check"
                    )
                continue
            if len(row) != 3:
                raise ValueError(
                    f"input.invalid_argument: {name} rad {line_no}: fel antal fält, väntade 3"
                )
            try:
                pixel = float(row[0])
            except ValueError as err:
                raise ValueError(
                    f"input.invalid_argument: {name} rad {line_no}: pixel är inte ett tal"
                ) from err
            try:
                wavelength = float(row[1])
            except ValueError as err:
                raise ValueError(
                    f"input.invalid_argument: {name} rad {line_no}: wavelength_nm är inte ett tal"
                ) from err
            if not math.isfinite(pixel) or pixel < 0:
                raise ValueError(
                    f"input.invalid_argument: {name} rad {line_no}: pixel har ett ogiltigt värde"
                )
            if row[2] not in ("0", "1"):
                raise ValueError(
                    f"input.invalid_argument: {name} rad {line_no}: check ska vara 0 eller 1"
                )
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
                    raise ValueError(
                        f"input.invalid_argument: {name} rad {line_no}: fel rubrik {row}"
                    )
                continue
            if len(row) != 2:
                raise ValueError(
                    f"input.invalid_argument: {name}: fel antal fält, rad {line_no}"
                )
            try:
                wavelength = float(row[0])
                power = float(row[1])
            except ValueError as err:
                raise ValueError(
                    f"input.invalid_argument: {name}: fältet är inte ett tal, rad {line_no}"
                ) from err
            if not (math.isfinite(wavelength) and math.isfinite(power)) or power < 0:
                raise ValueError(
                    f"input.invalid_argument: {name}: ogiltigt värde, rad {line_no}"
                )
            if wavelengths and wavelength <= wavelengths[-1]:
                raise ValueError(
                    f"input.invalid_argument: {name}: våglängden stiger inte, rad {line_no}"
                )
            wavelengths.append(wavelength)
            values.append(power)
    if len(wavelengths) < 2:
        raise ValueError(f"input.invalid_argument: färre än två datarader i {name}")
    return np.array(wavelengths, dtype=np.float64), np.array(values, dtype=np.float64)
