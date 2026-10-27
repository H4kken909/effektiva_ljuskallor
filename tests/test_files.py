import csv
import json

import cv2
import numpy as np
import pytest
from helpers import line_image, new_state, terminal

from spectrometer.core import files, registry


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


def test_load_points(tmp_path):
    path = tmp_path / "points.csv"
    path.write_text("pixel,wavelength_nm,check\n100,500,0\n200,600,0\n180,581.5,1\n", encoding="utf-8")
    pixels, wavelengths, is_check = files.load_points(path)
    np.testing.assert_array_equal(pixels, [100, 200, 180])
    np.testing.assert_array_equal(wavelengths, [500, 600, 581.5])
    np.testing.assert_array_equal(is_check, [False, False, True])
    bad_file = tmp_path / "bad.csv"
    bad_file.write_text("pixel;wavelength_nm;check\n100;500;0\n", encoding="utf-8")
    np.testing.assert_raises_regex(ValueError, "wrong header", files.load_points, bad_file)
    bad_file.write_text("pixel,wavelength_nm,check\n100,500\n", encoding="utf-8")
    np.testing.assert_raises_regex(ValueError, "needs 3 columns", files.load_points, bad_file)
    bad_file.write_text("pixel,wavelength_nm,check\n100,500,2\n", encoding="utf-8")
    np.testing.assert_raises_regex(ValueError, "check must be 0 or 1", files.load_points, bad_file)
    bad_file.write_text("pixel,wavelength_nm,check\n100,abc,0\n", encoding="utf-8")
    np.testing.assert_raises_regex(ValueError, "bad.csv: a value is not a number", files.load_points, bad_file)
    bad_file.write_text("pixel,wavelength_nm,check\n", encoding="utf-8")
    np.testing.assert_raises_regex(ValueError, "bad.csv: no data rows", files.load_points, bad_file)


def measured(tmp_path):
    path = tmp_path / "image.png"
    cv2.imwrite(str(path), line_image())
    state = new_state()
    registry.run_command(state, f"source file {path.as_posix()}")
    registry.run_command(state, "step")
    return state, tmp_path / "data"


def test_save_never_overwrites(tmp_path):
    state, data = measured(tmp_path)
    settings = {"measured_at": "2026-10-16T15:30:12"}
    first = files.save_measurement(data, state["spectrum"], state["image"], settings)
    before = (first / "spectrum.csv").read_bytes()
    second = files.save_measurement(data, state["spectrum"], state["image"], settings)
    assert (first.name, second.name) == ("20261016-153012", "20261016-153012-2")
    assert (first / "spectrum.csv").read_bytes() == before


def test_quit_asks_in_terminal_when_unsaved(monkeypatch, tmp_path):
    state, data = measured(tmp_path)
    asked = terminal(monkeypatch, ["n", "y"])
    assert registry.run_command(state, "quit") is None
    assert registry.run_command(state, "quit") is True
    assert asked == ["The measurement is not saved. Quit anyway? (y/n) "] * 2
    registry.run_command(state, f"save {data.as_posix()}")
    assert registry.run_command(state, "quit") is True
    assert len(asked) == 2


def saved_folder(tmp_path, capsys, *lines):
    image, points = tmp_path / "image.png", tmp_path / "p.csv"
    cv2.imwrite(str(image), line_image())
    points.write_text("pixel,wavelength_nm,check\n0,400.5,0\n19,590.5,0\n", encoding="utf-8")
    state = new_state()
    for line in (f"source file {image.as_posix()}", f"calibrate {points.as_posix()}", *lines, "step",
                 f"save {(tmp_path / 'data').as_posix()} --excel"):
        registry.run_command(state, line)
    capsys.readouterr()
    return state, next((tmp_path / "data").iterdir())


def test_csv_has_raw_counts_and_pixel_last(tmp_path, capsys):
    _, folder = saved_folder(tmp_path, capsys)
    with open(folder / "spectrum.csv", newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    assert rows[0] == ["x_nm", "value", "valid", "raw_counts", "stddev", "x_px"]
    assert rows[13] == ["520.5", "200", "true", "200", "", "12"]
    text = (folder / "spectrum_sv.csv").read_text(encoding="utf-8-sig").splitlines()
    assert text[0] == "x_nm;value;valid;raw_counts;stddev;x_px"
    assert text[13] == "520,5;200;true;200;;12"


def test_load_gives_back_the_measurement(tmp_path, capsys):
    state, folder = saved_folder(tmp_path, capsys)
    measured = state["spectrum"]
    registry.run_command(state, f"load {folder.as_posix()}")
    assert capsys.readouterr().out.splitlines() == [
        f"loaded: {folder.as_posix()} (20 position(s))",
    ]
    loaded = state["spectrum"]
    np.testing.assert_allclose(loaded["x"], measured["x"])
    np.testing.assert_array_equal(loaded["mask"], measured["mask"])
    np.testing.assert_allclose(loaded["values"][loaded["mask"]], measured["values"][measured["mask"]])
    assert (loaded["x_label"], loaded["y_label"]) == (measured["x_label"], measured["y_label"])
    np.testing.assert_array_equal(loaded["px"], np.arange(20.0))
    for line in ("save", "peaks"):
        with pytest.raises(ValueError, match="load"):
            registry.run_command(state, line)


def saved_settings_with(tmp_path, name, lines_before=(), lines_after=()):
    picture = tmp_path / "image.png"
    cv2.imwrite(str(picture), line_image())
    state = new_state()
    data = tmp_path / name
    for line in (f"source file {picture.as_posix()}", *lines_before, "step", *lines_after, f"save {data.as_posix()}"):
        registry.run_command(state, line)
    settings = json.loads((next(data.iterdir()) / "settings.json").read_text(encoding="utf-8"))
    return settings


def test_settings_json_has_controls_and_note(tmp_path):
    plain = saved_settings_with(tmp_path, "a")
    assert "controls" in plain and "note" in plain
    settings = saved_settings_with(tmp_path, "c", lines_after=("note hello",))
    assert settings["note"] == "hello"
    settings = saved_settings_with(tmp_path, "f", lines_before=("exposure -6",))
    assert settings["controls"] is not None
    keys = list(settings)
    assert keys[-4:] == ["coefficients", "dark", "use_response", "mode"]
