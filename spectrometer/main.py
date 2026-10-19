"""Håller ihop programmet: startas med python -m spectrometer.main och styrs med kommandon vid prompten spektro>."""
import argparse
import shlex
import sys

import matplotlib.pyplot as plt
import numpy as np

from spectrometer import calc, files, plot, source

DEFAULTS = {
    CAPTURE_FRAMES = 16  # bilder i dark och reference: medlet av flera bilder har mindre brus än en enda
    "source": ("camera", 0), # ("file", sökväg eller "camera", N)
    "roi": None, # None är hela bilden, annars (x, y, bredd, höjd) i pixlar
    "axis": "horizontal", # riktningen spektrumet läses längs
    "channel": "gray", # färgkanal: gray, sum, red, green eller blue
    "output_dir": "data", # föräldramappen för mätmapparna
    "frames": 1, # "bilder per mätning"
    "min_response": 0.01, # minsta respons, utan enhet
    "min_reference": 1.0, # minsta referens i counts
    "response": (cmd_response, "build KNOWNFILE | on | off"),

}

AXES = ("horizontal", "vertical")

def new_state(settings):
    """Ger en ny state-ordbok med en kopia av inställningarna.

    Parametrar: settings: inställningarna, till exempel DEFAULTS (ändras inte).
    Returnerar: state, en ordbok med nycklarna nedan.
    Fel: inga.
    """
    return {
        "settings": settings.copy(),  # inställningarna, skrivs till settings.json
        "image": None,  # senaste råbilden, (H, W, 3) uint8 i counts, None tills step
        "spectrum": None,  # senaste mätningen (ordbok från measure), None tills step
        "coefficients": None,  # kalibreringens koefficienter, float64, a0 först (calibrate)
        "pixel_range": None,  # kalibreringens giltiga intervall (låg, hög) i pixlar (calibrate)
        "dark": None,  # mörkret, (H, W, 3) float64 i counts (dark)
        "response": None,  # responsen: {"x": nm, "values": relativ} (response build)
        "use_response": False,  # True när responsen ska användas (response on och off)
        "reference": None,  # referensspektrumet med kanal, values i counts (reference)
        "mode": "direct",  # "direct" eller "transmission" (mode)
        "dark": (cmd_dark, "[N]: mät mörker med blockerad ljusväg"),
    }


def measure(state, src=None):
    """Mäter ett spektrum med inställningarna och lägger det och råbilden i state.

    Ordning: läs frames bilder, dra av mörkret, ROI, kanal och medel, nm, respons, transmission.

    Parametrar: state: programmets state; src: en redan öppen källa som lånas (start), eller None för att öppna och
    stänga källan här.
    Returnerar: spektrumet, en ordbok med x (P,) float64 i pixlar eller nm, values (P,) float64, mask (P,) bool,
    x_label och y_label.
    Fel: ValueError med input.invalid_argument eller input.missing_data, RuntimeError med camera.open_failed eller
    camera.read_failed.
    """
    cfg = state["settings"]
    kind, value = cfg["source"]
    frames = cfg["frames"]
    spectra = []
    opened_here = src is None
    if opened_here:
        src = source.open_source(kind, value)
    try:
        for i in range(frames):
            image = source.read_frame(src)
            if state["dark"] is not None:
                corrected = image.astype(np.float64)
                corrected = calc.subtract_dark(corrected, state["dark"])
            else:
                corrected = image
            roi = cfg["roi"]
            if roi is None:
                roi = (0, 0, image.shape[1], image.shape[0])
            table = calc.prepare(corrected, roi, cfg["axis"], cfg["channel"])
            values = calc.extract_spectrum(table)
            spectra.append(values)
    finally:
        if opened_here:
            source.close_source(src)
    stack = np.stack(spectra)
    mean, _stddev = calc.average_spectra(stack)
    if cfg["axis"] == "horizontal":
        first, count = roi[0], roi[2]
    else:
        first, count = roi[1], roi[3]
    x = np.arange(first, first + count).astype("float64")
    values = mean
    mask = np.isfinite(values)
    x_label = "pixel"
    y_label = "signal (counts)"
    if state["coefficients"] is not None:
        low, high = state["pixel_range"]
        inside = (x >= low) & (x <= high)
        mask = mask & inside
        x = calc.evaluate_wavelength(x, state["coefficients"])
        x_label = "våglängd (nm)"
    if x[0] > x[-1]:
        x = x[::-1]
        values = values[::-1]
        mask = mask[::-1]
    if state["use_response"] and state["mode"] == "direct":
        if state["coefficients"] is None:
            raise ValueError("input.missing_data: ingen kalibrering, kör calibrate först")
        response_at_x = np.interp(x, state["response"]["x"], state["response"]["values"], left=np.nan, right=np.nan)
        mask = mask & np.isfinite(response_at_x)
        values, mask = calc.apply_response(values, response_at_x, mask, cfg["min_response"])
        y_label = "korrigerad signal (relativ)"
    spectrum = {"x": x, "values": values, "mask": mask, "x_label": x_label, "y_label": y_label}
    if state["mode"] == "transmission":
        if state["reference"] is None:
            raise ValueError("input.missing_data: ingen referens, kör reference först")
        if not np.array_equal(spectrum["x"], state["reference"]["x"]):
            raise ValueError(
                "input.invalid_argument: x-axeln skiljer sig från referensens: "
                "ROI eller kalibrering ändrades, kör reference igen"
            )
        if cfg["channel"] != state["reference"]["channel"]:
            raise ValueError(
                f"input.invalid_argument: kanalen {cfg['channel']} skiljer sig från referensens "
                f"{state['reference']['channel']}, kör reference igen"
            )
        spectrum["values"], spectrum["mask"] = calc.transmission_ratio(
            spectrum["values"], state["reference"]["values"], spectrum["mask"] & state["reference"]["mask"],
            state["settings"]["min_reference"],
        )
        spectrum["y_label"] = "transmission (kvot)"
    state["image"] = image
    state["spectrum"] = spectrum
    return spectrum


