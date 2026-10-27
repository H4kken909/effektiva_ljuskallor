import math
from datetime import datetime
from pathlib import Path

import numpy as np

from spectrometer import __version__
from spectrometer.analysis import bandgap, color, peaks, series
from spectrometer.core import files, out, registry, session
from spectrometer.live import live
from spectrometer.measurement import calc, measure, source
from spectrometer.visual import display, plot, theme

LIMITS = (
    "The intensity is relative: the camera gives counts, not watts, lumens or efficiency.",
    "8 bits: every pixel is 0-255; at 255 it is saturated and the peak becomes too low (step warns).",
    f"The window is {bandgap.WINDOW_NM[0]:g}-{bandgap.WINDOW_NM[1]:g} nm with the KO calibration: outside it there is "
    "no calibrated wavelength.",
    "The resolution is the FWHM of a narrow line (laser or the fluorescent tube's 576.96 and 579.07 nm); "
    "fwhm prints it.",
    "Color and color temperature need response on; the color temperature only holds near the blackbody curve.",
    "The bandgap is the steepest slope extrapolated to A = 0; the uncertainty is only ±0.5 pixel steps.",
    "The tests show that the computation is right, not that the instrument measures correctly.",
)


def cmd_help(state, args):
    out.table([(name, text) for name, (text, func) in registry.COMMANDS.items()])
    out.say("help limits shows what the numbers mean.")


def cmd_help_limits(state, args):
    for line in LIMITS:
        out.say(line)


def cmd_quit(state, args):
    if state["spectrum"] is not None and "saved_in" not in state["spectrum"] and out.interactive():
        try:
            answer = out.ask("The measurement is not saved. Quit anyway? (y/n) ")
        except EOFError:
            answer = "y"
        if answer.strip().lower() not in ("y", "yes"):
            return None
    out.say("Quitting.")
    return True


def cmd_show(state, args):
    settings = state["settings"]
    out.say(session.describe(state))
    out.say(f"axis: {settings['axis']} · frames: {settings['frames']} · output_dir: {settings['output_dir']}")
    out.say(session.chain(state))
    out.say(f"reference {out.YES[state['reference'] is not None]} · mode {state['mode']} · "
            f"measurement {out.YES[state['spectrum'] is not None]}")
    for name, value in state["controls"].items():
        if value is not None:
            out.say(f"camera {name}: {value}")
    if state["note"]:
        out.say(f"note: {state['note']}")


def cmd_pause(state, args):
    text = " ".join(args)
    if out.interactive():
        out.ask(f"{text}. Press Enter: ")
    else:
        out.say(text)


def cmd_run(state, args):
    if len(args) != 1:
        raise ValueError("usage: run FILE")
    with open(args[0], encoding="utf-8-sig") as f:
        for row in f:
            line = row.strip().removeprefix("spektro>").strip()
            if line == "" or line.startswith("#"):
                continue
            out.say(f"spektro> {line}")
            if registry.run_command(state, line):
                return True


def cmd_source(state, args):
    if len(args) != 2 or args[0] not in ("file", "camera"):
        raise ValueError("usage: source file PATH or source camera N")
    session.set_setting(state, "source", (args[0], args[1] if args[0] == "file" else int(args[1])))
    state["image"] = None
    out.say(f"source {args[0]} {args[1]}")


def cmd_roi(state, args):
    if args == ["full"]:
        session.set_setting(state, "roi", None)
        out.say("roi full")
        return
    if len(args) != 4:
        raise ValueError("usage: roi X Y W H or roi full")
    roi = tuple(int(word) for word in args)
    session.set_setting(state, "roi", roi)
    out.say("roi " + " ".join(str(n) for n in roi) + " (checked at the next measurement)")


def cmd_channel(state, args):
    if len(args) != 1 or args[0] not in calc.CHANNELS:
        raise ValueError("usage: channel " + ", ".join(calc.CHANNELS))
    session.set_setting(state, "channel", args[0])
    out.say(f"channel: {args[0]}")


def cmd_axis(state, args):
    if len(args) != 1 or args[0] not in ("horizontal", "vertical"):
        raise ValueError("usage: axis horizontal or axis vertical")
    session.set_setting(state, "axis", args[0])
    out.say(f"axis: {args[0]}")


def cmd_frames(state, args):
    if len(args) != 1:
        raise ValueError("usage: frames N")
    n = registry.to_frames(args[0])
    session.set_setting(state, "frames", n)
    out.say(f"frames: {n}")


