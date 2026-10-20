"""step, save och start: mäta en gång, spara, och visa live. Sist kommandon som prövar själva mätningen."""

import numpy as np

from spectrometer import files, measure, out, plot, quality, registry, source


@registry.command("step", "mät och skriv toppen")
def cmd_step(state, args):
    """Kommandot step: mäter, skriver toppen och antalet bilder, varnar vid mättnad och transmission över 1."""
    registry.need(args, (), "step")
    spectrum = measure.measure(state)
    i = int(np.nanargmax(np.where(spectrum["mask"], spectrum["values"], np.nan)))
    frames = state["settings"]["frames"]
    word = "bild" if frames == 1 else "bilder"
    out.say(f"Topp {spectrum['values'][i]:g} vid {spectrum['x_label']} {spectrum['x'][i]:g} ({frames} {word})")
    quality.warn_saturated(spectrum["saturated_px"])
    if state["mode"] == "transmission":
        over = np.count_nonzero(spectrum["values"][spectrum["mask"]] > 1)
        if over:
            unit = "position" if over == 1 else "positioner"
            out.warn(f"transmission över 100 % på {over} {unit}")


@registry.command("save", "[DIR]: spara senaste mätningen")
def cmd_save(state, args):
    """Kommandot save [DIR]: sparar senaste mätningen i en ny mätmapp under DIR eller output_dir."""
    if len(args) > 1:
        raise ValueError("input.invalid_argument: save tar högst ett ord (DIR)")
    if state["spectrum"] is None:
        raise ValueError("input.missing_data: Ingen mätning än. Kör step först.")
    parent = args[0] if args else state["settings"]["output_dir"]
    saved = state["settings"].copy()
    saved["saturated_px"] = state["spectrum"].get("saturated_px")  # ROI-pixlar som var 255, i den värsta bilden
    saved["coefficients"] = state["coefficients"].tolist() if state["coefficients"] is not None else None
    saved["dark"] = state["dark"] is not None
    saved["use_response"] = state["use_response"]
    saved["mode"] = state["mode"]
    folder = files.save_measurement(parent, state["spectrum"], state["image"], saved)
    out.say(f"Sparad i {folder.as_posix()}")


@registry.command("start", "live med kameran, Ctrl+C stoppar")
def cmd_start(state, args):
    """Kommandot start: spektrumet live tills Ctrl+C eller tills fönstret stängs; källan och fönstret stängs alltid."""
    registry.need(args, (), "start")
    out.say("Live. Tryck Ctrl+C eller stäng fönstret för att stoppa.")
    kind, value = state["settings"]["source"]
    src = None
    win = None
    try:
        src = source.open_source(kind, value)
        win = plot.open_plot()
        while True:
            if not plot.is_open(win):
                out.say("live stoppad")
                break
            spectrum = measure.measure(state, src)
            masked = np.where(spectrum["mask"], spectrum["values"], np.nan)
            plot.draw(win, spectrum["x"], masked, spectrum["x_label"], spectrum["y_label"])
            plot.pause(0.05)
    except KeyboardInterrupt:
        out.say("live stoppad")
    finally:
        if src is not None:
            source.close_source(src)
        if win is not None:
            plot.close(win)



def peak_series(state, src, n):
    """Toppvärdet i n mätningar i rad, en bild var, ur en öppen källa. state ändras inte (en kopia mäter)."""
    single = state.copy()
    single["settings"] = state["settings"].copy()
    single["settings"]["frames"] = 1
    peaks = []
    for _ in range(n):
        spectrum = measure.measure(single, src)
        if not spectrum["mask"].any():
            raise ValueError("input.missing_data: ingen giltig position i spektrumet")
        peaks.append(np.max(spectrum["values"][spectrum["mask"]]))
    return np.array(peaks)


@registry.command("stability", "[N]: mät toppvärdet N gånger (30) och skriv variation och drift")
def cmd_stability(state, args):
    """Kommandot stability [N]: N bilder i rad med samma källa; skriver hur toppvärdet varierar och driver.

    variation: standardavvikelsen delad med medlet, i %. drift: medlet av sista tredjedelen minus medlet av första,
    delat med medlet, i %. Visar lampans uppvärmning, autoexponering som jagar och flimmer. Talen är relativa.
    """
    if len(args) > 1:
        raise ValueError("input.invalid_argument: stability tar högst ett ord (N)")
    n = registry.to_int("N", args[0], 3) if args else 30
    kind, value = state["settings"]["source"]
    src = source.open_source(kind, value)
    try:
        peaks = peak_series(state, src, n)
    finally:
        source.close_source(src)
    mean = np.mean(peaks)
    if mean <= 0:
        raise ValueError("input.missing_data: toppvärdet är 0, inget ljus i ROI:n")
    third = n // 3
    variation = 100 * np.std(peaks, ddof=1) / mean
    drift = 100 * (np.mean(peaks[-third:]) - np.mean(peaks[:third])) / mean
    out.say(f"stabilitet: {n} bilder, variation {variation:.1f} %, drift {drift:+.1f} %")