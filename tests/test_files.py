"""Testar att save_measurement skriver rätt spectrum.csv"""

import csv

import numpy as np

from spectrometer import files


def small():
    spectrum = {
        "x": np.array([0, 1, 2], dtype="float64"),
        "values": np.array([1.5, 2, 3], dtype="float64"),
        "mask": np.array([True, False, True]),
        "x_label": "pixel",
        "y_label": "signal (counts)",
    }
    image = np.zeros((2, 3, 3), dtype="uint8")
    settings = {"roi": (0, 0, 3, 2), "channel": "gray"}

    return spectrum, image, settings

def test_csv(tmp_path):
    spectrum, image, settings = small()
    folder = files.save_measurement(tmp_path, spectrum, image, settings)
    with open(folder / "spectrum.csv", newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))

    assert rows[0] == ["x_px", "value", "valid"]
    assert rows[1] == ["0", "1.5", "true"]
    assert rows[2] == ["1", "", "false"]
    assert rows[0] == ["x_px", "value", "valid"]