def set_control(state, name, args):
    if len(args) != 1:
        raise ValueError(f"usage: {name} N")
    value = float(args[0])
    if not math.isfinite(value):
        raise ValueError(f"{name} must be a number")
    state["controls"][name] = value
    state["spectrum"] = None
    out.say(f"{name}: {args[0]} (set when the camera opens)")


def cmd_exposure(state, args):
    set_control(state, "exposure", args)


def cmd_gain(state, args):
    set_control(state, "gain", args)


def cmd_auto(state, args):
    if args not in (["on"], ["off"]):
        raise ValueError("usage: auto on or auto off")
    state["controls"]["auto"] = args[0] == "on"
    state["spectrum"] = None
    out.say(f"auto: {args[0]} (set when the camera opens)")


def cmd_step(state, args):
    spectrum = measure.measure(state)
    if not spectrum["mask"].any():
        state["spectrum"] = None
        raise ValueError("no valid position in the spectrum (all below the threshold or outside the calibration)")
    i = int(np.nanargmax(calc.masked_values(spectrum)))
    frames = state["settings"]["frames"]
    out.say(f"Peak {out.fmt(spectrum['values'][i])} at {spectrum['x_label']} {out.fmt(spectrum['x'][i])} "
            f"({frames} frame{'s' if frames != 1 else ''})")
    measure.warn_saturated(spectrum["saturated_px"])
    if source.auto_on(spectrum["camera"]):
        out.warn("auto exposure is on, the exposure changes between measurements. Run auto off.")
    values = spectrum["values"][spectrum["mask"]]
    if state["dark"] is not None and state["mode"] == "direct" and not state["use_response"] and np.any(values < -5):
        out.warn("some positions are below -5 counts after dark subtraction, does the dark frame match?")
    if state["mode"] == "transmission" and np.any(values > 1.05):
        out.warn("transmission above 105 % at some positions")


def cmd_save(state, args):
    excel = "--excel" in args
    if excel:
        args.remove("--excel")
    if len(args) > 1:
        raise ValueError("usage: save [DIR] [--excel]")
    spectrum = registry.need_spectrum(state)
    if "loaded_from" in spectrum:
        raise ValueError(f"already saved, it was loaded from {spectrum['loaded_from']}")
    if args:
        parent = args[0]
    elif state["series"] is None:
        parent = state["settings"]["output_dir"]
    else:
        parent = state["series"]["folder"]
    saved = {
        **state["settings"],
        "camera": spectrum["camera"],
        "calibration_points_file": state["calibration_points_file"],
        "program_version": __version__,
        "measured_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "controls": state["controls"],
        "note": state["note"],
        "annotations": state["annotations"],
        "coefficients": None if state["coefficients"] is None else state["coefficients"].tolist(),
        "dark": state["dark"] is not None,
        "use_response": state["use_response"],
        "mode": state["mode"],
    }
    folder = files.save_measurement(parent, spectrum, state["image"], saved)
    spectrum["saved_in"] = folder.as_posix()
    try:
        display.save_png(state, folder)
    except (ValueError, RuntimeError, OSError) as error:
        out.warn(f"spectrum.png could not be drawn ({error})")
    out.say(f"Saved in {folder.as_posix()}")
    if state["series"] is not None:
        series.add_row(state["series"]["file"], folder, saved, spectrum)
        out.say(f"series {state['series']['name']}: row added to {state['series']['file']}")
    if excel:
        out.say(f"Excel: {files.save_excel(folder).as_posix()}")


def cmd_start(state, args):
    seconds = float(args[0]) if args else None
    if live.HOST is not None:
        live.HOST.start_live(seconds)
    else:
        live.run(state, seconds)


