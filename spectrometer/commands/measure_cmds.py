"""step, save och start: mäta en gång, spara, och visa live. Sist kommandon som prövar själva mätningen."""

import time

import numpy as np

from spectrometer import files, measure, out, plot, quality, registry, source

LIVE_INTERVAL = 0.05  # sekunder per varv i live (mål 20 bilder/s); pausen är det som blir över


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
    quality.warn_changed(spectrum["camera"], state["dark_camera"], "mörkret", "dark")
    if state["reference"] is not None:
        quality.warn_changed(spectrum["camera"], state["reference"].get("camera"), "referensen", "reference")
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
    saved["camera"] = state["spectrum"].get("camera")  # drivrutinens reglage under mätningen; för en fil bara kind: file, resten None
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
    before = state["spectrum"]  # kurvan före live; measure lägger en ny i state varje varv
    try:
        src = source.open_source(kind, value)
        win = plot.open_plot()
        while True:
            if not plot.is_open(win):
                out.say("live stoppad")
                break
            started = time.perf_counter()
            spectrum = measure.measure(state, src)
            masked = np.where(spectrum["mask"], spectrum["values"], np.nan)
            plot.draw(win, spectrum["x"], masked, spectrum["x_label"], spectrum["y_label"])
            plot.pause(max(0.001, LIVE_INTERVAL - (time.perf_counter() - started)))
    except KeyboardInterrupt:
        out.say("live stoppad")
    except RuntimeError:
        if state["spectrum"] is not before:  # live hann mäta minst en gång
            out.say("Senaste kurvan finns kvar: save sparar den.")
        raise
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
    peaks = measure._with_source(state, None, lambda s: peak_series(state, s, n))
    mean = np.mean(peaks)
    if mean <= 0:
        raise ValueError("input.missing_data: toppvärdet är 0, inget ljus i ROI:n")
    third = n // 3
    variation = 100 * np.std(peaks, ddof=1) / mean
    drift = 100 * (np.mean(peaks[-third:]) - np.mean(peaks[:third])) / mean
    out.say(f"stabilitet: {n} bilder, variation {variation:.1f} %, drift {drift:+.1f} %")


def time_series(state, src, n):
    """Tiderna för n mätningar i rad ur en öppen källa, som två arrayer med sekunder: läs och räkna. state ändras inte."""
    copy = state.copy()
    reads, computes = [], []
    for _ in range(n):
        timing = {}
        measure.measure(copy, src, timing)
        reads.append(timing["read"])
        computes.append(timing["compute"])
    return np.array(reads), np.array(computes)


@registry.command("perf", "[N]: tidta N mätningar (20) utan fönster: median, 95:e percentil, bilder/s")
def cmd_perf(state, args):
    """Kommandot perf [N]: N mätningar med nuvarande källa, ROI, kanal och frames, utan fönster; skriver tiderna.

    läs: bilderna ur källan. räkna: mörker, ROI, kanal, medel, kalibrering, respons. Att öppna källan räknas inte.
    """
    if len(args) > 1:
        raise ValueError("input.invalid_argument: perf tar högst ett ord (N)")
    n = registry.to_int("N", args[0], 1) if args else 20
    reads, computes = measure._with_source(state, None, lambda s: time_series(state, s, n))
    for name, seconds in (("läs", reads), ("räkna", computes)):
        out.say(f"{name}: median {np.median(seconds) * 1000:.2f} ms, p95 {np.percentile(seconds, 95) * 1000:.2f} ms")
    frames = state["settings"]["frames"]
    rate = n * frames / (reads.sum() + computes.sum())
    out.say(f"{n} mätningar med {frames} {'bild' if frames == 1 else 'bilder'}: {rate:.1f} bilder/s utan fönster")
