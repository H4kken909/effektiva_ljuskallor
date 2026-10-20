"""calibrate: våglängd ur en punktfil."""

import numpy as np

from spectrometer import calc, files, out, registry


@registry.command("calibrate", "PATH [DEGREE]: anpassa våglängd till en punktfil")
def cmd_calibrate(state, args):
    """Kommandot calibrate PATH [DEGREE]: anpassar våglängden till punktfilen och prövar mot kontrollpunkterna.

    Fel: ValueError med input.invalid_argument vid fel ord, fel i punktfilen, för få punkter eller en linje som inte
    är monoton i det giltiga intervallet; OSError om filen saknas. Den gamla kalibreringen står då kvar.
    """
    if not args:
        registry.need(args, ("PATH",), "calibrate")
    if len(args) > 2:
        raise ValueError("input.invalid_argument: calibrate tar högst två ord (PATH DEGREE)")
    degree = registry.to_int("DEGREE", args[1], 1) if len(args) == 2 else 1
    pixels, wavelengths, is_check = files.load_points(args[0])
    fit_pixels, fit_wavelengths = pixels[~is_check], wavelengths[~is_check]
    check_pixels, check_wavelengths = pixels[is_check], wavelengths[is_check]
    coefficients = calc.fit_wavelength(fit_pixels, fit_wavelengths, degree)  # bara anpassningspunkter
    out.say(f"a0: {coefficients[0]:g}")
    out.say(f"a1: {coefficients[1]:g}")
    if degree == 2:
        out.say(f"a2: {coefficients[2]:g}")
    width = np.max(fit_pixels) - np.min(fit_pixels)
    valid_range = (max(np.min(fit_pixels) - width, 0), np.max(fit_pixels) + width)
    out.say(f"anpassat: pixel {np.min(fit_pixels):g} till {np.max(fit_pixels):g}")
    out.say(f"giltigt: pixel {valid_range[0]:g} till {valid_range[1]:g}")
    # Linjen måste vara monoton i det giltiga intervallet, annars får två pixlar samma våglängd.
    test_pixels = np.arange(valid_range[0], valid_range[1] + 1, dtype=np.float64)
    diffs = np.diff(calc.evaluate_wavelength(test_pixels, coefficients))
    if not (np.all(diffs > 0) or np.all(diffs < 0)):
        raise ValueError(f"input.invalid_argument: inte monoton mellan pixel {valid_range[0]:g} och {valid_range[1]:g}")
    for residual in fit_wavelengths - calc.evaluate_wavelength(fit_pixels, coefficients):
        out.say(f"residual: {residual:g}")
    check_errors = check_wavelengths - calc.evaluate_wavelength(check_pixels, coefficients)
    # Lokalt steg: hur många nm en pixel är vid kontrollpunkten; varna när abs(fel) är större.
    steps = np.abs(calc.evaluate_wavelength(check_pixels + 1, coefficients)
                   - calc.evaluate_wavelength(check_pixels, coefficients))
    for pixel, error, step in zip(check_pixels, check_errors, steps):
        out.say(f"kontrollfel vid pixel {pixel:g}: {error:g}")
        if abs(error) > step:
            out.warn(f"kontrollfelet {error:g} nm är större än steget {step:g} nm.")
    if check_pixels.size == 0:
        out.say("inte kontrollerad: inga kontrollpunkter i filen")
    state["coefficients"] = coefficients
    state["pixel_range"] = valid_range
    state["spectrum"] = None