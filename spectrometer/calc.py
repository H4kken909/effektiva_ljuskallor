"""All räkning i programmet, bara med NumPy: spektrum, medel, våglängd, mörker, respons och transmission.

Filen vet ingenting om state, filer eller kameran.
"""

import numpy as np
from numpy.polynomial import polynomial as poly

CHANNEL_INDEX = {"blue": 0, "green": 1, "red": 2}
CHANNELS = ("gray", "sum", "red", "green", "blue")

# Gråvikter: gray = 0.299·R + 0.587·G + 0.114·B
blue_weight: float = 0.114
green_weight: float = 0.587
red_weight: float = 0.299


def _check(name, a):
    """Fel (input.invalid_argument, med name i texten) om a inte är en float64-array med bara ändliga tal."""
    if not isinstance(a, np.ndarray) or a.dtype != np.float64:
        raise ValueError(f"input.invalid_argument: {name} måste vara en float64-array")
    if not np.all(np.isfinite(a)):
        raise ValueError(f"input.invalid_argument: {name} får bara innehålla ändliga tal")


def prepare(image, roi, axis, channel):
    """Skär ut ROI:n (x, y, width, height) som float64, väljer kanal och vänder vid vertical.

    image är (H, W, 3) uint8 i BGR och counts, eller float64 efter mörkeravdrag. Ger tabellen (rader, kolumner)
    float64 i counts, med spektrumet längs kolumnerna.
    """
    if not isinstance(image, np.ndarray) or image.dtype not in (np.uint8, np.float64):
        raise ValueError("input.invalid_argument: image måste vara en uint8- eller float64-array")
    if image.ndim != 3 or image.shape[2] != 3:
        raise ValueError(f"input.invalid_argument: image måste ha formen (H, W, 3), fick {image.shape}")
    x, y, width, height = roi
    if width <= 0 or height <= 0:
        raise ValueError(f"input.invalid_argument: roi måste ha bredd och höjd större än 0, fick {roi}")
    h, w = image.shape[:2]
    if x < 0 or y < 0 or x + width > w or y + height > h:
        raise ValueError(f"input.invalid_argument: roi {roi} ligger utanför bilden ({w} bred, {h} hög)")
    cut = image[y : y + height, x : x + width].astype(np.float64)
    blue = cut[:, :, CHANNEL_INDEX["blue"]]
    green = cut[:, :, CHANNEL_INDEX["green"]]
    red = cut[:, :, CHANNEL_INDEX["red"]]
    if channel in CHANNEL_INDEX:
        result = cut[:, :, CHANNEL_INDEX[channel]]
    elif channel == "sum":
        result = blue + green + red
    elif channel == "gray":
        # Vikterna summerar till 1 (rev7 RX01).
        result = red_weight * red + green_weight * green + blue_weight * blue
    if axis == "vertical":
        result = result.T
    return result


def extract_spectrum(table):
    """Medlet av raderna i tabellen från prepare(), ett värde per kolumn, (kolumner,) float64. Se rev7, RX05."""
    return np.mean(table, axis=0)


def average_spectra(stack):
    """Ger medel och spridning av flera spektrum: stack är (N, P) float64, en rad per bild.

    mean och stddev är (P,) float64; stddev är NaN när N är 1.
    """
    mean = np.mean(stack, axis=0)
    if stack.shape[0] == 1:
        # En enda bild har ingen spridning: NaN utan varning (rev7 RX07).
        stddev = np.full(len(mean), np.nan)
    else:
        # Stickprovsstandardavvikelse, delad med N - 1 (rev7 RX06).
        stddev = np.std(stack, axis=0, ddof=1)
    return mean, stddev


def evaluate_wavelength(pixels, coefficients):
    """Ger våglängden i nm vid varje pixel: a0 + a1·p (+ a2·p²), a0 först (rev7 RX09).

    pixels är (P,) float64, räknade i hela bilden. coefficients är 2 eller 3 värden i nm, nm per pixel och nm per
    pixel i kvadrat.
    """
    _check("pixels", pixels)
    _check("coefficients", coefficients)
    if coefficients.size not in (2, 3):
        raise ValueError(f"input.invalid_argument: coefficients ska ha 2 eller 3 värden, fick {coefficients.size}")
    return poly.polyval(pixels, coefficients)


def fit_wavelength(pixels, wavelengths, degree):
    """Anpassar ett polynom av grad 1 eller 2 till anpassningspunkterna med minsta kvadrat (rev7 RX10).

    pixels (i hela bilden) och wavelengths (kända, i nm) är (K,) float64. Ger degree + 1 koefficienter, a0 först.
    """
    if degree not in (1, 2):
        raise ValueError(f"input.invalid_argument: degree ska vara 1 eller 2, fick {degree}")
    _check("pixels", pixels)
    _check("wavelengths", wavelengths)
    if np.unique(pixels).size < pixels.size:
        raise ValueError("input.invalid_argument: samma pixel står två gånger")
    if pixels.size < degree + 1:
        raise ValueError(
            f"input.invalid_argument: grad {degree} behöver minst {degree + 1} punkter, fick {pixels.size}"
        )
    return poly.polyfit(pixels, wavelengths, degree)


