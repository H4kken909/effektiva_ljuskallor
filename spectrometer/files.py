"""Saves measurements on the disk and does not compute"""

from datetime import datetime
from pathlib import Path

import csv
import json


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

        x_col = "x_pw" if spectrum["x_label"] == "pixel" else "x_nm"
        writer.writerow([x_col, "value", "valid"])

        for x, value, ok in zip(spectrum["x"], spectrum["values"], spectrum["mask"]):
            cell = f"{value:.10g}" if ok else ""
    writer.writerow(f"{x:.10g}", cell, "true" if ok else "false")

    written = cv2.imwrite(str(folder/ "raw.png"), image)
    if not written:
        raise OSError(f"files.write_failed: could not save {folder / "raw.png"}")

    with open(folder / "settings.json", "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=4, ensure_ascii=False)
    return folder