"""Gränsfall för calc, files och source: tom och minsta indata, exakt på gränsen, NaN och fel.

Mall för varje funktion: ett normalt fall, ett felfall (felkoden står i meddelandet) och ett gränsfall.
Bara publika funktioner, bilderna byggs med numpy. En RuntimeWarning räknas som fel i den här filen:
delning med noll och ogiltiga värden ska koden hantera, inte bara varna om.
"""

import csv
import json
import types

import cv2
import numpy as np
import pytest

from spectrometer import calc, files, source

pytestmark = pytest.mark.filterwarnings("error::RuntimeWarning")


def solid(height, width, value):
    """En enfärgad bild, (height, width, 3) uint8 i BGR."""
    return np.full((height, width, 3), value, dtype=np.uint8)


# ---- calc.prepare och calc.extract_spectrum: ROI, kanaler och tabellen ----


def test_prepare_normal():
    """Normalt: ROI:n (x 1, y 1, 3 bred, 2 hög) ur röd kanal ger tabellen 2 rader x 3 kolumner."""
    image = solid(4, 6, 0)
    image[:, :, 2] = np.arange(24).reshape(4, 6)
    table = calc.prepare(image, (1, 1, 3, 2), "horizontal", "red")
    np.testing.assert_array_equal(table, image[1:3, 1:4, 2])
    assert table.dtype == np.float64


@pytest.mark.parametrize("roi", [(0, 0, 0, 2), (0, 0, 2, 0), (0, 0, 0, 0), (0, 0, -1, 2)])
def test_prepare_empty_roi(roi):
    """Tom ROI (bredd eller höjd 0, eller negativ) ger fel i stället för en tom tabell."""
    with pytest.raises(ValueError, match="roi måste ha bredd och höjd större än 0"):
        calc.prepare(solid(4, 6, 0), roi, "horizontal", "gray")


def test_prepare_roi_up_to_the_edge():
    """Gräns: x + bredd == bildbredd och y + höjd == bildhöjd går."""
    image = solid(4, 6, 0)
    assert calc.prepare(image, (3, 0, 3, 4), "horizontal", "gray").shape == (4, 3)
    assert calc.prepare(image, (0, 2, 6, 2), "horizontal", "gray").shape == (2, 6)


@pytest.mark.parametrize("roi", [(3, 0, 4, 4), (0, 2, 6, 3), (-1, 0, 2, 2), (0, -1, 2, 2), (6, 0, 1, 1)])
def test_prepare_roi_outside(roi):
    """Gräns: en pixel för långt (eller negativ start) ger fel med bildens mått."""
    with pytest.raises(ValueError, match=r"roi .* ligger utanför bilden \(6 bred, 4 hög\)"):
        calc.prepare(solid(4, 6, 0), roi, "horizontal", "gray")


def test_prepare_one_pixel_roi():
    """Gräns: en enda pixel i bildens hörn ger en 1 x 1-tabell i båda riktningarna och ett spektrumvärde."""
    image = solid(4, 6, 0)
    image[3, 5] = (50, 100, 200)  # B, G, R
    for axis in ("horizontal", "vertical"):
        table = calc.prepare(image, (5, 3, 1, 1), axis, "red")
        assert table.shape == (1, 1)
        np.testing.assert_array_equal(calc.extract_spectrum(table), [200])


def test_prepare_all_saturated():
    """Allt mättat (255 överallt): varje färg 255, sum 765 och gray 255 eftersom vikterna summerar till 1."""
    image = solid(3, 4, 255)
    expected = {"red": 255, "green": 255, "blue": 255, "sum": 765, "gray": 255}
    for channel, value in expected.items():
        table = calc.prepare(image, (0, 0, 4, 3), "horizontal", channel)
        np.testing.assert_allclose(table, value, rtol=1e-9, atol=1e-9)


def test_prepare_float_image_keeps_negative_numbers():
    """En float64-bild efter mörkeravdrag får ha negativa tal; de klipps inte."""
    image = np.full((2, 3, 3), -3.0)
    table = calc.prepare(image, (0, 0, 3, 2), "horizontal", "sum")
    np.testing.assert_allclose(table, -9.0, rtol=1e-9, atol=1e-9)


@pytest.mark.parametrize(
    "image",
    [
        np.zeros((4, 6, 3), dtype=np.float32),
        np.zeros((4, 6, 3), dtype=np.uint16),
        np.zeros((4, 6), dtype=np.uint8),
        np.zeros((4, 6, 4), dtype=np.uint8),
        [[[0, 0, 0]]],
    ],
    ids=["float32", "uint16", "two-dimensional", "four-channels", "list"],
)
def test_prepare_bad_image(image):
    """Fel: bilden måste vara en uint8- eller float64-array med formen (H, W, 3)."""
    with pytest.raises(ValueError, match=r"input\.invalid_argument: image måste"):
        calc.prepare(image, (0, 0, 1, 1), "horizontal", "gray")


