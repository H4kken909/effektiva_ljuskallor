"""Mätkedjan: bilder ur källan till ett spektrum, med mörker, kalibrering, respons och transmission.

measure() gör samma sak som main.measure i v1.0.0, delad i steg som går att testa ett och ett.
"""

import time

import numpy as np

from spectrometer import calc, out, quality, source

CAPTURE_FRAMES = 16  # bilder i dark och reference: medlet av flera bilder har mindre brus än en enda


def frame_spectrum(state, image):
    """Ett spektrum ur en bild: mörkret av, ROI, kanal och medel över raderna. Ger (values, roi)."""
    cfg = state["settings"]
    corrected = image
    if state["dark"] is not None:
        corrected = calc.subtract_dark(image.astype(np.float64), state["dark"])
    roi = cfg["roi"] if cfg["roi"] is not None else (0, 0, image.shape[1], image.shape[0])
    table = calc.prepare(corrected, roi, cfg["axis"], cfg["channel"])
    if state["rows"] == "median":
        values = calc.extract_median(table)  # ROI-14
    else:
        values = calc.extract_spectrum(table)
    if state["background"] is not None:
        # Bakgrunden bredvid bandet (ströljus i kameran) dras av efter mörkret. ROI-21.
        values = values - calc.side_background(corrected, roi, state["background"], cfg["channel"], cfg["axis"])
    return values, roi


def pixel_axis(roi, axis):
    """Pixlarna längs spektrumet, räknade i hela bilden, som float64."""
    first, count = (roi[0], roi[2]) if axis == "horizontal" else (roi[1], roi[3])
    return np.arange(first, first + count).astype("float64")


def calibrate_axis(state, x, values, mask):
    """Pixlar till nm om kalibrering finns, masken bara inom det giltiga intervallet, x stigande.

    Returnerar: (x, values, mask, x_label). x_label "pixel" styr CSV-rubriken x_px i files.py; ändra den inte.
    """
    x_label = "pixel"
    if state["coefficients"] is not None:
        low, high = state["pixel_range"]
        mask = mask & (x >= low) & (x <= high)
        x = calc.evaluate_wavelength(x, state["coefficients"])
        if not (np.all(np.diff(x) > 0) or np.all(np.diff(x) < 0)):
            raise ValueError(
                "input.invalid_argument: x-axeln är inte monoton i ROI:n. "
                "Minska ROI:n till det giltiga intervallet eller prova grad 1"
            )
        x_label = "våglängd (nm)"
    if x[0] > x[-1]:
        x, values, mask = x[::-1], values[::-1], mask[::-1]
    return x, values, mask, x_label


def apply_response(state, spectrum):
    """Delar med responsen i mode direct när den är på. Ändrar spektrumet på plats."""
    if not (state["use_response"] and state["mode"] == "direct"):
        return
    if state["coefficients"] is None:
        raise ValueError("input.missing_data: ingen kalibrering, kör calibrate först")
    response = state["response"]
    at_x = np.interp(spectrum["x"], response["x"], response["values"], left=np.nan, right=np.nan)
    mask = spectrum["mask"] & np.isfinite(at_x)
    spectrum["values"], spectrum["mask"] = calc.apply_response(
        spectrum["values"], at_x, mask, state["settings"]["min_response"]
    )
    spectrum["y_label"] = "korrigerad signal (relativ)"


def apply_transmission(state, spectrum):
    """Delar provet med referensen i mode transmission. Ändrar spektrumet på plats."""
    if state["mode"] != "transmission":
        return
    reference = state["reference"]
    if reference is None:
        raise ValueError("input.missing_data: ingen referens, kör reference först")
    if not np.array_equal(spectrum["x"], reference["x"]):
        raise ValueError(
            "input.invalid_argument: x-axeln skiljer sig från referensens: "
            "ROI eller kalibrering ändrades, kör reference igen"
        )
    channel = state["settings"]["channel"]
    if channel != reference["channel"]:
        raise ValueError(
            f"input.invalid_argument: kanalen {channel} skiljer sig från referensens "
            f"{reference['channel']}, kör reference igen"
        )
    spectrum["values"], spectrum["mask"] = calc.transmission_ratio(
        spectrum["values"], reference["values"], spectrum["mask"] & reference["mask"],
        state["settings"]["min_reference"],
    )
    spectrum["y_label"] = "transmission (kvot)"


