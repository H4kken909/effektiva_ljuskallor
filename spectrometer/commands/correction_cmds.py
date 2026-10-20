"""dark, response, reference och mode: korrektionerna och transmission."""

import numpy as np

from spectrometer import calc, files, measure, out, quality, registry, source


@registry.command("dark", "[N]: mät mörker med blockerad ljusväg")
def cmd_dark(state, args):
    """Kommandot dark [N]: mörkret som medel av N bilder (CAPTURE_FRAMES utan N). Det gamla står kvar vid fel."""
    if len(args) > 1:
        raise ValueError("input.invalid_argument: dark tar högst ett ord (N)")
    n = registry.to_int("N", args[0], 1) if args else measure.CAPTURE_FRAMES
    kind, value = state["settings"]["source"]
    src = source.open_source(kind, value)
    flat = []
    try:
        for _ in range(n):
            frame = source.read_frame(src).astype(np.float64)
            shape = frame.shape
            flat.append(frame.reshape(-1))
    finally:
        source.close_source(src)
    # Mörkret är medlet av N bilder, pixel för pixel och kanal för kanal. Se rev7, RX03.
    mean_image, _spread = calc.average_spectra(np.stack(flat))
    state["dark"] = mean_image.reshape(shape)
    state["spectrum"] = None
    word = "bild" if n == 1 else "bilder"
    out.say(f"mörker: {n} {word}, medel {np.mean(state['dark']):g}")
    if state["image"] is not None and np.mean(state["dark"]) >= 0.5 * np.mean(state["image"]):
        out.warn("mörkret liknar bilden. Var ljusvägen blockerad?")
    if state["reference"] is not None:
        # Referensen mättes med det gamla mörkret, så den gäller inte längre.
        state["reference"] = None
        out.say("referensen togs bort: kör reference igen")


@registry.command("response", "build KNOWNFILE | on | off")
def cmd_response(state, args):
    """Kommandot response build KNOWNFILE, response on eller response off."""
    if not args or args[0] not in ("build", "on", "off"):
        raise ValueError("input.invalid_argument: första ordet ska vara build, on eller off")
    if args[0] == "build":
        rest = args[1:]
        registry.need(rest, ("KNOWNFILE",), "response")
        if state["dark"] is None:
            raise ValueError("input.missing_data: inget mörker, kör dark först")
        if state["coefficients"] is None:
            raise ValueError("input.missing_data: ingen kalibrering, kör calibrate först")
        known_wavelengths, known_values = files.load_known(rest[0])
        lamp = measure.measure_direct(state, measure.CAPTURE_FRAMES)
        lamp_values = np.where(lamp["mask"], lamp["values"], np.nan)
        values = calc.build_response(lamp["x"], lamp_values, known_wavelengths, known_values)
        state["response"] = {"x": lamp["x"].copy(), "values": values}
        state["spectrum"] = None
        out.say(f"respons: {np.count_nonzero(np.isfinite(values))} av {len(values)} positioner giltiga")
        quality.warn_saturated(lamp["saturated_px"])
    elif args[0] == "on":
        if state["response"] is None:
            raise ValueError("input.missing_data: ingen respons, kör response build först")
        state["use_response"] = True
        state["spectrum"] = None
        out.say("respons: on")
    else:
        state["use_response"] = False
        state["spectrum"] = None
        out.say("respons: off")


@registry.command("reference", "[N]: mät referens utan prov")
def cmd_reference(state, args):
    """Kommandot reference [N]: referensen utan prov, utan respons och transmission, sparad med kanalen."""
    if state["dark"] is None:
        raise ValueError("input.missing_data: inget mörker, kör dark först")
    if len(args) > 1:
        raise ValueError("input.invalid_argument: reference tar högst ett ord (N)")
    n = registry.to_int("N", args[0], 1) if args else measure.CAPTURE_FRAMES
    spectrum = measure.measure_direct(state, n)
    spectrum["channel"] = state["settings"]["channel"]
    state["reference"] = spectrum
    state["spectrum"] = None
    word = "bild" if n == 1 else "bilder"
    out.say(f"Referens: {n} {word}, x från {spectrum['x'][0]:g} till {spectrum['x'][-1]:g}")
    quality.warn_saturated(spectrum["saturated_px"])


@registry.command("mode", "direct|transmission")
def cmd_mode(state, args):
    """Kommandot mode direct eller mode transmission (transmission kräver en referens)."""
    if len(args) != 1 or args[0] not in ("direct", "transmission"):
        raise ValueError("input.invalid_argument: mode tar ett ord, direct eller transmission")
    if args[0] == "transmission" and state["reference"] is None:
        raise ValueError("input.missing_data: ingen referens, kör reference först")
    state["mode"] = args[0]
    state["spectrum"] = None
    out.say(f"mode: {args[0]}")