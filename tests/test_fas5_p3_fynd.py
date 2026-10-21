"""Fas 5, paket 3: toppar i ändpunkterna (B8), MÄTTAD vid tidigare bild (B9), theme ensam (B21), axelnamn (D4)."""

import numpy as np
from test_droop import state_in
from test_elias import line_image, new_state

from spectrometer import display, peaks, registry
from spectrometer.analysis import peaks as analysis_peaks
from spectrometer.analysis import series


def test_b8_analysis_peak_in_first_and_last_pixel():
    """B8: find_peaks i analysis ger en topp i pixel 0 och i sista pixeln; en topp inne i intervallet är oförändrad."""
    mask = np.ones(10, dtype=bool)
    first = np.array([10, 6, 3, 2, 1, 0.9, 0.8, 0.7, 0.6, 0.5], dtype=np.float64)
    last = first[::-1].copy()
    assert analysis_peaks.find_peaks(first, mask) == [0]
    assert analysis_peaks.find_peaks(last, mask) == [9]
    assert analysis_peaks.find_peaks(np.array([0, 1, 5, 1, 0, 0, 0, 0, 0, 0], dtype=np.float64), mask) == [2]


def test_b8_calibration_peak_in_first_and_last_pixel():
    """B8: find_peaks i kalibreringen hittar toppen i pixel 0 och i sista pixeln, också som platå (mättad)."""
    mask = np.ones(10, dtype=bool)
    first = np.array([10, 6, 3, 2, 1, 0.9, 0.8, 0.7, 0.6, 0.5], dtype=np.float64)
    assert peaks.find_peaks(first, mask, 2, 1) == [0]
    assert peaks.find_peaks(first[::-1].copy(), mask, 2, 1) == [9]
    plateau = np.array([0, 0, 0, 0, 0, 0, 0, 9, 9, 9], dtype=np.float64)
    assert peaks.find_peaks(plateau, mask, 2, 1) == [8]
    flat = np.full(10, 5.0)
    assert peaks.find_peaks(flat, mask, 2, 1) == [] and analysis_peaks.find_peaks(flat, mask) == []  # ingen topp


def test_b9_frame_info_uses_saturated_px_of_the_spectrum():
    """B9: MÄTTAD visas när en tidigare bild var mättad (saturated_px > 0) fast sista bilden inte är det."""
    state = new_state()
    state["image"] = line_image(12, 100)  # sista bilden: inte mättad
    x = np.arange(20.0)
    spectrum = {"x": x, "values": np.ones(20), "mask": np.ones(20, dtype=bool), "x_label": "pixel",
                "y_label": "signal (counts)", "saturated_px": 3}
    info = display.frame_info(state, {}, spectrum, spectrum["values"])
    assert info["warn"] == "MÄTTAD - sänk exponeringen"
    assert info["foot"].endswith("mättad ja")
    spectrum["saturated_px"] = 0
    info = display.frame_info(state, {}, spectrum, spectrum["values"])
    assert info["warn"] is None and info["foot"].endswith("mättad nej")


def test_b21_theme_alone_shows_the_mode(capsys):
    """B21: theme utan argument skriver läget, inget fel."""
    state = new_state()
    state["view"]["theme"] = "dark"
    registry.run_command(state, "theme")
    assert capsys.readouterr().out == "theme: dark\n"
    registry.run_command(state, "theme light")
    capsys.readouterr()
    registry.run_command(state, "theme")
    assert capsys.readouterr().out == "theme: light\n"


def test_d4_series_plot_names_the_axis(tmp_path, capsys):
    """D4: med --x voltage står det spänning, inte ström, i raden om upprepade mätningar."""
    (tmp_path / "data" / "led").mkdir(parents=True)
    for volts in (2.8, 2.8, 3.0):
        series.append(tmp_path / "data" / "led" / "serie.csv", {"voltage_V": volts, "area": 10.0})
    registry.run_command(state_in(tmp_path), f"series plot led --x voltage {(tmp_path / 'u.png').as_posix()}")
    text = capsys.readouterr().out
    assert "mellan upprepade mätningar vid samma spänning" in text and "vid samma ström" not in text