def _measure_direct(state, n):
    """Mäter med en kopia av state i mode direct, utan respons och med n bilder (lampa och referens).

    Parametrar: state: programmets state (ändras inte); n: antalet bilder, minst 1.
    Returnerar: spektrumet från measure, i counts.
    Fel: samma som measure.
    """
    direct_state = state.copy()
    direct_state["settings"] = state["settings"].copy()
    direct_state["mode"] = "direct"
    direct_state["use_response"] = False
    direct_state["settings"]["frames"] = n
    return measure(direct_state)

def _to_int(name, text, smallest):
    try:
        number = int(text)
    except ValueError as error:
        raise ValueError(f"input.invalid_argument: {name} ska vara ett heltal, fick {text}") from error
    if number < smallest:
        raise ValueError(f"input.invalid_argument: {name} ska vara minst {smallest}")
    return number

def _need(args, names, command):
    if len(args) < len(names):
        missing = names[len(args)]
        raise ValueError(f"input.invalid_argument: {command}: {missing} saknas")
    elif len(args) > len(names):
        raise ValueError(f"input.invalid_argument: {command}: för många ord, väntade {len(names)}")


def _set(state, key, value) -> None:
    """Lägger en inställning i state och glömmer den gamla mätningen (roi och channel glömmer också responsen).

    Parametrar: state: programmets state; key: nyckeln i settings (str); value: det nya värdet.
    Returnerar: None
    Fel: inga.
    """
    state["settings"][key] = value
    state["spectrum"] = None
    if key in ("roi", "channel") and state["response"] is not None:
        state["response"] = None
        state["use_response"] = False
        print("Responsen glömd. Kör response build igen.")



def cmd_help(state, args):
    """Kommandot help: skriver en rad per kommando ur COMMANDS.

    Parametrar: state: programmets state; args: orden efter kommandot, inga.
    Returnerar: None
    Fel: ValueError med input.invalid_argument vid ord efter help.
    """
    _need(args, (), "help")
    for name, entry in COMMANDS.items():
        _function, help_text = entry
        print(name, help_text)


def cmd_quit(state, args):
    """Kommandot quit: skriver Avslutar. och ber main att avsluta.

    Parametrar: state: programmets state; args: orden efter kommandot, inga.
    Returnerar: True
    Fel: ValueError med input.invalid_argument vid ord efter quit.
    """
    _need(args, (), "quit")
    print("Avslutar.")
    return True