def test_prepare_unknown_channel_and_axis():
    """Fel: okänd kanal och okänd riktning nämns vid namn."""
    with pytest.raises(ValueError, match="okänd kanal purple"):
        calc.prepare(solid(2, 2, 0), (0, 0, 2, 2), "horizontal", "purple")
    with pytest.raises(ValueError, match="okänd riktning diagonal"):
        calc.prepare(solid(2, 2, 0), (0, 0, 2, 2), "diagonal", "gray")


def test_nan_in_the_image_does_not_get_through():
    """NaN i en float64-bild tar sig inte genom prepare och extract_spectrum."""
    image = np.zeros((2, 3, 3))
    image[0, 1, 2] = np.nan
    with pytest.raises(ValueError, match=r"input\.invalid_argument"):
        calc.extract_spectrum(calc.prepare(image, (0, 0, 3, 2), "horizontal", "red"))


def test_extract_spectrum_one_row_and_one_column():
    """Gräns: en rad ger raden själv, en kolumn ger ett enda värde."""
    np.testing.assert_array_equal(calc.extract_spectrum(np.array([[1.0, 2.0, 3.0]])), [1, 2, 3])
    np.testing.assert_array_equal(calc.extract_spectrum(np.array([[1.0], [3.0]])), [2])


@pytest.mark.parametrize("bad", [np.nan, np.inf, -np.inf])
def test_extract_spectrum_not_finite(bad):
    """Fel: NaN och inf i tabellen."""
    with pytest.raises(ValueError, match="ändliga tal"):
        calc.extract_spectrum(np.array([[1.0, bad]]))


@pytest.mark.parametrize(
    ("table", "message"),
    [
        (np.zeros((2, 3), dtype=np.float32), "float64-array"),
        (np.zeros((2, 3), dtype=np.int64), "float64-array"),
        (np.zeros(3), "2 dimensions"),
        (np.zeros((2, 2, 2)), "2 dimensions"),
        (np.zeros((0, 3)), "table is empty"),
        (np.zeros((3, 0)), "table is empty"),
    ],
    ids=["float32", "int64", "one-dimensional", "three-dimensional", "no-rows", "no-columns"],
)
def test_extract_spectrum_bad_table(table, message):
    """Fel: fel typ, fel antal dimensioner och tom tabell."""
    with pytest.raises(ValueError, match=message):
        calc.extract_spectrum(table)

# ---- calc.average_spectra, evaluate_wavelength, fit_wavelength och subtract_dark ----


def test_average_one_frame_has_nan_stddev():
    """frames=1: medlet är raden själv och spridningen NaN, utan varning."""
    mean, stddev = calc.average_spectra(np.array([[2.0, 10.0, 5.0]]))
    np.testing.assert_array_equal(mean, [2, 10, 5])
    assert stddev.shape == (3,)
    assert np.isnan(stddev).all()


def test_average_two_frames_is_the_smallest_spread():
    """Gräns: två bilder är det minsta som ger spridning, delad med N - 1, alltså |a - b| / sqrt(2)."""
    mean, stddev = calc.average_spectra(np.array([[1.0, 5.0], [4.0, 5.0]]))
    np.testing.assert_allclose(mean, [2.5, 5.0], rtol=1e-9, atol=1e-9)
    np.testing.assert_allclose(stddev, [3 / np.sqrt(2), 0.0], rtol=1e-9, atol=1e-9)


def test_average_nan_stays_in_its_column():
    """NaN i en kolumn ger NaN i just den kolumnen, de andra räknas som vanligt."""
    mean, stddev = calc.average_spectra(np.array([[1.0, np.nan], [3.0, 4.0]]))
    np.testing.assert_allclose(mean, [2.0, np.nan], rtol=1e-9, atol=1e-9)
    np.testing.assert_allclose(stddev, [np.sqrt(2), np.nan], rtol=1e-9, atol=1e-9)


@pytest.mark.parametrize(
    ("stack", "message"),
    [
        (np.zeros(3), "måste vara 2D"),
        (np.zeros((2, 3), dtype=np.int64), "float64-array"),
        (np.zeros((0, 3)), "stack är tom"),
        (np.zeros((3, 0)), "stack är tom"),
    ],
    ids=["one-dimensional", "int64", "no-frames", "no-columns"],
)
def test_average_bad_stack(stack, message):
    """Fel: fel antal dimensioner, fel typ och tom stack."""
    with pytest.raises(ValueError, match=message):
        calc.average_spectra(stack)


def test_evaluate_wavelength_two_and_three_coefficients():
    """Normalt: a0 + a1*p, och med tre koefficienter också a2*p*p; inga pixlar ger ingen våglängd."""
    pixels = np.array([0.0, 10.0])
    np.testing.assert_allclose(calc.evaluate_wavelength(pixels, np.array([400.0, 0.5])), [400, 405], rtol=1e-9)
    np.testing.assert_allclose(calc.evaluate_wavelength(pixels, np.array([400.0, 0.5, 0.001])), [400, 405.1], rtol=1e-9)
    assert calc.evaluate_wavelength(np.array([]), np.array([400.0, 0.5])).shape == (0,)