def cmd_calibrate(state, args):
    if not args:
        raise ValueError("usage: calibrate PATH [DEGREE]")
    degree = int(args[1]) if len(args) > 1 else 1
    if degree < 1:
        raise ValueError("DEGREE must be at least 1")
    pixels, wavelengths, is_check = files.load_points(args[0])
    fit_pixels, fit_wavelengths = pixels[~is_check], wavelengths[~is_check]
    coefficients = calc.fit_wavelength(fit_pixels, fit_wavelengths, degree)
    for name, unit, value in zip(("a0", "a1", "a2"), ("nm", "nm/pixel", "nm/pixel^2"), coefficients):
        out.say(f"{name}: {out.fmt(value)} {unit}")
    low, high = np.min(fit_pixels), np.max(fit_pixels)
    valid_range = (max(low - (high - low), 0), high + (high - low))
    out.say(f"fitted: pixel {out.fmt(low)} to {out.fmt(high)}")
    out.say(f"valid: pixel {out.fmt(valid_range[0])} to {out.fmt(valid_range[1])}")
    for residual in fit_wavelengths - calc.evaluate_wavelength(fit_pixels, coefficients):
        out.say(f"residual: {out.fmt(round(residual, 6) + 0.0)}")
    for pixel, nm in zip(pixels[is_check], wavelengths[is_check]):
        error = nm - calc.evaluate_wavelength(pixel, coefficients)
        out.say(f"check error at pixel {out.fmt(pixel)}: {out.fmt(error)}")
        if abs(error) > abs(calc.evaluate_wavelength(pixel + 1, coefficients) - calc.evaluate_wavelength(pixel, coefficients)):
            out.warn(f"the check error {out.fmt(error)} nm is larger than one pixel")
    if not is_check.any():
        out.say("not checked: no check points in the file")
    if not np.array_equal(state["coefficients"], coefficients):
        session.forget_response(state)
    state["coefficients"] = coefficients
    state["pixel_range"] = valid_range
    state["fit_range"] = (low, high)
    state["calibration_points_file"] = args[0]
    state["spectrum"] = None
    session.mark_taken(state, "calibrate")


def find_peaks(state, n):
    spectrum = registry.need_spectrum(state)
    if "loaded_from" in spectrum:
        raise ValueError("peaks works after step, not after load (the pixels are counted from the roi)")
    values = calc.masked_values(spectrum)
    pixels = spectrum["px"]
    found = []
    for i in peaks.find_peaks(spectrum["values"], spectrum["mask"], 0.1, middle=True)[:n]:
        pixel = float(np.interp(peaks.refine_peak(values, i), np.arange(pixels.size), pixels))
        found.append((round(pixel, 1), float(spectrum["values"][i])))
    return sorted(found)


def propose_points(state, line_path):
    lines = files.load_lines(line_path)
    found = find_peaks(state, lines.size)
    if len(found) < 2:
        raise ValueError(f"the matching needs at least two peaks, found {len(found)}")
    pixels = np.array([item[0] for item in found])
    chosen, rms, next_rms = peaks.match_peaks(pixels, lines)
    rows = [f"{pixels[k]:.1f},{chosen[k]:.10g},{int(k == 1 and pixels.size >= 3)}" for k in range(pixels.size)]
    out.say(f"suggestion: {pixels.size} peaks against {lines.size} lines, rms {rms:.2f} nm (review before calibrate)")
    out.say("\n".join(["pixel,wavelength_nm,check", *rows]))
    if pixels.size < lines.size or next_rms - rms < 1.0:
        out.warn("the matching may be wrong (fewer peaks than lines, or a second matching almost as good)")


def cmd_peaks(state, args):
    if args and not args[0].lstrip("-").isdigit():
        propose_points(state, args[0])
        return
    n = int(args[0]) if args else 5
    if n < 1:
        raise ValueError("N must be at least 1")
    found = find_peaks(state, n)
    if not found:
        out.say("no peaks")
    for k, (pixel, value) in enumerate(found, start=1):
        text = f"peak {k}: pixel {pixel:.1f} value {out.fmt(value)}"
        if state["coefficients"] is not None:
            text += f"  {calc.evaluate_wavelength(pixel, state['coefficients']):.1f} nm"
            if not state["fit_range"][0] <= pixel <= state["fit_range"][1]:
                text += "  (outside the fitted range)"
        out.say(text)


def cmd_dark(state, args):
    n = registry.to_frames(args[0]) if args else measure.CAPTURE_FRAMES
    if not registry.ready(state, "Block the light path and press Enter (type cancel to skip): "):
        out.say("Cancelled.")
        return
    images, state["dark_camera"] = measure.read_frames(state, n)
    state["dark"] = np.mean(images, axis=0)
    state["spectrum"] = None
    session.mark_taken(state, "dark")
    out.say(f"dark: {n} frame(s), mean {out.fmt(np.mean(state['dark']))}")
    image = state["image"]
    if image is not None and image.shape == state["dark"].shape:
        settings = state["settings"]
        roi = calc.roi_or_whole(settings["roi"], image)
        dark_mean = np.mean(calc.prepare(state["dark"], roi, settings["axis"], settings["channel"]))
        if dark_mean >= 0.5 * np.mean(calc.prepare(image, roi, settings["axis"], settings["channel"])):
            out.warn("the dark frame is as bright as the image. Was the light path blocked?")
    session.forget_reference(state)
    if state["response"] is not None:
        out.warn("the response was built with the old dark frame")