def cmd_show(state, args):
    """Kommandot show: skriver inställningarna, kalibrering, mörker, respons, referens, mode och om en mätning finns.

    Parametrar: state: programmets state; args: orden efter kommandot, inga.
    Returnerar: None
    Fel: ValueError med input.invalid_argument vid ord efter show.
    """
    _need(args, (), "show")
    for key, value in state["settings"].items():
        print(f"{key}: {value}")
    calibration = "ja" if state["coefficients"] is not None else "nej"
    dark = "ja" if state["dark"] is not None else "nej"
    response = "ja" if state["response"] is not None else "nej"
    reference = "ja" if state["reference"] is not None else "nej"
    use = "on" if state["use_response"] else "off"
    print(f"kalibrering: {calibration}")
    print(f"mörker: {dark}")
    print(f"respons: {response}, {use}")
    print(f"referens: {reference}")
    print(f"mode: {state['mode']}")
    if state["spectrum"] is not None:
        print("Mätning: ja")
    else:
        print("Mätning: nej")



def cmd_source(state, args):
    """Kommandot source file PATH eller source camera N: byter källa och glömmer den gamla bilden.

    Parametrar: state: programmets state; args: ["file", PATH] eller ["camera", N].
    Returnerar: None
    Fel: ValueError med input.invalid_argument om ord saknas, sorten är okänd eller N inte är ett heltal minst 0.
    """
    if not args:
        raise ValueError("input.invalid_argument: source: kind saknas")
    if args[0] == "file":
        _need(args, ("kind", "path"), "source")
        _set(state, "source", ("file", args[1]))
    elif args[0] == "camera":
        _need(args, ("kind", "index"), "source")
        index = _to_int("index", args[1], 0)
        _set(state, "source", ("camera", index))
    else:
        raise ValueError(f"input.invalid_argument: okänd källa {args[0]}, välj file eller camera")
    state["image"] = None
    print(f"source: {state['settings']['source']}")


def cmd_roi(state, args):
    """Kommandot roi X Y W H eller roi full: sätter ROI:n i pixlar efter att ha kontrollerat den.

    Parametrar: state: programmets state; args: ["full"] eller fyra heltal x, y, width och height.
    Returnerar: None
    Fel: ValueError med input.invalid_argument om ord saknas, inte är heltal, är för små eller ROI:n inte ryms
    i den senaste bilden. Den gamla ROI:n står då kvar.
    """
    if args == ["full"]:
        _set(state, "roi", None)
        print("roi: None (hela bilden)")
        return
    _need(args, ("x", "y", "width", "height"), "roi")
    x = _to_int("x", args[0], 0)
    y = _to_int("y", args[1], 0)
    width = _to_int("width", args[2], 1)
    height = _to_int("height", args[3], 1)
    new_roi = (x, y, width, height)
    if state["image"] is not None:
        calc.prepare(state["image"], new_roi, state["settings"]["axis"], state["settings"]["channel"])
    else:
        print("ROI:n kontrolleras vid nästa mätning.")
    _set(state, "roi", new_roi)
    print(f"roi: {new_roi}")


def cmd_channel(state, args):
    """Kommandot channel NAMN: väljer färgkanal ur calc.CHANNELS.

    Parametrar: state: programmets state; args: ett namn.
    Returnerar: None
    Fel: ValueError med input.invalid_argument om namnet saknas eller är okänt.
    """
    _need(args, ("name",), "channel")
    if args[0] not in calc.CHANNELS:
        allowed = ", ".join(calc.CHANNELS)
        raise ValueError(f"input.invalid_argument: okänd kanal {args[0]}, välj {allowed}")
    _set(state, "channel", args[0])
    print(f"channel: {args[0]}")


def cmd_axis(state, args):
    """Kommandot axis RIKTNING: väljer riktning ur AXES.

    Parametrar: state: programmets state; args: ett namn.
    Returnerar: None
    Fel: ValueError med input.invalid_argument om namnet saknas eller är okänt.
    """
    _need(args, ("name",), "axis")
    if args[0] not in AXES:
        allowed = ", ".join(AXES)
        raise ValueError(f"input.invalid_argument: okänd riktning {args[0]}, välj {allowed}")
    _set(state, "axis", args[0])
    print(f"axis: {args[0]}")


