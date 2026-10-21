"""Läser en sparad mätmapp tillbaka: spectrum.csv och settings.json, som tal. Läser bara, skriver aldrig."""

import csv
import json
from pathlib import Path

import numpy as np

from spectrometer import files, out


def read(path):
    """Mätmappen path (eller dess spectrum.csv) som en ordbok: x, values, mask, x_label, columns, settings och folder.

    x är kolumnen x_nm när den finns och är ifylld, annars x_px (x_label "nm" eller "pixel"). values är kolumnen
    value med NaN i en tom cell; mask är sann där valid är true och värdet finns. columns har varje kolumn med tal
    (till exempel absorbance). settings är settings.json bredvid; saknas den blir det en tom ordbok och en varning.
    Fel: ValueError med input.invalid_argument om x_px/x_nm, value eller valid saknas; OSError om spectrum.csv saknas.
    """
    path = Path(path)
    # 1.2.13: en mapp utan spectrum.csv, eller en sökväg som inte finns, ger en Fel-rad i stället för [Errno 2]
    csv_path = files.measurement_folder(path) if path.is_dir() or not path.exists() else path
    with open(csv_path, newline="", encoding="utf-8-sig") as f:  # newline="": både CRLF och LF går
        reader = csv.reader(f)
        numbered = [(reader.line_num, row) for row in reader if row]
    for line_no, row in numbered[1:]:
        if len(row) != len(numbered[0][1]):  # en rad med fel antal fält ger annars IndexError nedan
            raise ValueError(f"input.invalid_argument: {csv_path.as_posix()} rad {line_no}: fel antal fält")
    rows = [row for _, row in numbered]
    header, body = (rows[0], rows[1:]) if rows else ([], [])
    columns = {}
    for k, name in enumerate(header):
        numbers = _numbers([row[k] for row in body])
        if numbers is not None:
            columns[name] = numbers
    x_name = "x_nm" if "x_nm" in columns and np.all(np.isfinite(columns["x_nm"])) else "x_px"
    if "value" not in columns or "valid" not in header or x_name not in columns:
        raise ValueError(f"input.invalid_argument: {csv_path.as_posix()}: kolumnerna x_px eller x_nm, value och valid behövs")
    valid = np.array([row[header.index("valid")] == "true" for row in body], dtype=bool)
    settings_path = csv_path.parent / "settings.json"
    settings = {}
    if settings_path.is_file():
        settings = json.loads(settings_path.read_text(encoding="utf-8"))
    else:
        out.warn(f"settings.json saknas i {csv_path.parent.as_posix()}, inställningarna är okända")
    return {"x": columns[x_name], "values": columns["value"], "mask": valid & np.isfinite(columns["value"]),
            "x_label": "nm" if x_name == "x_nm" else "pixel", "columns": columns, "settings": settings,
            "folder": csv_path.parent.as_posix()}


def _numbers(cells):
    """Cellerna som float64 med NaN för en tom cell, eller None om någon cell är text (som true och false)."""
    try:
        return np.array([float(cell) if cell.strip() else np.nan for cell in cells], dtype=np.float64)
    except ValueError:
        return None


def unit(settings):
    """Enheten för value ur settings.json: kvot (mode transmission), relativ signal (response on) eller counts."""
    if settings.get("mode") == "transmission":
        return "kvot"
    return "relativ signal" if settings.get("use_response") else "counts"


def require(saved, mode):
    """Fel om mätningen ur read inte är kalibrerad eller inte sparades i mode; "direct" kräver response on också.

    Fel: ValueError med input.missing_data som säger vad som saknas.
    """
    folder, settings = saved["folder"], saved["settings"]
    if saved["x_label"] != "nm":
        raise ValueError(f"input.missing_data: {folder}: ingen kalibrering (x är pixlar)")
    if mode == "transmission" and settings.get("mode") != "transmission":
        raise ValueError(f"input.missing_data: {folder}: inte en transmissionsmätning (mode transmission)")
    if mode == "direct" and (not settings.get("use_response") or settings.get("mode") != "direct"):
        raise ValueError(f"input.missing_data: {folder}: inte responskorrigerad (spara med response on i mode direct)")


def read_required(folder, mode):
    """En sparad mätmapp ur read, kontrollerad av require: kalibrerad och sparad i mode (transmission eller direct).

    Fel: ValueError med input.missing_data om mätningen saknar kalibrering eller inte passar mode.
    """
    saved = read(folder)
    require(saved, mode)  # kontrollen delas av prompten och analysskriptet
    return saved