def cmd_response(state, args):
    if not args or args[0] not in ("build", "on", "off"):
        raise ValueError("usage: response build KNOWNFILE [N], response on or response off")
    if args[0] == "build":
        if len(args) < 2:
            raise ValueError("usage: response build KNOWNFILE [N]")
        n = registry.to_frames(args[2]) if len(args) > 2 else measure.CAPTURE_FRAMES
        if state["dark"] is None:
            raise ValueError("no dark frame, run dark first")
        if state["coefficients"] is None:
            raise ValueError("no calibration, run calibrate first")
        known_wavelengths, known_values = files.load_known(args[1])
        lamp = measure.measure_direct(state, n)
        values = calc.build_response(lamp["x"], calc.masked_values(lamp), known_wavelengths, known_values)
        state["response"] = {"x": lamp["x"].copy(), "values": values, "frames": n, "known_file": args[1]}
        state["spectrum"] = None
        session.mark_taken(state, "response")
        out.say(f"response: {np.count_nonzero(np.isfinite(values))} of {len(values)} positions valid")
        if np.any((values > measure.MIN_RESPONSE) & (values < 0.1)):
            out.warn("some positions have a response below 0.1, the noise is amplified there")
        measure.warn_saturated(lamp["saturated_px"])
        return
    if args[0] == "on" and state["response"] is None:
        raise ValueError("no response, run response build first")
    state["use_response"] = args[0] == "on"
    state["spectrum"] = None
    out.say(f"response: {args[0]}")


def cmd_reference(state, args):
    if state["dark"] is None:
        raise ValueError("no dark frame, run dark first")
    n = registry.to_frames(args[0]) if args else measure.CAPTURE_FRAMES
    if not registry.ready(state, "Remove the sample and press Enter: "):
        out.say("Cancelled.")
        return
    spectrum = measure.measure_direct(state, n)
    spectrum["channel"] = state["settings"]["channel"]
    state["reference"] = spectrum
    state["spectrum"] = None
    session.mark_taken(state, "reference")
    peak = np.max(spectrum["values"][spectrum["mask"]]) if spectrum["mask"].any() else np.nan
    out.say(f"Reference: peak {peak:g}")
    measure.warn_saturated(spectrum["saturated_px"])


def cmd_mode(state, args):
    if len(args) != 1 or args[0] not in ("direct", "transmission"):
        raise ValueError("usage: mode direct or mode transmission")
    if args[0] == "transmission" and state["reference"] is None:
        raise ValueError("no reference, run reference first")
    state["mode"] = args[0]
    state["spectrum"] = None
    out.say(f"mode: {args[0]}")


PANES = ("camera", "roi", "spectrum", "panel", "rail", "status", "normalize")


def cmd_view(state, args):
    view = state["view"]
    if not args:
        out.say(", ".join(f"{name} {'on' if view[name] else 'off'}" for name in PANES))
        out.say(f"camera {view['camera_view']} (crop or full), glow {view['glow']}")
        return
    if len(args) != 2:
        raise ValueError("usage: view NAME on|off, view camera crop|full or view glow on|low|off")
    name, value = args
    if name == "camera" and value in ("crop", "full"):
        view["camera_view"] = value
        view["camera"] = True
    elif name == "glow" and value in theme.GLOW_LEVELS:
        view["glow"] = value
    elif name in PANES and value in ("on", "off"):
        view[name] = value == "on"
    else:
        raise ValueError(f"view {name} {value} does not exist. Names: {', '.join(PANES)}, glow")
    out.say(f"view {name}: {value}")


def cmd_plot(state, args):
    spectrum = registry.need_spectrum(state)
    if live.HOST is not None:
        live.HOST.show_latest()
        out.say("The latest measurement is shown in the window.")
        return
    masked = calc.masked_values(spectrum)
    win = plot.open_plot()
    try:
        win.update(display.window_info(state))
        win.update(display.frame_info(state, win, spectrum, masked))
        display.draw_spectrum(state, win, spectrum, masked)
        out.say("Close the window (the cross) to get back to the prompt.")
        plot.show()
    finally:
        plot.close(win)