def cmd_frames(state, args):
    """Kommandot frames N: antalet bilder per mätning.

    Parametrar: state: programmets state; args: ett heltal N, minst 1.
    Returnerar: None
    Fel: ValueError med input.invalid_argument om N saknas, inte är ett heltal eller är mindre än 1.
    """
    _need(args, ("N",), "frames")
    n = _to_int("N", args[0], 1)
    _set(state, "frames", n)
    print(f"frames: {n}")


def cmd_step(state, args):
    """Kommandot step: mäter, skriver toppen och antalet bilder, och varnar vid mättnad och transmission över 1.

    Parametrar: state: programmets state; args: orden efter kommandot, inga.
    Returnerar: None
    Fel: samma som measure, och ValueError med input.invalid_argument vid ord efter step.
    """
    _need(args, (), "step")
    spectrum = measure(state)
    i = np.nanargmax(spectrum["values"])
    word = "bild" if state["settings"]["frames"] == 1 else "bilder"
    print(f"Topp {spectrum["values"][i]:g} vid {spectrum["x_label"]} {spectrum["x"][i]:g} ({state["settings"]["frames"]} {word})")
    crop = state["image"]
    if state["settings"]["roi"] is not None:
        crop = state["image"][state["settings"]["roi"][1]:state["settings"]["roi"][1] + state["settings"]["roi"][3], state["settings"]["roi"][0]:state["settings"]["roi"][0] + state["settings"]["roi"][2]]
    if crop.max() >= 255:
        print("Varning: mättad (255 i råbilden). Sänk exponeringen.")
    if state["mode"] == "transmission":
        if np.any(spectrum["values"][spectrum["mask"]] > 1):
            over = np.count_nonzero(spectrum["values"][spectrum["mask"]] > 1)
            unit = "position" if over == 1 else "positioner"
            print(f"Varning: transmission över 100 % på {over} {unit}")



def cmd_save(state, args):
    """Kommandot save [DIR]: sparar senaste mätningen i en ny mätmapp.

    Parametrar: state: programmets state; args: inga ord (output_dir) eller en föräldramapp.
    Returnerar: None
    Fel: ValueError med input.invalid_argument vid fler än ett ord och input.missing_data om ingen mätning finns;
    OSError om något inte går att skriva.
    """
    if len(args) > 1:
        raise ValueError("input.invalid_argument: save tar högst ett ord (DIR)")
    if state["spectrum"] is None:
        raise ValueError("input.missing_data: Ingen mätning än. Kör step först.")
    parent = args[0] if args else state["settings"]["output_dir"]
    saved = state["settings"].copy()
    saved["coefficients"] = state["coefficients"].tolist() if state["coefficients"] is not None else None
    saved["dark"] = state["dark"] is not None
    saved["use_response"] = state["use_response"]
    saved["mode"] = state["mode"]
    folder = files.save_measurement(parent, state["spectrum"], state["image"], saved)
    print(f"Sparad i {folder.as_posix()}")



def cmd_start(state, args):
    """Kommandot start: visar spektrumet live tills Ctrl+C eller tills fönstret stängs.

    Parametrar: state: programmets state; args: orden efter kommandot, inga.
    Returnerar: None
    Fel: samma som measure; källan och fönstret stängs alltid i finally.
    """
    _need(args, (), "start")
    print("Live. Tryck Ctrl+C eller stäng fönstret för att stoppa.")
    kind, value = state["settings"]["source"]
    src = None
    win = None
    try:
        src = source.open_source(kind, value)
        win = plot.open_plot()
        while True:
            if not plt.fignum_exists(win["fig"].number):
                print("live stoppad")
                break
            spectrum = measure(state, src)
            plot.draw(win, spectrum["x"], np.where(spectrum["mask"], spectrum["values"], np.nan), spectrum["x_label"], spectrum["y_label"])
            plt.pause(0.05)
    except KeyboardInterrupt:
        print("live stoppad")
    finally:
        if src is not None:
            source.close_source(src)
        if win is not None:
            plt.close(win["fig"])


