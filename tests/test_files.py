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


def test_load_points(tmp_path):
    path = tmp_path / "punkter.csv"
    path.write_text("pixel,wavelength_nm,check\n100,500,0\n200,600,0\n180,581.5,1\n", encoding="utf-8")
    pixels, wavelengths, is_check = files.load_points(path)
    np.testing.assert_array_equal(pixels, [100, 200, 180])
    np.testing.assert_array_equal(wavelengths, [500, 600, 581.5])
    np.testing.assert_array_equal(is_check, [False, False, True])
    fel = tmp_path / "fel.csv"
    fel.write_text("pixel;wavelength_nm;check\n100;500;0\n", encoding="utf-8")
    np.testing.assert_raises_regex(ValueError, "rad 1: fel rubrik", files.load_points, fel)
    fel.write_text("pixel,wavelength_nm,check\n100,500\n", encoding="utf-8")
    np.testing.assert_raises_regex(ValueError, "rad 2: fel antal fält", files.load_points, fel)
    fel.write_text("pixel,wavelength_nm,check\n100,500,2\n", encoding="utf-8")
    np.testing.assert_raises_regex(ValueError, "rad 2: check ska vara 0 eller 1", files.load_points, fel)