def subtract_dark(image, dark):
    """Drar av mörkret från bilden, utan att klippa negativa tal (float64, så att inget slår runt; rev7 RX03).

    image och dark är (H, W, 3) float64 i counts. Ger en ny array.
    """
    _check("image", image)
    _check("dark", dark)
    if image.shape != dark.shape:
        raise ValueError(f"input.invalid_argument: mörkret har formen {dark.shape} men bilden har {image.shape}")
    return image - dark


def build_response(wavelengths, measured, known_wavelengths, known_values):
    """Räknar instrumentets relativa respons ur en lampmätning med känd fördelning.

    wavelengths (nm) och measured (counts) är (P,); measured får ha NaN där lampmätningen saknar värde, därför ingen
    _check på den. known_wavelengths (stigande nm) och known_values (relativ effekt) är (K,). Ger responsen (P,)
    float64, normerad så att största värdet är 1, NaN där den inte går att räkna.
    """
    # Ingen extrapolation: NaN utanför de kända punkterna (rev7 RX15).
    known_at_lamp = np.interp(wavelengths, known_wavelengths, known_values, left=np.nan, right=np.nan)
    valid = np.isfinite(measured) & np.isfinite(known_at_lamp) & (known_at_lamp > 0)
    # Uppmätt delat med känt, där det är giltigt (rev7 RX14).
    ratio = np.full(measured.shape[0], np.nan)
    np.divide(measured, known_at_lamp, out=ratio, where=valid)
    if not np.any(valid):
        raise ValueError("input.missing_data: inget giltigt värde i lampmätningen")
    peak = np.max(ratio[valid])
    if peak <= 0:
        raise ValueError("input.missing_data: toppen är inte större än 0")
    return ratio / peak


def _divide_where_above(numerator, denominator, mask, minimum, names):
    """Delar numerator med denominator där masken är True och denominator är strikt större än minimum.

    Gemensam kärna i apply_response och transmission_ratio. Strikt >: exakt minimum är ogiltigt. names är
    (tröskelns, täljarens, nämnarens) namn, för felmeddelandena. Ger (values, mask): kvoten (P,) float64, NaN där den
    inte går att räkna, och den nya masken (P,) bool.
    """
    minimum_name, numerator_name, denominator_name = names
    if not np.isfinite(minimum) or minimum <= 0:
        raise ValueError(f"input.invalid_argument: {minimum_name} måste vara ändligt och större än 0, fick {minimum}")
    _check(numerator_name, numerator[mask])
    _check(denominator_name, denominator[mask])
    new_mask = mask & (denominator > minimum)
    values = np.full(numerator.shape[0], np.nan)
    np.divide(numerator, denominator, out=values, where=new_mask)
    return values, new_mask


def apply_response(signal, response, mask, min_response):
    """Delar signalen med responsen där masken är True och responsen är strikt större än min_response.

    signal är (P,) float64 i counts, response relativ och utan enhet, mask (P,) bool (True där värdet duger).
    Ger (values, mask): den korrigerade signalen (relativ, NaN där den inte går att räkna) och den nya masken.
    Se rev7 RX16.
    """
    return _divide_where_above(signal, response, mask, min_response, ("min_response", "signal", "response"))


def transmission_ratio(sample, reference, mask, min_reference):
    """Delar provet med referensen där masken är True och referensen är strikt större än min_reference.

    sample (får vara negativt) och reference är (P,) float64 i counts, mask (P,) bool (True där värdet duger).
    Ger (values, mask): transmissionen T = I_prov / I_ref som kvot (NaN där den inte går att räkna) och den nya
    masken. Se rev7 T06 och RX17.
    """
    return _divide_where_above(sample, reference, mask, min_reference, ("min_reference", "sample", "reference"))


def extract_median(table):
    """Medianen av raderna i tabellen, ett värde per kolumn: som extract_spectrum, men median i stället för medel.

    Medianen bryr sig inte om en enstaka het pixel eller en rad med ströljus; medlet har mindre brus när raderna
    är lika. ROI-14.
    """
    return np.median(table, axis=0)


def side_background(image, roi, margin, channel, axis="horizontal"):
    """Bakgrunden bredvid bandet: medianen av margin rader ovanför och margin rader under ROI:n, per kolumn.

    Vid axis vertical är det margin kolumner till vänster och till höger. Dras av efter mörkret (ROI-21).
    margin är minst 1. Ger bakgrunden, (P,) float64 i counts, med samma P som prepare ger för roi.
    """
    if margin < 1:
        raise ValueError(f"input.invalid_argument: margin ska vara minst 1, fick {margin}")
    x, y, width, height = roi
    if axis == "vertical":
        sides = [(x - margin, y, margin, height), (x + width, y, margin, height)]
    else:
        sides = [(x, y - margin, width, margin), (x, y + height, width, margin)]
    h, w = image.shape[:2]
    for sx, sy, sw, sh in sides:
        if sx < 0 or sy < 0 or sx + sw > w or sy + sh > h:
            raise ValueError(
                f"input.invalid_argument: bakgrunden behöver {margin} fria rader på båda sidor om roi {roi}"
            )
    rows = np.vstack([prepare(image, side, axis, channel) for side in sides])
    return np.median(rows, axis=0)


def masked_values(spectrum):
    """values i en mätning med NaN där masken är falsk."""
    return np.where(spectrum["mask"], spectrum["values"], np.nan)


def roi_or_whole(roi, image):
    """ROI:n (x, y, bredd, höjd), eller hela bilden när ROI:n är None."""
    return roi if roi is not None else (0, 0, image.shape[1], image.shape[0])