def cmd_calibrate(state, args):
    """Kommandot calibrate PATH [DEGREE]: anpassar våglängden till en punktfil och prövar den mot kontrollpunkterna.

    Parametrar: state: programmets state; args: punktfilens sökväg och valfritt graden 1 eller 2.
    Returnerar: None
    Fel: ValueError med input.invalid_argument vid fel ord, fel i punktfilen, för få punkter eller en linje som inte
    är monoton i det giltiga intervallet; OSError om filen saknas. Den gamla kalibreringen står då kvar.
    """
    if not args:
        _need(args, ("PATH",), "calibrate")  # kommatecknet är obligatoriskt
    if len(args) > 2:
        raise ValueError("input.invalid_argument: calibrate tar högst två ord (PATH DEGREE)")
    if len(args) == 2:
        degree = _to_int("DEGREE", args[1], 1)
    else:
        degree = 1
    pixels, wavelengths, is_check = files.load_points(args[0])
    fit_pixels = pixels[~is_check]
    check_pixels = pixels[is_check]
    fit_wavelengths = wavelengths[~is_check]
    check_wavelengths = wavelengths[is_check]
    coefficients = calc.fit_wavelength(fit_pixels, fit_wavelengths, degree)  # bara anpassningspunkter
    print(f"a0: {coefficients[0]:g}")
    print(f"a1: {coefficients[1]:g}")
    if degree == 2:
        print(f"a2: {coefficients[2]:g}")
    width = np.max(fit_pixels) - np.min(fit_pixels)
    valid_range = (max(np.min(fit_pixels) - width, 0), np.max(fit_pixels) + width)
    print(f"anpassat: pixel {np.min(fit_pixels):g} till {np.max(fit_pixels):g}")
    print(f"giltigt: pixel {valid_range[0]:g} till {valid_range[1]:g}")
    # Linjen måste vara monoton i det giltiga intervallet, annars får två pixlar samma våglängd.
    test_pixels = np.arange(valid_range[0], valid_range[1] + 1, dtype=np.float64)
    diffs = np.diff(calc.evaluate_wavelength(test_pixels, coefficients))
    if not (np.all(diffs > 0) or np.all(diffs < 0)):
        raise ValueError(
            f"input.invalid_argument: inte monoton mellan pixel {valid_range[0]:g} och {valid_range[1]:g}"
        )
    residuals = fit_wavelengths - calc.evaluate_wavelength(fit_pixels, coefficients)
    for residual in residuals:
        print(f"residual: {residual:g}")
    check_errors = check_wavelengths - calc.evaluate_wavelength(check_pixels, coefficients)
    # Lokalt steg: hur många nm en pixel är vid kontrollpunkten.
    step = np.abs(calc.evaluate_wavelength(check_pixels + 1, coefficients) - calc.evaluate_wavelength(check_pixels, coefficients))
    # varna när abs(fel) är större än steget
    for pixel, error, s in zip(check_pixels, check_errors, step):
        print(f"kontrollfel vid pixel {pixel:g}: {error:g}")
        if abs(error) > s:
            print(f"Varning: kontrollfelet {error:g} nm är större än steget {s:g} nm.")
    if check_pixels.size == 0:
        print("inte kontrollerad: inga kontrollpunkter i filen")
    state["coefficients"] = coefficients
    low, high = valid_range  # packa upp först
    state["pixel_range"] = (low, high)
    state["spectrum"] = None

def cmd_dark(state, args):
    """Kommandot dark [N]: mäter mörkret som medel av N bilder med blockerad ljusväg.

    Parametrar: state: programmets state; args: inga ord (CAPTURE_FRAMES bilder) eller ett heltal N, minst 1.
    Returnerar: None
    Fel: ValueError med input.invalid_argument vid fel ord, RuntimeError från källan. Det gamla mörkret står då kvar.
    """
    if len(args) > 1:
        raise ValueError("input.invalid_argument: dark tar högst ett ord (N)")
    if args:
        N = _to_int("N", args[0], 1)
    else:
        N = CAPTURE_FRAMES
    kind, value = state["settings"]["source"]
    src = source.open_source(kind, value)
    flat = []
    try:
        for _ in range(N):
            frame = source.read_frame(src).astype(np.float64)
            shape = frame.shape
            flat.append(frame.reshape(-1))
    finally:
        source.close_source(src)
    stacked = np.stack(flat)
    # Mörkret är medlet av N bilder, pixel för pixel och kanal för kanal. Se rev7, RX03.
    mean_image, _spread = calc.average_spectra(stacked)
    state["dark"] = mean_image.reshape(shape)
    state["spectrum"] = None
    word = "bild" if N == 1 else "bilder"
    print(f"mörker: {N} {word}, medel {np.mean(state["dark"]):g}")
    if state["image"] is not None and np.mean(state["dark"]) >= 0.5 * np.mean(state["image"]):
        print("Varning: mörkret liknar bilden. Var ljusvägen blockerad?")
    if state["reference"] is not None:
    state["reference"] = None
    print("referensen togs bort: kör reference igen")