@pytest.mark.parametrize("count", [0, 1, 4])
def test_evaluate_wavelength_wrong_number_of_coefficients(count):
    """Fel: bara 2 eller 3 koefficienter."""
    with pytest.raises(ValueError, match="ska ha 2 eller 3 värden"):
        calc.evaluate_wavelength(np.array([1.0]), np.ones(count))


def test_evaluate_wavelength_bad_arrays():
    """Fel: NaN i pixlarna, heltal i pixlarna och inf i koefficienterna."""
    good = np.array([400.0, 0.5])
    with pytest.raises(ValueError, match="ändliga tal"):
        calc.evaluate_wavelength(np.array([np.nan]), good)
    with pytest.raises(ValueError, match="float64-array"):
        calc.evaluate_wavelength(np.array([1, 2]), good)
    with pytest.raises(ValueError, match="ändliga tal"):
        calc.evaluate_wavelength(np.array([1.0]), np.array([400.0, np.inf]))


def test_calibration_rises_when_the_points_rise():
    """Punkter där våglängden stiger med pixeln ger en stigande axel över hela bilden, för grad 1 och 2."""
    pixels = np.array([100.0, 400.0, 800.0, 1200.0])
    wavelengths = np.array([450.0, 520.0, 610.0, 700.0])
    whole_image = np.arange(0, 1920, dtype=np.float64)
    for degree in (1, 2):
        axis = calc.evaluate_wavelength(whole_image, calc.fit_wavelength(pixels, wavelengths, degree))
        assert np.all(np.diff(axis) > 0)


def test_calibration_falls_when_the_points_fall():
    """Punkter där våglängden sjunker med pixeln ger en sjunkande axel (measure vänder den sedan)."""
    pixels = np.array([100.0, 800.0])
    wavelengths = np.array([700.0, 450.0])
    axis = calc.evaluate_wavelength(np.arange(0, 1920, dtype=np.float64), calc.fit_wavelength(pixels, wavelengths, 1))
    assert np.all(np.diff(axis) < 0)


def test_fit_with_the_smallest_number_of_points_is_exact():
    """Gräns: grad 1 med 2 punkter och grad 2 med 3 punkter går genom punkterna exakt."""
    for pixels, wavelengths, degree in (
        (np.array([100.0, 200.0]), np.array([500.0, 600.0]), 1),
        (np.array([0.0, 100.0, 200.0]), np.array([400.0, 520.0, 680.0]), 2),
    ):
        coefficients = calc.fit_wavelength(pixels, wavelengths, degree)
        assert coefficients.shape == (degree + 1,)
        np.testing.assert_allclose(calc.evaluate_wavelength(pixels, coefficients), wavelengths, rtol=1e-9, atol=1e-9)


@pytest.mark.parametrize(("degree", "count"), [(1, 1), (2, 2)])
def test_fit_too_few_points(degree, count):
    """Gräns: en punkt för få för graden."""
    with pytest.raises(ValueError, match=f"grad {degree} behöver minst {degree + 1} punkter, fick {count}"):
        calc.fit_wavelength(np.arange(count, dtype=np.float64), np.arange(count, dtype=np.float64), degree)


@pytest.mark.parametrize("degree", [0, 3, -1])
def test_fit_wrong_degree(degree):
    """Fel: bara grad 1 och 2."""
    with pytest.raises(ValueError, match="degree ska vara 1 eller 2"):
        calc.fit_wavelength(np.array([1.0, 2.0, 3.0]), np.array([1.0, 2.0, 3.0]), degree)


def test_fit_bad_points():
    """Fel: samma pixel två gånger, olika längd och NaN."""
    with pytest.raises(ValueError, match="samma pixel står två gånger"):
        calc.fit_wavelength(np.array([1.0, 1.0]), np.array([500.0, 501.0]), 1)
    with pytest.raises(ValueError, match="olika form"):
        calc.fit_wavelength(np.array([1.0, 2.0]), np.array([500.0, 501.0, 502.0]), 1)
    with pytest.raises(ValueError, match="ändliga tal"):
        calc.fit_wavelength(np.array([1.0, 2.0]), np.array([500.0, np.nan]), 1)


def test_subtract_dark_normal_and_unchanged_inputs():
    """Normalt: bild minus mörker, negativt får bli kvar; in-arrayerna ändras inte och svaret är en ny array."""
    image = np.array([[[5.0, 6.0, 7.0]]])
    dark = np.array([[[1.0, 6.0, 9.0]]])
    result = calc.subtract_dark(image, dark)
    np.testing.assert_array_equal(result, [[[4.0, 0.0, -2.0]]])
    np.testing.assert_array_equal(image, [[[5.0, 6.0, 7.0]]])
    np.testing.assert_array_equal(dark, [[[1.0, 6.0, 9.0]]])
    assert result is not image


