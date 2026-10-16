"""All räkning i programmet. Filen importerar bara NumPy."""

import numpy as np


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
    # Kontrollera dimensioner och värden av bilden som ska behandlas
    if not isinstance(image, np.ndarray) or image.dtype != np.uint8:
        raise ValueError(f"input.invalid_argument: {image} is invalid.")

    if image.ndim != 3 or image.shape[2] != 3:
        raise ValueError(f"input.invalid_argument: Too many colours or wrong dimensions in {image}")

    x, y, width, height = roi

    if width <= 0 or height <= 0:
        raise ValueError(f"input.invalid_argument: Width {width} or height {height} of roi are not larger than zero.")

    # Check errors so we dont clip
    height, width = image.shape[:2]
    if x<0 or y<0 or x+width>width or y+height>height:
        raise ValueError(f"input.invalid_argument: Clipping detected: x={x}, y={y}, width={width}, height={height}")

    if channel not in CHANNELS:
        raise ValueError(f"input.invalid_argument: channel {channel} is not in {CHANNELS}")

    if axis not in ("horizontal", "vertical"):
        raise ValueError(f"input.invalid_argument: axis: {axis} is either not horizontal or vertical")

    # Actually getting the ROI!
    roi_view = image[y:height, x: width] #Går från y till height, x till width bror
    cut = image.astype(np.float64)

    blue = cut[:, :, CHANNEL_INDEX["blue"]]
    red = cut[:, CHANNEL_INDEX["red"], :]
    green = cut[CHANNEL_INDEX["green"], :, :]

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
    _check("table", table)

    # Kontrollera form
    if table.ndim != 2:
        raise ValueError(f"input.invalid_argument: {table} does not have 2 dimensions.")

    if table.size == 0:
        raise ValueError(f"{table} is empty.")

    return np.mean(table, axis=0)