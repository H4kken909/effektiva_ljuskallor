"""step, save och start: mäta en gång, spara, och visa live. Sist kommandon som prövar själva mätningen."""

import sys
import time

import numpy as np

from spectrometer import (
    calc,
    display,
    files,
    measure,
    meta,
    out,
    plot,
    quality,
    registry,
    session,
    source,
)
from spectrometer.analysis import series

LIVE_INTERVAL = 0.05  # sekunder per varv i live (mål 20 bilder/s); pausen är det som blir över


@registry.command("step", "mät och skriv toppen")
def cmd_step(state, args):
    """Kommandot step: mäter, skriver toppen och antalet bilder, varnar vid mättnad och transmission över 1,05."""
    registry.need(args, (), "step")
    spectrum = measure.measure(state)
    if not spectrum["mask"].any():
        state["spectrum"] = None  # save ska inte spara en mätning som step vägrade
        raise ValueError("input.missing_data: ingen giltig position i spektrumet "
                         "(alla under tröskeln eller utanför kalibreringen)")
    i = int(np.nanargmax(calc.masked_values(spectrum)))
    bilder_text = registry.plural(state["settings"]["frames"], "bild", "bilder")
    out.say(f"Topp {out.fmt(spectrum['values'][i])} vid {spectrum['x_label']} {out.fmt(spectrum['x'][i])} ({bilder_text})")
    quality.warn_saturated(spectrum["saturated_px"])
    if source.auto_on(spectrum["camera"]):  # 1.2.0: KRV-03
        out.warn("auto-exponering är på: kameran ändrar exponeringen själv mellan mätningarna. Kör auto off.")
    quality.warn_changed(spectrum["camera"], state["dark_camera"], "mörkret", "dark")
    session.warn_old_dark(state)  # PRO-12
    if state["reference"] is not None:
        quality.warn_changed(spectrum["camera"], state["reference"]["camera"], "referensen", "reference")
    if state["dark"] is not None and state["mode"] == "direct" and not state["use_response"]:
        # Negativt efter mörkret är rätt (brus), men starkt negativt betyder att mörkret inte passar. LOG-17.
        low = np.count_nonzero(spectrum["values"][spectrum["mask"]] < -5)
        if low:
            out.warn(
                f"{registry.plural(low, 'position', 'positioner')} under -5 counts efter mörkeravdrag. "
                "Mörkret passar inte (exponering, gain, temperatur)?"
            )
    if state["mode"] == "transmission":
        # Brus runt T = 1 ger T > 1 på ungefär halva positionerna; varna först över 1,05 (planens gräns). LOG-16.
        over = np.count_nonzero(spectrum["values"][spectrum["mask"]] > 1.05)
        if over:
            out.warn(
                f"transmission över 105 % på {registry.plural(over, 'position', 'positioner')} "
                f"(högst {spectrum['values'][i]:g} vid {spectrum['x_label']} {spectrum['x'][i]:g})"
            )


@registry.command("save", "[DIR] [--excel]: spara senaste mätningen (--excel: också spectrum_sv.csv för svensk Excel)",
                  "save [DIR] [--excel]")
def cmd_save(state, args):
    """Kommandot save [DIR]: sparar senaste mätningen i en ny mätmapp under DIR eller output_dir."""
    excel = "--excel" in args  # 1.2.2
    args = [word for word in args if word != "--excel"]
    registry.at_most_one(args, "save", "DIR")
    spectrum = state["spectrum"]
    if spectrum is None:
        raise ValueError("input.missing_data: Ingen mätning än. Kör step först.")
    if "loaded_from" in spectrum:
        raise ValueError(f"input.invalid_argument: mätningen kommer från load {spectrum['loaded_from']}, den är redan sparad")
    parent = args[0] if args else state["settings"]["output_dir"]
    if state["series"] is not None:  # 1.2.1
        if spectrum["saturated_px"]:
            raise ValueError("input.invalid_argument: mätningen är mättad och sparas inte i serien. "
                             "Sänk exposure eller strömmen")
        parent = args[0] if args else state["series"]["folder"]
    saved = state["settings"].copy()
    saved["saturated_px"] = spectrum["saturated_px"]  # ROI-pixlar som var 255, i den värsta bilden
    saved["camera"] = spectrum["camera"]  # drivrutinens reglage under mätningen; för en fil bara kind: file, resten None
    saved["pixel_range"] = [float(v) for v in state["pixel_range"]] if state["pixel_range"] is not None else None
    saved["image_size"] = [state["image"].shape[1], state["image"].shape[0]]  # bredd, höjd i pixlar
    saved["calibration_points_file"] = state["calibration_points_file"]
    saved["coefficients"] = state["coefficients"].tolist() if state["coefficients"] is not None else None
    saved["dark"] = state["dark"] is not None
    saved["use_response"] = state["use_response"]
    saved["mode"] = state["mode"]
    # Programversion, tid, git, bibliotek, profiler och settings_id, före coefficients. 1.0.32.
    saved = meta.with_metadata(state, saved)
    saved = meta.put_before(saved, "taken", session.taken_text(state))  # när profilerna togs. PRO-10
    if state["rigg"] is None and sys.stdout.isatty():
        out.warn("ingen rigg angiven (rigg rigg.json), uppställningens data saknas i settings.json")  # DOK-32
    saved = meta.put_before(saved, "rigg", state["rigg"])  # Krav 9, DOK-31
    saved = meta.put_before(saved, "controls", state["controls"])  # 1.2.0: exposure, gain och auto som du valde
    saved = meta.put_before(saved, "note", state["note"])  # 1.2.1
    saved = meta.put_before(saved, "annotations", state["annotations"])  # 1.2.1: ström, spänning, LED, prov
    saved = meta.put_before(saved, "series", None if state["series"] is None else state["series"]["name"])
    # Id sist, när rigg, reglage och serie finns med; note och annotations undantas av meta.NOT_IN_ID, taken är en tid.
    counted = {key: value for key, value in saved.items() if key not in ("settings_id", "taken")}
    saved["settings_id"] = meta.settings_id(counted)
    folder = files.save_measurement(parent, spectrum, state["image"], saved)
    spectrum["saved_in"] = folder.as_posix()  # quit frågar inte om en sparad mätning
    try:
        display.save_png(state, folder)
    except (ValueError, RuntimeError, OSError) as error:
        out.warn(f"spectrum.png kunde inte ritas ({error}). Mätningen är sparad ändå.")
    out.say(f"Sparad i {folder.as_posix()}")
    if state["series"] is not None:  # 1.2.1: en rad per mätning i serie.csv
        rows = series.add_row(state["series"]["file"], folder, saved, spectrum)
        out.say(f"serie {state['series']['name']}: rad {rows} i {state['series']['file']}")
    if excel:
        out.say(f"Excel: {files.save_excel(folder).as_posix()}")