def test_subtract_dark_bad_input():
    """Fel: olika form, uint8-bild och NaN i mörkret."""
    image = np.zeros((2, 2, 3))
    with pytest.raises(ValueError, match="mörkret har formen"):
        calc.subtract_dark(image, np.zeros((2, 3, 3)))
    with pytest.raises(ValueError, match="float64-array"):
        calc.subtract_dark(np.zeros((2, 2, 3), dtype=np.uint8), image)
    dark = np.zeros((2, 2, 3))
    dark[0, 0, 0] = np.nan
    with pytest.raises(ValueError, match="ändliga tal"):
        calc.subtract_dark(image, dark)

# ---- calc.build_response, apply_response och transmission_ratio ----

LAMP_X = np.array([500.0, 510.0, 520.0, 530.0])


def test_build_response_normal():
    """Normalt: uppmätt delat med känt, delat med det största värdet, så toppen blir exakt 1."""
    response = calc.build_response(LAMP_X, np.array([2.0, 4.0, 8.0, 4.0]), LAMP_X, np.array([1.0, 1.0, 2.0, 1.0]))
    np.testing.assert_allclose(response, [0.5, 1.0, 1.0, 1.0], rtol=1e-9, atol=1e-9)
    assert response.max() == 1.0


def test_build_response_nan_and_inf_only_where_they_are():
    """NaN och inf i lampmätningen ger NaN på just den platsen; resten räknas och toppen är 1."""
    response = calc.build_response(LAMP_X, np.array([2.0, np.nan, 4.0, np.inf]), LAMP_X, np.ones(4))
    np.testing.assert_allclose(response, [0.5, np.nan, 1.0, np.nan], rtol=1e-9, atol=1e-9)


def test_build_response_known_zero_is_not_divided():
    """Gräns: känt värde exakt 0 ger NaN på platsen (ingen delning med noll), de andra räknas."""
    response = calc.build_response(LAMP_X, np.array([2.0, 4.0, 4.0, 2.0]), LAMP_X, np.array([1.0, 0.0, 2.0, 1.0]))
    np.testing.assert_allclose(response, [1.0, np.nan, 1.0, 1.0], rtol=1e-9, atol=1e-9)


def test_build_response_two_known_points_and_no_extrapolation():
    """Gräns: precis två kända punkter räcker; lampan utanför dem blir NaN."""
    x = np.array([500.0, 510.0, 520.0])
    response = calc.build_response(x, np.array([1.0, 2.0, 3.0]), np.array([500.0, 510.0]), np.array([1.0, 1.0]))
    np.testing.assert_allclose(response, [0.5, 1.0, np.nan], rtol=1e-9, atol=1e-9)


def test_build_response_wrong_shapes():
    """Fel: olika längd på lampan eller på de kända värdena, och bara en känd punkt."""
    cases = [
        (np.ones(3), LAMP_X, np.ones(4)),
        (np.ones(4), LAMP_X, np.ones(3)),
        (np.ones(4), LAMP_X[:1], np.ones(1)),
    ]
    for measured, known_x, known_v in cases:
        with pytest.raises(ValueError, match="olika form eller färre än två kända punkter"):
            calc.build_response(LAMP_X, measured, known_x, known_v)


def test_build_response_missing_data():
    """Fel: bara NaN, lampan utanför de kända punkterna eller känt 0 överallt ger input.missing_data."""
    cases = [
        (np.full(4, np.nan), LAMP_X, np.ones(4)),
        (np.ones(4), LAMP_X + 1000, np.ones(4)),
        (np.ones(4), LAMP_X, np.zeros(4)),
    ]
    for measured, known_x, known_v in cases:
        with pytest.raises(ValueError, match=r"input\.missing_data: inget giltigt värde"):
            calc.build_response(LAMP_X, measured, known_x, known_v)


def test_build_response_peak_must_be_positive():
    """Gräns: toppen 0 (och negativ) går inte att normera."""
    for measured in (np.zeros(4), np.full(4, -1.0)):
        with pytest.raises(ValueError, match="toppen är inte större än 0"):
            calc.build_response(LAMP_X, measured, LAMP_X, np.ones(4))


RATIO_FUNCTIONS = pytest.mark.parametrize(
    "ratio", [calc.apply_response, calc.transmission_ratio], ids=["apply_response", "transmission_ratio"]
)


@RATIO_FUNCTIONS
def test_ratio_strictly_greater_than_the_threshold(ratio):
    """Gräns: strikt större än tröskeln. Exakt tröskeln och talet strax under är ogiltiga, strax över giltigt."""
    below, above = np.nextafter(0.5, 0), np.nextafter(0.5, 1)
    values, mask = ratio(np.ones(4), np.array([below, 0.5, above, 1.0]), np.ones(4, dtype=bool), 0.5)
    np.testing.assert_array_equal(mask, [False, False, True, True])
    np.testing.assert_array_equal(np.isnan(values), [True, True, False, False])
    np.testing.assert_allclose(values[2:], [1 / above, 1.0], rtol=1e-9, atol=1e-9)


