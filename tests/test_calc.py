import json
from pathlib import Path

import cv2
import numpy as np
import pytest

from spectrometer.core import registry, session
from spectrometer.measurement import calc


def test_rx02():
    image = np.zeros((2, 103, 3), dtype="uint8")
    image[0:2, 100:103, 2] = [[40, 255, 10], [42, 200, 12]]
    result_h = calc.prepare(image, (100, 0, 3, 2), "horizontal", "red")
    assert result_h.shape == (2, 3)
    np.testing.assert_array_equal(result_h, [[40, 255, 10], [42, 200, 12]])
    result_v = calc.prepare(image, (100, 0, 3, 2), "vertical", "red")
    assert result_v.shape == (3, 2)
    np.testing.assert_array_equal(result_v, [[40, 42], [255, 200], [10, 12]])


def test_rx01_gray():
    image = np.array([[[50, 100, 200]]], dtype="uint8")
    result = calc.prepare(image, (0, 0, 1, 1), "horizontal", "gray")
    np.testing.assert_allclose(result, 124.2, rtol=1e-9, atol=1e-9)


def test_rx06():
    stack = np.array([[2, 10, 5], [4, 10, 7]], dtype=np.float64)
    mean, stddev = calc.average_spectra(stack)
    np.testing.assert_allclose(mean, [3, 10, 6], rtol=1e-9, atol=1e-9)
    np.testing.assert_allclose(stddev, [np.sqrt(2), 0, np.sqrt(2)], rtol=1e-9, atol=1e-9)
    mean1, stddev1 = np.testing.assert_no_warnings(calc.average_spectra, stack[:1])
    np.testing.assert_allclose(mean1, [2, 10, 5], rtol=1e-9, atol=1e-9)
    assert np.isnan(stddev1).all()


def test_rx09_eval():
    pixels = np.array([100, 150, 180, 200], dtype=np.float64)
    coefficients = np.array([400, 1], dtype=np.float64)
    np.testing.assert_allclose(calc.evaluate_wavelength(pixels, coefficients), [500, 550, 580, 600], rtol=1e-9, atol=1e-9)


def test_fit_rx10():
    pixels = np.array([100, 150, 200], dtype=np.float64)
    wavelengths = np.array([500, 551, 600], dtype=np.float64)
    coefficients = calc.fit_wavelength(pixels, wavelengths, 1)
    np.testing.assert_allclose(coefficients, [400 + 1/3, 1], rtol=1e-9, atol=1e-9)
    residuals = wavelengths - calc.evaluate_wavelength(pixels, coefficients)
    np.testing.assert_allclose(residuals, [-1/3, 2/3, -1/3], rtol=1e-9, atol=1e-9)


def test_rx16():
    values, mask = calc.apply_response(np.array([1.0, 2.0, 2.0, 3.0, 3.0]), np.array([0.5, 1.0, 1.0, 0.005, 0.01]), np.array([True, True, True, True, True]), minimum=0.01)
    np.testing.assert_allclose(values, [2.0, 2.0, 2.0, np.nan, np.nan], rtol=1e-9, atol=1e-9)
    np.testing.assert_array_equal(mask, [True, True, True, False, False])


def test_response_rx14():
    x = np.arange(500, 541, 10)
    np.testing.assert_allclose(calc.build_response(x, np.array([2.0, 4.0, 8.0, 0.02, 0.04]), x, np.array([1.0, 1.0, 2.0, 1.0, 1.0])), [0.5, 1.0, 1.0, 0.005, 0.01], rtol=1e-9, atol=1e-9)


def test_response_rx15():
    np.testing.assert_allclose(calc.build_response(np.array([505.0, 510.0, 530.0]), np.array([1.25, 3.0, 1.0]), np.array([500.0, 520.0]), np.array([1.0, 2.0])), [0.5, 1.0, np.nan], equal_nan=True)


def test_rx17():
    values, mask = calc.apply_response(np.array([25, -2, 60, 5, 0.5], dtype=np.float64), np.array([50, 40, 50, 0.8, 1.0], dtype=np.float64), np.array([True, True, True, True, True]), minimum=1.0)
    np.testing.assert_allclose(values, [0.5, -0.05, 1.2, np.nan, np.nan], rtol=1e-9, atol=1e-9)
    np.testing.assert_array_equal(mask, [True, True, True, False, False])


def test_fit_refuses_equal_pixels():
    with pytest.raises(ValueError, match="different pixel"):
        calc.fit_wavelength(np.zeros(3), np.array([500.0, 510.0, 520.0]), 1)


def test_same_setting_keeps_response():
    state = session.new_state(session.DEFAULTS)
    state["response"] = np.ones(5)
    session.set_setting(state, "channel", "gray")
    assert state["response"] is not None
    session.set_setting(state, "channel", "red")
    assert state["response"] is None


