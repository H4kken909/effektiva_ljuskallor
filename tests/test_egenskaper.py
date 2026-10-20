"""Egenskaper som ska gälla för all indata, provade på slumptal med fast frö och på några handgjorda fall.

R = rader i ROI:n, N = bilder som medlas, P = positioner (pixlar) i ett spektrum.
Samma frö ger samma tal varje gång, så ett rött test går att köra om. Ingen ny modul behövs.
"""

import numpy as np
import pytest

from spectrometer import calc

R, N, P = 7, 5, 64

pytestmark = pytest.mark.filterwarnings("error::RuntimeWarning")


def rng():
    """Slumptalen: samma frö (1234) i varje test."""
    return np.random.default_rng(1234)


def test_average_of_equal_rows_is_that_row():
    """N lika rader ger samma rad som medel och spridning 0."""
    row = rng().uniform(0, 255, P)
    mean, stddev = calc.average_spectra(np.tile(row, (N, 1)))
    np.testing.assert_allclose(mean, row, rtol=1e-9, atol=1e-9)
    np.testing.assert_allclose(stddev, 0.0, rtol=1e-9, atol=1e-9)


def test_average_does_not_depend_on_the_order_of_the_frames():
    """Medel och spridning är desamma om bilderna kommer i annan ordning."""
    generator = rng()
    stack = generator.uniform(0, 255, (N, P))
    mean, stddev = calc.average_spectra(stack)
    mean2, stddev2 = calc.average_spectra(stack[generator.permutation(N)])
    np.testing.assert_allclose(mean2, mean, rtol=1e-9, atol=1e-9)
    np.testing.assert_allclose(stddev2, stddev, rtol=1e-9, atol=1e-9)


def test_mask_after_apply_response_is_a_subset_of_the_mask_before():
    """apply_response lägger aldrig till en giltig plats; den tar bara bort de med för liten respons."""
    generator = rng()
    signal = generator.uniform(0, 255, P)
    response = generator.uniform(0, 2, P)
    before = generator.random(P) < 0.8
    values, after = calc.apply_response(signal, response, before, 0.1)
    assert not (after & ~before).any()
    np.testing.assert_array_equal(after, before & (response > 0.1))
    np.testing.assert_array_equal(np.isnan(values), ~after)


def test_transmission_of_a_spectrum_with_itself_is_one():
    """transmission_ratio(x, x) är 1 på varje giltig plats; platser med x <= tröskeln är ogiltiga."""
    spectrum = rng().uniform(0, 255, P)
    spectrum[::10] = 0.0
    values, valid = calc.transmission_ratio(spectrum, spectrum, np.ones(P, dtype=bool), 1.0)
    np.testing.assert_array_equal(valid, spectrum > 1.0)
    np.testing.assert_allclose(values[valid], 1.0, rtol=1e-9, atol=1e-9)
    assert np.isnan(values[~valid]).all()


def test_no_inf_anywhere():
    """Inget svar innehåller inf, trots nollor i nämnare och i lampans kända värden."""
    generator = rng()
    spectrum = generator.uniform(0, 255, P)
    spectrum[::7] = 0.0
    mask = np.ones(P, dtype=bool)
    outputs = [
        *calc.apply_response(spectrum, spectrum, mask, 0.01),
        *calc.transmission_ratio(spectrum, spectrum, mask, 0.01),
        calc.build_response(np.arange(P, dtype=np.float64), spectrum + 1.0, np.arange(P, dtype=np.float64), spectrum),
        *calc.average_spectra(generator.uniform(0, 255, (N, P))),
        calc.extract_spectrum(generator.uniform(0, 255, (R, P))),
    ]
    for output in outputs:
        assert output.dtype == bool or not np.isinf(output).any()


def test_shapes_are_kept():
    """Formerna följer med genom kedjan: bild, tabell, spektrum, stack, respons, transmission och våglängd."""
    generator = rng()
    image = generator.integers(0, 256, (R, P, 3), dtype=np.uint8)
    table = calc.prepare(image, (0, 0, P, R), "horizontal", "gray")
    assert table.shape == (R, P)
    assert calc.prepare(image, (0, 0, P, R), "vertical", "gray").shape == (P, R)
    spectrum = calc.extract_spectrum(table)
    assert spectrum.shape == (P,)
    mean, stddev = calc.average_spectra(np.stack([spectrum] * N))
    assert mean.shape == stddev.shape == (P,)
    assert calc.subtract_dark(image.astype(np.float64), np.zeros((R, P, 3))).shape == (R, P, 3)
    x = np.arange(P, dtype=np.float64)
    assert calc.build_response(x, spectrum + 1.0, x, np.ones(P)).shape == (P,)
    ones = np.ones(P, dtype=bool)
    corrected = [*calc.apply_response(spectrum, spectrum, ones, 0.5), *calc.transmission_ratio(spectrum, spectrum, ones, 0.5)]
    assert all(output.shape == (P,) for output in corrected)
    assert calc.evaluate_wavelength(x, np.array([400.0, 0.3])).shape == (P,)


@pytest.mark.parametrize("degree", [1, 2])
def test_evaluate_reproduces_the_fitted_points(degree):
    """Ligger punkterna exakt på ett polynom ger evaluate_wavelength tillbaka dem inom 1e-9 (grad 1: 2 punkter, grad 2: 3)."""
    generator = rng()
    for _ in range(50):
        a0, a1, a2 = generator.uniform(300, 500), generator.uniform(0.1, 0.5), generator.uniform(-1e-5, 1e-5)
        coefficients = np.array([a0, a1, a2])
        pixels = np.sort(generator.choice(1920, size=degree + 1, replace=False)).astype(np.float64)
        wavelengths = calc.evaluate_wavelength(pixels, coefficients[: degree + 1])
        fitted = calc.fit_wavelength(pixels, wavelengths, degree)
        np.testing.assert_allclose(calc.evaluate_wavelength(pixels, fitted), wavelengths, rtol=0, atol=1e-9)


def test_gray_lies_between_the_darkest_and_the_brightest_channel():
    """gray är en vägd summa med vikter som summerar till 1, så den ligger mellan minsta och största kanalen; sum är röd+grön+blå."""
    image = rng().integers(0, 256, (R, P, 3), dtype=np.uint8)
    roi = (0, 0, P, R)
    gray = calc.prepare(image, roi, "horizontal", "gray")
    channels = np.stack([calc.prepare(image, roi, "horizontal", name) for name in ("blue", "green", "red")])
    assert (gray >= channels.min(axis=0) - 1e-9).all()
    assert (gray <= channels.max(axis=0) + 1e-9).all()
    np.testing.assert_allclose(calc.prepare(image, roi, "horizontal", "sum"), channels.sum(axis=0), rtol=1e-9, atol=1e-9)


def test_response_does_not_depend_on_the_lamp_scale():
    """Bygger man responsen ur en lampmätning gånger 7 blir den samma, och toppen är 1."""
    generator = rng()
    x = np.arange(P, dtype=np.float64)
    measured = generator.uniform(1, 255, P)
    known = generator.uniform(0.5, 2, P)
    response = calc.build_response(x, measured, x, known)
    np.testing.assert_allclose(calc.build_response(x, 7 * measured, x, known), response, rtol=1e-9, atol=1e-9)
    assert response.max() == 1.0