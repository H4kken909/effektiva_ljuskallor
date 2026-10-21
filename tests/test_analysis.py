"""Analysfunktionerna mot kända tal."""

import numpy as np

from spectrometer.analysis import bandgap, color, peaks, series


def gauss(x, mu, sigma, h=1.0):
    return h * np.exp(-0.5 * ((x - mu) / sigma) ** 2)


def test_peaks_fwhm_area():
    x = np.arange(400.0, 700.0, 1.0)
    y = gauss(x, 450, 5, 100) + gauss(x, 600, 10, 50)
    m = np.ones_like(x, dtype=bool)
    idx = peaks.find_peaks(y, m)
    assert [round(x[i]) for i in idx] == [450, 600]
    assert abs(peaks.fwhm(x, y, idx[0]) - 2.3548 * 5) < 0.2  # FWHM = 2.3548·σ
    assert abs(peaks.centroid(x, y, idx[1]) - 600) < 0.01
    assert abs(peaks.area(x, y, m) - (100 * 5 + 50 * 10) * np.sqrt(2 * np.pi)) / 3000 < 0.01


def test_color_equal_energy_is_white():
    x = np.arange(380.0, 781.0, 1.0)
    X, Y, Z = color.xyz(x, np.ones_like(x), np.ones_like(x, dtype=bool))
    cx, cy = color.xy(X, Y, Z)
    assert abs(cx - 1 / 3) < 0.01 and abs(cy - 1 / 3) < 0.01  # E-vitpunkten
    assert 5000 < color.cct_mccamy(cx, cy) < 6000


def test_droop_normalised():
    xs = np.array([10.0, 20.0, 40.0, 80.0])
    areas = np.array([100.0, 200.0, 360.0, 560.0])
    d = series.droop(xs, areas)
    assert d.max() == 1.0 and d[-1] < d[0]


def test_bandgap_edge():
    x = np.arange(380.0, 781.0, 2.0)
    T = 1 / (1 + np.exp((x - 550) / -4))  # transmission faller brant vid 550 nm (2,254 eV)
    eg, unc, _ = bandgap.edge(x, bandgap.absorbance(T, np.ones_like(x, dtype=bool)), 2.0)
    assert abs(eg - 2.254) < 0.05 and unc < 0.01
