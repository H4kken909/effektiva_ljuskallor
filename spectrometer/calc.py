"""All räkning i programmet, bara med NumPy: spektrum, medel, våglängd, mörker, respons och transmission.

Används av main.py. Filen vet ingenting om state, filer eller kameran.
"""

import numpy as np
from numpy.polynomial import polynomial as poly

# Variables
## Channels
CHANNEL_INDEX = {"blue": 0, "green": 1, "red": 2}
CHANNELS = ("gray", "sum", "red", "green", "blue")

## Grey weights
blue_weight: float = 0.114
green_weight: float = 0.587
red_weight: float = 0.299


def _check(name, a):
    """Kontrollera att a är en float64-array med bara ändliga tal.

    Parametrar: name: argumentets namn som text, för felmeddelandet (str).
                a: värdet som kontrolleras.
    Returnerar: None.
    Fel: ValueError med input.invalid_argument om a inte är en
         float64-array, eller om a innehåller inf eller NaN.
    """

    if not isinstance(a, np.ndarray) or a.dtype != np.float64:
        raise ValueError(f"input.invalid_argument: {name} måste vara en float64-array")

    if not np.all(np.isfinite(a)):
        raise ValueError(
            f"input.invalid_argument: {name} får bara innehålla ändliga tal"
        )


def prepare(image, roi, axis, channel):
    """Skär ut ROI:n som float64, väljer kanal och vänder vid vertical.

    Parametrar: image: bilden, (H, W, 3) uint8 i BGR och counts, eller float64 efter mörkeravdrag;
    roi: (x, y, width, height) i pixlar; axis: "horizontal" eller "vertical"; channel: ett namn i CHANNELS.
    Returnerar: tabellen, (rader, kolumner) float64 i counts, med spektrumet längs kolumnerna.
    Fel: ValueError med input.invalid_argument om bilden, ROI:n, axis eller channel är fel.
    """
    if not isinstance(image, np.ndarray) or image.dtype not in (np.uint8, np.float64):
        raise ValueError(
            "input.invalid_argument: image måste vara en uint8- eller float64-array"
        )
    if image.ndim != 3 or image.shape[2] != 3:
        raise ValueError(
            f"input.invalid_argument: image måste ha formen (H, W, 3), fick {image.shape}"
        )
    x, y, width, height = roi
    if width <= 0 or height <= 0:
        raise ValueError(
            f"input.invalid_argument: roi måste ha bredd och höjd större än 0, fick {roi}"
        )
    h, w = image.shape[:2]
    if x < 0 or y < 0 or x + width > w or y + height > h:
        raise ValueError(
            f"input.invalid_argument: roi {roi} ligger utanför bilden ({w} bred, {h} hög)"
        )
    if channel not in CHANNELS:
        raise ValueError(
            f"input.invalid_argument: okänd kanal {channel}, tillåtna är {CHANNELS}"
        )
    if axis not in ("horizontal", "vertical"):
        raise ValueError(
            f"input.invalid_argument: okänd riktning {axis}, tillåtna är ('horizontal', 'vertical')"
        )
    view = image[y : y + height, x : x + width]
    cut = view.astype(np.float64)
    blue = cut[:, :, CHANNEL_INDEX["blue"]]
    green = cut[:, :, CHANNEL_INDEX["green"]]
    red = cut[:, :, CHANNEL_INDEX["red"]]
    if channel in CHANNEL_INDEX:
        result = cut[:, :, CHANNEL_INDEX[channel]]
    elif channel == "sum":
        result = blue + green + red
    elif channel == "gray":
        # Gråvärdet är varje färg gånger sin vikt, ihop (vikterna summerar till 1). Se rev7, RX01.
        result = red_weight * red + green_weight * green + blue_weight * blue
    if axis == "vertical":
        result = result.T
    return result


def extract_spectrum(table):
    """
    Takes the average of the rows in the table, one amount per column.
    Parameters: Table: the table from prepare(), form (rows, columns), float64 (ndarray).
    Returns: Average per column, form (columns,), float64 (ndarray).
    Error: ValueError with input.invalid_argument if table is not float 64, is inf, is NaN, does not have two dimensions or is empty.
    """

    _check("table", table)

    # Kontrollera form
    if table.ndim != 2:
        raise ValueError(
            f"input.invalid_argument: table must have 2 dimensions, got shape {table.shape}"
        )

    if table.size == 0:
        raise ValueError("input.invalid_argument: table is empty")

    # Spektrumet är medlet av raderna, ett värde per kolumn. Se rev7, RX05.
    return np.mean(table, axis=0)


