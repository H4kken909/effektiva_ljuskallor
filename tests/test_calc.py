"""Testar calc med räkneexemplen RX01, RX02 och RX05 från rev7."""

import numpy as np

from spectrometer import calc


def test_rx05():
    table = np.array([[10, 28, 50], [12, 32, 54]], dtype="float64")
    result = calc.extract_spectrum(table)
    np.testing.assert_allclose(result, [11, 30, 52], rtol=1e-9, atol=1e-9)


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
