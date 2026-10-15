"""Main calculation core"""

import numpy as np

CHANNEL_INDEX:dict = {"blue": 0, "green":1, "red":2}
CHANNELS:tuple = ("gray", "sum", "red", "green", "blue")

def _check(name, a):
    """Det funktionen kontrollerar"""

    if not isinstance(a, np.ndarray) or a.dtype != np.float64:
        raise ValueError(f"input.invalid_argument: {name}")

    if not np.all(np.isfinite(a)):
        raise ValueError(f"input.invalid_argument: {name}")

def prepare(image, roi, axis, channel):
    