NUMBERS = ("current_mA", "voltage_V")
TEXTS = ("led", "sample", "lamp")


def cmd_note(state, args):
    if args == ["clear"]:
        state["note"] = None
    elif args:
        state["note"] = " ".join(args)
    out.say(f"note: {state['note'] or '(none)'}")


def cmd_series_start(state, args):
    if len(args) != 1 or not args[0].replace("-", "_").isalnum():
        raise ValueError("usage: series start NAME (letters, digits, _ and - only)")
    folder = Path(state["settings"]["output_dir"]) / args[0]
    state["series"] = {"name": args[0], "folder": folder.as_posix(), "file": (folder / "series.csv").as_posix()}
    state["annotations"] = {}
    state["spectrum"] = None
    out.say(f"series {args[0]}: {state['series']['file']}")


def cmd_series_note(state, args):
    if not args:
        raise ValueError("usage: series note KEY=VALUE")
    annotations = dict(state["annotations"])
    for word in args:
        key, _, value = word.partition("=")
        if key in NUMBERS and value:
            annotations[key] = float(value)
        elif key in TEXTS and value:
            annotations[key] = value
        else:
            raise ValueError(f"usage: series note KEY=VALUE, KEY is one of {', '.join(NUMBERS + TEXTS)}")
    state["annotations"] = annotations
    state["spectrum"] = None
    out.say("series note: " + " ".join(f"{k}={out.fmt(v) if isinstance(v, float) else v}" for k, v in annotations.items()))


def cmd_series_stop(state, args):
    if state["series"] is None:
        raise ValueError("no series is running. Run series start NAME")
    out.say(f"series {state['series']['name']} stopped")
    state["series"] = None
    state["annotations"] = {}


def cmd_series_plot(state, args):
    droop = "--droop" in args
    names = [word for word in args if word != "--droop"]
    target = None
    if names and names[-1].lower().endswith((".png", ".svg")):
        target = names.pop()
    if not names:
        raise ValueError("usage: series plot NAME... [--droop] [OUT.png]")
    curves = []
    for name in names:
        path = Path(state["settings"]["output_dir"]) / name / "series.csv"
        if not path.is_file():
            raise ValueError(f"{path.as_posix()} does not exist")
        xs, areas = series.curve(path)
        eff = series.droop(xs, areas)
        out.say(f"series {name}: {xs.size} point(s) from {path.as_posix()}")
        for x, area, e in zip(xs, areas, eff):
            text = f"  {out.fmt(x)} mA: relative output power {out.fmt(area)}"
            if droop:
                text += f", relative efficiency {out.fmt(e)}"
            out.say(text)
        curves.append((xs, eff if droop else areas, name))
    y_label = "relative efficiency (area/I, max 1)" if droop else "relative output power (area, arbitrary unit)"
    if target is not None:
        plot.save_figure(target, curves, "current (mA)", y_label)
        out.say(f"Saved: {target}")
    else:
        out.say("Close the window (the cross) to get back to the prompt.")
        plot.show_spectra(curves, "current (mA)", y_label)


UNITS = {"signal (counts)": "counts", "corrected signal (relative)": "relative", "transmission (ratio)": "ratio"}
NORM_LABEL = "normalized signal (relative, display only)"
RELATIVE = "Relative numbers from the camera; not watts, lumens or efficiency."


def cmd_load(state, args):
    if len(args) != 1:
        raise ValueError("usage: load FOLDER")
    spectrum = files.load_measurement(args[0])
    spectrum["loaded_from"] = spectrum["saved_in"] = spectrum["folder"]
    state["spectrum"], state["image"] = spectrum, None
    out.say(f"loaded: {spectrum['folder']} ({spectrum['x'].size} position(s))")


def normalized(values, name):
    top = np.nanmax(values) if np.any(np.isfinite(values)) else 0.0
    if top <= 0:
        raise ValueError(f"{name} cannot be normalized, the largest value is {top:g}")
    return values / top


def load_curves(folders):
    spectra = [files.load_measurement(folder) for folder in folders]
    return [(s, s["settings"].get("note") or Path(s["folder"]).name) for s in spectra]


