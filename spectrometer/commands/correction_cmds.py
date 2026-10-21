"""dark, response, reference och mode: korrektionerna och transmission."""

import sys

import numpy as np

from spectrometer import calc, files, measure, out, quality, registry, session, source


def _ready(state, prompt):
    """Kamera i en terminal: väntar på Enter efter prompten. Ger False om svaret är avbryt (fil eller pipad: True)."""
    if state["settings"]["source"][0] != "camera" or not sys.stdin.isatty():
        return True
    try:
        answer = out.ask(prompt)
    except EOFError:
        return False
    return answer.strip().lower() != "avbryt"


def _roi_mean(state, image):
    """Medlet i ROI:n och den valda kanalen (hela bilden utan ROI), i counts."""
    cfg = state["settings"]
    roi = cfg["roi"] if cfg["roi"] is not None else (0, 0, image.shape[1], image.shape[0])
    return float(np.mean(calc.prepare(image, roi, cfg["axis"], cfg["channel"])))


@registry.command("dark", "[N]: mät mörker med blockerad ljusväg", "dark [N]")
def cmd_dark(state, args):
    """Kommandot dark [N]: mörkret som medel av N bilder (CAPTURE_FRAMES utan N). Det gamla står kvar vid fel."""
    if len(args) > 1:
        raise ValueError("input.invalid_argument: dark tar högst ett ord (N)")
    n = registry.to_frames(args[0]) if args else measure.CAPTURE_FRAMES
    if not _ready(state, "Blockera ljusvägen och tryck Enter (skriv avbryt för att hoppa över): "):
        out.say("Avbrutet.")
        return

    def total_of(s):
        # Löpande summa: en bild i minnet i stället för N. PRO-01.
        total = source.read_frame(s).astype(np.float64)
        for _ in out.progress(range(n - 1), "mörker"):
            total += source.read_frame(s)
        return total, source.describe(s)

    total, camera = measure._with_source(state, None, total_of)
    # Mörkret är medlet av N bilder, pixel för pixel och kanal för kanal. Se rev7, RX03.
    state["dark"] = total / n
    state["dark_frames"] = n
    session.mark_taken(state, "dark")
    state["dark_camera"] = camera
    state["spectrum"] = None
    word = "bild" if n == 1 else "bilder"
    out.say(f"mörker: {n} {word}, medel {out.fmt(np.mean(state['dark']))}")
    # Jämför i ROI:n och kanalen: bandet är en liten del av bilden, så hela bildens medel märker lite ljus. PRO-04.
    image = state["image"]
    if image is not None and image.shape == state["dark"].shape and (
        _roi_mean(state, state["dark"]) >= 0.5 * _roi_mean(state, image)
    ):
        out.warn("mörkret liknar bilden. Var ljusvägen blockerad?")
    if state["reference"] is not None:
        # Referensen mättes med det gamla mörkret, så den gäller inte längre.
        state["reference"] = None
        out.say("referensen togs bort: kör reference igen")
    if state["response"] is not None:
        # Lampmätningen i responsen drogs av med det gamla mörkret. PRO-15.
        out.warn("responsen byggdes med det gamla mörkret")


@registry.command("response", "build KNOWNFILE [N] | on | off | export PATH", "response build KNOWNFILE [N], response on, response off eller response export PATH")
def cmd_response(state, args):
    """Kommandot response build KNOWNFILE [N], response on, response off eller response export PATH."""
    if not args or args[0] not in ("build", "on", "off", "export"):
        raise ValueError("input.invalid_argument: första ordet ska vara build, on, off eller export")
    if args[0] == "build":
        rest = args[1:]
        if not rest:
            raise ValueError("input.invalid_argument: response: KNOWNFILE saknas")
        if len(rest) > 2:
            raise ValueError("input.invalid_argument: response build tar högst två ord (KNOWNFILE N)")
        n = registry.to_frames(rest[1]) if len(rest) == 2 else measure.CAPTURE_FRAMES
        if state["dark"] is None:
            raise ValueError("input.missing_data: inget mörker, kör dark först")
        if state["coefficients"] is None:
            raise ValueError("input.missing_data: ingen kalibrering, kör calibrate först")
        known_wavelengths, known_values = files.load_known(rest[0])
        lamp = measure.measure_direct(state, n)
        lamp_values = np.where(lamp["mask"], lamp["values"], np.nan)
        values = calc.build_response(lamp["x"], lamp_values, known_wavelengths, known_values)
        state["response"] = {"x": lamp["x"].copy(), "values": values, "frames": n, "known_file": rest[0]}
        session.mark_taken(state, "response")
        state["spectrum"] = None
        out.say(f"respons: {np.count_nonzero(np.isfinite(values))} av {len(values)} positioner giltiga")
        # Under 0,1 förstärks bruset mer än 10 gånger; min_response (0,01) släpper igenom 100 gånger. PRO-31.
        weak = np.count_nonzero((values > state["settings"]["min_response"]) & (values < 0.1))
        if weak:
            unit = "position har" if weak == 1 else "positioner har"
            out.warn(f"{weak} {unit} respons under 0.1 (bruset förstärks mer än 10 gånger)")
        quality.warn_saturated(lamp["saturated_px"])
    elif args[0] == "export":
        registry.need(args[1:], ("PATH",), "response export")
        if state["response"] is None:
            raise ValueError("input.missing_data: ingen respons, kör response build först")
        files.save_response(args[1], state["response"]["x"], state["response"]["values"])
        out.say(f"respons: sparad i {args[1]}")
    elif args[0] == "on":
        if state["response"] is None:
            raise ValueError("input.missing_data: ingen respons, kör response build först")
        state["use_response"] = True
        state["spectrum"] = None
        if state["mode"] == "transmission":
            out.say("respons: on (används inte i mode transmission)")
        else:
            out.say("respons: on")
    else:
        state["use_response"] = False
        state["spectrum"] = None
        out.say("respons: off")