@RATIO_FUNCTIONS
def test_ratio_zero_and_negative_denominator(ratio):
    """Nämnaren 0 eller negativ är ogiltig och ger NaN, aldrig inf (en varning vore ett fel här)."""
    values, mask = ratio(np.ones(3), np.array([0.0, -1.0, 2.0]), np.ones(3, dtype=bool), 0.5)
    np.testing.assert_array_equal(mask, [False, False, True])
    np.testing.assert_allclose(values, [np.nan, np.nan, 0.5], rtol=1e-9, atol=1e-9)
    assert not np.isinf(values).any()


@RATIO_FUNCTIONS
def test_ratio_mask_false_hides_a_bad_number(ratio):
    """NaN under en falsk mask är tillåtet och ger NaN och False."""
    values, mask = ratio(np.array([np.nan, 2.0]), np.array([np.nan, 1.0]), np.array([False, True]), 0.5)
    np.testing.assert_allclose(values, [np.nan, 2.0], rtol=1e-9, atol=1e-9)
    np.testing.assert_array_equal(mask, [False, True])


@RATIO_FUNCTIONS
@pytest.mark.parametrize("bad", [np.nan, np.inf])
def test_ratio_bad_number_on_a_valid_position(ratio, bad):
    """Fel: NaN och inf under en sann mask, i täljaren eller nämnaren."""
    good = np.array([1.0, 1.0])
    for top, bottom in ((np.array([bad, 1.0]), good), (good, np.array([bad, 1.0]))):
        with pytest.raises(ValueError, match="ändliga tal"):
            ratio(top, bottom, np.ones(2, dtype=bool), 0.5)


@RATIO_FUNCTIONS
def test_ratio_everything_masked_out(ratio):
    """Gräns: ingen giltig plats ger bara NaN och False, inget fel."""
    values, mask = ratio(np.ones(3), np.ones(3), np.zeros(3, dtype=bool), 0.5)
    assert np.isnan(values).all()
    assert not mask.any()


@RATIO_FUNCTIONS
def test_ratio_empty_arrays(ratio):
    """Gräns: inga pixlar ger tomma svar."""
    values, mask = ratio(np.array([]), np.array([]), np.array([], dtype=bool), 0.5)
    assert values.shape == (0,)
    assert mask.shape == (0,)


@RATIO_FUNCTIONS
def test_ratio_threshold(ratio):
    """Tröskeln måste vara ändlig och större än 0; ett mycket litet positivt tal går."""
    for bad in (0.0, -1.0, np.nan, np.inf):
        with pytest.raises(ValueError, match="måste vara ändligt och större än 0"):
            ratio(np.ones(1), np.ones(1), np.ones(1, dtype=bool), bad)
    values, _ = ratio(np.ones(1), np.ones(1), np.ones(1, dtype=bool), 1e-300)
    np.testing.assert_array_equal(values, [1.0])


@RATIO_FUNCTIONS
def test_ratio_bad_mask_and_shapes(ratio):
    """Fel: mask som inte är bool, och en mask eller nämnare med annan form."""
    with pytest.raises(ValueError, match="måste vara en bool-array"):
        ratio(np.ones(2), np.ones(2), np.ones(2, dtype=np.int64), 0.5)
    with pytest.raises(ValueError, match="mask har annan form"):
        ratio(np.ones(2), np.ones(2), np.ones(3, dtype=bool), 0.5)
    with pytest.raises(ValueError, match="annan form"):
        ratio(np.ones(2), np.ones(3), np.ones(2, dtype=bool), 0.5)

# ---- files: save_measurement, load_points och load_known ----


def spectrum_of(values, mask, x_label="pixel"):
    """Ett spektrum i samma form som measure ger: x är 0, 1, 2 ..."""
    return {
        "x": np.arange(len(values), dtype=np.float64),
        "values": np.array(values, dtype=np.float64),
        "mask": np.array(mask, dtype=bool),
        "x_label": x_label,
        "y_label": "signal (counts)",
    }


def read_rows(folder):
    """Raderna i spectrum.csv som listor av text."""
    with (folder / "spectrum.csv").open(newline="", encoding="utf-8") as f:
        return list(csv.reader(f))


def write(tmp_path, text, name="p.csv"):
    """Skriver texten som den är (radbrytningarna orörda) och ger sökvägen."""
    path = tmp_path / name
    path.write_text(text, encoding="utf-8", newline="")
    return path