def cmd_fwhm(state, args):
    n = int(args[0]) if args else 5
    if n < 1:
        raise ValueError("N must be at least 1")
    spectrum = registry.need_spectrum(state)
    values = calc.masked_values(spectrum)
    x_unit = "nm" if spectrum["x_label"] == "wavelength (nm)" else "pixel"
    area_unit = f"{UNITS[spectrum['y_label']]}·{x_unit}"
    found = peaks.find_peaks(values, spectrum["mask"])[:n]
    if not found:
        out.say("no peaks")
    for k, i in enumerate(found, start=1):
        width = peaks.fwhm(spectrum["x"], values, i)
        text = "unknown" if np.isnan(width) else f"{out.fmt(width)} {x_unit}"
        out.say(f"peak {k}: {out.fmt(peaks.centroid(spectrum['x'], values, i))} {x_unit}, "
                f"height {out.fmt(float(values[i]))}, FWHM {text}")
    out.say(f"area: {out.fmt(peaks.area(spectrum['x'], values, spectrum['mask']))} {area_unit} (relative, not watts)")
    out.say("FWHM of a narrow line (laser, Hg) is the resolution of the instrument, not the width of the source.")


def cmd_compare(state, args):
    norm = "--norm" in args
    folders = [word for word in args if word != "--norm"]
    if not folders:
        raise ValueError("usage: compare FOLDER... [--norm]")
    loaded = load_curves(folders)
    curves = []
    for spectrum, name in loaded:
        values = calc.masked_values(spectrum)
        curves.append((spectrum["x"], normalized(values, name) if norm else values, name))
    out.say("normalized to their maximum: the shape, not the level" if norm else RELATIVE)
    out.say("Close the window (the cross) to get back to the prompt.")
    plot.show_spectra(curves, loaded[0][0]["x_label"], NORM_LABEL if norm else loaded[0][0]["y_label"])


def cmd_figure(state, args):
    if not args or not args[0].lower().endswith((".png", ".svg")):
        raise ValueError("usage: figure OUT.png [FOLDER...] [--norm]")
    path = args[0]
    norm = "--norm" in args
    folders = [word for word in args[1:] if word != "--norm"]
    if folders:
        loaded = load_curves(folders)
    else:
        loaded = [(registry.need_spectrum(state), "latest measurement")]
    curves, lines = [], []
    for spectrum, name in loaded:
        values = calc.masked_values(spectrum)
        curves.append((spectrum["x"], normalized(values, name) if norm else values, name))
        settings = spectrum.get("settings") or dict(state["settings"], mode=state["mode"],
                                                    use_response=state["use_response"])
        lines.append(f"{name}: folder {spectrum.get('folder') or spectrum.get('saved_in', 'not saved')}, "
                     f"measured {settings.get('measured_at', 'unknown')}, channel {settings.get('channel')}, "
                     f"frames {settings.get('frames')}, mode {settings.get('mode')}, "
                     f"response {out.YES[bool(settings.get('use_response'))]}")
    x_label = loaded[0][0]["x_label"]
    y_label = NORM_LABEL if norm else loaded[0][0]["y_label"]
    plot.save_figure(path, curves, x_label, y_label)
    caption = Path(path).with_suffix(".txt")
    caption.write_text("\n".join([f"Figure {Path(path).name}: x {x_label}, y {y_label}", *lines, RELATIVE]) + "\n",
                       encoding="utf-8")
    out.say(f"Saved: {path} and {caption.as_posix()} (the conditions for the caption)")


def cmd_color(state, args):
    spectrum = registry.need_spectrum(state)
    if spectrum["y_label"] != "corrected signal (relative)" or spectrum["x_label"] == "pixel":
        raise ValueError("color needs a calibrated measurement with response on in mode direct")
    for line in color.report(spectrum["x"], spectrum["values"], spectrum["mask"]):
        out.say(line)


