from pathlib import Path

import numpy as np

from spectrometer.core import out, session
from spectrometer.measurement import calc
from spectrometer.visual import plot


def window_info(state):
    kind, value = state["settings"]["source"]
    head = session.describe(state)
    if kind == "file":
        head = head.replace(f"file {value}", f"file {Path(value).name}", 1)
    ref = state["reference"]
    curve = None
    if ref is not None and units(state) == (ref["x_label"], "signal (counts)"):
        curve = ref["x"], calc.masked_values(ref)
    return {
        "name": f"spektro - {kind} {value} - {state['mode']}",
        "view": state["view"],
        "head": head,
        "ref": curve,
        "axis": state["settings"]["axis"],
    }


def units(state):
    x_label = "pixel" if state["coefficients"] is None else "wavelength (nm)"
    if state["mode"] == "transmission":
        return x_label, "transmission (ratio)"
    if state["use_response"]:
        return x_label, "corrected signal (relative)"
    return x_label, "signal (counts)"


def frame_info(state, win, spectrum, values, rates=None):
    x = spectrum["x"]
    full = spectrum.get("saturated_px", 0) > 0
    warnings = ["SATURATED - lower the exposure"] if full else []
    transmission = spectrum["y_label"] == "transmission (ratio)"
    if transmission:
        over = int(np.count_nonzero(values[np.isfinite(values)] > 1))
        if over:
            warnings.append(f"T > 1 at {over} {'position' if over == 1 else 'positions'}")
    text = "no valid position"
    if np.any(np.isfinite(values)):
        i = int(np.nanargmax(values))
        text = f"Peak {values[i]:.4g} at {spectrum['x_label']} {x[i]:.4g}"
    image = state["image"]
    roi = state["settings"]["roi"]
    if image is not None:
        roi = calc.roi_or_whole(roi, image)
    return {
        "title": f"{win.get('head', '')}\n{text}",
        "warn": " · ".join(warnings) or None,
        "guide": ([x[0], x[-1]], [1.0, 1.0]) if transmission else None,
        "foot": f"{session.chain(state)} · frames {state['settings']['frames']} · saturated {out.YES[full]}",
        "image": image,
        "roi": roi,
    }


def draw_spectrum(state, win, spectrum, values, live=None):
    y_label = spectrum["y_label"]
    finite = values[np.isfinite(values)]
    top = finite.max() if finite.size else 0.0
    if win["view"]["normalize"] and y_label != "transmission (ratio)" and top > 0:
        values, y_label = values / top, "normalized (relative)"
    if y_label == "signal (counts)":
        win["fixed_y"] = (0.0, 800.0 if state["settings"]["channel"] == "sum" else 270.0)
        level = 765.0 if state["settings"]["channel"] == "sum" else 255.0
    else:
        win["fixed_y"] = {"transmission (ratio)": (0.0, 1.2), "normalized (relative)": (0.0, 1.1)}.get(y_label)
        level = None
    win["px"] = spectrum.get("px")
    win["sat_level"] = level
    win["hot_band"] = None if level is None else (level * 222.0 / 255, level * 238.0 / 255)
    win["peak"] = win["peak_label"] = None
    if np.any(np.isfinite(values)):
        i = int(np.nanargmax(values))
        win["peak"] = ([spectrum["x"][i]], [values[i]])
        x_label = spectrum["x_label"]
        where = f"{spectrum['x'][i]:.1f} nm" if x_label == "wavelength (nm)" else f"{x_label} {spectrum['x'][i]:.4g}"
        win["peak_label"] = f"{where} · {values[i]:.1f} · {100 * values[i] / level:.1f} %" if level else \
            f"{where} · {values[i]:.4g}"
    if live is None:
        plot.draw(win, spectrum["x"], values, spectrum["x_label"], y_label)
        return None
    return plot.draw_live(win, spectrum["x"], values, spectrum["x_label"], y_label, live)