def test_save_one_pixel_and_nothing_valid(tmp_path):
    """Gräns: ett enda värde ger en datarad; ett helt ogiltigt spektrum ger tomma celler men raderna finns kvar."""
    folder = files.save_measurement(tmp_path, spectrum_of([5.0], [True]), solid(1, 1, 0), {})
    assert [row[:3] for row in read_rows(folder)] == [["x_px", "value", "valid"], ["0", "5", "true"]]
    folder = files.save_measurement(tmp_path, spectrum_of([np.nan, np.nan], [False, False]), solid(1, 2, 0), {})
    assert [row[:3] for row in read_rows(folder)[1:]] == [["0", "", "false"], ["1", "", "false"]]


def test_save_wavelength_header_and_absorbance(tmp_path):
    """Våglängdsaxeln ger x_nm; mode transmission lägger till absorbance = -log10(T), tom där T saknas eller är 0 eller mindre."""
    values = [0.1, 0.01, 1.0, 0.0, -0.5, 0.2]
    mask = [True, True, True, True, True, False]
    spectrum = spectrum_of(values, mask, x_label="våglängd (nm)")
    rows = read_rows(files.save_measurement(tmp_path, spectrum, solid(1, 6, 0), {"mode": "transmission"}))
    assert rows[0][:3] == ["x_nm", "value", "valid"]
    column = rows[0].index("absorbance")
    assert [float(row[column]) for row in rows[1:4]] == pytest.approx([1.0, 2.0, 0.0])
    assert [row[column] for row in rows[4:]] == ["", "", ""]


def test_save_same_second_gets_a_counter(tmp_path, monkeypatch):
    """Gräns: tre mätningar samma sekund får mapparna ...12, ...12-2 och ...12-3 och skriver inte över varandra."""
    now = types.SimpleNamespace(strftime=lambda fmt: "20261016-153012")
    monkeypatch.setattr(files, "datetime", types.SimpleNamespace(now=lambda: now))
    spectrum = spectrum_of([1.0], [True])
    names = [files.save_measurement(tmp_path, spectrum, solid(1, 1, 0), {}).name for _ in range(3)]
    assert names == ["20261016-153012", "20261016-153012-2", "20261016-153012-3"]


def test_save_creates_the_parent_and_keeps_the_data(tmp_path):
    """Föräldramappen skapas om den saknas; settings.json behåller å, ä, ö och tuple blir lista; raw.png är förlustfri."""
    image = np.random.default_rng(1234).integers(0, 256, size=(3, 4, 3), dtype=np.uint8)
    settings = {"roi": (0, 0, 4, 3), "text": "våglängd"}
    folder = files.save_measurement(tmp_path / "ny" / "mapp", spectrum_of([1.0], [True]), image, settings)
    text = (folder / "settings.json").read_text(encoding="utf-8")
    assert json.loads(text) == {"roi": [0, 0, 4, 3], "text": "våglängd"}
    assert "våglängd" in text
    np.testing.assert_array_equal(cv2.imread(str(folder / "raw.png")), image)


def test_save_parent_is_a_file(tmp_path):
    """Fel: om föräldern är en fil går mappen inte att skapa, och det blir ett OSError."""
    blocker = write(tmp_path, "i vägen", name="fil.txt")
    with pytest.raises(OSError):
        files.save_measurement(blocker, spectrum_of([1.0], [True]), solid(1, 1, 0), {})


POINTS = "pixel,wavelength_nm,check\n"


def test_load_points_valid_edges(tmp_path):
    """Gränser som går: pixel 0, blankrad mitt i, CRLF, ingen radbrytning sist och BOM i början."""
    pixels, wavelengths, is_check = files.load_points(write(tmp_path, POINTS + "0,450,0\r\n\r\n10,460.5,1"))
    np.testing.assert_array_equal(pixels, [0, 10])
    np.testing.assert_array_equal(wavelengths, [450, 460.5])
    np.testing.assert_array_equal(is_check, [False, True])
    bom = tmp_path / "bom.csv"
    bom.write_bytes(b"\xef\xbb\xbf" + (POINTS + "1,2,0\n").encode("utf-8"))
    np.testing.assert_array_equal(files.load_points(bom)[0], [1])