def average_spectra(stack):
    """Ger medel och spridning av flera spektrum.

    Parametrar: stack: en float64-array med formen (N, P), en rad per bild.
    Returnerar: mean och stddev, båda (P,) float64; stddev är NaN när N är 1.
    Fel: ValueError med input.invalid_argument om stack inte är 2D, inte float64 eller är tom.
    """
    if stack.ndim != 2:
        raise ValueError(
            f"input.invalid_argument: stack måste vara 2D (en rad per bild), fick ndim {stack.ndim}"
        )
    if stack.dtype != np.float64:
        raise ValueError("input.invalid_argument: stack måste vara en float64-array")
    if stack.size == 0:
        raise ValueError("input.invalid_argument: stack är tom")
    mean = np.mean(stack, axis=0)
    n = stack.shape[0]
    if n == 1:
        # En enda bild har ingen spridning: NaN utan varning. Se rev7, RX07.
        stddev = np.full(len(mean), np.nan)
    else:
        # Stickprovsstandardavvikelse, delad med N - 1 (ddof=1). Se rev7, RX06.
        stddev = np.std(stack, axis=0, ddof=1)
    return mean, stddev


def evaluate_wavelength(pixels, coefficients):
    """Ger våglängden i nm vid varje pixel.

    Parametrar: pixels: pixlar räknade i hela bilden, (P,) float64; coefficients: 2 eller 3 koefficienter,
    float64, a0 först (nm, nm per pixel, nm per pixel i kvadrat).
    Returnerar: våglängderna i nm, (P,) float64.
    Fel: ValueError med input.invalid_argument om en array inte är float64 med ändliga tal,
    eller om coefficients inte har 2 eller 3 värden.
    """
    _check("pixels", pixels)
    _check("coefficients", coefficients)
    if coefficients.size not in (2, 3):
        raise ValueError(
            f"input.invalid_argument: coefficients ska ha 2 eller 3 värden, fick {coefficients.size}"
        )
    # Våglängd = a0 + a1·p (+ a2·p²), a0 först. Se rev7, RX09.
    return poly.polyval(pixels, coefficients)


def fit_wavelength(pixels, wavelengths, degree):
    """Anpassar ett polynom av grad 1 eller 2 till anpassningspunkterna.

    Parametrar: pixels: pixlar i hela bilden, (K,) float64; wavelengths: kända våglängder i nm, (K,) float64;
    degree: 1 eller 2.
    Returnerar: degree + 1 koefficienter, float64, a0 först.
    Fel: ValueError med input.invalid_argument om graden inte är 1 eller 2, arrayerna är fel,
    samma pixel står två gånger eller punkterna är för få.
    """
    if degree not in (1, 2):
        raise ValueError(
            f"input.invalid_argument: degree ska vara 1 eller 2, fick {degree}"
        )
    _check("pixels", pixels)
    _check("wavelengths", wavelengths)
    if pixels.shape != wavelengths.shape:
        raise ValueError(
            f"input.invalid_argument: pixels och wavelengths har olika form, {pixels.shape} och {wavelengths.shape}"
        )
    unique = np.unique(pixels)
    if unique.size < pixels.size:
        raise ValueError("input.invalid_argument: samma pixel står två gånger")
    if pixels.size < degree + 1:
        raise ValueError(
            f"input.invalid_argument: grad {degree} behöver minst {degree + 1} punkter, fick {pixels.size}"
        )
    # Minsta kvadrat-anpassning, koefficienterna i stigande ordning. Se rev7, RX10.
    return poly.polyfit(pixels, wavelengths, degree)


def subtract_dark(image, dark):
    """Drar av mörkret från bilden, utan att klippa negativa tal.

    Parametrar: image och dark: (H, W, 3) float64 i counts.
    Returnerar: image minus dark, en ny (H, W, 3) float64-array i counts.
    Fel: ValueError med input.invalid_argument om en array inte är float64 med ändliga tal eller formerna skiljer sig.
    """
    _check("image", image)
    _check("dark", dark)
    if image.shape != dark.shape:
        raise ValueError(
            f"input.invalid_argument: mörkret har formen {dark.shape} men bilden har {image.shape}"
        )
    # Signal utan mörker = bild minus mörker, i float64 så att inget slår runt. Se rev7, RX03.
    return image - dark


