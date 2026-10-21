"""rows och background: hur ROI:ns rader blir ett spektrum (medel eller median) och bakgrunden bredvid bandet."""

from spectrometer import calc, out, registry


def _set(state, key, value):
    """Sätter rows eller background och glömmer mätningen, responsen och referensen (de gjordes på det gamla sättet)."""
    state[key] = value
    state["spectrum"] = None
    if state["response"] is not None:
        state["response"] = None
        state["use_response"] = False
        out.say("Responsen glömd. Kör response build igen.")
    if state["reference"] is not None:
        state["reference"] = None
        out.say("Referensen glömd. Kör reference igen.")


@registry.command("rows", "mean|median: medel eller median över ROI:ns rader (rows ensam visar valet)",
                  "rows, rows mean eller rows median")
def cmd_rows(state, args):
    """Kommandot rows [mean|median]: medel (calc.extract_spectrum) eller median (calc.extract_median) över raderna.

    Valet står i state["rows"], inte i settings, så show är som förut; save skriver det i settings.json (extraction).
    Fel: ValueError med input.invalid_argument för ett annat ord än mean och median.
    """
    if not args:
        out.say(f"rows: {state['rows']}")
        return
    registry.need(args, ("mean|median",), "rows")
    if args[0] not in ("mean", "median"):
        raise ValueError(f"input.invalid_argument: rows: okänt val {args[0]}, välj mean eller median")
    _set(state, "rows", args[0])
    out.say(f"rows: {args[0]}")


@registry.command("background", "N|off: dra av bakgrunden ur N rader ovanför och under ROI:n (background ensam visar läget)",
                  "background, background N eller background off")
def cmd_background(state, args):
    """Kommandot background [N|off]: medianen av N rader på var sida om ROI:n dras av efter mörkret.

    Vid axis vertical är det N kolumner till vänster och höger (calc.side_background). ROI-21, ROI-22.
    Fel: ValueError med input.invalid_argument om N inte är ett heltal över 0 eller inte ryms bredvid ROI:n i bilden.
    """
    if not args:
        out.say(f"background: {'off' if state['background'] is None else state['background']}")
        return
    registry.need(args, ("N",), "background")
    if args[0] == "off":
        _set(state, "background", None)
        out.say("background: off")
        return
    n = registry.to_int("N", args[0], 1)
    image, cfg = state["image"], state["settings"]
    if image is not None:
        roi = calc.roi_or_whole(cfg["roi"], image)
        calc.side_background(image, roi, n, cfg["channel"], cfg["axis"])  # fel här om raderna inte ryms
    else:
        out.say("Bakgrunden kontrolleras vid nästa mätning.")
    _set(state, "background", n)
    out.say(f"background: {n}")