def test_load_points_header_only(tmp_path):
    """Gräns: bara rubriken ger tre tomma arrayer med rätt typer (för få punkter stoppar först fit_wavelength)."""
    pixels, wavelengths, is_check = files.load_points(write(tmp_path, POINTS))
    assert (pixels.shape, wavelengths.shape, is_check.shape) == ((0,), (0,), (0,))
    assert (pixels.dtype, wavelengths.dtype, is_check.dtype) == (np.float64, np.float64, np.bool_)


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("pixel;wavelength_nm;check\n", "rad 1: fel rubrik"),
        ("wavelength_nm,pixel,check\n", "rad 1: fel rubrik"),
        ("Pixel,wavelength_nm,check\n", "rad 1: fel rubrik"),
        (POINTS + "-1,500,0\n", "rad 2: pixel har ett ogiltigt värde"),
        (POINTS + "nan,500,0\n", "rad 2: pixel har ett ogiltigt värde"),
        (POINTS + "inf,500,0\n", "rad 2: pixel har ett ogiltigt värde"),
        (POINTS + "tio,500,0\n", "rad 2: pixel är inte ett tal"),
        (POINTS + "10,gul,0\n", "rad 2: wavelength_nm är inte ett tal"),
        (POINTS + "10,500,2\n", "rad 2: check ska vara 0 eller 1"),
        (POINTS + "10,500,1.0\n", "rad 2: check ska vara 0 eller 1"),
        (POINTS + "10,500\n", "rad 2: fel antal fält"),
        (POINTS + "10,500,0,9\n", "rad 2: fel antal fält"),
        (POINTS + "10,500,0\n\n11,501,0\n20,gul,0\n", "rad 5: wavelength_nm är inte ett tal"),
    ],
)
def test_load_points_errors_name_the_line(tmp_path, text, message):
    """Fel: felet säger filnamnet och radnumret (blankrader räknas)."""
    with pytest.raises(ValueError, match=f"input.invalid_argument: p.csv {message}"):
        files.load_points(write(tmp_path, text))


def test_load_points_nan_wavelength_is_stopped_before_the_fit(tmp_path):
    """NaN som våglängd tar sig inte hela vägen till anpassningen (load_points eller fit_wavelength stoppar det)."""
    path = write(tmp_path, POINTS + "10,nan,0\n20,500,0\n")
    with pytest.raises(ValueError, match=r"input\.invalid_argument"):
        pixels, wavelengths, _ = files.load_points(path)
        calc.fit_wavelength(pixels, wavelengths, 1)


def test_load_missing_files_are_os_errors(tmp_path):
    """Fel: filen finns inte."""
    with pytest.raises(OSError):
        files.load_points(tmp_path / "saknas.csv")
    with pytest.raises(OSError):
        files.load_known(tmp_path / "saknas.csv")


KNOWN = "wavelength_nm,relative_power_per_nm\n"


def test_load_known_valid_edges(tmp_path):
    """Gränser som går: precis två rader, effekt 0, CRLF och BOM."""
    wavelengths, values = files.load_known(write(tmp_path, KNOWN + "500,0\r\n510,1\r\n"))
    np.testing.assert_array_equal(wavelengths, [500, 510])
    np.testing.assert_array_equal(values, [0, 1])
    bom = tmp_path / "bom.csv"
    bom.write_bytes(b"\xef\xbb\xbf" + (KNOWN + "500,1\n510,1\n").encode("utf-8"))
    np.testing.assert_array_equal(files.load_known(bom)[0], [500, 510])


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("wavelength_nm;relative_power_per_nm\n", "p.csv rad 1: fel rubrik"),
        (KNOWN, "färre än två datarader i p.csv"),
        (KNOWN + "500,1\n", "färre än två datarader i p.csv"),
        (KNOWN + "500,1\n500,2\n", "p.csv: våglängden stiger inte, rad 3"),
        (KNOWN + "500,1\n490,2\n", "p.csv: våglängden stiger inte, rad 3"),
        (KNOWN + "500,-0.1\n510,1\n", "p.csv: ogiltigt värde, rad 2"),
        (KNOWN + "nan,1\n510,1\n", "p.csv: ogiltigt värde, rad 2"),
        (KNOWN + "500,inf\n510,1\n", "p.csv: ogiltigt värde, rad 2"),
        (KNOWN + "500,gul\n510,1\n", "p.csv: fältet är inte ett tal, rad 2"),
        (KNOWN + "500,1,7\n510,1\n", "p.csv: fel antal fält, rad 2"),
    ],
)
def test_load_known_errors_name_the_line(tmp_path, text, message):
    """Fel: felet säger filnamnet och radnumret."""
    with pytest.raises(ValueError, match=f"input.invalid_argument: {message}"):
        files.load_known(write(tmp_path, text))

# ---- source: bildfiler och kameran (en låtsaskamera, aldrig en riktig) ----


def save_png(tmp_path, array, name="bild.png"):
    """Skriver arrayen som PNG och ger sökvägen."""
    path = tmp_path / name
    assert cv2.imwrite(str(path), array)
    return path


def test_open_one_pixel_image(tmp_path):
    """Gräns: en bild på en pixel läses som (1, 1, 3), med sökvägen som text eller Path."""
    path = save_png(tmp_path, solid(1, 1, 7))
    for value in (path, str(path)):
        src = source.open_source("file", value)
        assert source.read_frame(src).shape == (1, 1, 3)


def test_open_grey_image_becomes_three_channels(tmp_path):
    """En gråskalebild (2D) blir (H, W, 3) med samma värde i alla tre kanalerna."""
    path = save_png(tmp_path, np.array([[10, 20], [30, 40]], dtype=np.uint8))
    image = source.read_frame(source.open_source("file", path))
    assert image.shape == (2, 2, 3)
    for channel in range(3):
        np.testing.assert_array_equal(image[:, :, channel], [[10, 20], [30, 40]])