def build_response(wavelengths, measured, known_wavelengths, known_values):
    """Räknar instrumentets relativa respons ur en lampmätning med känd fördelning.

    measured får ha NaN där lampmätningen saknar värde, därför ingen _check på den.

    Parametrar: wavelengths: lampmätningens våglängder i nm, (P,); measured: lampmätningen i counts, (P,), får ha NaN;
    known_wavelengths: kända våglängder i stigande nm, (K,); known_values: känd relativ effekt, (K,).
    Returnerar: responsen, (P,) float64, normerad så att största värdet är 1, NaN där den inte går att räkna.
    Fel: ValueError med input.invalid_argument vid olika form eller färre än två kända punkter,
    och med input.missing_data om inget värde är giltigt eller toppen inte är större än 0.
    """
    if (
        wavelengths.shape != measured.shape
        or known_wavelengths.shape != known_values.shape
        or known_wavelengths.size < 2
    ):
        raise ValueError(
            "input.invalid_argument: olika form eller färre än två kända punkter"
        )
    # Interpolation utan extrapolation: NaN utanför de kända punkterna. Se rev7, RX15.
    known_at_lamp = np.interp(
        wavelengths, known_wavelengths, known_values, left=np.nan, right=np.nan
    )
    valid = np.isfinite(measured) & np.isfinite(known_at_lamp) & (known_at_lamp > 0)
    # Respons = uppmätt delat med känt, där det är giltigt. Se rev7, RX14.
    ratio = np.full(measured.shape[0], np.nan)
    np.divide(measured, known_at_lamp, out=ratio, where=valid)
    if not np.any(valid):
        raise ValueError("input.missing_data: inget giltigt värde i lampmätningen")
    peak = np.max(ratio[valid])
    if peak <= 0:
        raise ValueError("input.missing_data: toppen är inte större än 0")
    # Normerad: 1 där instrumentet är känsligast.
    return ratio / peak


def apply_response(signal, response, mask, min_response):
    """Delar signalen med responsen där masken är True och responsen är strikt större än min_response.

    Parametrar: signal: (P,) float64 i counts; response: (P,) float64, relativ, utan enhet;
    mask: (P,) bool, True där värdet duger; min_response: minsta giltiga respons, utan enhet.
    Returnerar: (values, mask): values (P,) float64, relativ, NaN där det inte går att räkna, och den nya masken (P,) bool.
    Fel: ValueError med input.invalid_argument vid olika form, en mask som inte är bool, en tröskel som inte är
    ändlig och större än 0, eller NaN och inf på en giltig plats.
    """
    if signal.shape != response.shape:
        raise ValueError(
            f"input.invalid_argument: response har annan form än signal {signal.shape} {response.shape}"
        )
    if signal.shape != mask.shape:
        raise ValueError(
            f"input.invalid_argument: mask har annan form än signal {signal.shape} {mask.shape}"
        )
    if mask.dtype != np.bool_:
        raise ValueError(
            f"input.invalid_argument: mask måste vara en bool-array, fick {mask.dtype}"
        )
    if not np.isfinite(min_response) or min_response <= 0:
        raise ValueError(
            f"input.invalid_argument: min_response måste vara ändligt och större än 0, fick {min_response}"
        )
    _check("signal", signal[mask])
    _check("response", response[mask])
    # Strikt >: exakt min_response är ogiltig. Se rev7, RX16.
    new_mask = mask & (response > min_response)
    values = np.full(signal.shape[0], np.nan)
    # Korrigerad signal = signal delad med responsen, bara där den nya masken är True.
    np.divide(signal, response, out=values, where=new_mask)
    return values, new_mask


def transmission_ratio(sample, reference, mask, min_reference):
    """Delar provet med referensen där masken är True och referensen är strikt större än min_reference.

    Parametrar: sample: provet, (P,) float64 i counts, får vara negativt; reference: referensen, (P,) float64 i counts;
    mask: (P,) bool, True där värdet duger; min_reference: minsta giltiga referens i counts.
    Returnerar: (values, mask): transmissionen (P,) float64 som kvot, NaN där den inte går att räkna,
    och den nya masken (P,) bool.
    Fel: ValueError med input.invalid_argument vid olika form, en mask som inte är bool, en tröskel som inte är
    ändlig och större än 0, eller NaN och inf på en giltig plats.
    """
    if sample.shape != reference.shape:
        raise ValueError(
            f"input.invalid_argument: reference har annan form än sample {sample.shape} {reference.shape}"
        )
    if sample.shape != mask.shape:
        raise ValueError(
            f"input.invalid_argument: mask har annan form än sample {sample.shape} {mask.shape}"
        )
    if mask.dtype != np.bool_:
        raise ValueError(
            f"input.invalid_argument: mask måste vara en bool-array, fick {mask.dtype}"
        )
    if not np.isfinite(min_reference) or min_reference <= 0:
        raise ValueError(
            f"input.invalid_argument: min_reference måste vara ändligt och större än 0, fick {min_reference}"
        )
    _check("sample", sample[mask])
    _check("reference", reference[mask])
    # Strikt >: exakt min_reference är ogiltig. Se rev7, T06.
    valid = mask & (reference > min_reference)
    values = np.full(sample.shape[0], np.nan)
    # Transmission T = I_prov / I_ref, bara där den nya masken är True. Se rev7, RX17.
    np.divide(sample, reference, out=values, where=valid)
    return values, valid