def dark_stale(state, camera=None):
    dark, then = state["dark"], state["dark_camera"]
    if dark is None:
        return None
    image = state["image"]
    if image is not None and image.shape != dark.shape:
        return f"{dark.shape[1]}×{dark.shape[0]} ≠ {image.shape[1]}×{image.shape[0]}"
    now = dict(camera or {})
    for name in ("exposure", "gain"):
        if now.get(name) is None:
            now[name] = state["controls"].get(name)
    changed = []
    if then is not None:
        for name in ("exposure", "gain"):
            if now.get(name) is not None and then[name] is not None and now[name] != then[name]:
                changed.append((name, now[name], then[name]))
    if not changed:
        return None
    return ", ".join(f"{out.fmt(old)} ≠ {out.fmt(value)}" if name == "exposure"
                     else f"{name} {out.fmt(old)} ≠ {out.fmt(value)}" for name, value, old in changed)


def chain_stages(state, stats):
    settings = state["settings"]
    kind, value = settings["source"]
    stages = [("✓ " + (f"camera {value}" if kind == "camera" else Path(str(value)).name), "done")]
    roi = settings["roi"]
    stages.append(("– roi full image", "off") if roi is None else
                  ("✓ roi " + " ".join(str(v) for v in roi), "done"))
    camera = stats.get("camera") or {}
    controls = []
    for name, short in (("exposure", "exp"), ("gain", "gain")):
        number = camera.get(name) if camera.get(name) is not None else state["controls"].get(name)
        if number is not None:
            controls.append(f"{short} {out.fmt(number)}")
    stages.append(("✓ " + " · ".join(controls), "done") if controls else ("– exp · gain –", "off"))
    stale = dark_stale(state, camera)
    if state["dark"] is None:
        stages.append(("○ dark", "todo"))
    elif stale is not None:
        stages.append((f"▲ dark {stale} · stale", "stale"))
    else:
        then = state["dark_camera"] or {}
        stages.append(("✓ dark" + (f" {out.fmt(then['exposure'])}" if then.get("exposure") is not None else ""),
                       "done"))
    if state["coefficients"] is None:
        stages.append(("○ cal", "todo"))
    else:
        stages.append((f"✓ cal {calibrated_range(state)}", "done"))
    if state["response"] is not None and state["use_response"]:
        stages.append(("✓ response on", "done"))
    else:
        stages.append(("– response off", "off"))
    if state["reference"] is None:
        stages.append(("– reference off", "off"))
    else:
        stages.append(("✓ reference" + (" · transmission" if state["mode"] == "transmission" else ""), "done"))
    spectrum = state["spectrum"]
    if spectrum is None:
        stages.append(("○ no measurement", "todo"))
    elif spectrum.get("saved_in"):
        stages.append(("✓ saved", "done"))
    else:
        stages.append(("○ unsaved", "todo"))
    if stats.get("live"):
        rate = stats.get("measured", 0.0)
        stages.append((f"● LIVE {rate:.1f}/s" if rate < 100 else f"● LIVE {rate:.0f}/s", "live"))
    else:
        stages.append(("○ idle", "still"))
    if stale is not None:
        hint = "dark"
    elif state["coefficients"] is None:
        hint = "calibrate"
    elif state["dark"] is None:
        hint = "dark"
    elif spectrum is None:
        hint = None if stats.get("live") else "start"
    elif not spectrum.get("saved_in"):
        hint = "save"
    else:
        hint = None
    return stages, hint


def calibrated_range(state):
    spectrum = state["spectrum"]
    if spectrum is not None and spectrum["x_label"] == "wavelength (nm)" and len(spectrum["x"]):
        low, high = float(np.min(spectrum["x"])), float(np.max(spectrum["x"]))
    else:
        first, last = state["pixel_range"]
        image = state["image"]
        if image is not None:
            across = image.shape[0] if state["settings"]["axis"] == "vertical" else image.shape[1]
            last = min(last, across - 1)
        low, high = sorted(calc.evaluate_wavelength(np.array([first, last], dtype=float), state["coefficients"]))
    return f"{low:.0f}–{high:.0f} nm"