def _check_reference(state, args):
    """reference check [N]: mäter referensen igen utan att byta den och skriver största relativa skillnaden (drift)."""
    reference = state["reference"]
    if reference is None:
        raise ValueError("input.missing_data: ingen referens, kör reference först")
    if len(args) > 1:
        raise ValueError("input.invalid_argument: reference check tar högst ett ord (N)")
    n = registry.to_frames(args[0]) if args else measure.CAPTURE_FRAMES
    if not _ready(state, "Ta bort provet och tryck Enter: "):
        out.say("Avbrutet.")
        return
    again = measure.measure_direct(state, n)
    if not np.array_equal(again["x"], reference["x"]) or state["settings"]["channel"] != reference["channel"]:
        raise ValueError("input.invalid_argument: x-axeln eller kanalen skiljer sig från referensens, kör reference igen")
    valid = reference["mask"] & again["mask"] & (reference["values"] > state["settings"]["min_reference"])
    if not np.any(valid):
        raise ValueError("input.missing_data: ingen position i referensen över min_reference")
    change = np.full(len(valid), -1.0)  # -1 där referensen är för svag, så att argmax hamnar på en giltig plats
    np.divide(np.abs(again["values"] - reference["values"]), reference["values"], out=change, where=valid)
    j = int(np.argmax(change))
    word = "bild" if n == 1 else "bilder"
    where = f"{again['x_label']} {again['x'][j]:g}"
    out.say(f"Referenskontroll: största skillnad {100 * change[j]:.1f} % vid {where} ({n} {word})")


@registry.command("reference", "[N] | check [N]: mät referens utan prov, eller jämför med den sparade", "reference [N] eller reference check [N]")
def cmd_reference(state, args):
    """Kommandot reference [N]: referensen utan prov, utan respons och transmission, sparad med kanalen.

    reference check [N] mäter igen och jämför med den sparade, utan att byta den (_check_reference).
    """
    if args[:1] == ["check"]:
        _check_reference(state, args[1:])
        return
    if state["dark"] is None:
        raise ValueError("input.missing_data: inget mörker, kör dark först")
    if len(args) > 1:
        raise ValueError("input.invalid_argument: reference tar högst ett ord (N)")
    n = registry.to_frames(args[0]) if args else measure.CAPTURE_FRAMES
    if not _ready(state, "Ta bort provet och tryck Enter: "):
        out.say("Avbrutet.")
        return
    spectrum = measure.measure_direct(state, n)
    spectrum["channel"] = state["settings"]["channel"]
    spectrum["frames"] = n  # till profiles i settings.json
    state["reference"] = spectrum
    session.mark_taken(state, "reference")
    state["spectrum"] = None
    word = "bild" if n == 1 else "bilder"
    valid = spectrum["mask"] & (spectrum["values"] > state["settings"]["min_reference"])
    peak = np.max(spectrum["values"][spectrum["mask"]]) if np.any(spectrum["mask"]) else np.nan
    out.say(
        f"Referens: {n} {word}, x från {spectrum['x'][0]:g} till {spectrum['x'][-1]:g}, "
        f"topp {peak:g}, {np.count_nonzero(~valid)} av {len(valid)} under min_reference"
    )
    if not np.any(valid):
        out.warn("alla positioner under min_reference, referensen är oanvändbar")
    quality.warn_saturated(spectrum["saturated_px"])


@registry.command("mode", "direct|transmission", "mode direct eller mode transmission")
def cmd_mode(state, args):
    """Kommandot mode direct eller mode transmission (transmission kräver en referens)."""
    if len(args) != 1 or args[0] not in ("direct", "transmission"):
        raise ValueError("input.invalid_argument: mode tar ett ord, direct eller transmission")
    if args[0] == "transmission" and state["reference"] is None:
        raise ValueError("input.missing_data: ingen referens, kör reference först")
    state["mode"] = args[0]
    state["spectrum"] = None
    out.say(f"mode: {args[0]}")