def cmd_response(state, args):
    """Kommandot response build KNOWNFILE, response on eller response off.

    Parametrar: state: programmets state; args: ["build", KNOWNFILE], ["on"] eller ["off"].
    Returnerar: None
    Fel: ValueError med input.invalid_argument vid fel ord och input.missing_data utan mörker, kalibrering eller respons;
    OSError om filen saknas.
    """
    if not args or args[0] not in ("build", "on", "off"):
        raise ValueError("input.invalid_argument: första ordet ska vara build, on eller off")
    if args[0] == "build":
        rest = args[1:]
        _need(rest, ("KNOWNFILE",), "response")
        if state["dark"] is None:
            raise ValueError("input.missing_data: inget mörker, kör dark först")
        if state["coefficients"] is None:
            raise ValueError("input.missing_data: ingen kalibrering, kör calibrate först")
        known_wavelengths, known_values = files.load_known(rest[0])
        lamp = _measure_direct(state, CAPTURE_FRAMES)
        lamp_values = np.where(lamp["mask"], lamp["values"], np.nan)
        response_values = calc.build_response(lamp["x"], lamp_values, known_wavelengths, known_values)
        state["response"] = {"x": lamp["x"].copy(), "values": response_values}
        state["spectrum"] = None
        print(f"respons: {np.count_nonzero(np.isfinite(state["response"]["values"]))} av {len(state["response"]["values"])} positioner giltiga")
    elif args[0] == "on":
        if state["response"] is None:
            raise ValueError("input.missing_data: ingen respons, kör response build först")
        state["use_response"] = True
        state["spectrum"] = None
        print("respons: on")
    elif args[0] == "off":
        state["use_response"] = False
        state["spectrum"] = None
        print("respons: off")

def cmd_reference(state, args):
    """Kommandot reference [N]: mäter referensen utan prov, utan respons och transmission, och sparar den med kanalen.

    Parametrar: state: programmets state; args: inga ord (CAPTURE_FRAMES bilder) eller ett heltal N, minst 1.
    Returnerar: None
    Fel: ValueError med input.invalid_argument vid fel ord och input.missing_data utan mörker; samma som measure.
    """
    if state["dark"] is None:
        raise ValueError("input.missing_data: inget mörker, kör dark först")
    if len(args) > 1:
        raise ValueError("input.invalid_argument: reference tar högst ett ord (N)")
    if args:
        N = _to_int("N", args[0], 1)
    else:
        N = CAPTURE_FRAMES
    spectrum = _measure_direct(state, N)
    spectrum["channel"] = state["settings"]["channel"]
    state["reference"] = spectrum
    state["spectrum"] = None
    word = "bild" if N == 1 else "bilder"
    print(f"Referens: {N} {word}, x från {spectrum["x"][0]:g} till {spectrum["x"][-1]:g}")

def cmd_mode(state, args):
    """Kommandot mode direct eller mode transmission.

    Parametrar: state: programmets state; args: ["direct"] eller ["transmission"].
    Returnerar: None
    Fel: ValueError med input.invalid_argument vid fel ord och input.missing_data för transmission utan referens.
    """
    if len(args) != 1 or args[0] not in ("direct", "transmission"):
        raise ValueError("input.invalid_argument: mode tar ett ord, direct eller transmission")
    if args[0] == "transmission" and state["reference"] is None:
        raise ValueError("input.missing_data: ingen referens, kör reference först")
    state["mode"] = args[0]
    state["spectrum"] = None
    print(f"mode: {args[0]}")