@registry.command("start", "[SEKUNDER]: live med kameran, Ctrl+C stoppar (med SEKUNDER: efter så lång tid)",
                  "start [SEKUNDER]")
def cmd_start(state, args):
    """Kommandot start [SEKUNDER]: spektrumet live tills Ctrl+C, tills fönstret stängs eller efter SEKUNDER.

    Källan och fönstret stängs alltid. Fel: ValueError med input.invalid_argument om SEKUNDER inte är ett tal över 0.
    """
    registry.at_most_one(args, "start", "SEKUNDER")
    seconds = registry.to_float("SEKUNDER", args[0], 0) if args else None  # None: tills Ctrl+C. KOM-42
    out.say("Live. Tryck Ctrl+C eller stäng fönstret för att stoppa.")
    kind, value = state["settings"]["source"]
    src = None
    win = None
    before = state["spectrum"]  # kurvan före live; measure lägger en ny i state varje varv
    try:
        src = source.open_source(kind, value)
        measure.apply_controls(state, src)  # 1.2.0
        win = plot.open_plot()
        win.update(display.window_info(state))
        begun = time.perf_counter()
        while True:
            if not plot.is_open(win):
                out.say("live stoppad")
                break
            if seconds is not None and time.perf_counter() - begun >= seconds:
                out.say("live stoppad")
                break
            started = time.perf_counter()
            spectrum = measure.measure(state, src)
            masked = calc.masked_values(spectrum)
            if not _live_frame(state, win, spectrum, masked):
                out.say("live stoppad")
                break
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
    registry.at_most_one(args, "stability", "N")
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
    registry.at_most_one(args, "perf", "N")
    n = registry.to_int("N", args[0], 1) if args else 20
    reads, computes = measure._with_source(state, None, lambda s: time_series(state, s, n))
    for name, seconds in (("läs", reads), ("räkna", computes)):
        out.say(f"{name}: median {np.median(seconds) * 1000:.2f} ms, p95 {np.percentile(seconds, 95) * 1000:.2f} ms")
    frames = state["settings"]["frames"]
    rate = n * frames / (reads.sum() + computes.sum())
    out.say(f"{n} mätningar med {registry.plural(frames, 'bild', 'bilder')}: {rate:.1f} bilder/s utan fönster")
    display.remember(state, "performance", {"read_ms": reads * 1000, "compute_ms": computes * 1000, "rate": rate})


def _live_frame(state, win, spectrum, masked):
    """Ett varv i live efter mätningen: info i win, kurvan, live-raden och tangenterna. Ger False när live ska sluta.

    Tangenter (fönstret i fokus): q eller Ctrl+C stoppar, s sparar som save, p pausar (ingen mätning under paus,
    fönstret lever och s sparar den stillastående kurvan), f c y n h ändrar bara visningen (display.view_key).
    """
    win.update(display.frame_info(state, win, spectrum, masked))
    display.draw_spectrum(state, win, spectrum, masked)
    out.live_line(win["status"])
    paused = False
    while True:
        keys = win.get("keys") or []
        while keys:
            key = keys.pop(0)
            if key in ("q", "ctrl+c"):
                return False
            if key == "p":
                paused = not paused
                win["paused"] = paused
            elif key == "s":
                cmd_save(state, [])
            else:
                display.view_key(win, key, spectrum, masked)
            display.draw_spectrum(state, win, spectrum, masked)
        if not paused:
            return True
        plot.pause(0.05)
        if not plot.is_open(win):
            return False