def test_open_image_with_alpha_loses_the_alpha(tmp_path):
    """En bild med alfakanal (4 kanaler) blir (H, W, 3) med färgerna kvar."""
    rgba = np.zeros((2, 3, 4), dtype=np.uint8)
    rgba[:, :, :3] = (50, 100, 200)
    rgba[:, :, 3] = 128
    image = source.read_frame(source.open_source("file", save_png(tmp_path, rgba)))
    assert image.shape == (2, 3, 3)
    np.testing.assert_array_equal(image, rgba[:, :, :3])


def test_open_bad_files(tmp_path):
    """Fel: 16 bitar, en fil som inte är en bild, en fil som saknas, en mapp och en okänd sort."""
    deep = save_png(tmp_path, np.full((2, 2, 3), 1000, dtype=np.uint16), name="djup.png")
    with pytest.raises(RuntimeError, match=r"camera\.open_failed: Non-8bit per channel"):
        source.open_source("file", deep)
    text = write(tmp_path, "det här är ingen bild", name="text.png")
    with pytest.raises(RuntimeError, match=r"camera\.open_failed: Could not open"):
        source.open_source("file", text)
    for missing in (tmp_path / "saknas.png", tmp_path):
        with pytest.raises(RuntimeError, match=r"camera\.open_failed: Image source does not exist"):
            source.open_source("file", missing)
    with pytest.raises(ValueError, match=r"input\.invalid_argument: Type is unknown video"):
        source.open_source("video", "x.png")


def test_read_frame_gives_a_copy(tmp_path):
    """read_frame ger en kopia: ändrar man den ändras inte källan."""
    src = source.open_source("file", save_png(tmp_path, solid(2, 2, 9)))
    first = source.read_frame(src)
    first[:] = 0
    second = source.read_frame(src)
    assert second is not first
    np.testing.assert_array_equal(second, solid(2, 2, 9))
    assert source.close_source(src) is None
    assert source.read_frame(src).shape == (2, 2, 3)


def use_fake_capture(monkeypatch, opened=True, results=()):
    """Byter cv2.VideoCapture mot ett låtsasobjekt. calls är (nummer, backend), released säger om kameran släpptes."""
    results = list(results)
    cap = types.SimpleNamespace(calls=[], released=False)
    cap.isOpened = lambda: opened
    cap.read = lambda: results.pop(0)

    def release():
        cap.released = True

    def capture(index, backend):
        cap.calls.append((index, backend))
        return cap

    cap.release = release
    monkeypatch.setattr(source.cv2, "VideoCapture", capture)
    return cap


@pytest.mark.parametrize(
    ("platform", "backend"),
    [("linux", cv2.CAP_V4L2), ("win32", cv2.CAP_DSHOW), ("darwin", cv2.CAP_ANY)],
)
def test_camera_backend_per_platform(monkeypatch, platform, backend):
    """Kameran öppnas med rätt backend per system (Linux V4L2, Windows DirectShow, annars OpenCV väljer)."""
    monkeypatch.setattr(source, "sys", types.SimpleNamespace(platform=platform))
    cap = use_fake_capture(monkeypatch)
    src = source.open_source("camera", 3)
    assert src["kind"] == "camera"
    assert cap.calls == [(3, backend)]


def test_camera_that_does_not_open_is_released(monkeypatch):
    """Fel: en kamera som inte öppnas ger camera.open_failed och släpps."""
    cap = use_fake_capture(monkeypatch, opened=False)
    with pytest.raises(RuntimeError, match=r"camera\.open_failed: kunde inte öppna /dev/video0"):
        source.open_source("camera", 0)
    assert cap.released


def test_camera_number_too_big_for_opencv(monkeypatch):
    """Gräns: ett nummer som OpenCV inte ryms ger cv2.error; det blir ett RuntimeError med camera.open_failed."""

    def refuse(index, backend):
        raise cv2.error("nummer utanför heltalen")

    monkeypatch.setattr(source.cv2, "VideoCapture", refuse)
    with pytest.raises(RuntimeError, match=r"camera\.open_failed") as caught:
        source.open_source("camera", 2147483648)
    assert isinstance(caught.value.__cause__, cv2.error)


def test_camera_read_failures_and_close(monkeypatch):
    """Normalt: bilden kommer ur kameran. Fel: (False, None) och (True, None) ger camera.read_failed. close släpper kameran."""
    frame = solid(2, 2, 5)
    cap = use_fake_capture(monkeypatch, results=[(True, frame), (False, None), (True, None)])
    src = source.open_source("camera", 0)
    assert source.read_frame(src) is frame
    for _ in range(2):
        with pytest.raises(RuntimeError, match=r"camera\.read_failed"):
            source.read_frame(src)
    source.close_source(src)
    assert cap.released