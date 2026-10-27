import numpy as np
from numpy.polynomial import polynomial as poly

CHANNEL_INDEX = {"blue": 0, "green": 1, "red": 2}
CHANNELS = ("gray", "sum", "red", "green", "blue")


def prepare(image, roi, axis, channel):
    x, y, width, height = roi
    h, w = image.shape[:2]
    if width <= 0 or height <= 0 or x < 0 or y < 0 or x + width > w or y + height > h:
        raise ValueError(f"roi {roi} does not fit in the image ({w}x{h})")
    cut = image[y:y + height, x:x + width].astype(np.float64)
    blue, green, red = cut[:, :, 0], cut[:, :, 1], cut[:, :, 2]
    if channel in CHANNEL_INDEX:
        result = cut[:, :, CHANNEL_INDEX[channel]]
    elif channel == "sum":
        result = blue + green + red
    else:
        result = 0.299 * red + 0.587 * green + 0.114 * blue
    return result.T if axis == "vertical" else result


def average_spectra(stack):
    mean = np.mean(stack, axis=0)
    if stack.shape[0] == 1:
        return mean, np.full(len(mean), np.nan)
    return mean, np.std(stack, axis=0, ddof=1)


def evaluate_wavelength(pixels, coefficients):
    return poly.polyval(pixels, coefficients)


def fit_wavelength(pixels, wavelengths, degree):
    if np.unique(pixels).size < degree + 1:
        raise ValueError(f"degree {degree} needs at least {degree + 1} different pixel values")
    return poly.polyfit(pixels, wavelengths, degree)


def build_response(wavelengths, measured, known_wavelengths, known_values):
    known = np.interp(wavelengths, known_wavelengths, known_values, left=np.nan, right=np.nan)
    valid = np.isfinite(measured) & np.isfinite(known) & (known > 0)
    if not np.any(valid):
        raise ValueError("no valid value in the lamp measurement")
    ratio = np.full(measured.shape[0], np.nan)
    np.divide(measured, known, out=ratio, where=valid)
    return ratio / np.max(ratio[valid])


def apply_response(signal, response, mask, minimum):
    new_mask = mask & (response > minimum)
    values = np.full(signal.shape[0], np.nan)
    np.divide(signal, response, out=values, where=new_mask)
    return values, new_mask


def masked_values(spectrum):
    return np.where(spectrum["mask"], spectrum["values"], np.nan)


def roi_or_whole(roi, image):
    return (0, 0, image.shape[1], image.shape[0]) if roi is None else roi