COMMANDS = {
    "help": (cmd_help, "Visa kommandona"),
    "quit": (cmd_quit, "Avsluta"),
    "show": (cmd_show, "Visa inställningarna"),
    "source": (cmd_source, "file PATH eller camera N"),
    "roi": (cmd_roi, "X Y W H i pixlar, eller full för hela bilden"),
    "channel": (cmd_channel, "gray, sum, red, green eller blue"),
    "axis": (cmd_axis, "horizontal eller vertical"),
    "frames": (cmd_frames, "N: bilder per mätning"),
    "step": (cmd_step, "mät och skriv toppen"),
    "save": (cmd_save, "[DIR]: spara senaste mätningen"),
    "start": (cmd_start, "live med kameran, Ctrl+C stoppar"),
    "calibrate": (cmd_calibrate, "PATH [DEGREE]: anpassa våglängd till en punktfil"),
    "reference": (cmd_reference, "[N]: mät referens utan prov"),
    "mode": (cmd_mode, "direct|transmission"),

}



def run_command(state, line):
    """Delar en rad i ord och anropar kommandot.

    Parametrar: state: programmets state; line: raden från prompten (str).
    Returnerar: svaret från kommandot: True från quit, annars None (också för en tom rad).
    Fel: ValueError med input.invalid_argument vid citattecken utan slut eller okänt kommando; kommandots egna fel.
    """
    try:
        words = shlex.split(line)
    except ValueError as error:
        raise ValueError("input.invalid_argument: citattecken saknar slut") from error
    if not words:
        return None  # tom rad: bara en ny prompt
    if words[0] not in COMMANDS:
        raise ValueError(f"input.invalid_argument: okänt kommando {words[0]}. Skriv help för en lista.")
    function, _help_text = COMMANDS[words[0]]
    return function(state, words[1:])


def run_file(state, path):
    """Mäter en bildfil en gång, som main gjorde i 0.3: skriver toppen, sparar mätningen och ritar spektrumet.

    Parametrar: state: programmets state; path: sökvägen till bildfilen (str).
    Returnerar: slutkoden, 0 om det gick och 1 vid ett fel (en rad Fel:).
    Fel: fångar ValueError, RuntimeError och OSError.
    """
    state["settings"]["source"] = ("file", path)
    try:
        spectrum = measure(state)
        i = np.argmax(spectrum["values"])
        print(f"Topp {spectrum["values"][i]:g} vid pixel {spectrum["x"][i]:g}")

        folder = files.save_measurement(state["settings"]["output_dir"], spectrum, state["image"], state["settings"])
        print(f"Sparad i {folder.as_posix()}")

        win = plot.open_plot()
        plot.draw(win, spectrum["x"], np.where(spectrum["mask"], spectrum["values"], np.nan), spectrum["x_label"], spectrum["y_label"])
        plt.show(block=True)

    except (ValueError, RuntimeError, OSError) as err:
        print(f"Fel: {err}")
        return 1
    return 0


def main():
    """Kör prompten spektro> tills quit, Ctrl+D eller Ctrl+C vid prompten; ett fel blir en rad Fel:.

    Med en sökväg efter kommandot mäts bara den bildfilen en gång, som i 0.3 (run_file).
    Parametrar: inga (sökvägen läses av argparse).
    Returnerar: None för prompten (sys.exit ger då koden 0), annars slutkoden från run_file.
    Fel: fångar ValueError, RuntimeError och OSError per rad, och KeyboardInterrupt under ett kommando (Avbrutet.).
    """
    parser = argparse.ArgumentParser(prog="python -m spectrometer.main", description="Utan sökväg: prompten spektro>. Med sökväg: läser bildfilen, skriver toppen, sparar mätningen och ritar spektrumet.")
    parser.add_argument("path", nargs="?", help="sökvägen till en bildfil (utan den startar prompten)")
    args = parser.parse_args()

    state = new_state(DEFAULTS)
    if args.path is not None:
        return run_file(state, args.path)
    print("Skriv help för kommandona. quit eller Ctrl+D avslutar.")
    while True:
        try:
            line = input("spektro> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        try:
            answer = run_command(state, line)
            if answer:
                break
        except (ValueError, RuntimeError, OSError) as error:
            print(f"Fel: {error}")
        except KeyboardInterrupt:
            print("Avbrutet.")


if __name__ == "__main__":
    sys.exit(main())
