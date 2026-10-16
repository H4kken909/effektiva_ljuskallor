"""All räkning i programmet. Filen importerar bara NumPy."""

import numpy as np

CHANNEL_INDEX = {"blue": 0, "green": 1, "red": 2}
CHANNELS = ("gray", "sum", "red", "green", "blue")


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
