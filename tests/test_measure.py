import csv

import cv2
import numpy as np
import pytest
from helpers import (
    cameras,
    line_image,
    new_state,
    terminal,
    transmission_state,
    use_camera,
)

from spectrometer.analysis import series
from spectrometer.core import registry, session
from spectrometer.measurement import measure


def test_dark_running_mean(monkeypatch):
    cameras(monkeypatch, [line_image(value=v) for v in (90, 100, 110)])
    state = new_state()
    registry.run_command(state, "source camera 0")
    registry.run_command(state, "dark 3")
    assert state["dark"].dtype == np.float64
    assert state["dark"].shape == (10, 20, 3)
    assert np.all(state["dark"][:, 12] == 100)
    assert np.all(state["dark"][:, :12] == 0)


def test_reference_prints_peak(tmp_path, capsys):
    black = tmp_path / "black.png"
    lamp = tmp_path / "lamp.png"
    cv2.imwrite(str(black), np.zeros((10, 20, 3), dtype="uint8"))
    cv2.imwrite(str(lamp), line_image())
    state = new_state()
    for line in (f"source file {black.as_posix()}", "dark 1", f"source file {lamp.as_posix()}"):
        registry.run_command(state, line)
    capsys.readouterr()
    registry.run_command(state, "reference 1")
    assert capsys.readouterr().out == "Reference: peak 200\n"


def test_transmission_steps(monkeypatch, capsys):
    frames = [line_image(value=0), line_image(value=100), line_image(value=108), line_image(value=104)]
    cameras(monkeypatch, frames)
    state = new_state()
    for line in ("source camera 0", "dark 1", "reference 1", "mode transmission"):
        registry.run_command(state, line)
    capsys.readouterr()
    registry.run_command(state, "step")
    assert capsys.readouterr().out.splitlines() == [
        "Opening the camera ...",
        "Peak 1.08 at pixel 12 (1 frame)",
        "Warning: transmission above 105 % at some positions",
    ]
    registry.run_command(state, "step")
    assert capsys.readouterr().out.splitlines() == ["Opening the camera ...", "Peak 1.04 at pixel 12 (1 frame)"]


def test_losing_the_reference_in_direct_says_nothing_about_mode(tmp_path, capsys):
    state = transmission_state(tmp_path)
    registry.run_command(state, "mode direct")
    capsys.readouterr()
    registry.run_command(state, "channel green")
    assert capsys.readouterr().out.splitlines() == ["Reference forgotten. Run reference again.", "channel: green"]
    assert state["mode"] == "direct"


def chain_files(tmp_path):
    black = np.zeros((10, 20, 3), dtype="uint8")
    lamp = black.copy()
    lamp[:, 10], lamp[:, 11], lamp[:, 12] = 5, 100, 200
    cv2.imwrite(str(tmp_path / "black.png"), black)
    cv2.imwrite(str(tmp_path / "lamp.png"), lamp)
    (tmp_path / "points.csv").write_text("pixel,wavelength_nm,check\n10,500,0\n12,520,0\n", encoding="utf-8")
    (tmp_path / "known.csv").write_text(
        "wavelength_nm,relative_power_per_nm\n490,1\n500,1\n510,1\n520,2\n530,1\n", encoding="utf-8"
    )
    names = {"black": "black.png", "lamp": "lamp.png", "points": "points.csv", "known": "known.csv"}
    return {key: (tmp_path / name).as_posix() for key, name in names.items()}


def calibrated(tmp_path):
    paths = chain_files(tmp_path)
    state = new_state()
    for line in (f"source file {paths['black']}", "dark 1", f"source file {paths['lamp']}", "roi 10 0 3 2",
                 "channel red", f"calibrate {paths['points']}"):
        registry.run_command(state, line)
    return state, paths


def test_response_on_in_transmission(tmp_path, capsys):
    state, paths = calibrated(tmp_path)
    for line in (f"response build {paths['known']} 1", "reference 1", "mode transmission"):
        registry.run_command(state, line)
    capsys.readouterr()
    registry.run_command(state, "response on")
    registry.run_command(state, "show")
    out = capsys.readouterr().out.splitlines()
    assert out[0] == "response: on"
    assert any("response on" in row for row in out)
    registry.run_command(state, "mode direct")
    registry.run_command(state, "response on")
    assert capsys.readouterr().out.splitlines()[-1] == "response: on"