def measure(state, src=None, timing=None):
    """Mäter ett spektrum med inställningarna och lägger det och råbilden i state.

    Ordning: frames bilder (mörker, ROI, kanal, medel per bild), medel över bilderna, nm, respons, transmission.
    Parametrar: state: programmets state; src: en redan öppen källa som lånas (start), eller None för att öppna och
    stänga källan här; timing: en ordbok som får sekunderna för read (bilderna ur källan) och compute (resten), eller None.
    Returnerar: spektrumet, en ordbok med x, values, mask, x_label, y_label, saturated_px, saturated, stddev och camera.
    Fel: ValueError med input.invalid_argument eller input.missing_data, RuntimeError med camera.open_failed eller
    camera.read_failed.
    """
    n = state["settings"]["frames"]
    started = time.perf_counter()
    images, camera = _with_source(state, src, lambda s: (_read_frames(s, n, src is None), source.describe(s)))
    read_done = time.perf_counter()
    spectra = []
    saturated_px, saturated = 0, False  # flest mättade ROI-pixlar i en bild, och var längs spektrumet (alla bilder)
    for image in images:
        values, roi = frame_spectrum(state, image)
        spectra.append(values)
        part = quality.crop(image, roi)
        saturated_px = max(saturated_px, quality.saturated_count(part, state["settings"]["channel"]))
        saturated = saturated | quality.saturated_positions(part, state["settings"]["axis"], state["settings"]["channel"])
    mean, stddev = calc.average_spectra(np.stack(spectra))
    x = pixel_axis(roi, state["settings"]["axis"])
    saturated = calibrate_axis(state, x, saturated, np.isfinite(mean))[1]  # samma ordning som values: vänds med x
    stddev = calibrate_axis(state, x, stddev, np.isfinite(mean))[1]  # spridningen mellan bilderna, NaN för en bild
    px = calibrate_axis(state, x, x, np.isfinite(mean))[1]  # 1.2.2: pixeln för varje position, också i nm-läge
    x, values, mask, x_label = calibrate_axis(state, x, mean, np.isfinite(mean))
    spectrum = {"x": x, "values": values, "mask": mask, "x_label": x_label, "y_label": "signal (counts)"}
    spectrum["saturated_px"], spectrum["saturated"] = saturated_px, saturated
    spectrum["stddev"] = stddev  # slumpbrus mellan bilderna i counts (stickprov, ddof=1); ingen osäkerhet för instrumentet
    spectrum["px"] = px
    spectrum["raw"] = np.where(mask, values, np.nan)  # 1.2.2: före respons och transmission, i counts
    spectrum["camera"] = camera  # kamerans reglage under mätningen (source.describe)
    apply_response(state, spectrum)
    apply_transmission(state, spectrum)
    state["image"] = image
    state["spectrum"] = spectrum
    if timing is not None:
        timing["read"] = read_done - started
        timing["compute"] = time.perf_counter() - read_done
    return spectrum


def measure_direct(state, n):
    """Mäter med en kopia av state i mode direct, utan respons och med n bilder (lampa och referens)."""
    direct = state.copy()
    direct["settings"] = state["settings"].copy()
    direct["mode"] = "direct"
    direct["use_response"] = False
    direct["settings"]["frames"] = n
    return measure(direct)


def _with_source(state, src, funktion):
    """Kör funktion(src) med en öppen källa och ger det funktion ger.

    Parametrar: state: programmets state (källan står i settings); src: en öppen källa som lånas (start), eller None
    för att öppna källan här och alltid stänga den efteråt, också vid fel och Ctrl+C; funktion: tar den öppna källan.
    Exempel: images = _with_source(state, None, lambda s: source.read_frames(s, 16))
    """
    opened_here = src is None
    if opened_here:
        kind, value = state["settings"]["source"]
        if kind == "camera":
            out.say("Öppnar kameran ...")  # kan ta en sekund, och uppvärmningen läses bort
        src = source.open_source(kind, value)
    try:
        if opened_here:
            apply_controls(state, src)  # 1.2.0: exposure, gain och auto varje gång kameran öppnas
        return funktion(src)
    finally:
        if opened_here:
            source.close_source(src)


SLOW_SECONDS = 30  # beräknad insamling längre än så: measure skriver hur lång tid den tar. LOG-19


def _read_frames(src, n, show):
    """n bilder ur en öppen källa, som en lista. UT-17 och LOG-19.

    show (measure öppnade källan själv, alltså inte live): vid n över 4 en förloppsrad (bara i terminal, out.progress),
    och efter första bilden en rad med tiden för alla, om den blir längre än SLOW_SECONDS (då även i en kommandofil).
    """
    started = time.perf_counter()
    images = [source.read_frame(src)]
    estimate = n * (time.perf_counter() - started)
    if show and estimate > SLOW_SECONDS:
        out.say(f"Mäter {n} bilder, ca {max(1, round(estimate / 60))} min. Ctrl+C avbryter.")
    rest = range(n - 1)
    steps = out.progress(rest, "mäter") if show and n > 4 else rest
    for _ in steps:
        images.append(source.read_frame(src))
    return images


def apply_controls(state, src):
    """Sätter exposure, gain och auto som du valt (state["controls"]; None hoppas över) i en nyöppnad kamera. 1.2.0.

    auto först: på många kameror går exponeringen bara att sätta när auto är av. Varnar för det drivrutinen inte tar emot.
    """
    for name in ("auto", "exposure", "gain"):
        value = state["controls"][name]
        if value is not None and not source.set_control(src, name, value):
            out.warn(f"kameran tog inte emot {name}; info visar vad drivrutinen har")
