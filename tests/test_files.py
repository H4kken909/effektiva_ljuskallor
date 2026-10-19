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


def test_load_known_rx14(tmp_path):
    """RX14, T16: load_known ger våglängderna och värdena; våglängder som inte stiger eller färre än två rader ger fel."""
    known_file = tmp_path / "rx14_t16.csv"
    known_file.write_text("wavelength_nm,relative_power_per_nm\n500,1\n510,1\n520,2\n530,1\n540,1\n", encoding="utf-8")
    wavelengths, values = files.load_known(known_file)
    np.testing.assert_allclose(wavelengths, [500, 510, 520, 530, 540], rtol=1e-9, atol=1e-9)
    np.testing.assert_allclose(values, [1, 1, 2, 1, 1], rtol=1e-9, atol=1e-9)
    for text in ("wavelength_nm,relative_power_per_nm\n500,1\n490,1\n", "wavelength_nm,relative_power_per_nm\n500,1\n"):
        known_file.write_text(text, encoding="utf-8")
        try:
            files.load_known(known_file)
        except ValueError as error:
            assert "input.invalid_argument" in str(error)
        else:
            raise AssertionError(f"load_known godtog {text!r}")
