import time

import numpy as np

from spectrometer.core import out
from spectrometer.measurement import calc, source

CAPTURE_FRAMES = 16
MIN_RESPONSE = 0.01
MIN_REFERENCE = 1.0


def monotonic(x):
    steps = np.diff(x)
    return x.size > 1 and (np.all(steps > 0) or np.all(steps < 0))


def calibrate_axis(state, x, values, mask):
    x_label = "pixel"
    if state["coefficients"] is not None:
        low, high = state["pixel_range"]
        inside = (x >= low) & (x <= high)
        mask = mask & inside
        wavelength = calc.evaluate_wavelength(x, state["coefficients"])
        if not monotonic(wavelength):
            wavelength, values, mask = wavelength[inside], values[inside], mask[inside]
            if not monotonic(wavelength):
                raise ValueError("the wavelength is not monotonic in the ROI. Shrink the ROI or try degree 1")
        x, x_label = wavelength, "wavelength (nm)"
    if x[0] > x[-1]:
        x, values, mask = x[::-1], values[::-1], mask[::-1]
    return x, values, mask, x_label


_lent = None


def lend(source_setting, src):
    global _lent
    _lent = None if src is None else (source_setting, src)


def read_frames(state, n, src=None):
    lent = src is None and _lent is not None and _lent[0] == state["settings"]["source"]
    if lent:
        src = _lent[1]
    opened_here = src is None
    if opened_here:
        kind, value = state["settings"]["source"]
        if kind == "camera":
            out.say("Opening the camera ...")
        src = source.open_source(kind, value)
    try:
        if opened_here or lent:
            apply_controls(state, src)
        return [source.read_frame(src) for _ in range(n)], source.describe(src)
    finally:
        if opened_here:
            source.close_source(src)


def apply_controls(state, src):
    for name in ("auto", "exposure", "gain"):
        value = state["controls"][name]
        if value is not None and not source.set_control(src, name, value):
            out.warn(f"the camera did not accept {name}")


def warn_saturated(count):
    if count:
        out.warn("saturated (255 in the raw image). Lower the exposure.")


def make_spectrum(state, images, camera):
    cfg = state["settings"]
    roi = calc.roi_or_whole(cfg["roi"], images[0])
    x0, y0, width, height = roi
    spectra = []
    saturated_px, saturated = 0, False
    used = [calc.CHANNEL_INDEX[cfg["channel"]]] if cfg["channel"] in calc.CHANNEL_INDEX else [0, 1, 2]
    for image in images:
        hit = (image[y0:y0 + height, x0:x0 + width][:, :, used] >= 255).any(axis=2)
        saturated_px = max(saturated_px, int(hit.sum()))
        saturated = saturated | hit.any(axis=0 if cfg["axis"] == "horizontal" else 1)
        if state["dark"] is not None:
            if image.shape != state["dark"].shape:
                raise ValueError(f"the dark frame is {state['dark'].shape} but the image is {image.shape}")
            image = image.astype(np.float64) - state["dark"]
        spectra.append(np.mean(calc.prepare(image, roi, cfg["axis"], cfg["channel"]), axis=0))
    mean, stddev = calc.average_spectra(np.stack(spectra))
    first, count = (x0, width) if cfg["axis"] == "horizontal" else (y0, height)
    pixels = np.arange(first, first + count).astype("float64")
    x, order, mask, x_label = calibrate_axis(state, pixels, np.arange(pixels.size), np.isfinite(mean))
    values = mean[order]
    return {"x": x, "values": values, "mask": mask, "x_label": x_label, "y_label": "signal (counts)",
            "saturated_px": saturated_px, "saturated": saturated[order], "stddev": stddev[order],
            "frames": cfg["frames"], "px": pixels[order], "raw": np.where(mask, values, np.nan), "camera": camera}


def measure(state, src=None, timing=None):
    started = time.perf_counter()
    images, camera = read_frames(state, state["settings"]["frames"], src)
    read_done = time.perf_counter()
    spectrum = make_spectrum(state, images, camera)
    if state["use_response"] and state["mode"] == "direct":
        response = state["response"]
        at_x = np.interp(spectrum["x"], response["x"], response["values"], left=np.nan, right=np.nan)
        spectrum["values"], spectrum["mask"] = calc.apply_response(
            spectrum["values"], at_x, spectrum["mask"] & np.isfinite(at_x), MIN_RESPONSE)
        spectrum["y_label"] = "corrected signal (relative)"
    if state["mode"] == "transmission":
        reference = state["reference"]
        if reference is None:
            raise ValueError("no reference, run reference first")
        if not np.array_equal(spectrum["x"], reference["x"]) or state["settings"]["channel"] != reference["channel"]:
            raise ValueError("the ROI, calibration or channel differs from the reference's, run reference again")
        spectrum["values"], spectrum["mask"] = calc.apply_response(
            spectrum["values"], reference["values"], spectrum["mask"] & reference["mask"], MIN_REFERENCE)
        spectrum["y_label"] = "transmission (ratio)"
    state["image"] = images[-1]
    state["spectrum"] = spectrum
    if timing is not None:
        timing["read"] = read_done - started
        timing["compute"] = time.perf_counter() - read_done
    return spectrum


def measure_direct(state, n):
    direct = state.copy()
    direct["settings"] = dict(state["settings"], frames=n)
    direct["mode"] = "direct"
    direct["use_response"] = False
    return measure(direct)