def spectrum_image(lines, width=640, height=8, sigma=1.5, noise=0.0, seed=1):
    columns = np.arange(width, dtype=np.float64)
    row = np.zeros(width)
    for pixel, top in lines:
        row += top * np.exp(-0.5 * ((columns - pixel) / sigma) ** 2)
    table = row + np.random.default_rng(seed).normal(0, noise, (height, width))
    gray = np.clip(np.round(table), 0, 255).astype("uint8")
    return np.dstack([gray, gray, gray])


def state_with_image(tmp_path, image):
    path = tmp_path / "spectrum.png"
    cv2.imwrite(str(path), image)
    state = session.new_state(session.DEFAULTS)
    registry.run_command(state, f"source file {path.as_posix()}")
    return state


def peak_rows(text):
    return [row.split() for row in text.splitlines() if row.startswith("peak ")]


def test_peaks_pixels_in_whole_image(tmp_path, capsys):
    state = state_with_image(tmp_path, spectrum_image([(100.4, 200), (250, 120), (400.7, 60), (500, 10)]))
    registry.run_command(state, "roi 50 0 500 8")
    registry.run_command(state, "step")
    capsys.readouterr()
    registry.run_command(state, "peaks")
    rows = peak_rows(capsys.readouterr().out)
    assert [row[:3] for row in rows] == [["peak", "1:", "pixel"], ["peak", "2:", "pixel"], ["peak", "3:", "pixel"]]
    np.testing.assert_allclose([float(row[3]) for row in rows], [100.4, 250, 400.7], atol=0.15)
    assert rows[0][4:] == ["value", "193"]
    registry.run_command(state, "peaks 2")
    rows = peak_rows(capsys.readouterr().out)
    np.testing.assert_allclose([float(row[3]) for row in rows], [100.4, 250], atol=0.15)


ROOT = Path(__file__).resolve().parents[1]
HG = [404.656, 435.833, 546.074, 576.960, 579.066]
LINES = (ROOT / "examples" / "calibration" / "hg_lines.csv").as_posix()


def hg_image(nm_per_pixel=0.4, sigma=1.5, noise=2.0):
    pixels = [(nm - 380) / nm_per_pixel for nm in HG]
    image = spectrum_image(list(zip(pixels, [120, 200, 230, 90, 100])), 640, 480, sigma, noise)
    return image, pixels


def point_rows(text):
    return [row.split(",") for row in text.splitlines() if row[:1].isdigit()]


def test_peaks_line_file_proposes_rows(tmp_path, capsys):
    image, pixels = hg_image()
    state = state_with_image(tmp_path, image)
    registry.run_command(state, "step")
    capsys.readouterr()
    registry.run_command(state, f"peaks {LINES}")
    text = capsys.readouterr().out
    rows = point_rows(text)
    np.testing.assert_allclose([float(row[0]) for row in rows], pixels, atol=0.2)
    assert [row[1] for row in rows] == ["404.656", "435.833", "546.074", "576.96", "579.066"]
    assert [row[2] for row in rows] == ["0", "1", "0", "0", "0"]
    assert "Warning" not in text
    assert state["coefficients"] is None


def calibrate_text(state, tmp_path, rows, words="", name="p.csv"):
    points = tmp_path / name
    points.write_text("pixel,wavelength_nm,check\n" + "\n".join(rows) + "\n", encoding="utf-8")
    registry.run_command(state, f"calibrate {points.as_posix()} {words}".strip())
    return points


def test_calibrate_units_and_range(tmp_path, capsys):
    state = session.new_state(session.DEFAULTS)
    calibrate_text(state, tmp_path, ["100,500,0", "200,600,0"])
    text = capsys.readouterr().out
    assert "a0: 400 nm\na1: 1 nm/pixel\n" in text
    assert "valid: pixel 0 to 300" in text
    assert state["pixel_range"] == (0, 300)
    with pytest.raises(ValueError, match="DEGREE"):
        calibrate_text(state, tmp_path, ["100,500,0", "200,600,0"], "0", "q.csv")


def test_save_keeps_calibration(tmp_path):
    state = state_with_image(tmp_path, spectrum_image([(100, 200)], width=320))
    points = calibrate_text(state, tmp_path, ["100,500,0", "200,600,0"])
    registry.run_command(state, "step")
    registry.run_command(state, f"save {(tmp_path / 'data').as_posix()}")
    folder = next((tmp_path / "data").iterdir())
    saved = json.loads((folder / "settings.json").read_text(encoding="utf-8"))
    assert saved["calibration_points_file"] == points.as_posix()
    assert saved["coefficients"] == pytest.approx([400, 1])


def test_peaks_and_fwhm_need_a_positive_number(tmp_path):
    state = state_with_image(tmp_path, spectrum_image([(100.4, 200)]))
    registry.run_command(state, "step")
    for command in ("peaks -1", "peaks 0", "fwhm -1"):
        with pytest.raises(ValueError, match="at least 1"):
            registry.run_command(state, command)