def cmd_mix(state, args):
    if len(args) == 6 and args[3] == "--target":
        target = (float(args[4]), float(args[5]))
        if not (target[0] > 0 and target[1] > 0 and sum(target) < 1):
            raise ValueError("X and Y must be positive and X + Y less than 1")
    elif len(args) == 5 and args[3] == "--cct":
        target = color.planck_xy(float(args[4]))
        out.say(f"target: the blackbody curve at {args[4]} K, x {target[0]:.4f}  y {target[1]:.4f}")
    else:
        raise ValueError("usage: mix FOLDER_R FOLDER_G FOLDER_B --target X Y or --cct K")
    primaries = []
    for folder in args[:3]:
        led = files.load_measurement(folder)
        if led["y_label"] != "corrected signal (relative)" or led["x_label"] == "pixel":
            raise ValueError(f"{folder}: not calibrated and response-corrected (save with response on in mode direct)")
        primaries.append(color.xyz(led["x"], led["values"], led["mask"]))
    primaries = np.array(primaries).T
    for k, name in enumerate("RGB"):
        x, y = color.xy(*primaries[:, k])
        out.say(f"{name}: x {x:.4f}  y {y:.4f}")
    w = color.weights(primaries, target)
    out.say(f"weights (relative, largest 1): R {w[0]:.3f}  G {w[1]:.3f}  B {w[2]:.3f}")
    if np.any(w < 0):
        out.warn("negative weight: the target lies outside the triangle, the three LEDs are not enough")
        return
    x, y = color.xy(*(primaries @ w))
    out.say(f"blend: x {x:.4f}  y {y:.4f}")
    out.say(color.cct_line(x, y))


def cmd_bandgap(state, args):
    spectrum = registry.need_spectrum(state)
    if spectrum["y_label"] != "transmission (ratio)" or spectrum["x_label"] == "pixel":
        raise ValueError("bandgap needs a calibrated measurement in mode transmission")
    bandgap.report(spectrum["x"], spectrum["values"], spectrum["mask"])


COMMANDS = [
    ["help", "list the commands", cmd_help],
    ["help limits", "what the numbers mean and do not mean", cmd_help_limits],
    ["quit", "quit the program", cmd_quit],
    ["show", "show the settings", cmd_show],
    ["pause", "TEXT: print the text and wait for Enter", cmd_pause],
    ["run", "FILE: run the commands in a command file, stops at the first error", cmd_run],
    ["source", "file PATH or camera N: where the image comes from", cmd_source],
    ["roi", "X Y W H in pixels, or full", cmd_roi],
    ["channel", "gray, sum, red, green or blue", cmd_channel],
    ["axis", "horizontal or vertical", cmd_axis],
    ["frames", "N: frames per measurement", cmd_frames],
    ["exposure", "N: camera exposure in driver units", cmd_exposure],
    ["gain", "N: camera gain in driver units", cmd_gain],
    ["auto", "on|off: camera auto exposure (off for series)", cmd_auto],
    ["step", "measure and print the peak", cmd_step],
    ["save", "[DIR] [--excel]: save the latest measurement (--excel: also a copy for Swedish Excel)", cmd_save],
    ["start", "[SECONDS]: live spectrum until Ctrl+C, stop or SECONDS", cmd_start],
    ["calibrate", "PATH [DEGREE]: fit the wavelength to a points file", cmd_calibrate],
    ["peaks", "[N] or LINEFILE: list the peaks, or suggest a points file from LINEFILE", cmd_peaks],
    ["dark", "[N]: measure a dark frame (light path blocked)", cmd_dark],
    ["response", "build KNOWNFILE [N] | on | off: detector sensitivity", cmd_response],
    ["reference", "[N]: measure the reference (no sample)", cmd_reference],
    ["mode", "direct or transmission", cmd_mode],
    ["view", "camera|roi|spectrum|normalize on|off", cmd_view],
    ["plot", "show the latest measurement in a window", cmd_plot],
    ["note", "[TEXT...]: a note saved with every measurement (note clear removes it)", cmd_note],
    ["series start", "NAME: start a series; save then writes a row in series.csv", cmd_series_start],
    ["series note", "KEY=VALUE...: current_mA, voltage_V, led, sample or lamp for the next measurement", cmd_series_note],
    ["series stop", "end the series", cmd_series_stop],
    ["series plot", "NAME... [--droop] [OUT.png]: output power against current, or droop", cmd_series_plot],
    ["load", "FOLDER: read a saved measurement", cmd_load],
    ["fwhm", "[N]: position, height and width (FWHM) of the N highest peaks, and the area", cmd_fwhm],
    ["compare", "FOLDER... [--norm]: several measurements in one figure (--norm: same height)", cmd_compare],
    ["figure", "OUT.png|OUT.svg [FOLDER...] [--norm]: figure for the report, with a caption file", cmd_figure],
    ["color", "x, y, color temperature and distance to warm and cool white", cmd_color],
    ["mix", "R G B --target X Y | --cct K: mix three saved LED measurements into a color", cmd_mix],
    ["bandgap", "bandgap in eV from the absorption edge of the latest measurement", cmd_bandgap],
]