def status_line(state, stats):
    _x_label, y_label = units(state)
    left = {"signal (counts)": "relative counts · not absolute power",
            "corrected signal (relative)": "corrected signal, relative · not absolute power",
            "transmission (ratio)": "transmission (ratio, sample/reference)"}[y_label]
    if state["view"]["normalize"] and y_label != "transmission (ratio)":
        left = "normalized (relative) · not absolute power"
    settings = state["settings"]
    sep = ("  │  ", "sep")
    right = []
    if stats.get("warn"):
        right += [(f"▲ {stats['warn']}", "warn"), sep]
    right += [(settings["channel"], "value"), (" · ", "sep"), (state["mode"], "value"), (" · ", "sep"),
              ("frames ", "label"), (str(settings["frames"]), "value")]
    if stats.get("live"):
        right += [sep, (f"{stats['measured'] * settings['frames']:.0f}", "value"), (" frames/s", "label"),
                  (" · ", "sep"), (f"{stats['drawn']:.0f}", "value"), (" draws/s", "label")]
        if stats.get("read_ms") is not None:
            right += [(" · ", "sep"), ("read ", "label"), (f"{stats['read_ms']:.1f} ms", "value"),
                      (" · ", "sep"), ("compute ", "label"), (f"{stats['compute_ms']:.1f} ms", "value")]
    spectrum = state["spectrum"]
    if spectrum is not None:
        saturated = spectrum.get("saturated_px", 0)
        right += [(" · ", "sep"), ("saturated px ", "label"), (str(saturated), "warn" if saturated else "value")]
    return left, right


def info_lines(state, stats):
    settings, spectrum = state["settings"], state["spectrum"]
    frames = settings["frames"]
    lines = ["state       " + ("LIVE" if stats["live"] else "idle")]
    if stats["live"]:
        lines += [f"measured/s  {stats['measured']:.0f}", f"frames/s    {stats['measured'] * frames:.0f}",
                  f"draws/s     {stats['drawn']:.0f}"]
        if stats.get("read_ms") is not None:
            lines += [f"read        {stats['read_ms']:.1f} ms", f"compute     {stats['compute_ms']:.1f} ms"]
    lines.append("")
    camera = spectrum["camera"] if spectrum is not None and spectrum.get("camera") else {}
    kind, value = settings["source"]
    lines.append(f"source      {'camera ' + str(value) if kind == 'camera' else Path(str(value)).name}")
    if camera.get("width"):
        lines.append(f"image       {camera['width']:.0f}×{camera['height']:.0f} {camera.get('fourcc') or ''}".rstrip())
        lines.append(f"camera fps  {camera['fps']:g}" if camera.get("fps") else "camera fps  unknown")
        for name in ("exposure", "gain"):
            if camera.get(name) is not None:
                lines.append(f"{name:<11} {camera[name]:g}")
    roi = settings["roi"]
    lines += ["", f"roi         {'full image' if roi is None else ' '.join(str(v) for v in roi)}",
              f"channel     {settings['channel']}", f"frames      {frames}", f"axis        {settings['axis']}",
              f"mode        {state['mode']}", ""]
    for name, what in (("dark", "dark"), ("calibration", "calibrate"), ("response", "response"),
                       ("reference", "reference")):
        present = state[session.TAKEN_KEYS[what]] is not None
        age = session.age_minutes(state, what)
        lines.append(f"{name:<11} {out.YES[present]}" + (f" ({age} min)" if age else ""))
    if state["response"] is not None:
        lines.append(f"response on {out.YES[state['use_response']]}")
    if spectrum is not None:
        values = calc.masked_values(spectrum)
        lines.append("")
        if np.any(np.isfinite(values)):
            i = int(np.nanargmax(values))
            lines.append(f"peak        {values[i]:.4g} at {spectrum['x'][i]:.4g}")
        lines.append(f"saturated px {spectrum.get('saturated_px', 0)}")
        lines.append(f"saved       {out.YES[bool(spectrum.get('saved_in'))]}")
    if state["series"] is not None:
        lines.append(f"series      {state['series']['name']}")
    return lines


def save_png(state, folder):
    spectrum = state["spectrum"]
    values = calc.masked_values(spectrum)
    title = f"{folder.name} · {session.describe(state)} · frames {state['settings']['frames']}"
    plot.save_png(folder / "spectrum.png", spectrum["x"], values, spectrum["x_label"], spectrum["y_label"], title)
