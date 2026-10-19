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
blue_weight:float = 0.114
green_weight:float = 0.587
red_weight:float = 0.299

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
        raise ValueError(f"input.invalid_argument: {name} får bara innehålla ändliga tal")

def prepare(image, roi, axis, channel):
    """
    Check image and convert ROI to table in float64 for a channel

    Parameters:
        image: The image, shape (H, W, 3), uint8 in BGR (ndarray).
        roi: Region (x, y, width, height) in pixels (tuple).
        axis: "horiontal" or "vertical" (str).
        channel: onee of the naems in CHANNELS (str).
    Returns:
        2D-array in float64 with spectrum along columns
    Errors:
        ValueError with input.invalid_argument if image, roi, axis or channel is invalid.
    """
    
    if not isinstance(image, np.ndarray) or image.dtype != np.uint8:
        raise ValueError("input.invalid_argument: image must be a uint8 array")

    if image.ndim != 3 or image.shape[2] != 3:
        raise ValueError(f"input.invalid_argument: image must have shape (H, W, 3), got {image.shape}")

    x, y, width, height = roi

    if width <= 0 or height <= 0:
        raise ValueError(f"input.invalid_argument: Width {width} or height {height} of roi are not larger than zero.")

    # Check errors so we dont clip
    h, w = image.shape[:2]
    if x<0 or y<0 or x+width>w or y+height>h:
        raise ValueError(f"input.invalid_argument: roi {roi} is outside the image, width {w} and height {h}")

    if channel not in CHANNELS:
        raise ValueError(f"input.invalid_argument: channel {channel} is not in {CHANNELS}")

    if axis not in ("horizontal", "vertical"):
        raise ValueError(f"input.invalid_argument: axis {axis} must be horizontal or vertical")

    # Actually getting the ROI!
    roi_view = image[y:y+height, x: x+width] # Rows y to y+height, kolumns x to x+width
    cut = roi_view.astype(np.float64)

    blue = cut[:, :, CHANNEL_INDEX["blue"]]
    red = cut[:, :, CHANNEL_INDEX["red"]]
    green = cut[:, :, CHANNEL_INDEX["green"]]

    if channel in CHANNEL_INDEX:
        result = cut[:, :, CHANNEL_INDEX[channel]]
    elif channel == "sum":
        result = blue + green + red
    elif channel == "gray":
        result = red_weight  * red + green_weight * green + blue_weight * blue

    if axis == "vertical":
        result = result.T
    return result

def extract_spectrum(table):
    """
    Takes the average of the rows in the table, one amount per column.
    Parameters: Table: the table from prepare(), form (rows, columns), float64 (ndarray).
    Returns: Average per column, form (kolumns,), float64 (ndarray).
    Error: ValueError with input.invalid_argument if table is not float 64, is inf, is NaN, does not have two dimensions or is empty.
    """

    _check("table", table)

    # Kontrollera form
    if table.ndim != 2:
        raise ValueError(f"input.invalid_argument: table must have 2 dimensions, got shaope {table.shape}")

    if table.size == 0:
        raise ValueError("input.invalid_argument: table is empty")

    return np.mean(table, axis=0)


def average_spectra(stack):
    """Ger medel och spridning av flera spektrum.

    Parametrar: stack: en float64-array med formen (N, P), en rad per bild.
    Returnerar: mean och stddev, båda (P,) float64; stddev är NaN när N är 1.
    Fel: ValueError med input.invalid_argument om stack inte är 2D, inte float64 eller är tom.
    """
    if stack.ndim != 2:
        raise ValueError(f"input.invalid_argument: stack måste vara 2D (en rad per bild), fick ndim {stack.ndim}")
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
        raise ValueError(f"input.invalid_argument: coefficients ska ha 2 eller 3 värden, fick {coefficients.size}")
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
        raise ValueError(f"input.invalid_argument: degree ska vara 1 eller 2, fick {degree}")
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
        raise ValueError(f"input.invalid_argument: grad {degree} behöver minst {degree + 1} punkter, fick {pixels.size}")
    # Minsta kvadrat-anpassning, koefficienterna i stigande ordning. Se rev7, RX10.
    return poly.polyfit(pixels, wavelengths, degree)