def state_for(folder):
    image = np.zeros((10, 20, 3), dtype="uint8")
    image[:, 12] = 200
    cv2.imwrite(str(folder / "image.png"), image)
    state = session.new_state(session.DEFAULTS)
    state["settings"]["source"] = ("file", folder / "image.png")
    return state


def test_measure_peak(tmp_path):
    state = state_for(tmp_path)
    spectrum = measure.measure(state)
    expected = np.zeros(20)
    expected[12] = 200
    np.testing.assert_allclose(spectrum["values"], expected)
    np.testing.assert_allclose(spectrum["x"], np.arange(20))
    assert np.all(spectrum["mask"])
    assert state["image"].shape == (10, 20, 3)


def flank_image(left, right, top=220):
    image = line_image(value=top)
    image[:, 11], image[:, 13] = left, right
    return image


def saved(tmp_path, monkeypatch, frames, images):
    use_camera(monkeypatch, images)
    state = new_state()
    state["settings"]["output_dir"] = (tmp_path / "data").as_posix()
    for line in ("source camera 0", f"frames {frames}", "step", "save"):
        registry.run_command(state, line)
    return state, next((tmp_path / "data").iterdir())


def test_stddev_column_after_raw_counts(tmp_path, monkeypatch):
    _state, folder = saved(tmp_path, monkeypatch, 2, [line_image(value=90), line_image(value=110)])
    with open(folder / "spectrum.csv", newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    assert rows[0] == ["x_px", "value", "valid", "raw_counts", "stddev"]
    assert rows[13][:4] == ["12", "100", "true", "100"]
    assert float(rows[13][4]) == pytest.approx(np.std([90, 110], ddof=1))
    assert rows[1][4] == "0"


def test_fwhm_of_two_frames(tmp_path, monkeypatch, capsys):
    state, _folder = saved(tmp_path, monkeypatch, 2, [flank_image(80, 120), flank_image(120, 80)])
    capsys.readouterr()
    registry.run_command(state, "fwhm 1")
    assert capsys.readouterr().out.splitlines() == [
        "peak 1: 12 pixel, height 220, FWHM 1.83333 pixel",
        "area: 420 counts·pixel (relative, not watts)",
        "FWHM of a narrow line (laser, Hg) is the resolution of the instrument, not the width of the source.",
    ]


def test_series_repeats_give_mean_and_spread(tmp_path, capsys):
    folder = tmp_path / "data" / "led"
    folder.mkdir(parents=True)
    (folder / "series.csv").write_text("current_mA,area\n10,5.0\n20,9.0\n20,10.0\n20,11.0\n", encoding="utf-8")
    xs, means = series.curve(folder / "series.csv")
    assert xs.tolist() == [10, 20] and means.tolist() == [5, 10]
    state = new_state()
    state["settings"]["output_dir"] = (tmp_path / "data").as_posix()
    registry.run_command(state, f"series plot led {(tmp_path / 'led.png').as_posix()}")
    assert capsys.readouterr().out.splitlines()[:1] == [
        f"series led: 2 point(s) from {(folder / 'series.csv').as_posix()}",
    ]


def test_dark_asks_on_camera_in_terminal(monkeypatch, capsys):
    cameras(monkeypatch, [line_image(value=0)])
    asked = terminal(monkeypatch, ["cancel", ""])
    state = new_state()
    registry.run_command(state, "source camera 0")
    registry.run_command(state, "dark 1")
    assert state["dark"] is None
    assert "Cancelled." in capsys.readouterr().out
    registry.run_command(state, "dark 1")
    assert state["dark"] is not None
    assert asked == ["Block the light path and press Enter (type cancel to skip): "] * 2


def test_negative_after_dark_warns(monkeypatch, capsys):
    cameras(monkeypatch, [line_image(value=200), line_image(value=0)])
    state = new_state()
    registry.run_command(state, "source camera 0")
    registry.run_command(state, "dark 1")
    registry.run_command(state, "step")
    out = capsys.readouterr().out
    assert "Warning: some positions are below -5 counts" in out


def test_response_weak_warning(tmp_path, capsys):
    state, paths = calibrated(tmp_path)
    capsys.readouterr()
    registry.run_command(state, f"response build {paths['known']} 1")
    assert capsys.readouterr().out.splitlines() == [
        "response: 3 of 3 positions valid",
        "Warning: some positions have a response below 0.1, the noise is amplified there",
    ]
