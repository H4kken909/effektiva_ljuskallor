"""1.2.2 spectrum.csv med raw_counts och x_px, spectrum_sv.csv för svensk Excel, och load MAPP (fram och tillbaka)."""

import csv

import cv2
import numpy as np
import pytest
from test_elias import line_image, new_state

from spectrometer import files, registry


def saved_folder(tmp_path, capsys, *lines):
    """Linjebilden kalibrerad till 400,5 + 10·pixel nm, raderna i lines, step och save --excel. Ger (state, mätmappen)."""
    image, points = tmp_path / "bild.png", tmp_path / "p.csv"
    cv2.imwrite(str(image), line_image())
    points.write_text("pixel,wavelength_nm,check\n0,400.5,0\n19,590.5,0\n", encoding="utf-8")
    state = new_state()
    for line in (f"source file {image.as_posix()}", f"calibrate {points.as_posix()}", *lines, "step",
                 f"save {(tmp_path / 'data').as_posix()} --excel"):
        registry.run_command(state, line)
    capsys.readouterr()
    return state, next((tmp_path / "data").iterdir())


def test_csv_has_raw_counts_and_pixel_last(tmp_path, capsys):
    """Kolumn 1-3 som förut; raw_counts och x_px sist; spectrum_sv.csv med semikolon och decimalkomma."""
    _, folder = saved_folder(tmp_path, capsys)
    with open(folder / "spectrum.csv", newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    assert rows[0] == ["x_nm", "value", "valid", "raw_counts", "stddev", "x_px"]  # 1.2.14: stddev
    assert rows[13] == ["520.5", "200", "true", "200", "", "12"]
    text = (folder / "spectrum_sv.csv").read_text(encoding="utf-8-sig").splitlines()
    assert text[0] == "x_nm;value;valid;raw_counts;stddev;x_px"
    assert text[13] == "520,5;200;true;200;;12"


def test_load_gives_back_the_measurement(tmp_path, capsys):
    """load MAPP ger samma x, värden, mask och etiketter som mätningen; save och toppar vägrar efteråt."""
    state, folder = saved_folder(tmp_path, capsys)
    measured = state["spectrum"]
    registry.run_command(state, f"load {folder.as_posix()}")
    assert capsys.readouterr().out.splitlines() == [
        f"laddad: {folder.as_posix()} (20 positioner, med raw_counts)", "Topp 200 vid våglängd (nm) 520.5",
    ]
    loaded = state["spectrum"]
    np.testing.assert_allclose(loaded["x"], measured["x"])
    np.testing.assert_array_equal(loaded["mask"], measured["mask"])
    np.testing.assert_allclose(loaded["values"][loaded["mask"]], measured["values"][measured["mask"]])
    assert (loaded["x_label"], loaded["y_label"]) == (measured["x_label"], measured["y_label"])
    np.testing.assert_array_equal(loaded["px"], np.arange(20.0))
    for line in ("save", "toppar"):
        with pytest.raises(ValueError, match="load"):
            registry.run_command(state, line)


def test_load_old_folder_with_three_columns(tmp_path):
    """En mapp från före 1.2.2 (tre kolumner, ingen settings.json): tom cell blir NaN, valid false blir falsk mask."""
    (tmp_path / "gammal").mkdir()
    (tmp_path / "gammal" / "spectrum.csv").write_text("x_px,value,valid\n0,1.5,true\n1,,false\n", encoding="utf-8")
    spectrum = files.load_measurement(tmp_path / "gammal")
    np.testing.assert_array_equal(spectrum["values"], [1.5, np.nan])
    assert spectrum["mask"].tolist() == [True, False]
    assert (spectrum["x_label"], spectrum["y_label"], spectrum["settings"]) == ("pixel", "signal (counts)", {})
    assert "raw" not in spectrum
    (tmp_path / "gammal" / "spectrum.csv").write_text("x;y\n0;1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="saknar x_nm eller x_px"):
        files.load_measurement(tmp_path / "gammal")
